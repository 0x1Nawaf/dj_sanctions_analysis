# DJ Sanctions Analysis

Downloads Dow Jones PFA sanctions XML files, parses them, and produces a single `sanctions_seeder.json` ready for database import.

## Requirements

Python 3.8+ (no external dependencies).

## Usage

```bash
# Full re-baseline: latest full snapshot (_f) only. Run monthly.
python3 -m dj_sanctions_analysis --auth <base64_credentials> --full

# Daily sync: all daily files (_d) only
python3 -m dj_sanctions_analysis --auth <base64_credentials> --daily

# Today sync: today's daily file(s) (_d) only, falling back to yesterday
python3 -m dj_sanctions_analysis --auth <base64_credentials> --today

# List available files on the DJ feed
python3 -m dj_sanctions_analysis --auth <base64_credentials> --list

# Parse a local XML file
python3 -m dj_sanctions_analysis --local /path/to/PFA2_file.xml

# Specify output directory
python3 -m dj_sanctions_analysis --auth <base64_credentials> --full --outdir /path/to/output
```

Output is always `sanctions_seeder.json` in the output directory.

**Important:** `_meta.feed_scope` tells the Go seeder how to treat the file. `--full` emits `complete`, meaning the JSON is the whole universe of records and anything missing from it has genuinely left the feed. `--daily` and `--today` emit `delta_only`, which makes the seeder apply the adds/changes/deletes in the file without inactivating everything absent from it.

## How it works

1. Connects to `https://djrcfeed.dowjones.com/xml/` with Basic auth
2. Lists available files and classifies them:
   - `_f.zip` = full snapshot (all records)
   - `_d.zip` = daily delta (adds/changes/deletes since yesterday)
   - `_i.zip` = incremental (weekly cumulative delta)
3. **Phase 1 -- Download**: zip files are streamed to `pfa_data/` inside the output directory. Already-downloaded files are skipped after an integrity check, and anything truncated is re-downloaded (safe to re-run).
4. **Phase 2 -- Parse base**: the first file of the run is extracted to `pfa_data/xml/` and streamed to JSONL in `pfa_data/jsonl/`. The extracted XML size is checked against the archive, so a run interrupted mid-extraction is repaired on the next run instead of failing to parse. The JSONL directory is rebuilt from scratch each run, so switching between `--full` and `--daily` cannot leak tables between them.
5. **Phase 3 -- Apply deltas**: any remaining files are parsed in memory and merged on top of the base.
6. **Phase 4 -- Write JSON**: the merged result is written to a `.part` file and renamed into place as `sanctions_seeder.json`, so an interrupted run never leaves a half-written file for the seeder.

### Modes

- **`--full`**: latest full file (`_f`) only. This is the complete universe of records (~8.5 GB XML, hours to parse) -- run it monthly to re-baseline.
- **`--daily`**: all daily files (`_d`) on the feed, merged together. No full snapshot involved.
- **`--today`**: only today's daily file(s), falling back to yesterday if today's has not been published yet. Intended for cron.

Within a run, files are merged in date order: `add`/`chg` records replace earlier ones, `del` records are dropped from the output.

## Output JSON structure

The JSON contains keys matching the database schema:

- `_meta` -- file date, type, `feed_scope` (`complete` for `--full`, `delta_only` for `--daily`/`--today`), and `record_count`
- `ref_*` -- 10 reference/lookup tables (countries, occupations, sanctions lists, etc.)
- `record` -- main sanctions records (persons + entities)
- `record_name`, `record_date`, `record_country`, etc. -- 11 child tables
- `association` -- relationship links between records
