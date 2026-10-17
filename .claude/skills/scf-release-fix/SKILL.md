---
name: scf-release-fix
description: Repair the SCF parser after a new upstream workbook release breaks the pipeline (validation gate failed, "no column matching", "no sheet matching", thousands of findings). Use when a new SCF version arrives or an update-scf issue is opened.
---

# Fix the parser for a new SCF release

Goal: one parser reads every supported release (2026.1.1, 2026.2, 2026.3, + the new one).
Run everything as `nix develop -c python -m scf_api.cli ...`. Workbook is in `workbooks/`
(or `fetch` it). Keep output small; do not open `validation/validation-report.json` directly.

## Step 1 — get the workbook and a first reading
```
fetch                                   # only if workbooks/ lacks the new file
diagnose --workbook workbooks/<file>.xlsx
```
Output is one of:
- `STRUCTURE: no tab matches kind 'K'` → go to **Fix A**
- `STRUCTURE: tab 'T' has no column matching [...]` → go to **Fix B**
- `PARSED ...` with fails → go to **Fix C**
- `PARSED ...` with 0 fails → go to **Step 3**

## Fix A — a tab was renamed or removed
`src/scf_api/workbook.py` `SHEET_PATTERNS[kind] = (accepted patterns, excludes)`.
- Renamed: put the new name FIRST in the tuple, keep the old names. Match the stable part
  (patterns are substrings after `norm_key`: lowercase, dashes folded, spaces collapsed).
- Removed because its data moved elsewhere (2026.3 did this for compensating controls):
  keep the old pattern, use `wb.has_sheet(kind)` and read the data from the new tab. See
  `_parse_compensating` in `parse.py` for the exact pattern.
- Check the new tab doesn't also match another kind's pattern (`excludes`).

## Fix B — a header was renamed or removed
Find the failing `sheet.col("<old>")` in `src/scf_api/parse.py` (grep the pattern text).
- Renamed: `sheet.col("<new>", alts=("<old>",))`. New first, old kept.
- Use `headers --workbook W --sheet <tab> --grep <word>` to see real headers and a sample
  value; confirm the sample looks like what the field means before mapping to it.
- Removed (field no longer exists): ask whether another column now carries it
  (`--grep`). If not, stop and hand back — dropping an output field is a contract change.

## Fix C — parsed, but the gate has fails
Run `triage`. Typical shapes:
- Thousands of `control-risk`/`control-threat` fails with values like `Unlikely`: a matrix
  column is being read as an id list. See `scf-workbook-recon`.
- A handful of `control-erl` etc. with real-looking ids: probably a genuine workbook typo.
  Confirm in the sheet cell (`sheet!cell` is in the sample), then add an entry to
  `overrides/overrides.json` with `applies_to: ["<version>"]` and a `reason`.
- `xwalk-source` warnings for 3 MCR/DSR columns are normal. Many more = the crosswalk
  landmark slice moved (`parse.py` `_parse_controls`, `sources.py`).

## Step 3 — prove it is right, not just green
1. Compare counts printed by `diagnose` with the previous `GROUND_TRUTH` row in
   `tests/test_integration_real.py`. Big drops mean a misread column.
2. Spot-check 2 records: `jq` one control from a scratch `--out` dir (see
   `scf-regenerate`), and compare fields to the sheet row via `headers --sample`.
3. Then follow `scf-regenerate`.

If stuck after 3 different fixes for the same miss, stop and write the handoff note
described in `AGENTS.md`.
