# scf-api

SC2's canonical, validated [Secure Controls Framework](https://securecontrolsframework.com)
dataset: official SCF Excel workbook → validated `data/*.json` → static JSON API under
`docs/` (GitHub Pages).

- **1,591 controls** across 34 families (SCF 2026.3), 270 framework crosswalks,
  6,446 assessment objectives, 422 evidence requests, risk/threat catalogs
  (65 risks, 45 threats, with a per-control likelihood rating), compensating
  controls, privacy principles.
- **Validated**: every id-bearing cell is checked for cross-sheet referential
  integrity before a release ships. The SCF master workbook is maintained by hand;
  this gate is what keeps its inconsistencies from silently reaching consumers.
- **Autopilot**: a clean upstream SCF release flows fetch → parse → validate →
  build → push → tag → Pages with zero human touch. A human is summoned (via
  GitHub issue) only when validation finds a workbook inconsistency it cannot
  resolve; the fix is an audited entry in `overrides/overrides.json`.
- **Deterministic**: parse twice → byte-identical. No timestamps in generated
  data (the validation report carries the only `generated_at`).

## Consuming

Static JSON, no auth. Base URL: the GitHub Pages deployment of `docs/`.

| endpoint | content |
|---|---|
| `api/summary.json` | version, counts, weight distribution |
| `api/controls.json`, `api/controls/{ID}.json` | controls with crosswalks |
| `api/families.json`, `api/families/{CODE}.json` | family index/detail |
| `api/crosswalks.json`, `api/crosswalks/{FW_ID}.json` | bidirectional crosswalks |
| `api/assessment-objectives[.json\|/{SCF_ID}.json]` | assessment objectives |
| `api/evidence-requests[.json\|/{ERL_ID}.json]` | evidence request list |
| `api/risks/…`, `api/threats/…`, `api/compensating-controls/…`, `api/privacy-principles.json` | catalogs |
| `api/legacy-map.json` | previous-release → current control ids (2026.3+) |

Or consume `data/*.json` directly (praxis-style) via a flake input / submodule.

### Migrating to SCF 2026.3 control ids

2026.3 renumbered the catalog: 858 control ids were added and 801 removed relative to
2026.2, and 1,457 of the 1,591 controls carry a `- renumbered` errata note. Any stored
reference to a 2026.2 (or older) control id — policies, mappings, assessments, praxis /
policypress / grc imports — must be migrated before it is trusted against 2026.3 data.

- The workbook's `Legacy SCF #` column (and its `READ THIS` tab, which lists deprecated
  controls and where they merged) is the authoritative old→new map, and this API emits it:
  - `controls[].legacy_ids` — the 2026.2 ids each 2026.3 control replaces: one id
    (renumbered or unchanged), several (a merge), or `[]` (a new control). Only present
    for releases whose workbook has the column (2026.3+).
  - `data/scf-legacy-map.json` (also `api/legacy-map.json`) — the same data keyed by old
    id: `{"from_version": "2026.2", "to_version": "2026.3", "map": {"<old id>":
    {"new": "<new id>", "merged": bool, "deprecated": bool}}}`. `merged`: the new control
    absorbed several old ids; `deprecated`: the old control was a duplicate removed by the
    merge (`READ THIS`). The validation gate proves every 2026.2 id (all 1,534) maps to
    exactly one real 2026.3 control; 45 old ids sit in 22 merges, 23 of them deprecated.
- `controls[].errata` says what changed for each control (`- renumbered`, `- renamed`,
  `- wordsmithed`, `- new control`).
- `CHANGELOG.md` lists the exact added, removed and changed ids per release.
- Dangling ids surface as validation failures in consumers that check against this
  catalog, so run your own reference check after bumping.

## Pipeline

```
scf-api fetch                      # gh release download + sha256 (upstream SCF repo)
scf-api parse --workbook X.xlsx    # → data/*.json; hard validation gate
scf-api validate --data data/      # hermetic re-check of committed data
scf-api build                      # data/ → docs/ static tree
scf-api changelog old/ new/        # human-readable release notes
scf-api verify-tree A B            # semantic docs/api equivalence proof
scf-api all                        # the autopilot path
scf-api diagnose --workbook X.xlsx # bounded, fix-oriented parse/validate output
scf-api triage                     # validation report grouped by check
scf-api headers --workbook X.xlsx --sheet T   # one line per column of a tab
```

Development: `nix develop`, then `pytest`. Full gate: `nix flake check -L`
(pytest, data-valid, docs-fresh, version-consistent). Real-workbook
integration tests activate when `$SCF_WORKBOOK` points at the official xlsx.

## Licensing & provenance

- **Code**: AGPL-3.0-only (`LICENSE`).
- **Data** (`data/`, `docs/`): Secure Controls Framework content,
  CC BY-ND 4.0 with attribution — see `data/LICENSE-SCF.md`. This repo
  format-shifts the official workbook; content is never altered beyond the
  documented, version-scoped override map.

## Credits

- The [Secure Controls Framework Council](https://securecontrolsframework.com)
  authors and maintain the SCF itself.
- [hackIDLE/scf-api](https://github.com/hackIDLE/scf-api) (archived) is prior
  art for the API surface. This repository is an independent clean-room
  reimplementation — no code was reused; its published output shapes served
  as the compatibility contract and test oracle.
- Reimplemented for SC2 with [Claude Code](https://claude.com/claude-code)
  (Claude Fable 5) driving the clean-room build, equivalence proofs, and
  validation gate design.
