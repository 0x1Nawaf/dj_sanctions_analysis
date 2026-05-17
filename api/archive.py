import sys
import zipfile
from pathlib import Path


def extract_xml_from_zip_to_disk(zip_path, output_dir):
    zip_path = Path(zip_path)
    output_dir = Path(output_dir)

    with zipfile.ZipFile(str(zip_path)) as zf:
        xml_files = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        if not xml_files:
            print("No XML file found in %s" % zip_path, file=sys.stderr)
            sys.exit(1)

        xml_name = xml_files[0]
        if len(xml_files) > 1:
            pfa2 = [n for n in xml_files if "PFA2" in n or "pfa2" in n]
            if pfa2:
                xml_name = pfa2[0]

        out_name = Path(xml_name).name
        out_path = output_dir / out_name

        if out_path.exists():
            print("  XML already extracted: %s" % out_path)
            return out_path

        print("  Extracting %s -> %s ..." % (xml_name, out_path))
        with zf.open(xml_name) as src, open(out_path, "wb") as dst:
            while True:
                chunk = src.read(4 * 1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)

        size_mb = out_path.stat().st_size / (1024 * 1024)
        print("  Extracted %.1f MB" % size_mb)
        return out_path
