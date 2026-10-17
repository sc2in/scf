---
name: scf-regenerate
description: Regenerate data/, docs/ and the validation report for a new SCF version once the parser reads it, add tests/ground truth, update the changelog, and run the full verification. Use after scf-release-fix reaches PARSED with 0 fails.
---

# Regenerate and verify (no commits)

1. **Tests first.** Extend `tests/conftest.py` `build_workbook` with the new shape (a
   `layout-<version>` flag like `layout-2026-3`; keep older layouts intact) and add tests in
   `tests/test_parse.py` proving the same synthetic content parses identically across layouts.
   Add the new `GROUND_TRUTH` row in `tests/test_integration_real.py` from `diagnose` counts
   (controls, families, frameworks, aos, erls, compensating, privacy, threats, risks).
2. **Run the suite** (real workbook included):
   `SCF_WORKBOOK=workbooks/<file>.xlsx nix develop -c python -m pytest -q`
3. **Regenerate:**
   `nix develop -c python -m scf_api.cli all --workbook workbooks/<file>.xlsx`
   This writes `data/`, prunes the old `scf-<old>.json`, rebuilds `docs/`, rewrites
   `.scf-version` and `validation/validation-report.json`. Expect exit 0 and `fail: 0`.
4. **Make new files visible to nix:** `git add -N data docs` (flake checks only see tracked files).
5. **Changelog:** build the old dataset into a scratch dir
   (`mkdir -p $SCRATCH/old; for f in $(git ls-tree --name-only HEAD data/ | grep json); do git show HEAD:$f > $SCRATCH/old/$(basename $f); done`),
   run `changelog $SCRATCH/old data`, and put under a new top section of `CHANGELOG.md`,
   with a short hand-written summary of what upstream changed and how we absorbed it.
6. **Docs/README:** if output fields were added, mention them in the CHANGELOG; contract
   additions must be optional in `src/scf_api/schemas/*.schema.json`.
7. **Verify:** `nix fmt && nix flake check -L` must end with `all checks passed!`.
8. If an override became unused (upstream fixed a typo), scope it with `applies_to` to the
   older versions instead of deleting it.

Report to the human: version, counts, any new warnings, anything that needed a judgement
call (especially mapping semantics). Do not commit.
