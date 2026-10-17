# AGENTS.md — fixing this repo when a new SCF release breaks it

Read `CLAUDE.md` for the rules (clean-room, no commits unless asked, determinism). This file
is the short operating guide for **small-context agents** (24GB local models, 64-128k
context). Keep your context lean: never `cat` big files, never open the full validation
report, never print a whole sheet. Use the bounded tools below.

## What this repo does

SCF Excel workbook → `src/scf_api/parse.py` → validation gate (`validate.py`) → `data/*.json`
→ `build.py` → `docs/api/**`. Upstream renames tabs/headers and restructures columns almost
every release. A release breaks us when the parser cannot find a tab/column, or reads the
wrong column and the gate fails with thousands of nonsense findings.

## Run commands like this

```bash
nix develop -c python -m scf_api.cli <command>     # dev shell has openpyxl/rapidfuzz/pytest
```

| command | use |
|---|---|
| `diagnose --workbook W` | parse+validate; on a miss prints the closest real tabs/headers and the fix location |
| `triage` | validation report grouped by check (counts, 3 samples, hint). Use this, not the JSON |
| `headers --workbook W --sheet SUBSTR [--grep TEXT] [--sample]` | one line per column; `--sample` shows first data row |
| `all --workbook W` | parse → validate → write `data/` → build `docs/` → bump `.scf-version` |
| `fetch` | download the latest upstream workbook into `workbooks/` (needs `gh`) |

## The loop (details in `.claude/skills/scf-release-fix/SKILL.md`)

1. `diagnose` → fix the ONE thing it names → `diagnose` again. Repeat until it says PARSED.
2. If the gate passed but counts look wrong, or the gate fails on thousands of rows, a column
   was misread: use `headers --sample` and read `.claude/skills/scf-workbook-recon/SKILL.md`.
3. Add the new shape to the synthetic fixture (`tests/conftest.py`) + a test, and a
   `GROUND_TRUTH` row in `tests/test_integration_real.py`.
4. Regenerate and verify (`.claude/skills/scf-regenerate/SKILL.md`): `nix fmt && nix flake check -L`.

## Rules that save you from yourself

- **Add, never replace.** New header/tab name goes FIRST, the old name stays (`alts=(...)`,
  ordered tuples in `SHEET_PATTERNS`). One parser must read every supported release.
- **Never hard-code a version** (`"2026.3"`, `"scf 2026.3"`) in a pattern. Tab names embed
  the version; match the stable part.
- **Do not weaken the gate to go green**: no deleting tests, no loosening validators, no
  overrides for anything except a genuine upstream workbook typo (with a written reason).
- **Do not hand-edit `data/` or `docs/`**; regenerate them.
- Output contract change (new/removed/renamed JSON fields) = stop and ask the human.
- No commits, no `git push`. `git add -N data docs` is fine (nix only sees tracked files).

## When to stop and hand back to the human

- The gate reports a real cross-sheet inconsistency (ids that exist in no catalog, after you
  have confirmed the right column is being read).
- A fix needs a contract change, or you have tried 3 different fixes for the same miss.
- Counts changed by >20% and `headers --sample` does not explain why.

Write the handoff as: what broke (tab/column), what you tried, `triage` output, the next
question for the human. Keep it under 30 lines.
