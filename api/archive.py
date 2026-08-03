import os
import shutil
import sys
import zipfile
from pathlib import Path

EXTRACT_CHUNK_SIZE = 4 * 1024 * 1024


def _discard(path):
    try:
        Path(path).unlink()
    except OSError:
        pass


def extract_xml_from_zip_to_disk(zip_path, output_dir):
    zip_path = Path(zip_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        zf = zipfile.ZipFile(str(zip_path))
    except (zipfile.BadZipFile, OSError) as e:
        print(
            "Cannot open %s: %s\nDelete it and re-run to download a fresh copy."
            % (zip_path, e),
            file=sys.stderr,
        )
        sys.exit(1)

    with zf:
        xml_files = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        if not xml_files:
            print("No XML file found in %s" % zip_path, file=sys.stderr)
            sys.exit(1)

        xml_name = xml_files[0]
        if len(xml_files) > 1:
            pfa2 = [n for n in xml_files if "PFA2" in n or "pfa2" in n]
            if pfa2:
                xml_name = pfa2[0]

        expected = zf.getinfo(xml_name).file_size
        out_path = output_dir / Path(xml_name).name

        if out_path.exists():
            actual = out_path.stat().st_size
            if actual == expected:
                print("  XML already extracted: %s (%.1f MB)" % (out_path, actual / (1024 * 1024)))
                return out_path
            print(
                "  WARN: cached %s is %d bytes but the archive says %d - "
                "re-extracting truncated file" % (out_path.name, actual, expected),
                file=sys.stderr,
            )
            _discard(out_path)

        free = shutil.disk_usage(str(output_dir)).free
        if free < expected:
            print(
                "Not enough free space in %s: need %.1f GB, have %.1f GB."
                % (output_dir, expected / (1024 ** 3), free / (1024 ** 3)),
                file=sys.stderr,
            )
            sys.exit(1)

        part_path = out_path.with_name(out_path.name + ".part")
        print("  Extracting %s -> %s (%.1f MB) ..." % (xml_name, out_path, expected / (1024 * 1024)))

        try:
            with zf.open(xml_name) as src, open(part_path, "wb") as dst:
                while True:
                    chunk = src.read(EXTRACT_CHUNK_SIZE)
                    if not chunk:
                        break
                    dst.write(chunk)
                dst.flush()
                os.fsync(dst.fileno())
        except (zipfile.BadZipFile, EOFError, OSError) as e:
            _discard(part_path)
            print("Failed to extract %s from %s: %s" % (xml_name, zip_path, e), file=sys.stderr)
            sys.exit(1)

        actual = part_path.stat().st_size
        if actual != expected:
            _discard(part_path)
            print(
                "Incomplete extraction of %s: wrote %d bytes, expected %d."
                % (xml_name, actual, expected),
                file=sys.stderr,
            )
            sys.exit(1)

        part_path.replace(out_path)
        print("  Extracted %.1f MB" % (actual / (1024 * 1024)))
        return out_path
