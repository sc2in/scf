---
name: scf-workbook-recon
description: Understand a changed SCF workbook layout cheaply (sheet/column shapes, how upstream has restructured it before) without loading the whole file into context. Use when diagnose/triage show misread columns or a layout change beyond a rename.
---

# Reading an SCF workbook on a small context budget

Never print a sheet. The control tab has 400+ columns × 1500 rows.

```
headers --workbook W --sheet "evidence"                # all columns of one tab
headers --workbook W --sheet "SCF 20" --grep risk --sample
headers --workbook W --sheet "SCF 20" --grep "errata"
```
`--sheet` is a tab-name substring (normalized). `--grep` filters header text.
`--sample` adds the first data row's cell beside each header: this is how you learn that a
column holds ratings (`Unlikely`), ids (`R-AC-1`), or free text.

## Tab kinds the parser needs (`SHEET_PATTERNS`)
domains · sources (focal documents) · controls · compensating (legacy tab) · evidence ·
aos · privacy · risks · threats. Others (READ THIS, Change Overview, STRM Errata, Lists)
are ignored.

## Column landmarks on the controls tab
`AICPA …` is the first crosswalk column. The crosswalk slice ends at the first risk
column. Between the SCR-CMM columns and AICPA sit profile columns whose header starts
with a line `SCF` (profiles: marked if non-empty). Order is: identity/description cols →
ERL → possible solutions → question/weight/PPTDF/NIST/SCRM → (2026.3: compensating cols) →
maturity 0-5 → profiles → crosswalks → risks/threats → errata.

## How upstream has changed things (so you recognize the pattern)
| release | change | how we absorbed it |
|---|---|---|
| 2026.2 | tab `Authoritative Sources` → `Focal Documents`; compensating `SCF Control #` → `SCF #` | ordered pattern tuples, `alts=` |
| 2026.3 | compensating controls moved onto the control tab (tab deleted) | `has_sheet` + same reader on controls tab |
| 2026.3 | risk/threat summary text columns → likelihood matrix (`Risk R-AC-1`, `Threat NT-1`, cells Unlikely/Possible/Likely) | `sources.matrix_columns`; `risks`/`threats` = Possible\|Likely ids, plus `*_likelihood` maps |
| 2026.3 | `Documentation Artifact` → `ERL Artifact`; ODP column → `Notes`; catalog gained `Old Risk #` | `alts=`, name column by header not position |
| 2026.3 | tab names embed the version (`SCF 2026.3`) | match the stable part only |

## Misread-column checklist
- Gate fails with "unknown id <word>": the word is a rating/flag, so you read a matrix or
  flag column as ids. Find the real id source (header names containing the id) .
- Count dropped to ~0: wrong tab matched, or the id column is now a different header.
- A field is silently empty everywhere: the pattern matched an earlier look-alike header.
  `headers --grep <pattern>` shows every column containing it; `sheet.col` takes the FIRST
  match, so tighten the pattern or use `exclude=(...)`.
- Positional assumptions are fragile (`id_col + 1`). Prefer finding a column by header.
