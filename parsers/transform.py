from dj_sanctions.parsers.references import parse_reference_tables
from dj_sanctions.parsers.records import parse_records
from dj_sanctions.parsers.associations import parse_associations


def transform_xml_to_dict(root):
    pfa_meta = {
        "date": root.attrib.get("date"),
        "type": root.attrib.get("type"),
    }
    print("  PFA date=%s  type=%s" % (pfa_meta["date"], pfa_meta["type"]))

    print("  Extracting reference tables ...")
    ref_tables = parse_reference_tables(root)
    for name, rows in ref_tables.items():
        print("    %s: %d rows" % (name, len(rows)))

    print("  Extracting records ...")
    record_tables = parse_records(root)
    for name, rows in record_tables.items():
        print("    %s: %d rows" % (name, len(rows)))

    print("  Extracting associations ...")
    assoc = parse_associations(root)
    print("    association: %d rows" % len(assoc))

    output = {"_meta": pfa_meta}
    output.update(ref_tables)
    output.update(record_tables)
    output["association"] = assoc

    return output
