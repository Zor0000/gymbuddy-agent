"""Phase 1 — download the free-exercise-db dataset.

    python scripts/01_download.py

Pulls dist/exercises.json (Public Domain, ~873 exercises) into data/raw/.
Idempotent: re-running just re-downloads.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data")) / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

URL = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json"


def main() -> int:
    out = RAW_DIR / "exercises.json"
    print(f"Downloading {URL}")
    with urllib.request.urlopen(URL, timeout=60) as resp:  # noqa: S310
        data = json.loads(resp.read().decode("utf-8"))
    out.write_text(json.dumps(data), encoding="utf-8")
    print(f"✅ wrote {out} ({len(data)} exercises, {out.stat().st_size // 1024} KB)")

    # Quick integrity check.
    assert len(data) > 800, f"expected >800 exercises, got {len(data)}"
    required = {"id", "name", "primaryMuscles", "equipment", "level", "category"}
    missing = required - set(data[0].keys())
    assert not missing, f"missing fields: {missing}"
    print("✅ schema check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
