# SCF API Reference

Static JSON API for the [Secure Controls Framework](https://securecontrolsframework.com) (SCF) v2026.3,
maintained by SC2 (sc2in/scf).

- **1591** controls across **34** families
- **270** framework crosswalks
- **45** threats, **65** risks
- **6446** assessment objectives, **422** evidence requests
- **1397** compensating controls, **263** privacy principles
- All static JSON, no auth, CC BY-ND.

## Endpoints

### summary

`GET api/summary.json` — Version, all counts, weight distribution.

### controls

`GET api/controls.json` — All controls with full metadata and crosswalks.

### families

`GET api/families.json` — Family index.

### crosswalks

`GET api/crosswalks.json` — Framework index.

### threats

`GET api/threats.json` — Threat catalog.

### risks

`GET api/risks.json` — Risk catalog.

### assessment-objectives

`GET api/assessment-objectives.json` — All assessment objectives.

### evidence-requests

`GET api/evidence-requests.json` — Evidence request list.

### compensating-controls

`GET api/compensating-controls.json` — Compensating control guidance.

### privacy-principles

`GET api/privacy-principles.json` — Data privacy management principles.

### legacy-map

`GET api/legacy-map.json` — Old→new control ids, SCF 2026.2 → 2026.3.

## Detail endpoints

- `GET api/controls/{ID}.json` — single control (e.g., GOV-01)
- `GET api/families/{CODE}.json` — family detail (e.g., GOV)
- `GET api/crosswalks/{FW_ID}.json` — bidirectional crosswalk
- `GET api/threats/{ID}.json` — single threat (e.g., NT-1)
- `GET api/risks/{ID}.json` — single risk (e.g., R-AC-1)
- `GET api/assessment-objectives/{SCF_ID}.json` — AOs for a control
- `GET api/evidence-requests/{ERL_ID}.json` — evidence request (e.g., E-GOV-01)
- `GET api/compensating-controls/{SCF_ID}.json` — compensating controls

## Families

| code | family | controls |
|---|---|---|
| AAT | Artificial Intelligence & Autonomous Technologies | 160 |
| AST | Asset Management | 64 |
| BCD | Business Continuity & Disaster Recovery | 61 |
| CAP | Capacity & Performance Planning | 8 |
| CFG | Configuration Management | 58 |
| CHG | Change Management | 20 |
| CLD | Cloud Security | 19 |
| CPL | Compliance | 48 |
| CRY | Cryptographic Protections | 27 |
| DCH | Data Classification & Handling | 94 |
| EMB | Embedded Technology | 27 |
| END | Endpoint Security | 31 |
| GOV | Security, Compliance & Resilience Governance | 37 |
| HRS | Human Resources Security | 45 |
| IAC | Identification & Authentication | 123 |
| IAO | Information Assurance | 17 |
| IRO | Incident Response | 48 |
| MDM | Mobile Device Management | 10 |
| MNT | Maintenance | 29 |
| MON | Continuous Monitoring | 76 |
| NET | Network Security | 103 |
| OPS | Security Operations | 11 |
| PES | Physical & Environmental Security | 51 |
| PRI | Data Privacy | 102 |
| PRM | Project & Resource Management | 15 |
| QTS | Quantum Security | 31 |
| RSK | Risk Management | 35 |
| SAT | Security Awareness & Training | 22 |
| SEA | Secure Engineering & Architecture | 40 |
| TDA | Technology Development & Acquisition | 74 |
| THR | Threat Management | 17 |
| TPM | Third-Party Management | 43 |
| VPM | Vulnerability & Patch Management | 32 |
| WEB | Web Security | 13 |

Data: Control identifiers, titles, and crosswalk references from the Secure Controls Framework (SCF), https://securecontrolsframework.com, licensed CC BY-ND 4.0.
