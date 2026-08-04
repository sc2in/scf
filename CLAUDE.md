# CLAUDE.md — sc2in/scf (canonical SCF dataset pipeline)

SC2's owned, maintained, **public** canonical source for Secure Controls Framework data:
official SCF Excel workbook → validated `data/*.json` → static `docs/api/**`. Replaces the
archived, unlicensed `hackIDLE/scf-api` for every SC2 consumer (praxis, policypress, grc).
**Read `PLAN.md` first** — it is the approved implementation plan (M1–M8) with verified
ground truth, output contracts, and acceptance proofs. Work milestone by milestone.

## Golden rules

- **Commit only when explicitly asked. No attribution trailers** (no `Co-Authored-By`) —
  the user wants a clean log.
- `nix fmt` before finishing; `nix flake check` must stay green at every milestone.
- **Autopilot is a requirement, not a feature**: a clean SCF release must flow
  fetch → parse → validate → build → push → tag → Pages with zero human touch. A human is
  summoned (GitHub issue) ONLY when the validation gate finds an unresolved workbook
  inconsistency.

## The clean-room rule (legal constraint — never violate)

- `/home/tsunami/code/sc2/scf-api` is the **hackIDLE oracle checkout**: archived, UNLICENSED,
  third-party-authored (Ethan Troy). Its `data/` and `docs/api/` **outputs** are the test
  oracle for equivalence proofs, and its scripts define the output *shape contract* — but
  **no code may be read-and-ported from `scripts/*.mjs` into this repo**. Reimplement from
  the shape of the data and from the user's own prior art.
- Freely portable (user-authored, their IP):
  - `/home/tsunami/code/sc2/securecontrols/utils/scf_import.py` — pattern-based sheet
    resolution, landmark crosswalk slicing ("AICPA" … "Risk Threat Summary"), rapidfuzz
    header↔Sources reconciliation, column manifests
  - `/home/tsunami/code/sc2/securecontrols/utils/file_prep.py` — CONFIG column mappings
    (sheet→field knowledge)
  - `/home/tsunami/code/sc2/securecontrols/utils/schema/root.json`,
    `securecontrols/securecontrols/manual_mapping.json`
- License here: code `AGPL-3.0-only`; SCF data CC BY-ND 4.0 with attribution
  (`data/LICENSE-SCF.md`, praxis-style attribution string). README credits hackIDLE/scf-api
  as prior art for the API surface: independent reimplementation, no code reused.

## Key reference paths (read-only consumers this repo must not break)

- praxis: `/home/tsunami/code/sc2/praxis` — `scripts/generate-facts.py` (hardcodes
  `scf-2026-1-1.json`), `modules/flake/checks.nix` `praxis-facts-fresh`. Acceptance:
  facts.json regenerated from this repo's `data/` is **byte-identical**.
  **The catalog filename carries the SCF version**, so it is now `scf-2026-2.json` —
  de-hardcode praxis (glob `scf-*.json` or read `.scf-version`) before bumping its pin.
- policypress: `/home/tsunami/code/sc2/policypress` — `src/control_report.zig` reads
  `data/scf.json` (bare array of `{domain, control_id, control}`).
- grc: `/home/tsunami/code/sc2/grc` — `import/import-scf.mjs` consumes
  `scf-api/docs/api/*.json` (submodule); count asserts are its acceptance test.
- Known deviations (documented in PLAN.md): MON-03.3 evidence_requests workbook typo
  (override: drop — still present at 2026.2, so the entry is deliberately NOT
  version-scoped), TDA-11.2 `["[object Object]"]` upstream parser bug (we emit real
  values; allowlisted in the tree proof). The hackIDLE oracle equivalence proof is frozen
  at 2026.1.1 — the archive has no later release to compare against.

## Upstream renames tabs and headers between releases

SCF 2026.2 renamed the `Authoritative Sources` tab to `Focal Documents` and shortened the
compensating-controls `SCF Control #` header to `SCF #`, breaking autopilot. So:

- `SHEET_PATTERNS` (workbook.py) maps each logical kind to an **ordered tuple** of accepted
  patterns, current name first; `Sheet.col(..., alts=(...))` does the same for headers.
  Add the new name, keep the old — one parser must read every supported release, and
  `tests/test_integration_real.py` pins ground-truth counts per version.
- Tab names match via `norm_key`, same as column headers, so invisible whitespace drift
  does not summon a human.
- A rename found in production is fixable **without a code change**: the `resolution`
  section of `overrides/overrides.json` carries `sheets[]`/`columns[]` fallbacks. Those are
  tried only after the built-in patterns miss and raise a `resolution-alias` WARN, so the
  alias gets folded back into `SHEET_PATTERNS` later.

## House style

- Nix: flake-parts, one concern per file under `modules/flake/` if the flake grows;
  treefmt (ruff-format + alejandra); `om.yaml` CI mirroring sc2in/praxis.
- Python ≥3.11, stdlib-first; runtime deps only `openpyxl`, `rapidfuzz`, `jsonschema`.
  Deterministic output is sacred: sorted/stable ordering, no timestamps in generated data
  (the validation report carries the only `generated_at`), parse-twice → byte-identical.
- Tests: pytest; the workbook fixture is SYNTHETIC and built at test time (no SCF content,
  no binaries in git). Real-workbook integration tests gate on `$SCF_WORKBOOK`.

## Verify

```bash
nix fmt && nix flake check -L   # pytest, data-valid, docs-fresh, version-consistent
```
