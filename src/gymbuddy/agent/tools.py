"""GymBuddy graph tools — the deterministic reasoning layer.

Each function runs a parameterised Cypher query against the Aura graph and
returns a structured dict: rows + the cypher executed + a reasoning fragment.
The orchestrator (graph_agent.py) exposes these to Groq as callable functions.

Schema reminder:
  (Exercise{id,name,level,category,force,mechanic,equipment,instructions,image_url,embedding})
  (Exercise)-[:TARGETS{role}]->(Muscle{name})
  (Exercise)-[:NEEDS]->(Equipment{name})
  (Exercise)-[:OF_CATEGORY]->(Category{name})
  (Muscle)-[:IN_REGION]->(Region{name})
  (Exercise)-[:ALTERNATIVE_OF{shared}]->(Exercise)
  (Exercise)-[:PROGRESSES_TO]->(Exercise)
  fulltext index: exercise_name_ft   |   vector index: exercise_idx (384d)
"""
from __future__ import annotations

from typing import Any

from gymbuddy.constants import normalize_equipment_query
from gymbuddy.graph_client import run


# ── helpers ──────────────────────────────────────────────────────────────────
def _clean_ft_query(text: str) -> str:
    """Lucene-safe fulltext query: keep alphanumerics, OR the terms."""
    terms = [t for t in "".join(c if c.isalnum() else " " for c in text).split() if t]
    return " OR ".join(terms) if terms else text


def _name_tokens(name: str) -> list[str]:
    return [t for t in name.lower().replace("-", " ").split() if t]


def resolve_exercise(query: str) -> dict[str, Any] | None:
    """Resolve a user's phrasing to a real exercise via the fulltext index.

    Fulltext alone can pick odd variants (e.g. 'Guillotine Bench Press' for
    'barbell bench press'). We fetch the top candidates and prefer the one whose
    name CONTAINS the full query phrase, then the one with the most token overlap
    and fewest extra words — which lands on the canonical variant.
    """
    cy = """
    CALL db.index.fulltext.queryNodes('exercise_name_ft', $q) YIELD node, score
    RETURN node.id AS id, node.name AS name, node.equipment AS equipment,
           node.level AS level, node.image_url AS image_url, score
    ORDER BY score DESC LIMIT 10
    """
    cands = run(cy, q=_clean_ft_query(query)).records
    if not cands:
        return None
    ql = query.lower().strip()
    qtokens = [t for t in ql.replace("-", " ").split() if t]

    def rank(c: dict[str, Any]) -> tuple:
        name = c["name"].lower()
        contiguous = ql in name
        overlap = sum(1 for t in qtokens if t in _name_tokens(c["name"]))
        extra = len(_name_tokens(c["name"])) - overlap
        return (contiguous, overlap, -extra, c.get("score", 0))

    cands.sort(key=rank, reverse=True)
    return cands[0]


# ── tool 1: exercises_for_muscle ─────────────────────────────────────────────
def exercises_for_muscle(
    muscle: str, equipment: list[str] | None = None, level: str | None = None
) -> dict[str, Any]:
    equipment = normalize_equipment_query(equipment)
    # Accept either a muscle name ('chest') OR a region word ('legs','push',…):
    # if the term is a Region, expand to every muscle in that region.
    cy = """
    MATCH (e:Exercise)-[:TARGETS {role: 'primary'}]->(m:Muscle)
    WHERE (m.name = $muscle OR EXISTS { (m)-[:IN_REGION]->(:Region {name: $muscle}) })
      AND ($equipment IS NULL OR size($equipment) = 0 OR e.equipment IN $equipment)
      AND ($level IS NULL OR e.level = $level)
    RETURN DISTINCT e.id AS id, e.name AS name, e.equipment AS equipment,
           e.level AS level, e.category AS category, e.image_url AS image_url
    ORDER BY CASE e.level WHEN 'beginner' THEN 0 WHEN 'intermediate' THEN 1 ELSE 2 END, e.name
    LIMIT 15
    """
    res = run(cy, muscle=muscle.lower(), equipment=equipment, level=level)
    return {
        "tool": "exercises_for_muscle",
        "args": {"muscle": muscle, "equipment": equipment, "level": level},
        "rows": res.records,
        "cypher": cy,
    }


