import json
from pathlib import Path

from dj_sanctions_analysis.config import CHILD_TABLES


def merge_jsonl_with_deltas(tmp_dir, delta_list, out_path, feed_scope="complete"):
    tmp_dir = Path(tmp_dir)
    out_path = Path(out_path)

    deleted_ids = set()
    replaced_records = {}
    replaced_children = {}
    replaced_assocs = {}

    for delta in delta_list:
        for delta_rec in delta.get("record", []):
            rid = delta_rec["id"]
            action = delta_rec.get("action", "chg")

            if action == "del":
                deleted_ids.add(rid)
                replaced_records.pop(rid, None)
                for tbl in CHILD_TABLES:
                    replaced_children.setdefault(tbl, {}).pop(rid, None)
                replaced_assocs.pop(rid, None)
            else:
                deleted_ids.discard(rid)
                replaced_records[rid] = delta_rec
                for tbl in CHILD_TABLES:
                    rows = [r for r in delta.get(tbl, []) if r.get("record_id") == rid]
                    replaced_children.setdefault(tbl, {})[rid] = rows
                replaced_assocs[rid] = [
                    r for r in delta.get("association", []) if r.get("record_id") == rid
                ]

        for key in list(delta.keys()):
            if key.startswith("ref_") and delta[key]:
                ref_path = tmp_dir / (key + ".jsonl")
                with open(ref_path, "w") as f:
                    for row in delta[key]:
                        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    affected_ids = deleted_ids | set(replaced_records.keys())

    meta_path = tmp_dir / "_meta.json"
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
    else:
        meta = {}

    if delta_list:
        latest_meta = delta_list[-1].get("_meta", {})
        if latest_meta:
            meta = latest_meta

    meta["feed_scope"] = feed_scope
    record_count = _count_merged_records(tmp_dir, affected_ids, replaced_records)
    if record_count:
        meta["record_count"] = record_count

    jsonl_files = sorted(tmp_dir.glob("*.jsonl"))
    table_keys = [f.stem for f in jsonl_files]

    print("  Writing %s (streaming) ..." % out_path)

    with open(out_path, "w", encoding="utf-8") as out:
        out.write("{\n")
        out.write('  "_meta": %s' % json.dumps(meta, ensure_ascii=False))

        for table_key in table_keys:
            out.write(",\n")
            out.write('  "%s": [\n' % table_key)

            jsonl_path = tmp_dir / (table_key + ".jsonl")
            first = True
            base_count = 0
            skip_count = 0

            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    if affected_ids:
                        row = json.loads(line)
                        rid = row.get("id") if table_key == "record" else row.get("record_id")
                        if rid is not None and rid in affected_ids:
                            skip_count += 1
                            continue

                    if not first:
                        out.write(",\n")
                    out.write("    " + line)
                    first = False
                    base_count += 1

            append_count = 0

            if table_key == "record":
                for rec in replaced_records.values():
                    if not first:
                        out.write(",\n")
                    out.write("    " + json.dumps(rec, ensure_ascii=False))
                    first = False
                    append_count += 1
            elif table_key == "association":
                for rows in replaced_assocs.values():
                    for row in rows:
                        if not first:
                            out.write(",\n")
                        out.write("    " + json.dumps(row, ensure_ascii=False))
                        first = False
                        append_count += 1
            elif table_key in replaced_children:
                for rows in replaced_children[table_key].values():
                    for row in rows:
                        if not first:
                            out.write(",\n")
                        out.write("    " + json.dumps(row, ensure_ascii=False))
                        first = False
                        append_count += 1

            out.write("\n  ]")

            total = base_count + append_count
            if skip_count or append_count:
                print("    %s: %d rows (kept %d, skipped %d, added %d)" % (
                    table_key, total, base_count, skip_count, append_count))
            else:
                print("    %s: %d rows" % (table_key, total))

        out.write("\n}\n")

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print("  Done. %d records. File size: %.1f MB" % (record_count, size_mb))
    return record_count


def _count_merged_records(tmp_dir, affected_ids, replaced_records):
    count = 0
    rec_path = tmp_dir / "record.jsonl"
    if rec_path.exists():
        with open(rec_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if affected_ids:
                    row = json.loads(line)
                    if row.get("id") in affected_ids:
                        continue
                count += 1
    count += len(replaced_records)
    return count
