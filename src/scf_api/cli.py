"""scf-api CLI: fetch | parse | validate | build | changelog | verify-tree | all.

The pipeline contract (autopilot depends on these exit codes):
- `parse` writes data/ ONLY when the validation gate passes (overrides
  applied); on unresolved fail-severity findings it writes the report,
  prints the summary, and exits 1.
- `validate` re-checks a committed data/ directory hermetically (schemas +
  referential integrity) — the `data-valid` flake check.
- `build` regenerates docs/ from data/ deterministically — `docs-fresh`
  diffs its output.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from . import jsonio
from .build import build_docs, find_catalog
from .changelog import generate_changelog
from .overrides import load_overrides
from .parse import parse_workbook
from .report import build_report, human_summary, write_report
from .schemas import validate_schemas
from .validate import validate_data_dir, validate_result
from .verify_tree import compare_trees, load_allowlist
from .workbook import ColumnResolveError, SheetResolveError

_VERSION_RE = re.compile(r"(\d{4})[.\-](\d+)(?:[.\-](\d+))?")


def infer_version(filename: str) -> str | None:
    m = _VERSION_RE.search(filename)
    if not m:
        return None
    parts = [g for g in m.groups() if g is not None]
    return ".".join(parts)


def _cmd_fetch(args: argparse.Namespace) -> int:
    from .fetch import fetch_workbook

    result = fetch_workbook(Path(args.dest), tag=args.tag)
    print(
        json.dumps(
            {
                "version": result.version,
                "tag": result.tag,
                "path": str(result.path),
                "sha256": result.sha256,
            }
        )
    )
    return 0


def _run_parse(
    workbook: Path,
    version: str,
    out_dir: Path | None,
    overrides_path: Path | None,
    report_path: Path | None,
) -> int:
    overrides = load_overrides(overrides_path)
    try:
        result = parse_workbook(workbook, version)
    except (SheetResolveError, ColumnResolveError) as exc:
        report = build_report(
            version,
            "",
            _structural_failure(str(exc)),
            {},
            str(workbook),
        )
        if report_path:
            write_report(report, report_path)
        print(f"FATAL structure error: {exc}", file=sys.stderr)
        return 1

    outcome = validate_result(result, overrides)
    report = build_report(version, result.workbook_sha256, outcome, result.manifest, str(workbook))
    if report_path:
        write_report(report, report_path)

    summary = outcome.summary()
    print(f"validation: {summary}", file=sys.stderr)
    if not outcome.ok:
        print(human_summary(report), file=sys.stderr)
        return 1

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, obj in result.files.items():
            jsonio.write(out_dir / name, obj)
        print(f"wrote {len(result.files)} data files to {out_dir}", file=sys.stderr)
    return 0


def _structural_failure(message: str):
    from .validate import FAIL, Finding, ValidationOutcome

    outcome = ValidationOutcome()
    check = "sheet-resolve" if "sheet" in message.lower() else "col-resolve"
    outcome.findings.append(
        Finding(check=check, severity=FAIL, message=message, owner="", value="")
    )
    return outcome


def _cmd_parse(args: argparse.Namespace) -> int:
    version = args.scf_version or infer_version(Path(args.workbook).name)
    if not version:
        print("cannot infer --scf-version from workbook filename", file=sys.stderr)
        return 2
    return _run_parse(
        Path(args.workbook),
        version,
        Path(args.out),
        Path(args.overrides) if args.overrides else None,
        Path(args.report) if args.report else None,
    )


def _cmd_validate(args: argparse.Namespace) -> int:
    data_dir = Path(args.data)
    version = args.scf_version
    if not version:
        _, version = find_catalog(data_dir)
    schema_errors = validate_schemas(data_dir)
    for err in schema_errors:
        print(f"schema: {err}", file=sys.stderr)

    overrides = load_overrides(Path(args.overrides) if args.overrides else None)
    outcome = validate_data_dir(data_dir, overrides, version)
    report = build_report(version, "", outcome, {}, None)
    if args.report:
        write_report(report, Path(args.report))
    summary = outcome.summary()
    print(f"validation: {summary}", file=sys.stderr)
    if schema_errors or not outcome.ok:
        for f in outcome.findings:
            if f.unresolved_fail:
                print(f"FAIL {f.check}: {f.message}", file=sys.stderr)
        return 1
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    summary = build_docs(Path(args.data), Path(args.out))
    print(
        f"built docs for SCF {summary['scf_version']}: "
        f"{summary['total_controls']} controls, "
        f"{summary['total_families']} families",
        file=sys.stderr,
    )
    return 0


def _cmd_changelog(args: argparse.Namespace) -> int:
    print(generate_changelog(Path(args.old), Path(args.new)))
    return 0


def _cmd_verify_tree(args: argparse.Namespace) -> int:
    allowlist = load_allowlist(Path(args.allowlist) if args.allowlist else None)
    diffs = compare_trees(Path(args.ours), Path(args.theirs), allowlist)
    if diffs:
        for d in diffs:
            print(d)
        print(f"{len(diffs)} difference(s)", file=sys.stderr)
        return 1
    print("trees are semantically equivalent", file=sys.stderr)
    return 0


def _cmd_all(args: argparse.Namespace) -> int:
    if args.workbook:
        workbook = Path(args.workbook)
        version = args.scf_version or infer_version(workbook.name)
    else:
        from .fetch import fetch_workbook

        fetched = fetch_workbook(Path(args.workdir), tag=args.tag)
        workbook, version = fetched.path, fetched.version
    if not version:
        print("cannot determine SCF version", file=sys.stderr)
        return 2

    data_dir = Path(args.data)
    rc = _run_parse(
        workbook,
        version,
        data_dir,
        Path(args.overrides) if args.overrides else None,
        Path(args.report) if args.report else None,
    )
    if rc != 0:
        return rc
    build_docs(data_dir, Path(args.docs))
    Path(args.version_file).write_text(version + "\n", encoding="utf-8")
    print(f"SCF {version}: data + docs built", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scf-api", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fetch", help="download the workbook from the upstream release")
    p.add_argument("--tag", default=None, help="release tag (default: latest)")
    p.add_argument("--dest", default="workbooks", help="download directory")
    p.set_defaults(func=_cmd_fetch)

    p = sub.add_parser("parse", help="workbook -> validated data/*.json (hard gate)")
    p.add_argument("--workbook", required=True)
    p.add_argument("--scf-version", default=None)
    p.add_argument("--out", default="data")
    p.add_argument("--overrides", default="overrides/overrides.json")
    p.add_argument("--report", default="validation/validation-report.json")
    p.set_defaults(func=_cmd_parse)

    p = sub.add_parser("validate", help="re-check a committed data/ dir (JSON-input mode)")
    p.add_argument("--data", default="data")
    p.add_argument("--scf-version", default=None)
    p.add_argument("--overrides", default=None)
    p.add_argument("--report", default=None)
    p.set_defaults(func=_cmd_validate)

    p = sub.add_parser("build", help="data/ -> docs/ static API tree")
    p.add_argument("--data", default="data")
    p.add_argument("--out", default="docs")
    p.set_defaults(func=_cmd_build)

    p = sub.add_parser("changelog", help="markdown diff between two data dirs")
    p.add_argument("old")
    p.add_argument("new")
    p.set_defaults(func=_cmd_changelog)

    p = sub.add_parser("verify-tree", help="semantic JSON compare of two docs/api trees")
    p.add_argument("ours")
    p.add_argument("theirs")
    p.add_argument("--allowlist", default=None)
    p.set_defaults(func=_cmd_verify_tree)

    p = sub.add_parser("all", help="fetch -> parse -> validate -> build")
    p.add_argument("--workbook", default=None, help="skip fetch, use this workbook")
    p.add_argument("--tag", default=None)
    p.add_argument("--scf-version", default=None)
    p.add_argument("--workdir", default="workbooks")
    p.add_argument("--data", default="data")
    p.add_argument("--docs", default="docs")
    p.add_argument("--overrides", default="overrides/overrides.json")
    p.add_argument("--report", default="validation/validation-report.json")
    p.add_argument("--version-file", default=".scf-version")
    p.set_defaults(func=_cmd_all)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
