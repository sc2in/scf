"""data/*.json -> docs/ static API tree (GitHub Pages).

Every JSON endpoint is derived purely from data/; rebuilding must be
byte-identical (the docs-fresh check). The human-facing pages (index.html,
docs.md, llms.txt) are SC2-branded but equally deterministic.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from . import jsonio

CATALOG_RE = re.compile(r"scf-(\d{4}(?:-\d+)+)\.json$")

ATTRIBUTION = (
    "Control identifiers, titles, and crosswalk references from the "
    "Secure Controls Framework (SCF), https://securecontrolsframework.com, "
    "licensed CC BY-ND 4.0."
)


def find_catalog(data_dir: Path) -> tuple[Path, str]:
    """Locate the version-named catalog file; returns (path, dotted version)."""
    for path in sorted(data_dir.glob("scf-*.json")):
        m = CATALOG_RE.match(path.name)
        if m:
            return path, m.group(1).replace("-", ".")
    raise FileNotFoundError(f"no scf-<version>.json catalog in {data_dir}")


def build_docs(data_dir: Path, out_dir: Path) -> dict:
    """Build the docs/ tree. Returns the summary object (for reporting)."""
    data_dir, out_dir = Path(data_dir), Path(out_dir)
    catalog_path, version = find_catalog(data_dir)
    catalog = jsonio.read(catalog_path)
    aos = jsonio.read(data_dir / "scf-assessment-objectives.json")
    compensating = jsonio.read(data_dir / "scf-compensating-controls.json")
    crosswalks = jsonio.read(data_dir / "scf-crosswalks.json")
    evidence = jsonio.read(data_dir / "scf-evidence-requests.json")
    privacy = jsonio.read(data_dir / "scf-privacy-principles.json")
    risks = jsonio.read(data_dir / "scf-risks.json")
    threats = jsonio.read(data_dir / "scf-threats.json")
    # Only releases whose workbook has a Legacy SCF # column (2026.3+).
    legacy_path = data_dir / "scf-legacy-map.json"
    legacy = jsonio.read(legacy_path) if legacy_path.exists() else None

    if out_dir.exists():
        shutil.rmtree(out_dir)
    api = out_dir / "api"
    api.mkdir(parents=True)

    families: dict[str, str] = catalog["families"]
    controls: list[dict] = catalog["controls"]

    # Per-control crosswalks: framework order follows scf_to_framework
    # (Authoritative Sources sheet order).
    xwalk_by_control: dict[str, dict[str, list[str]]] = {}
    for fw_id, mapping in crosswalks["scf_to_framework"].items():
        for cid, refs in mapping.items():
            xwalk_by_control.setdefault(cid, {})[fw_id] = refs

    enriched: list[dict] = []
    for c in controls:
        e = dict(c)
        e["family_name"] = families.get(c["family"], "")
        e["crosswalks"] = xwalk_by_control.get(c["control_id"], {})
        enriched.append(e)

    # controls
    jsonio.write(api / "controls.json", {"total": len(enriched), "controls": enriched})
    for e in enriched:
        jsonio.write(api / "controls" / f"{e['control_id']}.json", e)

    # families
    family_counts: dict[str, int] = {}
    for c in controls:
        family_counts[c["family"]] = family_counts.get(c["family"], 0) + 1
    family_index = [
        {
            "family_code": code,
            "family_name": families.get(code, ""),
            "control_count": family_counts[code],
        }
        for code in sorted(family_counts)
    ]
    jsonio.write(
        api / "families.json",
        {
            "total_families": len(family_index),
            "total_controls": len(controls),
            "families": family_index,
        },
    )
    for entry in family_index:
        code = entry["family_code"]
        jsonio.write(
            api / "families" / f"{code}.json",
            {
                **entry,
                "controls": [e for e in enriched if e["family"] == code],
            },
        )

    # crosswalks
    display_names: dict[str, str] = crosswalks["metadata"]["framework_display_names"]
    framework_index = [
        {
            "framework_id": fw_id,
            "display_name": display_names.get(fw_id, fw_id),
            "scf_controls_mapped": len(crosswalks["scf_to_framework"][fw_id]),
            "framework_controls_mapped": len(crosswalks["framework_to_scf"][fw_id]),
        }
        for fw_id in sorted(crosswalks["scf_to_framework"])
    ]
    jsonio.write(
        api / "crosswalks.json",
        {"total_frameworks": len(framework_index), "frameworks": framework_index},
    )
    for fw_id in sorted(crosswalks["scf_to_framework"]):
        forward = crosswalks["scf_to_framework"][fw_id]
        reverse = crosswalks["framework_to_scf"][fw_id]
        jsonio.write(
            api / "crosswalks" / f"{fw_id}.json",
            {
                "framework_id": fw_id,
                "display_name": display_names.get(fw_id, fw_id),
                "scf_to_framework": {"total_mappings": len(forward), "mappings": forward},
                "framework_to_scf": {"total_mappings": len(reverse), "mappings": reverse},
            },
        )

    # assessment objectives (aggregate mirrors the data file byte-for-byte)
    jsonio.write(api / "assessment-objectives.json", aos)
    aos_by_control: dict[str, list[dict]] = {}
    for a in aos["assessment_objectives"]:
        aos_by_control.setdefault(a["scf_control_id"], []).append(a)
    for c in controls:
        cid = c["control_id"]
        records = aos_by_control.get(cid, [])
        jsonio.write(
            api / "assessment-objectives" / f"{cid}.json",
            {"scf_control_id": cid, "total": len(records), "assessment_objectives": records},
        )

    # evidence requests
    jsonio.write(api / "evidence-requests.json", evidence)
    for e in evidence["evidence_requests"]:
        jsonio.write(api / "evidence-requests" / f"{e['erl_id']}.json", e)

    # compensating controls
    jsonio.write(api / "compensating-controls.json", compensating)
    for r in compensating["compensating_controls"]:
        jsonio.write(api / "compensating-controls" / f"{r['control_id']}.json", r)

    # privacy principles (aggregate only)
    jsonio.write(api / "privacy-principles.json", privacy)

    # risks & threats
    jsonio.write(api / "risks.json", risks)
    for r in risks["risks"]:
        jsonio.write(api / "risks" / f"{r['risk_id']}.json", r)
    jsonio.write(api / "threats.json", threats)
    for t in threats["threats"]:
        jsonio.write(api / "threats" / f"{t['threat_id']}.json", t)

    # legacy id map (mirrors the data file byte-for-byte)
    if legacy is not None:
        jsonio.write(api / "legacy-map.json", legacy)

    # summary
    weight_distribution: dict[str, int] = {}
    for c in controls:
        key = str(c["relative_weight"])
        weight_distribution[key] = weight_distribution.get(key, 0) + 1
    summary = {
        "scf_version": version,
        "total_controls": len(controls),
        "total_families": len(family_index),
        "families": family_index,
        "crosswalk_frameworks": framework_index,
        "total_threats": threats["total"],
        "total_risks": risks["total"],
        "total_assessment_objectives": aos["total"],
        "total_evidence_requests": evidence["total"],
        "total_compensating_controls": compensating["total"],
        "total_privacy_principles": privacy["total"],
        "weight_distribution": {
            k: weight_distribution[k] for k in sorted(weight_distribution, key=int)
        },
    }
    jsonio.write(api / "summary.json", summary)

    _write_static_pages(out_dir, summary, legacy)
    return summary


# ---------------------------------------------------------------------------
# Human/agent-facing pages (SC2-branded, deterministic)
# ---------------------------------------------------------------------------


def _write_static_pages(out_dir: Path, s: dict, legacy: dict | None = None) -> None:
    version = s["scf_version"]
    stats = (
        f"{s['total_controls']} controls, {s['total_families']} families, "
        f"{len(s['crosswalk_frameworks'])} framework crosswalks, "
        f"{s['total_threats']} threats, {s['total_risks']} risks, "
        f"{s['total_assessment_objectives']} assessment objectives, and "
        f"{s['total_evidence_requests']} evidence requests"
    )

    endpoints = [
        ("summary", "summary.json", "Version, all counts, weight distribution."),
        ("controls", "controls.json", "All controls with full metadata and crosswalks."),
        ("families", "families.json", "Family index."),
        ("crosswalks", "crosswalks.json", "Framework index."),
        ("threats", "threats.json", "Threat catalog."),
        ("risks", "risks.json", "Risk catalog."),
        ("assessment-objectives", "assessment-objectives.json", "All assessment objectives."),
        ("evidence-requests", "evidence-requests.json", "Evidence request list."),
        ("compensating-controls", "compensating-controls.json", "Compensating control guidance."),
        ("privacy-principles", "privacy-principles.json", "Data privacy management principles."),
    ]
    if legacy is not None:
        endpoints.append(
            (
                "legacy-map",
                "legacy-map.json",
                f"Old→new control ids, SCF {legacy['from_version']} → {legacy['to_version']}.",
            )
        )
    details = [
        ("api/controls/{ID}.json", "single control (e.g., GOV-01)"),
        ("api/families/{CODE}.json", "family detail (e.g., GOV)"),
        ("api/crosswalks/{FW_ID}.json", "bidirectional crosswalk"),
        ("api/threats/{ID}.json", "single threat (e.g., NT-1)"),
        ("api/risks/{ID}.json", "single risk (e.g., R-AC-1)"),
        ("api/assessment-objectives/{SCF_ID}.json", "AOs for a control"),
        ("api/evidence-requests/{ERL_ID}.json", "evidence request (e.g., E-GOV-01)"),
        ("api/compensating-controls/{SCF_ID}.json", "compensating controls"),
    ]

    llms = [
        "# SCF API (sc2in/scf)",
        "",
        f"> Source-faithful static JSON API for the Secure Controls Framework (SCF) "
        f"v{version}. {stats}. All static JSON, no auth required.",
        "",
        "All data is static JSON. Append paths to the base URL.",
        "",
    ]
    llms += [f"- `{path}` — {desc}" for path, desc in details]
    llms += ["", "## Endpoints", ""]
    llms += [f"- [{name}](api/{fn}): {desc}" for name, fn, desc in endpoints]
    llms += [
        "",
        "## Documentation",
        "",
        "- [API Reference](api/docs.md): Endpoint reference.",
        "- [Complete Documentation](llms-full.txt): Everything in one file.",
        "",
        f"Data: {ATTRIBUTION}",
    ]
    (out_dir / "llms.txt").write_text("\n".join(llms) + "\n", encoding="utf-8")

    md = [
        "# SCF API Reference",
        "",
        f"Static JSON API for the [Secure Controls Framework]"
        f"(https://securecontrolsframework.com) (SCF) v{version},",
        "maintained by SC2 (sc2in/scf).",
        "",
        f"- **{s['total_controls']}** controls across **{s['total_families']}** families",
        f"- **{len(s['crosswalk_frameworks'])}** framework crosswalks",
        f"- **{s['total_threats']}** threats, **{s['total_risks']}** risks",
        f"- **{s['total_assessment_objectives']}** assessment objectives, "
        f"**{s['total_evidence_requests']}** evidence requests",
        f"- **{s['total_compensating_controls']}** compensating controls, "
        f"**{s['total_privacy_principles']}** privacy principles",
        "- All static JSON, no auth, CC BY-ND.",
        "",
        "## Endpoints",
        "",
    ]
    for name, fn, desc in endpoints:
        md.append(f"### {name}")
        md.append("")
        md.append(f"`GET api/{fn}` — {desc}")
        md.append("")
    md += ["## Detail endpoints", ""]
    md += [f"- `GET {path}` — {desc}" for path, desc in details]
    md += [
        "",
        "## Families",
        "",
        "| code | family | controls |",
        "|---|---|---|",
    ]
    md += [
        f"| {f['family_code']} | {f['family_name']} | {f['control_count']} |"
        for f in s["families"]
    ]
    md += ["", f"Data: {ATTRIBUTION}"]
    (out_dir / "api" / "docs.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    full = ["\n".join(llms), "", "---", "", "\n".join(md), "", "---", "", "## Frameworks", ""]
    full += [
        f"- `{f['framework_id']}` — {f['display_name']} "
        f"({f['scf_controls_mapped']} SCF controls, "
        f"{f['framework_controls_mapped']} framework controls)"
        for f in s["crosswalk_frameworks"]
    ]
    (out_dir / "llms-full.txt").write_text("\n".join(full) + "\n", encoding="utf-8")

    tiles = [
        (f"{s['total_controls']:,}", "controls"),
        (str(s["total_families"]), "families"),
        (str(len(s["crosswalk_frameworks"])), "crosswalks"),
        (f"{s['total_assessment_objectives']:,}", "assessment objectives"),
        (str(s["total_evidence_requests"]), "evidence requests"),
        (str(f"{s['total_compensating_controls']:,}"), "compensating controls"),
    ]
    tile_divs = "\n".join(
        f'      <div class="tile"><span class="n">{n}</span><span class="l">{label}</span></div>'
        for n, label in tiles
    )
    endpoint_rows = "\n".join(
        f'      <tr><td><a href="api/{fn}"><code>api/{fn}</code></a></td><td>{desc}</td></tr>'
        for name, fn, desc in endpoints
    )
    detail_rows = "\n".join(
        f"      <tr><td><code>{path}</code></td><td>{desc}</td></tr>" for path, desc in details
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SCF API — SC2</title>
  <meta name="description" content="Validated static JSON API for the Secure Controls Framework. {stats}." />
  <style>
    :root {{
      --bg: #1e1e2e; --surface: #27273a; --border: #3b3b54;
      --fg: #cdd6f4; --muted: #a6adc8; --faint: #6c7086;
      --accent: #89b4fa; --accent-2: #b4befe; --ok: #a6e3a1;
    }}
    @media (prefers-color-scheme: light) {{
      :root {{
        --bg: #f7f7fb; --surface: #ffffff; --border: #dcdce6;
        --fg: #24243a; --muted: #55556e; --faint: #8a8aa0;
        --accent: #2455c3; --accent-2: #1a3f94; --ok: #256d3b;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui, sans-serif; background: var(--bg); color: var(--fg);
           max-width: 760px; margin: 0 auto; padding: 3rem 1.25rem 2rem; line-height: 1.6; }}
    h1 {{ font-size: 1.6rem; margin: 0 0 0.25rem; letter-spacing: -0.01em; }}
    h1 .v {{ font-size: 0.8rem; font-weight: 600; color: var(--ok); border: 1px solid var(--border);
             border-radius: 999px; padding: 0.1rem 0.6rem; vertical-align: 0.25em; margin-left: 0.5rem; }}
    h2 {{ color: var(--muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em;
          margin: 2rem 0 0.6rem; }}
    p {{ color: var(--muted); margin: 0.5rem 0 0.75rem; font-size: 0.95rem; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ color: var(--accent-2); text-decoration: underline; }}
    code {{ color: var(--ok); font-size: 0.85em; }}
    .tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
              gap: 0.6rem; margin-top: 1.25rem; }}
    .tile {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
             padding: 0.7rem 0.9rem; display: flex; flex-direction: column; }}
    .tile .n {{ font-size: 1.25rem; font-weight: 700; font-variant-numeric: tabular-nums; }}
    .tile .l {{ font-size: 0.75rem; color: var(--faint); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
    td {{ padding: 0.35rem 0.5rem 0.35rem 0; vertical-align: top; border-bottom: 1px solid var(--border); }}
    td:last-child {{ color: var(--muted); }}
    pre {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
           padding: 0.8rem 1rem; overflow-x: auto; font-size: 0.85rem; line-height: 1.5; }}
    pre code {{ color: var(--fg); }}
    pre .c {{ color: var(--faint); }}
    .sub {{ color: var(--faint); font-size: 0.8rem; margin-top: 2.5rem; border-top: 1px solid var(--border);
            padding-top: 1rem; }}
    .sub a {{ color: var(--faint); text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>SCF API<span class="v">v{version}</span></h1>
  <p>The <a href="https://securecontrolsframework.com">Secure Controls Framework</a> as a validated,
  versioned, static JSON API — parsed from the official SCF workbook, gated on cross-sheet
  referential integrity, and rebuilt automatically on every upstream release.
  No auth, no rate limits, plain files.</p>

  <div class="tiles">
{tile_divs}
  </div>

  <h2>Try it</h2>
  <pre><code><span class="c"># one control, with its framework crosswalks</span>
curl -s https://sc2in.github.io/scf/api/controls/GOV-01.json | jq .title

<span class="c"># everything SCF maps to NIST SP 800-53 R5</span>
curl -s https://sc2in.github.io/scf/api/crosswalks/general-nist-800-53-r5-2.json | jq .scf_to_framework</code></pre>

  <h2>Endpoints</h2>
  <table>
{endpoint_rows}
  </table>

  <h2>Detail endpoints</h2>
  <table>
{detail_rows}
  </table>

  <h2>Agents</h2>
  <p><a href="llms.txt">llms.txt</a> &middot; <a href="llms-full.txt">llms-full.txt</a> &middot;
  <a href="api/docs.md">api/docs.md</a></p>

  <p class="sub">SCF v{version}, format-shifted verbatim from the official workbook —
  content &copy; <a href="https://securecontrolsframework.com">Secure Controls Framework Council</a>,
  CC BY-ND 4.0. Pipeline: <a href="https://github.com/sc2in/scf">sc2in/scf</a> (AGPL-3.0),
  maintained by SC2. Every release ships its validation report.</p>
</body>
</html>
"""
    (out_dir / "index.html").write_text(html, encoding="utf-8")
