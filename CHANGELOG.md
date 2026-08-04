# Changelog

## SCF 2026.2

Upstream restructured the workbook: the **Authoritative Sources** tab was
renamed **Focal Documents**, and the compensating-controls **SCF Control #**
header was shortened to **SCF #**. Both broke the weekly autopilot (issues #1,
#2). Sheet and column resolution now accept an ordered list of historical
names, so one parser reads every supported release, and tab names are matched
with the same normalization column headers already got.

New this release: the **QTS** (Quantum Security) control family, threat **MT-28**
(mapped to nearly every control, which is why almost all controls show a
`threats` change), and 25 crosswalk frameworks — most of the churn is upstream
adding explicit year suffixes to framework names.

The MON-03.3 evidence-request typo is still present upstream, so its override
is no longer version-scoped (`mon-03.3-erl-typo`); the gate resolves it
automatically and will warn once upstream fixes it.

Equivalence against the archived hackIDLE/scf-api dataset stays frozen at
2026.1.1 — that archive has no 2026.2 to compare against. Parsing the 2026.1.1
workbook with this release still reproduces the committed 2026.1.1 dataset
byte-for-byte.

## SCF 2026.1.1 → 2026.2

### Controls

66 added, 0 removed, 1468 changed (1534 total)

**Added:** AAT-01.5, AAT-12.5, AAT-12.6, AAT-29.24, AAT-33, AST-05.2, CFG-09, CFG-09.1, CFG-09.2, CFG-09.3, CPL-03.8, GOV-01.4, GOV-10.1, GOV-19.3, GOV-21, IAC-01.4, IAC-15.10, NET-06.8, NET-06.9, PRI-01.12, QTS-01, QTS-01.1, QTS-01.2, QTS-01.3, QTS-01.4, QTS-02, QTS-02.1, QTS-02.2, QTS-02.3, QTS-03, QTS-03.1, QTS-03.2, QTS-03.3, QTS-03.4, QTS-04, QTS-04.1, QTS-04.2, QTS-04.3, QTS-05, QTS-05.1, QTS-05.2, QTS-06, QTS-06.1, QTS-06.10, QTS-06.2, QTS-06.3, QTS-06.4, QTS-06.5, QTS-06.6, QTS-06.7 …
**Changed:** AAT-01 (threats); AAT-01.1 (threats); AAT-01.2 (threats); AAT-01.3 (maturity, threats); AAT-01.4 (threats); AAT-02 (threats); AAT-02.1 (threats); AAT-02.2 (errata, threats); AAT-02.3 (errata, maturity, threats); AAT-02.4 (threats); AAT-03 (threats); AAT-03.1 (maturity, threats); AAT-03.2 (threats); AAT-04 (threats); AAT-04.1 (threats); AAT-04.2 (threats); AAT-04.3 (threats); AAT-04.4 (threats); AAT-05 (threats); AAT-06 (threats); AAT-07 (threats); AAT-07.1 (threats); AAT-07.2 (threats); AAT-07.3 (threats); AAT-08 (threats); AAT-09 (threats); AAT-09.1 (description, maturity, scf_question, threats); AAT-10 (maturity, threats); AAT-10.1 (maturity, threats); AAT-10.10 (maturity, threats); AAT-10.11 (maturity, threats); AAT-10.12 (maturity, threats); AAT-10.13 (maturity, threats); AAT-10.14 (maturity, threats); AAT-10.15 (maturity, threats); AAT-10.16 (maturity, threats); AAT-10.17 (maturity, scf_question, threats); AAT-10.18 (maturity, threats); AAT-10.19 (threats); AAT-10.2 (maturity, threats); AAT-10.3 (maturity, threats); AAT-10.4 (maturity, threats); AAT-10.5 (maturity, threats); AAT-10.6 (maturity, threats); AAT-10.7 (maturity, threats); AAT-10.8 (maturity, threats); AAT-10.9 (maturity, threats); AAT-11 (threats); AAT-11.1 (threats); AAT-11.2 (threats) …

### Assessment objectives

180 added, 0 removed, 4 changed (5956 total)

**Added:** AAT-01.5_A01, AAT-01.5_A02, AAT-01.5_A03, AAT-01.5_A04, AAT-01.5_A05, AAT-01.5_A06, AAT-01.5_A07, AAT-12.5_A01, AAT-12.6_A01, AAT-29.24_A01, AAT-29.24_A02, AAT-29.24_A03, AAT-29.24_A04, AAT-33_A01, AAT-33_A02, AAT-33_A03, AAT-33_A04, AST-05.2_A01, AST-05.2_A02, AST-05.2_A03, CFG-09.1_A01, CFG-09.2_A01, CFG-09.2_A02, CFG-09.2_A03, CFG-09.2_A04, CFG-09.3_A01, CFG-09_A01, CPL-03.8_A01, CPL-03.8_A02, GOV-01.4_A01, GOV-01.4_A02, GOV-10.1_A01, GOV-10.1_A02, GOV-19.3_A01, GOV-19.3_A02, GOV-19.3_A03, GOV-19.3_A04, GOV-21_A01, GOV-21_A02, GOV-21_A03, GOV-21_A04, GOV-21_A05, GOV-21_A06, GOV-21_A07, IAC-01.4_A01, IAC-01.4_A02, IAC-01.4_A03, IAC-15.10_A01, NET-06.8_A01, NET-06.8_A02 …
**Changed:** MON-03_A13 (scf_defined_parameters); RSK-01_A12 (scf_defined_parameters); RSK-09_A31 (scf_defined_parameters); TPM-05_A05 (scf_defined_parameters)

