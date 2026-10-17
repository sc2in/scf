# sc2in/scf-api — SC2-owned canonical SCF dataset (corp #12, "once and for all")

## Context

Every SC2 product keys on the Secure Controls Framework, and all three consume descendants
of `hackIDLE/scf-api` — which is now **archived and unlicensed** (all pipeline code authored
by Ethan Troy, a third party; the AGPL LICENSE added in the local checkout isn't ours to
grant). The drift is live pain: corp's new `praxis-policy-gaps` gate reports 40 required ids
absent from PolicyPress' hand-copied 2025-vintage catalog. Root cause of every past stall
(securecontrols, assessment_tool): the SCF master workbook is **manually maintained** — ids
in one sheet don't reliably match other sheets, and no pipeline ever validated that.

Decisions (user-confirmed): clean-room **reimplement in Python** (porting the user's own
techniques from `securecontrols/utils/scf_import.py` — their authorship), new **public**
repo `sc2in/scf-api`, **full scope** (repo + repoint praxis, policypress, grc), and the repo
must run on **autopilot**: a new SCF release requires zero human intervention when clean;
humans are summoned only when validation finds a workbook inconsistency it can't resolve.

Session logistics: THIS session only bootstraps the new local repo with handoff materials;
implementation happens in a fresh session (Fable) opened in that repo.

## Phase 0 — bootstrap (this session, immediately after approval)

Create `sc2/scf-api-sc2in` (the hackIDLE oracle checkout keeps
`sc2/scf-api`; rename after M8), `git init -b main`, seed and commit:
- `PLAN.md` — the implementation plan below (M1–M8), verbatim.
- `CLAUDE.md` — project conventions + the hard constraints (clean-room rule, oracle paths,
  house style, no commit attribution, `nix fmt` + `nix flake check` green).
- `.gitignore` (result, .direnv, workbook xlsx, __pycache__).
Then tell the user to flip sessions. **Recommended model: Fable** (parity-critical
clean-room work with legal constraints).

## Hard constraints (verbatim into the new repo's CLAUDE.md)

- **Clean-room rule**: NO code from `sc2/scf-api` (hackIDLE — archived,
  unlicensed, third-party). Its committed `data/` + `docs/api/` outputs are the **test
  oracle only**; its scripts define the output *shape contract*, never implementation.
- Freely portable (user-authored): `sc2/securecontrols/utils/scf_import.py`
  (pattern sheet resolution, landmark crosswalk slicing "AICPA"…"Risk Threat Summary",
  rapidfuzz header↔Sources reconciliation, column manifests), `utils/file_prep.py`
  CONFIG column mappings, `utils/schema/root.json`, `securecontrols/manual_mapping.json`.
- License: code `AGPL-3.0-only`; SCF data CC BY-ND 4.0 with praxis-style attribution string
  in `data/LICENSE-SCF.md` (CC 4.0 treats format-shifting as non-adaptation). README credits
  hackIDLE/scf-api as prior art for the API surface, explicitly "independent
  reimplementation, no code reused".
- Natural SCF ids in all outputs (no PocketBase 15-char hash ids).

## Verified ground truth (explored + confirmed)

- Oracle: `.scf-version` 2026.1.1; 1,468 controls, 33 families, 249 crosswalk frameworks,
  5,776 AOs, 303 ERLs. Pipeline shape: `parse` (xlsx → `data/*.json`, 8 files) then `build`
  (`data/` → committed `docs/api/**` static tree, GitHub Pages).
- Known defects at 2026.1.1 (the equivalence-proof deviation list): (1) `MON-03.3` lists
  control id `MON-03.2` in `evidence_requests` (workbook typo; praxis filters non-`E-*`);
  (2) `TDA-11.2` `risks`/`threats` = `["[object Object]"]` (upstream exceljs parser bug —
  our parser fixes this class by construction).
- praxis (`sc2/praxis`): input `scf-api = { url = "github:hackIDLE/scf-api"; flake = false; }`
  (flake.nix:11-14); `scripts/generate-facts.py` **hardcodes `scf-2026-1-1.json`** (line 50)
  and reads `scf-{assessment-objectives,crosswalks,evidence-requests}.json`;
  `praxis-facts-fresh` check (modules/flake/checks.nix:153) diffs regenerated facts.json.
  hackIDLE also referenced in `data/scf/LICENSE-SCF.md:11`, `docs/architecture.md:6`.
- policypress (`sc2/policypress`): stale hand-committed
  `data/scf.{yml,json}` (1,239 flat `{domain, control_id, control}`); consumed at runtime by
  `src/control_report.zig:142,182`; count floor asserts in `src/test.zig:304,1308`; golden
  fixture `report_scf.typ` (build.zig:276); `config.toml:221` has `scf_controls` override.
  `data/tsc2017.*` is AICPA content — separate provenance, out of scope.
