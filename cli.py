import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from dj_sanctions_analysis.api import (
    list_remote_files,
    download_file_to_path,
    is_complete_zip,
    classify_files,
    extract_date_from_filename,
    extract_xml_from_zip_to_disk,
)
from dj_sanctions_analysis.parsers.transform import transform_xml_file_to_dict, transform_xml_file_to_jsonl
from dj_sanctions_analysis.streaming import merge_jsonl_with_deltas
from dj_sanctions_analysis.writer import write_json


def _fetch_zip(filename, auth_b64, data_dir):
    """Return a local, verified copy of a feed file, downloading it if needed."""
    path = data_dir / filename
    if path.exists():
        if is_complete_zip(path):
            return path, True
        print(
            "  WARN: cached %s is truncated or corrupt - re-downloading" % filename,
            file=sys.stderr,
        )
        path.unlink()
    return download_file_to_path(filename, auth_b64, path), False


def _extract_xml(zip_path, xml_dir):
    filename = zip_path.name
    if filename.lower().endswith(".zip"):
        return extract_xml_from_zip_to_disk(zip_path, xml_dir)
    return zip_path


def _run_local(args):
    xml_path = Path(args.local)
    if not xml_path.exists():
        print("File not found: %s" % xml_path, file=sys.stderr)
        sys.exit(1)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print("Parsing %s ..." % xml_path)
    output = transform_xml_file_to_dict(xml_path)
    meta = output.setdefault("_meta", {})
    meta["feed_scope"] = "complete"
    meta["record_count"] = len(output.get("record", []))

    out_path = outdir / "sanctions_seeder.json"
    write_json(output, out_path)


def _run_list(args):
    files = list_remote_files(args.auth)
    classified = classify_files(files)

    print("\nAvailable files (%d):" % len(files))
    print("\n  Full files (%d):" % len(classified["full"]))
    for f in classified["full"]:
        print("    %s" % f)
    print("\n  Incremental files (%d):" % len(classified["incremental"]))
    for f in classified["incremental"]:
        print("    %s" % f)
    print("\n  Daily files (%d):" % len(classified["daily"]))
    for f in classified["daily"]:
        print("    %s" % f)


def _resolve_full_base(classified, data_dir, auth_b64):
    """Ensure the latest full snapshot zip is available locally."""
    data_dir.mkdir(parents=True, exist_ok=True)

    if classified["full"]:
        latest_full = classified["full"][-1]
        path, _ = _fetch_zip(latest_full, auth_b64, data_dir)
        return path

    cached = sorted(data_dir.glob("*_f.zip"))
    if cached:
        print(
            "WARN: No full file on remote feed; using cached %s"
            % cached[-1].name,
            file=sys.stderr,
        )
        return cached[-1]

    print(
        "No full snapshot (_f.zip) found on the DJ feed or in %s."
        % data_dir,
        file=sys.stderr,
    )
    sys.exit(1)


def _run_full(args):
    """Full snapshot only (_f). Monthly re-baseline; produces a complete feed."""
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    data_dir = outdir / "pfa_data"

    files = list_remote_files(args.auth)
    classified = classify_files(files)

    full_base = _resolve_full_base(classified, data_dir, args.auth)
    print("\nUsing full snapshot: %s" % full_base.name)

    _download_extract_merge([full_base.name], args.auth, outdir, feed_scope="complete")


def _run_daily(args):
    """Daily files only (_d). Produces a delta-only feed."""
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    files = list_remote_files(args.auth)
    classified = classify_files(files)

    delta_files = sorted(classified["daily"], key=extract_date_from_filename)

    if not delta_files:
        print("No daily (_d) files found on the DJ feed.", file=sys.stderr)
        sys.exit(1)

    print("\nFound %d daily file(s):" % len(delta_files))
    for f in delta_files:
        print("  %s" % f)

    _download_extract_merge(delta_files, args.auth, outdir, feed_scope="delta_only")


