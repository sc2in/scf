# scf-api

SC2's canonical, validated [Secure Controls Framework](https://securecontrolsframework.com)
dataset: official SCF Excel workbook → validated `data/*.json` → static JSON API under
`docs/` (GitHub Pages).

- **1,534 controls** across 34 families (SCF 2026.2), 252 framework crosswalks,
  5,956 assessment objectives, 316 evidence requests, risk/threat catalogs,
  compensating controls, privacy principles.
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

Or consume `data/*.json` directly (praxis-style) via a flake input / submodule.

## Pipeline

```
scf-api fetch                      # gh release download + sha256 (upstream SCF repo)
scf-api parse --workbook X.xlsx    # → data/*.json; hard validation gate
scf-api validate --data data/      # hermetic re-check of committed data
scf-api build                      # data/ → docs/ static tree
scf-api changelog old/ new/        # human-readable release notes
scf-api verify-tree A B            # semantic docs/api equivalence proof
scf-api all                        # the autopilot path
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
