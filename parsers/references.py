TAG_TO_KEY = {
    "CountryList": "ref_country",
    "OccupationList": "ref_occupation",
    "RelationshipList": "ref_relationship",
    "SanctionsReferencesList": "ref_sanctions",
    "Description1List": "ref_description1",
    "Description2List": "ref_description2",
    "Description3List": "ref_description3",
    "DateTypeList": "ref_date_type",
    "NameTypeList": "ref_name_type",
    "RoleTypeList": "ref_role_type",
}

_PARSERS = {}


def parse_single_reference(elem):
    tag = elem.tag
    key = TAG_TO_KEY.get(tag)
    if key is None:
        return None, []
    parser = _PARSERS.get(tag)
    if parser is None:
        return key, []
    return key, parser(elem)


def _reg(tag):
    def decorator(fn):
        _PARSERS[tag] = fn
        return fn
    return decorator


@_reg("CountryList")
def _parse_countries(el):
    return [
        {
            "code": c.attrib["code"],
            "name": c.attrib["name"],
            "is_territory": c.attrib.get("IsTerritory") == "True",
            "profile_url": c.attrib.get("ProfileURL"),
        }
        for c in el
    ]


@_reg("OccupationList")
def _parse_occupations(el):
    return [
        {"code": int(o.attrib["code"]), "name": o.attrib["name"]}
        for o in el
    ]


@_reg("RelationshipList")
def _parse_relationships(el):
    return [
        {"code": int(r.attrib["code"]), "name": r.attrib["name"]}
        for r in el
    ]


@_reg("SanctionsReferencesList")
def _parse_sanctions_refs(el):
    return [
        {
            "id": int(s.attrib["code"]),
            "name": s.attrib["name"],
            "status": s.attrib.get("status"),
            "description2_id": int(s.attrib["Description2Id"]) if "Description2Id" in s.attrib else None,
        }
        for s in el
    ]


@_reg("Description1List")
def _parse_description1(el):
    return [
        {
            "description1_id": int(d.attrib["Description1Id"]),
            "record_type": d.attrib["RecordType"],
            "name": d.text,
        }
        for d in el
    ]


@_reg("Description2List")
def _parse_description2(el):
    return [
        {
            "description2_id": int(d.attrib["Description2Id"]),
            "description1_id": int(d.attrib["Description1Id"]),
            "name": d.text,
        }
        for d in el
    ]


@_reg("Description3List")
def _parse_description3(el):
    return [
        {
            "description3_id": int(d.attrib["Description3Id"]),
            "description2_id": int(d.attrib.get("Description2Id", 0)) or None,
            "name": d.text,
        }
        for d in el
    ]


@_reg("DateTypeList")
def _parse_date_types(el):
    return [
        {
            "id": int(d.attrib["Id"]),
            "record_type": d.attrib["RecordType"],
            "name": d.attrib["name"],
        }
        for d in el
    ]


@_reg("NameTypeList")
def _parse_name_types(el):
    return [
        {
            "name_type_id": int(n.attrib["NameTypeID"]),
            "record_type": n.attrib["RecordType"],
            "name": n.text,
        }
        for n in el
    ]


@_reg("RoleTypeList")
def _parse_role_types(el):
    return [
        {
            "id": int(r.attrib["Id"]),
            "name": r.attrib["name"],
        }
        for r in el
    ]
