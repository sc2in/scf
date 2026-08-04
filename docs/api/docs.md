# SCF API Reference

Static JSON API for the [Secure Controls Framework](https://securecontrolsframework.com) (SCF) v2026.2,
maintained by SC2 (sc2in/scf).

- **1534** controls across **34** families
- **252** framework crosswalks
- **42** threats, **39** risks
- **5956** assessment objectives, **316** evidence requests
- **1371** compensating controls, **258** privacy principles
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
| AAT | Artificial Intelligence & Autonomous Technologies | 161 |
| AST | Asset Management | 64 |
| BCD | Business Continuity & Disaster Recovery | 59 |
| CAP | Capacity & Performance Planning | 6 |
| CFG | Configuration Management | 32 |
| CHG | Change Management | 20 |
| CLD | Cloud Security | 24 |
| CPL | Compliance | 41 |
| CRY | Cryptographic Protections | 29 |
| DCH | Data Classification & Handling | 85 |
| EMB | Embedded Technology | 19 |
| END | Endpoint Security | 47 |
| GOV | Security, Compliance & Resilience Governance | 42 |
| HRS | Human Resources Security | 46 |
| IAC | Identification & Authentication | 116 |
| IAO | Information Assurance | 15 |
| IRO | Incident Response | 44 |
| MDM | Mobile Device Management | 11 |
| MNT | Maintenance | 28 |
| MON | Continuous Monitoring | 71 |
| NET | Network Security | 100 |
| OPS | Security Operations | 8 |
| PES | Physical & Environmental Security | 51 |
| PRI | Data Privacy | 103 |
| PRM | Project & Resource Management | 11 |
| QTS | Quantum Security | 34 |
| RSK | Risk Management | 33 |
| SAT | Security Awareness & Training | 18 |
| SEA | Secure Engineering & Architecture | 47 |
| TDA | Technology Development & Acquisition | 74 |
| THR | Threat Management | 15 |
| TPM | Third-Party Management | 31 |
| VPM | Vulnerability & Patch Management | 34 |
| WEB | Web Security | 15 |

Data: Control identifiers, titles, and crosswalk references from the Secure Controls Framework (SCF), https://securecontrolsframework.com, licensed CC BY-ND 4.0.
