"""Phase 6 (win-mode) — enrich the graph with reasoning relationships.

    python scripts/06_enrich.py

Adds (idempotent):
  (Muscle)-[:ANTAGONIST_OF]->(Muscle)      opposing movers
  (Muscle)-[:SYNERGIST_OF]->(Muscle)       assisting movers
  Muscle.recovery_hours                    training-frequency reasoning
  (:MovementPattern {name})                squat/hinge/push/pull/…
  (Exercise)-[:PATTERN]->(MovementPattern) one per exercise

Requires a populated .env + an already-loaded graph (run 04/05 first).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gymbuddy.constants import (  # noqa: E402
    MOVEMENT_PATTERNS,
    RECOVERY_HOURS,
    SYNERGISTS,
    antagonist_map,
    classify_pattern,
)
from gymbuddy.graph_client import run  # noqa: E402

RAW = Path(os.environ.get("DATA_DIR", ROOT / "data")) / "raw" / "exercises.json"


def main() -> int:
    # ── antagonist edges ──────────────────────────────────────────────────────
    anta = antagonist_map()
    pairs = [{"a": a, "b": b} for a, bs in anta.items() for b in bs]
    run(
        """UNWIND $rows AS r
           MATCH (a:Muscle {name: r.a}), (b:Muscle {name: r.b})
           MERGE (a)-[:ANTAGONIST_OF]->(b)""",
        rows=pairs,
    )
    print(f"  ANTAGONIST_OF: {len(pairs)} edges")

    # ── synergist edges ───────────────────────────────────────────────────────
    syn = [{"a": a, "b": b} for a, bs in SYNERGISTS.items() for b in bs]
    run(
        """UNWIND $rows AS r
           MATCH (a:Muscle {name: r.a}), (b:Muscle {name: r.b})
           MERGE (a)-[:SYNERGIST_OF]->(b)""",
        rows=syn,
    )
    print(f"  SYNERGIST_OF: {len(syn)} edges")

    # ── recovery hours ────────────────────────────────────────────────────────
    rec = [{"name": m, "h": h} for m, h in RECOVERY_HOURS.items()]
    run(
        """UNWIND $rows AS r
           MATCH (m:Muscle {name: r.name}) SET m.recovery_hours = r.h""",
        rows=rec,
    )
    print(f"  recovery_hours set on {len(rec)} muscles")

    # ── movement-pattern nodes + edges ────────────────────────────────────────
    run("UNWIND $names AS n MERGE (:MovementPattern {name: n})", names=MOVEMENT_PATTERNS)
    data = json.loads(RAW.read_text(encoding="utf-8"))
    pat_rows = [
        {
            "id": e["id"],
            "pattern": classify_pattern(
                e.get("name", ""), e.get("force"),
                e.get("primaryMuscles") or [], e.get("mechanic"),
            ),
        }
        for e in data
    ]
    run(
        """UNWIND $rows AS r
           MATCH (e:Exercise {id: r.id})
           MATCH (p:MovementPattern {name: r.pattern})
           MERGE (e)-[:PATTERN]->(p)""",
        rows=pat_rows,
    )
    print(f"  PATTERN: {len(pat_rows)} edges")

    # ── validation + pattern distribution ─────────────────────────────────────
    print("\nPattern distribution:")
    for r in run(
        """MATCH (:Exercise)-[:PATTERN]->(p:MovementPattern)
           RETURN p.name AS pattern, count(*) AS n ORDER BY n DESC"""
    ).records:
        print(f"  {r['pattern']:16s} {r['n']}")
    print("\nSample antagonist reasoning:")
    for r in run(
        """MATCH (m:Muscle {name:'chest'})-[:ANTAGONIST_OF]->(a:Muscle)
           RETURN a.name AS antagonist"""
    ).records:
        print(f"  chest ⟷ {r['antagonist']}")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
