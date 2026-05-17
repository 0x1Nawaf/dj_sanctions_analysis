import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from dj_sanctions.api import (
    list_remote_files,
    download_file,
    classify_files,
    extract_date_from_filename,
    extract_xml_from_zip,
)
from dj_sanctions.parsers import transform_xml_to_dict
from dj_sanctions.merger import merge_delta_into
from dj_sanctions.writer import write_json


def _save_zip(data, filename, data_dir):
    path = data_dir / filename
    with open(path, "wb") as f:
        f.write(data)
    print("  Saved %s (%.1f MB)" % (path, len(data) / (1024 * 1024)))
    return path


def _extract_and_parse(zip_path):
    with open(zip_path, "rb") as f:
        zip_bytes = f.read()

    filename = zip_path.name
    if filename.lower().endswith(".zip"):
        xml_name, xml_content = extract_xml_from_zip(zip_bytes)
    else:
        xml_name = filename
        xml_content = zip_bytes.decode("utf-8")

    print("  Parsing %s ..." % xml_name)
    root = ET.fromstring(xml_content)
    return transform_xml_to_dict(root)


def _run_local(args):
    xml_path = Path(args.local)
    if not xml_path.exists():
        print("File not found: %s" % xml_path, file=sys.stderr)
        sys.exit(1)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print("Parsing %s ..." % xml_path)
    root = ET.parse(str(xml_path)).getroot()
    output = transform_xml_to_dict(root)

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


def _download_extract_merge(all_files, auth_b64, outdir):
    data_dir = outdir / "pfa_data"
    data_dir.mkdir(parents=True, exist_ok=True)

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
    print("  Phase 2: Extracting and parsing %d file(s)" % total)
    print("%s\n" % sep)

    print("[1/%d] Base: %s" % (total, saved_paths[0].name))
    merged = _extract_and_parse(saved_paths[0])

    for i, path in enumerate(saved_paths[1:], start=2):
        print("\n[%d/%d] Delta: %s" % (i, total, path.name))
        delta = _extract_and_parse(path)
        merge_delta_into(merged, delta)

    rec_count = len(merged.get("record", []))
    print("\n%s" % sep)
    print("  Merge complete: %d records from %d file(s)" % (rec_count, total))
    print("%s\n" % sep)

    out_path = outdir / "sanctions_seeder.json"
    write_json(merged, out_path)


def main():
    parser = argparse.ArgumentParser(
        prog="dj_sanctions",
        description="Download and parse Dow Jones PFA sanctions XML into normalized JSON.",
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--local", metavar="FILE", help="Parse a local XML file")
    source.add_argument("--auth", metavar="BASE64", help="DJ API Basic auth credentials (base64)")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list", action="store_true", help="List available files and exit")
    mode.add_argument("--full", action="store_true", help="Download latest full snapshot + all deltas after it")
    mode.add_argument("--daily", action="store_true", help="Download only daily/incremental files (no full snapshot)")

    parser.add_argument("--outdir", metavar="DIR", default=".", help="Output directory (default: current dir)")

    args = parser.parse_args()

    if args.local:
        _run_local(args)
    elif args.list:
        _run_list(args)
    elif args.daily:
        _run_daily(args)
    else:
        _run_full(args)
