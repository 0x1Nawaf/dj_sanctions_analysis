def parse_reference_tables(root):
    return {
        "ref_country": _parse_countries(root),
        "ref_occupation": _parse_occupations(root),
        "ref_relationship": _parse_relationships(root),
        "ref_sanctions": _parse_sanctions_refs(root),
        "ref_description1": _parse_description1(root),
        "ref_description2": _parse_description2(root),
        "ref_description3": _parse_description3(root),
        "ref_date_type": _parse_date_types(root),
        "ref_name_type": _parse_name_types(root),
        "ref_role_type": _parse_role_types(root),
    }


def _parse_countries(root):
    return [
        {
            "code": c.attrib["code"],
            "name": c.attrib["name"],
            "is_territory": c.attrib.get("IsTerritory") == "True",
            "profile_url": c.attrib.get("ProfileURL"),
        }
        for c in root.find("CountryList")
    ]


def _parse_occupations(root):
    return [
        {"code": int(o.attrib["code"]), "name": o.attrib["name"]}
        for o in root.find("OccupationList")
    ]


def _parse_relationships(root):
    return [
        {"code": int(r.attrib["code"]), "name": r.attrib["name"]}
        for r in root.find("RelationshipList")
    ]


def _parse_sanctions_refs(root):
    return [
        {
            "id": int(s.attrib["code"]),
            "name": s.attrib["name"],
            "status": s.attrib.get("status"),
            "description2_id": int(s.attrib["Description2Id"]) if "Description2Id" in s.attrib else None,
        }
        for s in root.find("SanctionsReferencesList")
    ]


def _parse_description1(root):
    return [
        {
            "description1_id": int(d.attrib["Description1Id"]),
            "record_type": d.attrib["RecordType"],
            "name": d.text,
        }
        for d in root.find("Description1List")
    ]


def _parse_description2(root):
    return [
        {
            "description2_id": int(d.attrib["Description2Id"]),
            "description1_id": int(d.attrib["Description1Id"]),
            "name": d.text,
        }
        for d in root.find("Description2List")
    ]


def _parse_description3(root):
    return [
        {
            "description3_id": int(d.attrib["Description3Id"]),
            "description2_id": int(d.attrib.get("Description2Id", 0)) or None,
            "name": d.text,
        }
        for d in root.find("Description3List")
    ]


def _parse_date_types(root):
    return [
        {
            "id": int(d.attrib["Id"]),
            "record_type": d.attrib["RecordType"],
            "name": d.attrib["name"],
        }
        for d in root.find("DateTypeList")
    ]


def _parse_name_types(root):
    return [
        {
            "name_type_id": int(n.attrib["NameTypeID"]),
            "record_type": n.attrib["RecordType"],
            "name": n.text,
        }
        for n in root.find("NameTypeList")
    ]


def _parse_role_types(root):
    return [
        {
            "id": int(r.attrib["Id"]),
            "name": r.attrib["name"],
        }
        for r in root.find("RoleTypeList")
    ]