def _run_today(args):
    """Today's daily file(s) only (_d), falling back to yesterday."""
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    files = list_remote_files(args.auth)
    classified = classify_files(files)

    today_str = date.today().strftime("%Y%m%d")
    yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y%m%d")

    all_candidates = sorted(classified["daily"], key=extract_date_from_filename)

    target_files = [
        f for f in all_candidates
        if extract_date_from_filename(f).startswith(today_str)
    ]
    target_date = today_str

    if not target_files:
        target_files = [
            f for f in all_candidates
            if extract_date_from_filename(f).startswith(yesterday_str)
        ]
        target_date = yesterday_str

    if not target_files:
        print(
            "No daily (_d) files found for today (%s) or yesterday (%s) on the DJ feed."
            % (today_str, yesterday_str),
            file=sys.stderr,
        )
        sys.exit(1)

    print("\nFound %d daily file(s) for %s:" % (len(target_files), target_date))
    for f in target_files:
        print("  %s" % f)

    _download_extract_merge(target_files, args.auth, outdir, feed_scope="delta_only")


def _download_extract_merge(all_files, auth_b64, outdir, feed_scope="complete"):
    data_dir = outdir / "pfa_data"
    xml_dir = outdir / "pfa_data" / "xml"
    jsonl_dir = outdir / "pfa_data" / "jsonl"
    data_dir.mkdir(parents=True, exist_ok=True)
    xml_dir.mkdir(parents=True, exist_ok=True)
    jsonl_dir.mkdir(parents=True, exist_ok=True)

    sep = "=" * 60
    total = len(all_files)

    print("\n%s" % sep)
    print("  Phase 1: Downloading %d file(s) to %s" % (total, data_dir))
    print("%s\n" % sep)

    saved_paths = []
    for i, filename in enumerate(all_files, start=1):
        print("[%d/%d] %s" % (i, total, filename))
        path, cached = _fetch_zip(filename, auth_b64, data_dir)
        if cached:
            print("  Already downloaded: %s" % path)
        saved_paths.append(path)

    print("\n%s" % sep)
    print("  Phase 2: Parsing base file (streaming to JSONL)")
    print("%s\n" % sep)

    print("[1/%d] Base: %s" % (total, saved_paths[0].name))
    base_xml = _extract_xml(saved_paths[0], xml_dir)
    transform_xml_file_to_jsonl(base_xml, jsonl_dir)

    delta_dicts = []
    if total > 1:
        print("\n%s" % sep)
        print("  Phase 3: Parsing %d delta file(s) (in memory)" % (total - 1))
        print("%s\n" % sep)

        for i, path in enumerate(saved_paths[1:], start=2):
            print("[%d/%d] Delta: %s" % (i, total, path.name))
            delta_xml = _extract_xml(path, xml_dir)
            delta = transform_xml_file_to_dict(delta_xml)
            delta_dicts.append(delta)

    print("\n%s" % sep)
    print("  Phase 4: Merging and writing final JSON")
    print("%s\n" % sep)

    out_path = outdir / "sanctions_seeder.json"
    record_count = merge_jsonl_with_deltas(jsonl_dir, delta_dicts, out_path, feed_scope=feed_scope)

    print("\n%s" % sep)
    print(
        "  Complete: %d records merged from %d file(s) (feed_scope=%s)"
        % (record_count, total, feed_scope)
    )
    print("  Output: %s" % out_path)
    print("%s" % sep)


def main():
    parser = argparse.ArgumentParser(
        prog="dj_sanctions_analysis",
        description="Download and parse Dow Jones PFA sanctions XML into normalized JSON.",
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--local", metavar="FILE", help="Parse a local XML file")
    source.add_argument("--auth", metavar="BASE64", help="DJ API Basic auth credentials (base64)")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list", action="store_true", help="List available files and exit")
    mode.add_argument(
        "--full",
        action="store_true",
        help="Latest full snapshot (_f) only - complete feed, run monthly",
    )
    mode.add_argument(
        "--daily",
        action="store_true",
        help="All daily files (_d) only - delta-only feed",
    )
    mode.add_argument(
        "--today",
        action="store_true",
        help="Today's daily file(s) (_d) only, falling back to yesterday - delta-only feed",
    )

    parser.add_argument("--outdir", metavar="DIR", default=".", help="Output directory (default: current dir)")

    args = parser.parse_args()

    if args.local:
        _run_local(args)
    elif args.list:
        _run_list(args)
    elif args.today:
        _run_today(args)
    elif args.daily:
        _run_daily(args)
    else:
        _run_full(args)
