def parse_associations(root):
    rows = []
    assoc_el = root.find("Associations")
    if assoc_el is None:
        return rows
    for group in assoc_el:
        record_id = int(group.attrib["id"])
        for a in group.findall("Associate"):
            rows.append({
                "record_id": record_id,
                "associate_id": int(a.attrib["id"]),
                "relationship_code": int(a.attrib["code"]) if "code" in a.attrib else None,
                "is_ex": a.attrib.get("ex") == "Yes",
            })
    return rows