# ── tool 2: find_alternatives  (signature feature) ───────────────────────────
def find_alternatives(
    exercise: str, equipment: list[str] | None = None
) -> dict[str, Any]:
    equipment = normalize_equipment_query(equipment)
    target = resolve_exercise(exercise)
    if not target:
        return {"tool": "find_alternatives", "rows": [], "error": f"couldn't find '{exercise}'"}
    cy = """
    MATCH (orig:Exercise {id: $id})-[:TARGETS {role: 'primary'}]->(m:Muscle)
    OPTIONAL MATCH (orig)-[:PATTERN]->(op:MovementPattern)
    WITH orig, collect(DISTINCT m.name) AS orig_muscles, head(collect(op.name)) AS opat
    MATCH (alt:Exercise)-[:TARGETS {role: 'primary'}]->(m2:Muscle)
    WHERE alt.id <> orig.id AND m2.name IN orig_muscles
      AND alt.equipment <> orig.equipment
      AND ($equipment IS NULL OR size($equipment) = 0 OR alt.equipment IN $equipment)
    OPTIONAL MATCH (alt)-[:PATTERN]->(ap:MovementPattern)
    WITH orig_muscles, opat, alt, collect(DISTINCT m2.name) AS shared, head(collect(ap.name)) AS apat
    WHERE size(shared) = size(orig_muscles)
    RETURN alt.id AS id, alt.name AS name, alt.equipment AS equipment,
           alt.level AS level, shared AS shared_muscles, alt.image_url AS image_url,
           apat AS pattern, opat AS orig_pattern
    ORDER BY alt.name LIMIT 14
    """
    rows = run(cy, id=target["id"], equipment=equipment).records
    # Rank: same movement pattern first (a true like-for-like swap), then most
    # name-token overlap (e.g. 'Dumbbell Bench Press' for 'Barbell Bench Press').
    tgt_tokens = set(_name_tokens(target["name"]))

    def _rank(r: dict) -> tuple:
        same_pat = 1 if r.get("pattern") and r.get("pattern") == r.get("orig_pattern") else 0
        overlap = len(set(_name_tokens(r["name"])) & tgt_tokens)
        return (same_pat, overlap)

    rows.sort(key=_rank, reverse=True)
    return {
        "tool": "find_alternatives",
        "args": {"resolved": target, "equipment": equipment},
        "rows": rows[:10],
        "cypher": cy,
    }


# ── tool 3: build_split ───────────────────────────────────────────────────────
def build_split(
    region: str, equipment: list[str] | None = None, level: str | None = None
) -> dict[str, Any]:
    equipment = normalize_equipment_query(equipment)
    cy = """
    MATCH (r:Region {name: $region})<-[:IN_REGION]-(m:Muscle)
    OPTIONAL MATCH (e:Exercise)-[:TARGETS {role: 'primary'}]->(m)
    WHERE ($equipment IS NULL OR size($equipment) = 0 OR e.equipment IN $equipment)
      AND ($level IS NULL OR e.level = $level)
    WITH m, e
    ORDER BY CASE e.level WHEN 'beginner' THEN 0 WHEN 'intermediate' THEN 1 ELSE 2 END
    WITH m.name AS muscle, collect(e {.id, .name, .equipment, .level, .image_url})[0..2] AS exercises
    RETURN muscle, exercises ORDER BY muscle
    """
    res = run(cy, region=region.lower(), equipment=equipment, level=level)
    return {
        "tool": "build_split",
        "args": {"region": region, "equipment": equipment, "level": level},
        "rows": res.records,
        "cypher": cy,
    }


# ── tool 4: progression ───────────────────────────────────────────────────────
def progression(exercise: str) -> dict[str, Any]:
    target = resolve_exercise(exercise)
    if not target:
        return {"tool": "progression", "rows": [], "error": f"couldn't find '{exercise}'"}
    cy = """
    MATCH (orig:Exercise {id: $id})-[:TARGETS {role: 'primary'}]->(m:Muscle)
    OPTIONAL MATCH (orig)-[:PATTERN]->(op:MovementPattern)
    WITH orig, collect(DISTINCT m.name) AS muscles, head(collect(op.name)) AS opat,
         CASE orig.level WHEN 'beginner' THEN 0 WHEN 'intermediate' THEN 1 ELSE 2 END AS lvl
    MATCH (v:Exercise)-[:TARGETS {role: 'primary'}]->(m2:Muscle)
    WHERE v.id <> orig.id AND m2.name IN muscles
      AND v.category = orig.category   // keep a strength move's progressions in 'strength', not stretches
    OPTIONAL MATCH (v)-[:PATTERN]->(vp:MovementPattern)
    WITH lvl, opat, v, head(collect(vp.name)) AS vpat,
         CASE v.level WHEN 'beginner' THEN 0 WHEN 'intermediate' THEN 1 ELSE 2 END AS vlvl
    RETURN v.id AS id, v.name AS name, v.level AS level, v.equipment AS equipment,
           v.image_url AS image_url, vpat AS pattern, opat AS orig_pattern, vlvl AS vlvl, lvl AS lvl
    """
    recs = run(cy, id=target["id"]).records
    keys = ("id", "name", "level", "equipment", "image_url")

    def _same(r: dict) -> int:  # prefer same movement pattern (a true regression/progression)
        return 1 if r.get("pattern") and r["pattern"] == r.get("orig_pattern") else 0

    easier = sorted([r for r in recs if r["vlvl"] < r["lvl"]], key=_same, reverse=True)[:5]
    harder = sorted([r for r in recs if r["vlvl"] > r["lvl"]], key=_same, reverse=True)[:5]
    rows = [{
        "easier": [{k: r[k] for k in keys} for r in easier],
        "harder": [{k: r[k] for k in keys} for r in harder],
    }]
    return {
        "tool": "progression",
        "args": {"resolved": target},
        "rows": rows,
        "cypher": cy,
    }


