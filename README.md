# DJ Sanctions

Downloads Dow Jones PFA sanctions XML files, parses them, and produces a single `sanctions_seeder.json` ready for database import.

## Requirements

Python 3.8+ (no external dependencies).

## Usage

```bash
# Full sync: downloads the latest full snapshot + all daily deltas after it, merges into one file
python3 -m dj_sanctions --auth <base64_credentials> --full

# Daily only: downloads only daily/incremental delta files, merges them
python3 -m dj_sanctions --auth <base64_credentials> --daily

# List available files on the DJ feed
python3 -m dj_sanctions --auth <base64_credentials> --list

# Parse a local XML file
python3 -m dj_sanctions --local /path/to/PFA2_file.xml

# Specify output directory
python3 -m dj_sanctions --auth <base64_credentials> --full --outdir /path/to/output
```

Output is always `sanctions_seeder.json` in the output directory.

## How it works

1. Connects to `https://djrcfeed.dowjones.com/xml/` with Basic auth
2. Lists available files and classifies them:
   - `_f.zip` = full snapshot (all records)
   - `_d.zip` = daily delta (adds/changes/deletes since yesterday)
   - `_i.zip` = incremental (weekly cumulative delta)
3. **Phase 1 -- Download**: all zip files are downloaded to `pfa_data/` inside the output directory. Already-downloaded files are skipped automatically (safe to re-run).
4. **Phase 2 -- Extract & Merge**: each zip is extracted and parsed from disk, then deltas are applied on top of the base.
5. **`--full` mode**: picks the latest full file as base, then applies all deltas dated after it
6. **`--daily` mode**: downloads only daily + incremental files and merges them sequentially
7. Deltas are merged: `add`/`chg` records replace existing ones, `del` records are removed
8. The merged result is written as `sanctions_seeder.json`


## Output JSON structure

The JSON contains keys matching the database schema:

- `_meta` -- file date and type
- `ref_*` -- 10 reference/lookup tables (countries, occupations, sanctions lists, etc.)
- `record` -- main sanctions records (persons + entities)
- `record_name`, `record_date`, `record_country`, etc. -- 11 child tables
- `association` -- relationship links between records
