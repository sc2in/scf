# Secure Controls Framework (SCF) — attribution & data policy

Everything in `data/` and `docs/` derives from the **Secure Controls
Framework**:

> <https://securecontrolsframework.com>

Control identifiers, titles, descriptions, family codes, framework crosswalk
references, assessment objectives, evidence requests, risk and threat
catalogs, compensating-control guidance, and privacy principles come from the
SCF master workbook, licensed **CC BY-ND 4.0**
(<https://creativecommons.org/licenses/by-nd/4.0/>).

Attribution (embed this wherever the data is consumed):

> Control identifiers, titles, and crosswalk references from the
> Secure Controls Framework (SCF), https://securecontrolsframework.com,
> licensed CC BY-ND 4.0.

## Faithfulness policy

- This repository **format-shifts** the official SCF Excel workbook into
  JSON; CC BY-ND 4.0 treats format-shifting as non-adaptation. Content is
  reproduced verbatim — never edited, reworded, or extended.
- The only permitted departures from the workbook are documented,
  version-scoped entries in `overrides/overrides.json`, each carrying its
  reason (unresolvable workbook inconsistencies found by the validation
  gate, e.g. a control id where an evidence-request id belongs).
- `validation/validation-report.json` records the workbook sha256 each
  release was generated from, plus every finding and override applied.

The SCF has carried a lot of practitioners through their careers, this
project's author included. Please use it, cite it, and support it in your
own work.