### Evidence requests

13 added, 0 removed, 3 changed (316 total)

**Added:** E-QTS-01, E-QTS-02, E-QTS-03, E-QTS-04, E-QTS-05, E-QTS-06, E-QTS-07, E-QTS-08, E-QTS-09, E-QTS-10, E-QTS-11, E-QTS-12, E-QTS-13
**Changed:** E-CPL-01 (scf_controls); E-SAT-05 (scf_controls); E-THR-03 (scf_controls)

### Threats

1 added, 0 removed, 1 changed (42 total)

**Added:** MT-28
**Changed:** MT-12 (description)

### Compensating controls

66 added, 0 removed, 0 changed (1371 total)

**Added:** AAT-01.5, AAT-12.5, AAT-12.6, AAT-29.24, AAT-33, AST-05.2, CFG-09, CFG-09.1, CFG-09.2, CFG-09.3, CPL-03.8, GOV-01.4, GOV-10.1, GOV-19.3, GOV-21, IAC-01.4, IAC-15.10, NET-06.8, NET-06.9, PRI-01.12, QTS-01, QTS-01.1, QTS-01.2, QTS-01.3, QTS-01.4, QTS-02, QTS-02.1, QTS-02.2, QTS-02.3, QTS-03, QTS-03.1, QTS-03.2, QTS-03.3, QTS-03.4, QTS-04, QTS-04.1, QTS-04.2, QTS-04.3, QTS-05, QTS-05.1, QTS-05.2, QTS-06, QTS-06.1, QTS-06.10, QTS-06.2, QTS-06.3, QTS-06.4, QTS-06.5, QTS-06.6, QTS-06.7 …

### Crosswalk frameworks

25 added, 22 removed, 65 with mapping changes (252 total)

**Added:** americas-can-osfi-self-assessment, americas-can-osfi-self-assessment-2, apac-aus-ism-2026-march, apac-jpn-appi-2020, apac-mys-bnm-rmit-2025, emea-aut-dpa-2018, emea-bel-act-30-2018, emea-esp-ccn-stic-825-2026, emea-eu-cyber-resilience-act-2024, emea-eu-cyber-resilience-act-annex-i-2024, emea-eu-psd2-2015, emea-gbr-dpa-2018, emea-hun-act-cxii-2011, emea-irl-dpa-2018, emea-isr-cmo-2-0, emea-isr-ppl-5741-2025, emea-ita-pdpc-2018, emea-pol-act-10-2018, emea-rus-152-fz-2025, general-mitre-att_ck-16-1, general-nist-800-172-r3, general-nist-800-172a-r3, general-nist-cswp-39, usa-federal-law-33-cfr-part-101-subpart-f, usa-state-nv-privacy-law-2023
**Removed:** amaericas-can-osfi-self-assessment, apac-aus-ism-2024-june, apac-aus-privacy-act-1998, apac-jpn-ppi-2020, emea-aut-fappd-2000, emea-bel-act-8-1992, emea-esp-boe-a-2022-7191, emea-esp-ccn-stic-825-2023, emea-esp-decree-1720-2007, emea-eu-cyber-resilience-act-2022, emea-eu-cyber-resilience-act-annexes-2022, emea-gbr-dpa-1998, emea-hun-isdfi-2011, emea-irl-dpa-2003, emea-isr-cmo-1-0, emea-isr-ppl-5741-1981, emea-ita-pdpc-2003, emea-pol-act-29-1997, emea-rus-federal-law-27-2006, emea-us-psd2-2015, general-mitre-att&ck-16-1, general-nist-800-172
**Mapping changes:** americas-arg-ppd-2018, americas-bhs-dpa-2003, americas-bmu-mba-coc-2020, americas-bra-lgpd-2018, americas-can-itsp-10-171-2025, americas-can-pipeda-2000, americas-chl-act-19628-1999, americas-col-law-1581-2012, americas-mex-fdpa-2010, apac-aus-cop-sitc-2020, apac-aus-privacy-principles-2026, apac-aus-ps-cps-230-2023, apac-aus-ps-cps-234-2019, apac-chn-csnip-2012, apac-chn-data-security-law-2021, apac-chn-pipl-2021, apac-hkg-pdo-2022, apac-ind-privacy-rules-2011, apac-jpn-ismap, apac-kor-pipa-2011, apac-mys-pdpa-2010, apac-nzl-hisf-microsmall-2023, apac-nzl-hisf-mlhsp-2023, apac-nzl-ism-3-9, apac-nzl-privacy-act-2020, apac-phl-dpa-2012, apac-sgp-cyber-hygiene-practice-2019, apac-sgp-mas-trm-2021, apac-sgp-pdpa-2012, apac-twn-pdpa-2025 …

## SCF 2026.1.1 — initial canonical release

First release of sc2in/scf: 1,468 controls across 33 families, 249
framework crosswalks, 5,776 assessment objectives, 303 evidence requests,
39 risks, 41 threats, 1,305 compensating controls, 258 privacy principles.

Proven equivalent to the archived hackIDLE/scf-api dataset at 2026.1.1
(independent clean-room reimplementation; praxis facts byte-proof + docs
tree proof), with two documented improvements: TDA-11.2 risks/threats carry
real values instead of the upstream "[object Object]" parser artifact, and
MON-03.3's evidence_requests drops the workbook's MON-03.2 control-id typo
(override mon-03.3-erl-typo-2026.1.1).
