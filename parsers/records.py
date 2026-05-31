from dj_sanctions_analysis.parsers.helpers import text_or_none


def parse_single_record(rec):
    rid = int(rec.attrib["id"])

    result = {
        "record": {
            "id": rid,
            "record_type": rec.tag,
            "action": rec.attrib.get("action"),
            "action_date": rec.attrib.get("date"),
            "gender": text_or_none(rec, "Gender"),
            "active_status": text_or_none(rec, "ActiveStatus"),
            "deceased": text_or_none(rec, "Deceased"),
            "profile_notes": text_or_none(rec, "ProfileNotes"),
        },
        "record_name": _parse_names(rec, rid),
        "record_description": _parse_descriptions(rec, rid),
        "record_role": _parse_roles(rec, rid),
        "record_date": _parse_dates(rec, rid),
        "record_birth_place": _parse_birth_places(rec, rid),
        "record_sanctions_ref": _parse_sanctions_references(rec, rid),
        "record_country": _parse_countries_detail(rec, rid),
        "record_id_number": _parse_id_numbers(rec, rid),
        "record_source": _parse_sources(rec, rid),
        "record_image": _parse_images(rec, rid),
        "record_address": _parse_addresses(rec, rid),
    }

    return result


def _parse_names(rec, rid):
    rows = []
    nd = rec.find("NameDetails")
    if nd is None:
        return rows
    for name_el in nd.findall("Name"):
        name_type = name_el.attrib.get("NameType")
        for nv in name_el.findall("NameValue"):
            rows.append({
                "record_id": rid, "name_type": name_type,
                "title_honorific": text_or_none(nv, "TitleHonorific"),
                "first_name": text_or_none(nv, "FirstName"),
                "middle_name": text_or_none(nv, "MiddleName"),
                "surname": text_or_none(nv, "Surname"),
                "maiden_name": text_or_none(nv, "MaidenName"),
                "suffix": text_or_none(nv, "Suffix"),
                "single_string_name": text_or_none(nv, "SingleStringName"),
                "original_script_name": text_or_none(nv, "OriginalScriptName"),
                "entity_name": text_or_none(nv, "EntityName"),
            })
    return rows


def _parse_descriptions(rec, rid):
    rows = []
    descs = rec.find("Descriptions")
    if descs is None:
        return rows
    for d in descs.findall("Description"):
        rows.append({
            "record_id": rid,
            "description1_id": int(d.attrib["Description1"]) if "Description1" in d.attrib else None,
            "description2_id": int(d.attrib["Description2"]) if "Description2" in d.attrib else None,
            "description3_id": int(d.attrib["Description3"]) if "Description3" in d.attrib else None,
        })
    return rows


def _parse_roles(rec, rid):
    rows = []
    rd = rec.find("RoleDetail")
    if rd is None:
        return rows
    for roles_el in rd.findall("Roles"):
        role_type = roles_el.attrib.get("RoleType")
        for occ in roles_el.findall("OccTitle"):
            rows.append({
                "record_id": rid, "role_type": role_type,
                "occ_cat_code": int(occ.attrib["OccCat"]) if "OccCat" in occ.attrib else None,
                "title": occ.text,
                "since_day": occ.attrib.get("SinceDay"), "since_month": occ.attrib.get("SinceMonth"),
                "since_year": occ.attrib.get("SinceYear"), "to_day": occ.attrib.get("ToDay"),
                "to_month": occ.attrib.get("ToMonth"), "to_year": occ.attrib.get("ToYear"),
            })
    return rows


def _parse_dates(rec, rid):
    rows = []
    dd = rec.find("DateDetails")
    if dd is None:
        return rows
    for date_el in dd.findall("Date"):
        date_type = date_el.attrib.get("DateType")
        for dv in date_el.findall("DateValue"):
            rows.append({
                "record_id": rid, "date_type": date_type,
                "day": dv.attrib.get("Day"), "month": dv.attrib.get("Month"),
                "year": dv.attrib.get("Year"), "note": dv.attrib.get("Note"),
            })
    return rows


def _parse_birth_places(rec, rid):
    rows = []
    bp = rec.find("BirthPlace")
    if bp is None:
        return rows
    for p in bp.findall("Place"):
        rows.append({"record_id": rid, "place": p.attrib.get("name")})
    return rows


def _parse_sanctions_references(rec, rid):
    rows = []
    sr = rec.find("SanctionsReferences")
    if sr is None:
        return rows
    for ref in sr.findall("Reference"):
        rows.append({
            "record_id": rid,
            "sanctions_ref_id": int(ref.text) if ref.text and ref.text.strip().isdigit() else None,
            "since_day": ref.attrib.get("SinceDay"), "since_month": ref.attrib.get("SinceMonth"),
            "since_year": ref.attrib.get("SinceYear"), "to_day": ref.attrib.get("ToDay"),
            "to_month": ref.attrib.get("ToMonth"), "to_year": ref.attrib.get("ToYear"),
        })
    return rows


def _parse_countries_detail(rec, rid):
    rows = []
    cd = rec.find("CountryDetails")
    if cd is None:
        return rows
    for country_el in cd.findall("Country"):
        country_type = country_el.attrib.get("CountryType")
        for cv in country_el.findall("CountryValue"):
            rows.append({"record_id": rid, "country_type": country_type, "country_code": cv.attrib.get("Code")})
    return rows


def _parse_id_numbers(rec, rid):
    rows = []
    ids = rec.find("IDNumberTypes")
    if ids is None:
        return rows
    for id_el in ids.findall("ID"):
        id_type = id_el.attrib.get("IDType")
        for idv in id_el.findall("IDValue"):
            rows.append({"record_id": rid, "id_type": id_type, "id_value": idv.text, "id_notes": idv.attrib.get("IDnotes")})
    return rows


def _parse_sources(rec, rid):
    rows = []
    sd = rec.find("SourceDescription")
    if sd is None:
        return rows
    for src in sd.findall("Source"):
        rows.append({"record_id": rid, "url": src.attrib.get("name")})
    return rows


def _parse_images(rec, rid):
    rows = []
    imgs = rec.find("Images")
    if imgs is None:
        return rows
    for img in imgs.findall("Image"):
        rows.append({"record_id": rid, "url": img.attrib.get("URL")})
    return rows


def _parse_addresses(rec, rid):
    rows = []
    for cd in rec.findall("CompanyDetails"):
        addr_line = text_or_none(cd, "AddressLine")
        addr_city = text_or_none(cd, "AddressCity")
        addr_country = text_or_none(cd, "AddressCountry")
        url = text_or_none(cd, "URL")
        if any([addr_line, addr_city, addr_country, url]):
            rows.append({"record_id": rid, "address_line": addr_line, "address_city": addr_city, "address_country": addr_country, "url": url})
    return rows
