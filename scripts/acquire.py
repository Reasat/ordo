#!/usr/bin/env python3
"""
Download the latest ORDO OWL from Orphadata (public endpoint, no auth required).

Resolves the current version by scraping the Orphadata ORDO page, then
constructs the download URL. Use --url to pin a specific version.

Usage:
    python scripts/acquire.py --output tmp/ordo_raw.owl
    python scripts/acquire.py --output tmp/ordo_raw.owl --url https://...ORDO_en_4.8.owl
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import requests

ORDO_PAGE = "https://www.orphadata.com/ordo/"
ORDO_BASE = "https://www.orphadata.com/data/ontologies/ordo/last_version/"
CHUNK_SIZE = 1024 * 1024  # 1 MB


def resolve_latest_url() -> str:
    """Scrape the Orphadata ORDO page to find the current English OWL download URL."""
    print(f"Resolving latest ORDO version from {ORDO_PAGE}", file=sys.stderr)
    resp = requests.get(ORDO_PAGE, timeout=30)
    resp.raise_for_status()
    # Matches e.g. last_version/ORDO_en_4.8.owl
    match = re.search(r'last_version/(ORDO_en_[\d.]+\.owl)', resp.text)
    if not match:
        raise RuntimeError(
            "Could not find ORDO_en_*.owl link on Orphadata page. "
            "Page structure may have changed. Use --url to pin a version."
        )
    filename = match.group(1)
    url = ORDO_BASE + filename
    print(f"Resolved: {url}", file=sys.stderr)
    return url


def download(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url}", file=sys.stderr)
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(output, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                fh.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r  {pct:.1f}%  ({downloaded:,} / {total:,} bytes)", end="", file=sys.stderr)
        print(file=sys.stderr)
    print(f"Saved: {output}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download latest ORDO OWL")
    parser.add_argument("--output", type=Path, default=Path("tmp/ordo_raw.owl"))
    parser.add_argument("--url", default=None, help="Pin a specific download URL (skips version resolution)")
    args = parser.parse_args()

    url = args.url if args.url else resolve_latest_url()
    download(url, args.output)


if __name__ == "__main__":
    main()
