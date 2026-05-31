from dj_sanctions_analysis.config import CHILD_TABLES


def merge_delta_into(base, delta):
    delta_meta = delta.get("_meta", {})
    print("    Merging delta: date=%s  type=%s" % (delta_meta.get("date"), delta_meta.get("type")))

    for key in list(delta.keys()):
        if key.startswith("ref_") and delta[key]:
            base[key] = delta[key]

    base_records_idx = {}
    for i, rec in enumerate(base.get("record", [])):
        base_records_idx[rec["id"]] = i

    for delta_rec in delta.get("record", []):
        rid = delta_rec["id"]
        action = delta_rec.get("action", "chg")

        if action == "del":
            if rid in base_records_idx:
                base["record"][base_records_idx[rid]] = None
            for tbl in CHILD_TABLES:
                base[tbl] = [r for r in base.get(tbl, []) if r and r.get("record_id") != rid]
            base["association"] = [r for r in base.get("association", []) if r and r.get("record_id") != rid]
        else:
            if rid in base_records_idx:
                base["record"][base_records_idx[rid]] = delta_rec
            else:
                base["record"].append(delta_rec)
                base_records_idx[rid] = len(base["record"]) - 1

            for tbl in CHILD_TABLES:
                base[tbl] = [r for r in base.get(tbl, []) if r and r.get("record_id") != rid]
                base[tbl].extend([r for r in delta.get(tbl, []) if r.get("record_id") == rid])

            base["association"] = [r for r in base.get("association", []) if r and r.get("record_id") != rid]
            base["association"].extend([r for r in delta.get("association", []) if r.get("record_id") == rid])

    base["record"] = [r for r in base["record"] if r is not None]
    base["_meta"] = delta_meta
