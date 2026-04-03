#!/usr/bin/env python3
"""
Extract the ORDO version from the downloaded OWL file (owl:versionInfo triple)
and print it to stdout. Optionally writes ORDO_VERSION to env/.env.

Usage:
    python scripts/resolve_version.py --input tmp/ordo_raw.owl
    python scripts/resolve_version.py --input tmp/ordo_raw.owl --write-env
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def extract_version(owl_path: Path) -> str:
    """Parse owl:versionInfo from RDF/XML without loading the full graph."""
    pattern = re.compile(r"<versionInfo[^>]*>([^<]+)</versionInfo>")
    with open(owl_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = pattern.search(line)
            if m:
                return m.group(1).strip()
    raise RuntimeError(f"owl:versionInfo not found in {owl_path}")


def write_env(version: str, env_path: Path) -> None:
    env_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()
    lines = [ln for ln in lines if not ln.startswith("ORDO_VERSION=")]
    lines.append(f"ORDO_VERSION={version}")
    env_path.write_text("\n".join(lines) + "\n")
    print(f"Written ORDO_VERSION={version} to {env_path}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve ORDO version from downloaded OWL")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--write-env", action="store_true", help="Write version to env/.env")
    parser.add_argument("--env-file", type=Path, default=Path("env/.env"))
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    version = extract_version(args.input)
    print(version)

    if args.write_env:
        write_env(version, args.env_file)


if __name__ == "__main__":
    main()
