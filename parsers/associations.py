def parse_association_group(group):
    rows = []
    record_id = int(group.attrib["id"])
    for a in group.findall("Associate"):
        rows.append({
            "record_id": record_id,
            "associate_id": int(a.attrib["id"]),
            "relationship_code": int(a.attrib["code"]) if "code" in a.attrib else None,
            "is_ex": a.attrib.get("ex") == "Yes",
        })
    return rows