- grc (`sc2/grc`): submodule `scf-api` → hackIDLE @ 71ded89;
  `import/import-scf.mjs` consumes `scf-api/docs/api/*.json` with built-in count asserts;
  `import/pb-client.mjs:27` `SCF_API_DIR` env-overridable. **docs/ must be committed.**

## The new repo (target layout)

```
scf-api-sc2in/
├── flake.nix / flake.lock / om.yaml     # flake-parts, devshell (python3 + openpyxl/rapidfuzz/jsonschema/pytest, gh, jq), treefmt (ruff-format + alejandra)
├── pyproject.toml                        # package scf_api; console script `scf-api`
├── src/scf_api/
│   ├── cli.py        # fetch | parse | validate | build | changelog | verify-tree | all
│   ├── fetch.py      # gh release download from securecontrolsframework/securecontrolsframework; record sha256
│   ├── workbook.py   # openpyxl read_only; find_sheet() pattern resolution; rich-text/formula flattening
│   ├── normalize.py  # NFKC → unicode-dash fold → NBSP/zero-width → collapse ws → strip; case-fold for matching only; raw preserved for provenance
│   ├── sources.py    # crosswalk-column ↔ Authoritative Sources reconciliation: exact → normalized → rapidfuzz token_sort_ratio ≥70; FDI→api_id lowercase + `-2` collision suffix (id parity, e.g. general-nist-800-53-r5-2); AICPA…Risk-Threat-Summary landmark slice
│   ├── parse.py      # sheet extractors → data/*.json (2-space indent, upstream key order)
│   ├── overrides.py / validate.py / report.py   # the validation gate (below)
│   ├── build.py      # data/ → docs/api/** + summary.json + llms.txt/llms-full.txt/api/docs.md/index.html (SC2 branding)
│   ├── changelog.py  # old vs new data dir → human-readable added/removed/changed md
│   └── schemas/      # draft-07 JSON Schema per output file + override-map + validation-report schemas
├── overrides/overrides.json              # committed, version-scoped, every entry has `reason`
├── data/*.json  docs/  validation/validation-report.json  .scf-version
├── tests/        # synthetic mini-workbook fixture BUILT AT TEST TIME (no SCF content in git, no binaries) with deliberate defects: dangling AO ref, en-dash id, NBSP, control-id-in-ERL-column, dup id, renamed source header; unit tests per module; parse goldens; $SCF_WORKBOOK-gated integration test
└── .github/workflows/  ci.yml · update-scf.yml · release.yml · pages.yml
```

Hermetic `nix flake check` gates: `pytest`; `data-valid` (schemas + referential validator in
JSON-input mode over committed data); `docs-fresh` (rebuild docs/ → byte-diff, the
praxis-facts-fresh analog); `version-consistent` (.scf-version ↔ data filename ↔
docs/api/summary.json agree).

## Validation gate (the marquee feature — why this stays solved)

Cross-sheet referential integrity, every id-bearing cell normalized first, raw value kept:

| check | reference → target | severity |
|---|---|---|
| ao-control / erl-control / cc-control / privacy-control | AO / ERL / CompControls / Privacy sheets → controls sheet | fail |
| control-erl | controls' ERL column → ERL sheet (catches MON-03.3) | fail |
| control-risk / control-threat | controls' columns → Risk/Threat catalogs | fail |
| family-domain | id prefix → Domains sheet | fail |
| dup-id | duplicates within any sheet | fail |
| sheet-resolve / col-resolve | required sheet/column not found by pattern | fail |
| xwalk-source | crosswalk headers ↔ Sources rows, bidirectional + fuzzy score <100 | warn (manifest records score) |
| normalized-only | id resolves only after normalization | warn + auto-resolve, recorded |

Override map entry: `{id, check, sheet, control, match, action: drop|replace|accept,
reason (required), reported_upstream, applies_to: [versions]}`; unused entries → warn.
`validation/validation-report.json` records workbook sha256, findings with sheet+cell
provenance, override usage, reconciliation manifest. **Exit nonzero iff any fail-severity
finding is unresolved** — the hard gate everywhere.

## Autopilot (user requirement: zero human touch on a clean SCF release)

