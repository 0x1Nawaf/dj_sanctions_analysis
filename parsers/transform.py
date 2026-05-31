import json
import xml.etree.ElementTree as ET
from pathlib import Path

from dj_sanctions_analysis.parsers.references import TAG_TO_KEY, parse_single_reference
from dj_sanctions_analysis.parsers.records import parse_single_record
from dj_sanctions_analysis.parsers.associations import parse_association_group

REFERENCE_TAGS = frozenset(TAG_TO_KEY.keys())
RECORD_TAGS = frozenset(("Person", "Entity"))


def transform_xml_file_to_dict(xml_path):
    pfa_meta = {}
    ref_tables = {}
    record_tables = {
        "record": [], "record_name": [], "record_description": [],
        "record_role": [], "record_date": [], "record_birth_place": [],
        "record_sanctions_ref": [], "record_country": [], "record_id_number": [],
        "record_source": [], "record_image": [], "record_address": [],
    }
    associations = []
    rec_count = 0

    for event, elem in ET.iterparse(str(xml_path), events=("start", "end")):

        if event == "start" and elem.tag == "PFA":
            pfa_meta = {"date": elem.attrib.get("date"), "type": elem.attrib.get("type")}
            print("  PFA date=%s  type=%s" % (pfa_meta.get("date"), pfa_meta.get("type")))
            continue

        if event != "end":
            continue

        if elem.tag in REFERENCE_TAGS:
            key, rows = parse_single_reference(elem)
            if key:
                ref_tables[key] = rows
            elem.clear()
            continue

        if elem.tag in RECORD_TAGS:
            single = parse_single_record(elem)
            record_tables["record"].append(single["record"])
            for key in record_tables:
                if key != "record" and key in single:
                    record_tables[key].extend(single[key])
            rec_count += 1
            if rec_count % 10000 == 0:
                print("    %d records ..." % rec_count)
            elem.clear()
            continue

        if elem.tag == "PublicFigure":
            associations.extend(parse_association_group(elem))
            elem.clear()
            continue

    print("  Total records parsed: %d" % rec_count)

    output = {"_meta": pfa_meta}
    output.update(ref_tables)
    output.update(record_tables)
    output["association"] = associations
    return output


def transform_xml_file_to_jsonl(xml_path, tmp_dir):
    tmp_dir = Path(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    handles = {}
    counters = {}

    def _write(table_key, row):
        if table_key not in handles:
            handles[table_key] = open(tmp_dir / (table_key + ".jsonl"), "w")
            counters[table_key] = 0
        handles[table_key].write(json.dumps(row, ensure_ascii=False) + "\n")
        counters[table_key] += 1

    pfa_meta = {}
    rec_count = 0

    for event, elem in ET.iterparse(str(xml_path), events=("start", "end")):

        if event == "start" and elem.tag == "PFA":
            pfa_meta = {"date": elem.attrib.get("date"), "type": elem.attrib.get("type")}
            print("  PFA date=%s  type=%s" % (pfa_meta.get("date"), pfa_meta.get("type")))
            continue

        if event != "end":
            continue

        if elem.tag in REFERENCE_TAGS:
            key, rows = parse_single_reference(elem)
            if key:
                for row in rows:
                    _write(key, row)
            print("    Parsed ref: %s" % elem.tag)
            elem.clear()
            continue

        if elem.tag in RECORD_TAGS:
            single = parse_single_record(elem)
            _write("record", single["record"])
            for key in single:
                if key != "record":
                    for row in single[key]:
                        _write(key, row)
            rec_count += 1
            if rec_count % 10000 == 0:
                print("    %d records ..." % rec_count)
            elem.clear()
            continue

        if elem.tag == "PublicFigure":
            for row in parse_association_group(elem):
                _write("association", row)
            elem.clear()
            continue

    for h in handles.values():
        h.close()

    with open(tmp_dir / "_meta.json", "w") as f:
        json.dump(pfa_meta, f)

    print("  Total records parsed: %d" % rec_count)
    for name in sorted(counters.keys()):
        print("    %s: %d rows" % (name, counters[name]))

    return pfa_meta
