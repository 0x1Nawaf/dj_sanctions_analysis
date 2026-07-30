# DJ Sanctions Analysis

Downloads Dow Jones PFA sanctions XML files, parses them, and produces a single `sanctions_seeder.json` ready for database import.

## Requirements

Python 3.8+ (no external dependencies).

## Usage

```bash
# Full sync: latest full snapshot + all daily deltas after it
python3 -m dj_sanctions_analysis --auth <base64_credentials> --full

# Daily sync: latest full snapshot + all daily/incremental deltas (complete feed for seeder)
python3 -m dj_sanctions_analysis --auth <base64_credentials> --daily

# Today sync: latest full snapshot + today's delta(s) only (complete feed for seeder)
python3 -m dj_sanctions_analysis --auth <base64_credentials> --today

# List available files on the DJ feed
python3 -m dj_sanctions_analysis --auth <base64_credentials> --list

# Parse a local XML file
python3 -m dj_sanctions_analysis --local /path/to/PFA2_file.xml

# Specify output directory
python3 -m dj_sanctions_analysis --auth <base64_credentials> --full --outdir /path/to/output
```

Output is always `sanctions_seeder.json` in the output directory.

**Important:** The Go seeder expects a **complete merged feed** (millions of records), not raw delta files alone. All modes above produce a complete feed by starting from the latest full snapshot (`_f.zip`) and applying deltas on top.

## How it works

1. Connects to `https://djrcfeed.dowjones.com/xml/` with Basic auth
2. Lists available files and classifies them:
   - `_f.zip` = full snapshot (all records)
   - `_d.zip` = daily delta (adds/changes/deletes since yesterday)
   - `_i.zip` = incremental (weekly cumulative delta)
3. **Phase 1 -- Download**: zip files are saved to `pfa_data/` inside the output directory. Already-downloaded files are skipped (safe to re-run).
4. **Phase 2 -- Parse base**: the latest full snapshot is streamed to JSONL on disk.
5. **Phase 3 -- Apply deltas**: daily/incremental files are parsed in memory and merged on top of the base.
6. **Phase 4 -- Write JSON**: the merged result is written as `sanctions_seeder.json` with `_meta.feed_scope = "complete"`.

### Modes

- **`--full`**: latest full file + all deltas dated after it
- **`--daily`**: latest full file + all daily/incremental deltas after it (same merge strategy as `--full`, intended for cron)
- **`--today`**: latest full file + only today's delta(s), falling back to yesterday if none found

Deltas are merged: `add`/`chg` records replace existing ones, `del` records are removed from the output.

## Output JSON structure

The JSON contains keys matching the database schema:

- `_meta` -- file date, type, `feed_scope` (`complete`), and `record_count`
- `ref_*` -- 10 reference/lookup tables (countries, occupations, sanctions lists, etc.)
- `record` -- main sanctions records (persons + entities)
- `record_name`, `record_date`, `record_country`, etc. -- 11 child tables
- `association` -- relationship links between records
