"""JSON writing conventions for every generated artifact.

2-space indent, insertion-order keys, raw unicode (no \\uXXXX escapes), and
no trailing newline — the exact shape consumers already parse. Determinism
is sacred: same input -> byte-identical output.
"""

from __future__ import annotations

import json
from pathlib import Path


def dumps(obj: object) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def write(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(obj), encoding="utf-8")


def read(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))
