"""Phase 4a — apply constraints, indexes, and the vector index to Aura.

    python scripts/04_apply_schema.py

Runs every statement in aura_agent/schema.cypher. Idempotent.
Requires a populated .env (NEO4J_*).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gymbuddy.graph_client import run  # noqa: E402

SCHEMA = ROOT / "aura_agent" / "schema.cypher"


def statements(text: str) -> list[str]:
    out, buf = [], []
    for line in text.splitlines():
        if line.strip().startswith("//") or not line.strip():
            continue
        buf.append(line)
        if line.rstrip().endswith(";"):
            out.append("\n".join(buf).rstrip().rstrip(";"))
            buf = []
    if buf:
        out.append("\n".join(buf))
    return [s for s in out if s.strip()]


def main() -> int:
    stmts = statements(SCHEMA.read_text(encoding="utf-8"))
    print(f"Applying {len(stmts)} schema statements …")
    for s in stmts:
        first = s.strip().splitlines()[0][:70]
        try:
            run(s)
            print(f"  ✅ {first}")
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ {first}\n     {type(e).__name__}: {e}")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
