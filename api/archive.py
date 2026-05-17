import io
import sys
import zipfile


def extract_xml_from_zip(zip_bytes):
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        xml_files = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        if not xml_files:
            print("No XML file found in the archive.", file=sys.stderr)
            sys.exit(1)

        xml_name = xml_files[0]
        if len(xml_files) > 1:
            pfa2 = [n for n in xml_files if "PFA2" in n or "pfa2" in n]
            if pfa2:
                xml_name = pfa2[0]

        print("  Extracting %s from archive ..." % xml_name)
        xml_content = zf.read(xml_name).decode("utf-8")
        return xml_name, xml_content