`update-scf.yml` — weekly cron + workflow_dispatch(tag, force):
1. Resolve latest securecontrolsframework release; exit 0 if == `.scf-version` (unless force).
2. fetch → parse → apply overrides → **validate (hard gate)** → build → changelog.
3. Run the full hermetic gate in-workflow: `nix flake check -L` over the updated tree.
4. **Green → commit directly to main** (data/, docs/, validation/, .scf-version, an
   auto-generated CHANGELOG section) and push. No PR, no human.
   `release.yml` (push to main touching .scf-version) tags `<version>`, creates the GH
   release with stats + validation-report.json attached; `pages.yml` redeploys docs/.
5. **Red → no push; open a GitHub issue** titled with the version, body = validation summary
   (findings with sheet/cell provenance), full report as artifact. The human's only job:
   author an override-map entry (or upstream-report the workbook bug) and re-dispatch.
   (Direct-push chosen over PR+auto-merge deliberately: GITHUB_TOKEN-created PRs don't
   trigger required-check workflows — the classic unattended-flow trap. Keep main
   unprotected-for-bot or grant the workflow bypass via ruleset.)
6. Consumers stay pull-based (their own input/submodule bumps), so scf-api autopilot never
   breaks a downstream build.

## Equivalence proofs at 2026.1.1 (M2/M3 acceptance)

1. **praxis byte-proof**: `python3 praxis/scripts/generate-facts.py <new>/data → diff` vs
   committed `praxis/data/scf/facts.json` — must be byte-identical.
2. **tree proof**: in-repo `scf-api verify-tree <new>/docs/api <oracle>/docs/api` — semantic
   JSON compare, with a committed deviation allowlist: TDA-11.2 risks/threats (real values
   vs `[object Object]`), MON-03.3 evidence_requests (override `drop` + allowlist entry).
3. **Determinism**: parse twice → byte-identical.

## Milestones (each lands green; M1–M4 in the new repo, M5–M8 per consumer)

- **M1 scaffold**: flake + package skeleton + synthetic-fixture tests + ci.yml.
- **M2 parser parity**: parse the real 2026.1.1 workbook; pass proofs 1–3.
- **M3 validation gate + canonical data**: validator, overrides (MON-03.3 entry), report;
  commit data/, docs/, validation/, .scf-version; enable all checks; tag 2026.1.1; Pages.
- **M4 autopilot**: update-scf.yml (prove idempotence: force-dispatch at same tag → no-op),
  release.yml, pages.yml. Create the public sc2in/scf-api repo, push, verify Pages + a
  dispatch run end-to-end.
- **M5 praxis repoint**: flake.nix input URL → sc2in/scf-api; update hackIDLE refs
  (LICENSE-SCF.md:11, architecture.md:6); regen facts.json (**zero diff expected**);
  `praxis-facts-fresh` + full CI green.
- **M6 policypress**: add `scf-api` non-flake input; new stdlib-only
  `tools/gen-scf-catalog.py` (resolve `.scf-version` → emit `data/scf.{json,yml}`, yml gets
  a "generated — do not hand-edit" header, json stays bare array for control_report.zig);
  perSystem app + `scf-catalog-fresh` check mirroring praxis-facts-fresh; regenerate
  (1,239 → 1,468); raise test floors (src/test.zig:304,1308) + add scf yml↔json parity
  test; regen golden `report_scf.typ`; CHANGELOG entry. Verify: zig build test + om ci +
  demo site build. (tsc2017.* untouched — different provenance; note in PR.)
- **M7 grc**: `.gitmodules` url → sc2in/scf-api, submodule sync + checkout the 2026.1.1
  tag; README attribution. Verify: `node import/import-scf.mjs` (its count asserts are the
  acceptance test) + derive-scope smoke.
- **M8 corp ripple + close**: bump corp's policypress input; `nix run .#praxis-policy-gaps`
  — the 40 "absent from PolicyPress SCF catalog" ids disappear as a class; close corp #12;
  optionally rename local dirs (oracle → scf-api-hackidle-oracle, scf-api-sc2in → scf-api).

## Risks

- Consumer hardcodes: only praxis' `scf-2026-1-1.json` filename (kept); later hardening:
  resolve via `.scf-version` in generate-facts.py.
- rapidfuzz drift vs manual header knowledge → committed reconciliation manifest makes every
  match auditable per release.
- Future sheet renames → pattern resolution + `sheet-resolve` fail check surfaces them as a
  validation issue (autopilot summons the human) instead of silent mis-parse.

## Verification (end-to-end, after M8)

New SCF release simulation: `workflow_dispatch` with the current tag + force → autopilot
no-ops cleanly; with a doctored workbook (via $SCF_WORKBOOK integration path) containing a
dangling id → validation fails, issue opens, nothing pushed. praxis/policypress/grc all
build green against sc2in/scf-api with zero facts.json diff, 1,468-control catalog, and
passing import asserts respectively.
