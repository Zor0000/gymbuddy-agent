"""Phase 4b — load nodes & edges into Aura, attach embeddings.

    python scripts/05_load.py

Reads data/processed/*.csv  + exercise_embeddings.parquet
Loads via the neo4j driver using batched UNWIND. Idempotent (MERGE everywhere).
Run AFTER 04_apply_schema.py.
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gymbuddy.graph_client import run, session  # noqa: E402

PROC = Path(os.environ.get("DATA_DIR", ROOT / "data")) / "processed"
BATCH = 500


def read_csv(name: str) -> list[dict]:
    with (PROC / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_batched(cypher: str, rows: list[dict], label: str) -> None:
    with session() as s:
        for i in range(0, len(rows), BATCH):
            chunk = rows[i : i + BATCH]
            s.run(cypher, rows=chunk).consume()
    print(f"  ✅ {label}: {len(rows)}")


def main() -> int:
    # ── simple label nodes ───────────────────────────────────────────────────
    for fname, label in [
        ("nodes_region.csv", "Region"),
        ("nodes_category.csv", "Category"),
        ("nodes_equipment.csv", "Equipment"),
        ("nodes_muscle.csv", "Muscle"),
    ]:
        rows = read_csv(fname)
        load_batched(
            f"UNWIND $rows AS r MERGE (n:{label} {{name: r.name}})", rows, label
        )

    # ── exercises (+ embeddings) ──────────────────────────────────────────────
    ex_rows = read_csv("nodes_exercise.csv")
    emb_path = PROC / "exercise_embeddings.parquet"
    if emb_path.exists():
        import pandas as pd

        emb = dict(
            zip(*[pd.read_parquet(emb_path)[c] for c in ("exercise_id", "embedding")])
        )
        for r in ex_rows:
            r["embedding"] = list(emb.get(r["id"], []))
        print(f"  attached embeddings to {sum(1 for r in ex_rows if r['embedding'])} exercises")
    else:
        for r in ex_rows:
            r["embedding"] = []
        print("  ⚠ no embeddings parquet found — loading without vectors")

    load_batched(
        """
        UNWIND $rows AS r
        MERGE (e:Exercise {id: r.id})
        SET e.name = r.name, e.level = r.level, e.category = r.category,
            e.force = r.force, e.mechanic = r.mechanic, e.equipment = r.equipment,
            e.instructions = r.instructions, e.image_url = r.image_url
        """,
        ex_rows,
        "Exercise",
    )
    # set vectors only where present (separate pass keeps the property clean)
    with session() as s:
        vec_rows = [{"id": r["id"], "v": r["embedding"]} for r in ex_rows if r["embedding"]]
        for i in range(0, len(vec_rows), BATCH):
            s.run(
                """
                UNWIND $rows AS r
                MATCH (e:Exercise {id: r.id})
                CALL db.create.setNodeVectorProperty(e, 'embedding', r.v)
                """,
                rows=vec_rows[i : i + BATCH],
            ).consume()
    print(f"  ✅ embeddings set on {len(vec_rows)} exercises")

    # ── edges ─────────────────────────────────────────────────────────────────
    load_batched(
        """
        UNWIND $rows AS r
        MATCH (e:Exercise {id: r.exercise_id})
        MATCH (m:Muscle {name: r.muscle})
        MERGE (e)-[t:TARGETS {role: r.role}]->(m)
        """,
        read_csv("edges_targets.csv"),
        "TARGETS",
    )
    load_batched(
        """
        UNWIND $rows AS r
        MATCH (e:Exercise {id: r.exercise_id})
        MATCH (q:Equipment {name: r.equipment})
        MERGE (e)-[:NEEDS]->(q)
        """,
        read_csv("edges_needs.csv"),
        "NEEDS",
    )
    load_batched(
        """
        UNWIND $rows AS r
        MATCH (e:Exercise {id: r.exercise_id})
        MATCH (c:Category {name: r.category})
        MERGE (e)-[:OF_CATEGORY]->(c)
        """,
        read_csv("edges_of_category.csv"),
        "OF_CATEGORY",
    )
    load_batched(
        """
        UNWIND $rows AS r
        MATCH (m:Muscle {name: r.muscle})
        MATCH (g:Region {name: r.region})
        MERGE (m)-[:IN_REGION]->(g)
        """,
        read_csv("edges_in_region.csv"),
        "IN_REGION",
    )
    load_batched(
        """
        UNWIND $rows AS r
        MATCH (a:Exercise {id: r.a_id})
        MATCH (b:Exercise {id: r.b_id})
        MERGE (a)-[x:ALTERNATIVE_OF]->(b)
        SET x.shared = toInteger(r.shared)
        """,
        read_csv("edges_alternative.csv"),
        "ALTERNATIVE_OF",
    )
    load_batched(
        """
        UNWIND $rows AS r
        MATCH (a:Exercise {id: r.easier_id})
        MATCH (b:Exercise {id: r.harder_id})
        MERGE (a)-[:PROGRESSES_TO]->(b)
        """,
        read_csv("edges_progresses.csv"),
        "PROGRESSES_TO",
    )

    # ── validation ──────────────────────────────────────────────────────────────
    print("\nValidation:")
    for label in ["Exercise", "Muscle", "Equipment", "Category", "Region"]:
        n = run(f"MATCH (n:{label}) RETURN count(n) AS n").records[0]["n"]
        print(f"  {label:10s} {n}")
    for rel in ["TARGETS", "NEEDS", "OF_CATEGORY", "IN_REGION", "ALTERNATIVE_OF", "PROGRESSES_TO"]:
        n = run(f"MATCH ()-[r:{rel}]->() RETURN count(r) AS n").records[0]["n"]
        print(f"  {rel:14s} {n}")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
