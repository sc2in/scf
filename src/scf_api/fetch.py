"""Fetch the SCF workbook from the upstream GitHub release.

Uses the `gh` CLI (already authenticated in CI and dev shells) rather than
raw HTTP: release assets on securecontrolsframework/securecontrolsframework
are the canonical distribution. Records the sha256 so the validation report
pins exactly which bytes were parsed.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

UPSTREAM_REPO = "securecontrolsframework/securecontrolsframework"


@dataclass
class FetchResult:
    version: str  # dotted, e.g. 2026.1.1
    tag: str  # release tag as published
    path: Path  # downloaded workbook
    sha256: str


def _gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def latest_release_tag(repo: str = UPSTREAM_REPO) -> str:
    out = _gh("release", "view", "--repo", repo, "--json", "tagName")
    return json.loads(out)["tagName"]


def normalize_version(tag: str) -> str:
    return tag.lstrip("vV").strip()


def fetch_workbook(
    dest_dir: Path,
    tag: str | None = None,
    repo: str = UPSTREAM_REPO,
) -> FetchResult:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    if tag is None:
        tag = latest_release_tag(repo)

    assets = json.loads(_gh("release", "view", tag, "--repo", repo, "--json", "assets"))["assets"]
    xlsx = [a["name"] for a in assets if a["name"].lower().endswith(".xlsx")]
    if not xlsx:
        raise FileNotFoundError(f"release {tag} of {repo} has no .xlsx asset")
    name = sorted(xlsx)[0]

    target = dest_dir / name
    if target.exists():
        target.unlink()
    _gh(
        "release",
        "download",
        tag,
        "--repo",
        repo,
        "--pattern",
        name,
        "--dir",
        str(dest_dir),
    )
    sha256 = hashlib.sha256(target.read_bytes()).hexdigest()
    return FetchResult(
        version=normalize_version(tag),
        tag=tag,
        path=target,
        sha256=sha256,
    )