# ── tool 5: similar_exercises  (vector search) ────────────────────────────────
def similar_exercises(text: str, k: int = 8) -> dict[str, Any]:
    from gymbuddy.agent.embeddings import embed_list  # lazy (needs ST installed)

    vec = embed_list(text)
    cy = """
    CALL db.index.vector.queryNodes('exercise_idx', $k, $vec) YIELD node AS e, score
    OPTIONAL MATCH (e)-[:TARGETS {role: 'primary'}]->(m:Muscle)
    RETURN e.id AS id, e.name AS name, e.equipment AS equipment, e.level AS level,
           collect(DISTINCT m.name) AS primary_muscles, e.image_url AS image_url, score
    ORDER BY score DESC
    """
    res = run(cy, k=k, vec=vec)
    return {
        "tool": "similar_exercises",
        "args": {"text": text, "k": k},
        "rows": res.records,
        "cypher": cy,
    }


# ── tool 6: explain_exercise  (for "how good is X / what does X work") ────────
def explain_exercise(exercise: str) -> dict[str, Any]:
    target = resolve_exercise(exercise)
    if not target:
        return {"tool": "explain_exercise", "rows": [], "error": f"couldn't find '{exercise}'"}
    cy = """
    MATCH (e:Exercise {id: $id})
    OPTIONAL MATCH (e)-[:TARGETS {role: 'primary'}]->(pm:Muscle)
    OPTIONAL MATCH (e)-[:TARGETS {role: 'secondary'}]->(sm:Muscle)
    OPTIONAL MATCH (e)-[:PATTERN]->(p:MovementPattern)
    OPTIONAL MATCH (e)-[:PROGRESSES_TO]->(harder:Exercise)
    OPTIONAL MATCH (easier:Exercise)-[:PROGRESSES_TO]->(e)
    RETURN e.id AS id, e.name AS name, e.level AS level, e.equipment AS equipment,
           e.mechanic AS mechanic, e.force AS force, e.image_url AS image_url,
           collect(DISTINCT pm.name) AS primary_muscles,
           collect(DISTINCT sm.name) AS secondary_muscles,
           max(pm.recovery_hours) AS recovery_hours,
           head(collect(DISTINCT p.name)) AS pattern,
           count(DISTINCT harder) AS harder_count,
           count(DISTINCT easier) AS easier_count
    """
    return {
        "tool": "explain_exercise",
        "args": {"resolved": target},
        "rows": run(cy, id=target["id"]).records,
        "cypher": cy,
    }


# ── tool 7: antagonist_balance  ★ headline multi-hop reasoning ★ ──────────────
def antagonist_balance(muscle: str, equipment: list[str] | None = None) -> dict[str, Any]:
    """Given a muscle/region the user trained, suggest exercises for its
    ANTAGONIST muscles — the 'you did push, now balance with pull' insight."""
    equipment = normalize_equipment_query(equipment)
    cy = """
    MATCH (m:Muscle)
    WHERE m.name = $muscle OR EXISTS { (m)-[:IN_REGION]->(:Region {name: $muscle}) }
    MATCH (m)-[:ANTAGONIST_OF]->(anta:Muscle)
    WITH collect(DISTINCT anta.name) AS antas
    UNWIND antas AS am
    OPTIONAL MATCH (e:Exercise)-[:TARGETS {role: 'primary'}]->(:Muscle {name: am})
    WHERE ($equipment IS NULL OR size($equipment) = 0 OR e.equipment IN $equipment)
    WITH am, collect(e {.id, .name, .equipment, .level, .image_url})[0..4] AS exercises
    RETURN am AS antagonist_muscle, exercises
    """
    return {
        "tool": "antagonist_balance",
        "args": {"muscle": muscle, "equipment": equipment},
        "rows": run(cy, muscle=muscle.lower(), equipment=equipment).records,
        "cypher": cy,
    }


# ── registry (used by the orchestrator) ───────────────────────────────────────
TOOLS = {
    "exercises_for_muscle": exercises_for_muscle,
    "find_alternatives": find_alternatives,
    "build_split": build_split,
    "progression": progression,
    "similar_exercises": similar_exercises,
    "explain_exercise": explain_exercise,
    "antagonist_balance": antagonist_balance,
}
