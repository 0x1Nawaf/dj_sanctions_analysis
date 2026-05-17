import json
from pathlib import Path


def write_json(output, out_path):
    out_path = Path(out_path)
    print("  Writing %s ..." % out_path)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    total_rows = sum(len(v) for k, v in output.items() if isinstance(v, list))
    print("Done. %d total rows across all tables. File size: %.1f MB" % (total_rows, size_mb))
