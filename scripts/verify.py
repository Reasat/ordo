#!/usr/bin/env python3
"""
Structural checks on produced ontology YAML (Phase 9).

Usage:
  python scripts/verify.py --yaml ordo.yaml
  python scripts/verify.py --yaml ordo.yaml --expected-version "2026-04-02"
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter

import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Mondo source YAML structure")
    parser.add_argument("--yaml", type=str, required=True, dest="yaml_path")
    parser.add_argument("--expected-version", type=str, default=None)
    args = parser.parse_args()

    with open(args.yaml_path, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)

    errors: list[str] = []
    if not doc or not isinstance(doc, dict):
        print("FAIL: document is missing or not a mapping", file=sys.stderr)
        sys.exit(1)

    for key in ("title", "version"):
        val = doc.get(key)
        if val is None or not str(val).strip():
            errors.append(f"missing or empty {key!r}")

    if args.expected_version is not None and doc.get("version") != args.expected_version:
        errors.append(
            "version mismatch: expected "
            f"{args.expected_version!r}, got {doc.get('version')!r}"
        )

    terms = doc.get("terms")
    if not isinstance(terms, list):
        errors.append("terms must be a list")
        terms = []

    ids = [t.get("id") for t in terms if isinstance(t, dict)]
    id_counts = Counter(ids)
    dupes = sorted({i for i, c in id_counts.items() if c > 1 and i is not None})
    if dupes:
        shown = dupes[:20]
        suffix = "..." if len(dupes) > 20 else ""
        errors.append(f"duplicate term IDs ({len(dupes)}): {shown}{suffix}")

    known = {i for i in id_counts if i is not None}
    broken_parents: list[tuple[str, str]] = []

    for t in terms:
        if not isinstance(t, dict):
            errors.append(f"non-dict term entry: {t!r}")
            continue
        tid = t.get("id")
        if tid is None or not str(tid).strip():
            errors.append(f"term missing id: {t!r}")
            continue
        lbl = t.get("label")
        if lbl is None or not str(lbl).strip():
            errors.append(f"term {tid!r} missing non-empty label")
        for p in t.get("parents") or []:
            if p not in known:
                broken_parents.append((str(tid), str(p)))

    if broken_parents:
        preview = broken_parents[:15]
        more = f" (+{len(broken_parents) - len(preview)} more)" if len(broken_parents) > len(preview) else ""
        errors.append(f"broken parent refs ({len(broken_parents)}): {preview}{more}")

    term_count = len(terms)
    print(f"verify: terms={term_count}, unique_ids={len(known)}, broken_parent_refs={len(broken_parents)}")
    if errors:
        print("FAIL", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    print("PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
