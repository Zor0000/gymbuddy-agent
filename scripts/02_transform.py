"""Phase 2 — transform exercises.json into graph node/edge CSVs.

    python scripts/02_transform.py

Reads  data/raw/exercises.json
Writes data/processed/nodes_*.csv  and  data/processed/edges_*.csv

Derived edges:
  ALTERNATIVE_OF : same category + identical primary-muscle set + different equipment
                   (capped at 8 per exercise to keep the graph lean)
  PROGRESSES_TO  : identical primary-muscle set + same force + level step (+1)
Pure stdlib (json + csv) so it runs without pandas.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# ETL scripts deliberately avoid importing the credentialed config; they only
# need data paths, so they run in a bare environment (no pydantic/groq/neo4j).
import os  # noqa: E402

from gymbuddy.constants import (  # noqa: E402
    LEVEL_ORDER,
    MUSCLE_TO_REGION,
    image_url,
    normalize_equipment,
)

DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {path.name:28s} {len(rows):5d} rows")


def main() -> int:
    raw = RAW_DIR / "exercises.json"
    data = json.loads(raw.read_text(encoding="utf-8"))
    out = PROCESSED_DIR
    print(f"Loaded {len(data)} exercises from {raw}")

    # ── collectors ───────────────────────────────────────────────────────────
    ex_rows, targets, needs, of_cat = [], [], [], []
    muscles: set[str] = set()
    equipment: set[str] = set()
    categories: set[str] = set()

    for e in data:
        eid = e["id"]
        equip = normalize_equipment(e.get("equipment"))
        cat = e.get("category") or "uncategorized"
        instructions = " ".join(e.get("instructions") or []).strip()
        imgs = e.get("images") or []
        img = f"https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/{imgs[0]}" if imgs else image_url(eid)

        ex_rows.append([
            eid, e.get("name", eid), e.get("level", ""), cat,
            e.get("force") or "", e.get("mechanic") or "", equip, instructions, img,
        ])
        equipment.add(equip)
        categories.add(cat)

        for m in e.get("primaryMuscles") or []:
            targets.append([eid, m, "primary"]); muscles.add(m)
        for m in e.get("secondaryMuscles") or []:
            targets.append([eid, m, "secondary"]); muscles.add(m)

        needs.append([eid, equip])
        of_cat.append([eid, cat])

    # ── derived: ALTERNATIVE_OF ────────────────────────────────────────────────
    by_group: dict[tuple, list[dict]] = defaultdict(list)
    for e in data:
        key = (e.get("category"), frozenset(e.get("primaryMuscles") or []))
        by_group[key].append(e)

    alt_rows: list[list] = []
    alt_count: dict[str, int] = defaultdict(int)
    for (_cat, pmset), members in by_group.items():
        if not pmset:
            continue
        members = sorted(members, key=lambda x: x["id"])
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                if normalize_equipment(a.get("equipment")) == normalize_equipment(b.get("equipment")):
                    continue
                if alt_count[a["id"]] >= 8 or alt_count[b["id"]] >= 8:
                    continue
                alt_rows.append([a["id"], b["id"], len(pmset)])
                alt_count[a["id"]] += 1
                alt_count[b["id"]] += 1

    # ── derived: PROGRESSES_TO (easier → harder) ───────────────────────────────
    by_prog: dict[tuple, list[dict]] = defaultdict(list)
    for e in data:
        key = (frozenset(e.get("primaryMuscles") or []), e.get("force"))
        by_prog[key].append(e)

    prog_rows: list[list] = []
    prog_count: dict[str, int] = defaultdict(int)
    for (pmset, _force), members in by_prog.items():
        if not pmset:
            continue
        for a in sorted(members, key=lambda x: x["id"]):
            la = LEVEL_ORDER.get(a.get("level", ""), 0)
            for b in members:
                lb = LEVEL_ORDER.get(b.get("level", ""), 0)
                if lb == la + 1 and prog_count[a["id"]] < 5:
                    prog_rows.append([a["id"], b["id"]])
                    prog_count[a["id"]] += 1

    # ── region edges (muscle → region), only for muscles actually present ──────
    region_rows = [[m, MUSCLE_TO_REGION[m]] for m in sorted(muscles) if m in MUSCLE_TO_REGION]
    regions = sorted({r for _, r in region_rows})
    unmapped = sorted(muscles - set(MUSCLE_TO_REGION))
    if unmapped:
        print(f"  ⚠ muscles with no region mapping: {unmapped}")

    # ── write everything ───────────────────────────────────────────────────────
    print("Writing CSVs:")
    write_csv(out / "nodes_exercise.csv",
              ["id", "name", "level", "category", "force", "mechanic", "equipment", "instructions", "image_url"],
              ex_rows)
    write_csv(out / "nodes_muscle.csv", ["name"], [[m] for m in sorted(muscles)])
    write_csv(out / "nodes_equipment.csv", ["name"], [[q] for q in sorted(equipment)])
    write_csv(out / "nodes_category.csv", ["name"], [[c] for c in sorted(categories)])
    write_csv(out / "nodes_region.csv", ["name"], [[r] for r in regions])

    write_csv(out / "edges_targets.csv", ["exercise_id", "muscle", "role"], targets)
    write_csv(out / "edges_needs.csv", ["exercise_id", "equipment"], needs)
    write_csv(out / "edges_of_category.csv", ["exercise_id", "category"], of_cat)
    write_csv(out / "edges_in_region.csv", ["muscle", "region"], region_rows)
    write_csv(out / "edges_alternative.csv", ["a_id", "b_id", "shared"], alt_rows)
    write_csv(out / "edges_progresses.csv", ["easier_id", "harder_id"], prog_rows)

    # ── spot check ──────────────────────────────────────────────────────────────
    print("\nSpot check — alternatives for Barbell_Bench_Press:")
    hits = [r for r in alt_rows if "Barbell_Bench_Press" in (r[0], r[1])]
    names = {e["id"]: e["name"] for e in data}
    for a, b, shared in hits[:8]:
        other = b if a == "Barbell_Bench_Press" else a
        print(f"    ↔ {names.get(other, other)}  (shared muscles: {shared})")
    if not hits:
        print("    (none — check the dataset id)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
