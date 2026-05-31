import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from dj_sanctions_analysis.api import (
    list_remote_files,
    download_file,
    classify_files,
    extract_date_from_filename,
    extract_xml_from_zip_to_disk,
)
from dj_sanctions_analysis.parsers.transform import transform_xml_file_to_dict, transform_xml_file_to_jsonl
from dj_sanctions_analysis.streaming import merge_jsonl_with_deltas
from dj_sanctions_analysis.writer import write_json


def _save_zip(data, filename, data_dir):
    path = data_dir / filename
    with open(path, "wb") as f:
        f.write(data)
    print("  Saved %s (%.1f MB)" % (path, len(data) / (1024 * 1024)))
    return path


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


def _run_full(args):
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    files = list_remote_files(args.auth)
    classified = classify_files(files)

    if not classified["full"]:
        print("No full (_f) file found on the DJ feed.", file=sys.stderr)
        sys.exit(1)

    latest_full = classified["full"][-1]
    full_date = extract_date_from_filename(latest_full)

    all_deltas = sorted(
        classified["daily"] + classified["incremental"],
        key=extract_date_from_filename,
    )
    deltas_after_full = [f for f in all_deltas if extract_date_from_filename(f) > full_date]
    all_files = [latest_full] + deltas_after_full

    _download_extract_merge(all_files, args.auth, outdir)


def _run_daily(args):
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    files = list_remote_files(args.auth)
    classified = classify_files(files)

    all_files = sorted(
        classified["daily"] + classified["incremental"],
        key=extract_date_from_filename,
    )

    if not all_files:
        print("No daily/incremental files found on the DJ feed.", file=sys.stderr)
        sys.exit(1)

    _download_extract_merge(all_files, args.auth, outdir)


def _run_today(args):
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    files = list_remote_files(args.auth)
    classified = classify_files(files)

    today_str = date.today().strftime("%Y%m%d")
    yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y%m%d")

    all_candidates = sorted(
        classified["full"] + classified["daily"] + classified["incremental"],
        key=extract_date_from_filename,
    )

    today_files = [
        f for f in all_candidates
        if extract_date_from_filename(f).startswith(today_str)
    ]

    if today_files:
        target_date = today_str
        target_files = today_files
    else:
        target_files = [
            f for f in all_candidates
            if extract_date_from_filename(f).startswith(yesterday_str)
        ]
        target_date = yesterday_str

    if not target_files:
        print(
            "No files found for today (%s) or yesterday (%s) on the DJ feed."
            % (today_str, yesterday_str),
            file=sys.stderr,
        )
        sys.exit(1)

    print("\nFound %d file(s) for %s:" % (len(target_files), target_date))
    for f in target_files:
        print("  %s" % f)

    _download_extract_merge(target_files, args.auth, outdir)


def _download_extract_merge(all_files, auth_b64, outdir):
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
        existing = data_dir / filename
        if existing.exists():
            print("[%d/%d] Already exists: %s" % (i, total, existing))
            saved_paths.append(existing)
            continue
        print("[%d/%d] %s" % (i, total, filename))
        raw_data = download_file(filename, auth_b64)
        path = _save_zip(raw_data, filename, data_dir)
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
    merge_jsonl_with_deltas(jsonl_dir, delta_dicts, out_path)

    rec_line_count = 0
    rec_jsonl = jsonl_dir / "record.jsonl"
    if rec_jsonl.exists():
        with open(rec_jsonl) as f:
            for _ in f:
                rec_line_count += 1

    print("\n%s" % sep)
    print("  Complete: ~%d base records from %d file(s)" % (rec_line_count, total))
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
    mode.add_argument("--full", action="store_true", help="Download latest full snapshot + all deltas after it")
    mode.add_argument("--daily", action="store_true", help="Download only daily/incremental files (no full snapshot)")
    mode.add_argument("--today", action="store_true", help="Download and parse today's file(s), falls back to yesterday if none found")

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
