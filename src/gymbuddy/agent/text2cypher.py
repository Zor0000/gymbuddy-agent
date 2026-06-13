"""Text2Cypher fallback tool — generates Cypher for unusual asks.

Safety: read-only guard (rejects write clauses), validate-then-execute with one
retry that feeds the error back to the model.
"""
from __future__ import annotations

import re
from typing import Any

from gymbuddy.agent.llm import complete
from gymbuddy.graph_client import run

SCHEMA = """\
Nodes:
  (:Exercise {id, name, level, category, force, mechanic, equipment, instructions, image_url})
  (:Muscle {name})        // 17: chest, shoulders, triceps, lats, biceps, quadriceps, ...
  (:Equipment {name})     // dumbbell, barbell, body only, bands, machine, cable, ...
  (:Category {name})      // strength, stretching, plyometrics, cardio, ...
  (:Region {name})        // push, pull, legs, core, neck
Relationships:
  (Exercise)-[:TARGETS {role:'primary'|'secondary'}]->(Muscle)
  (Exercise)-[:NEEDS]->(Equipment)
  (Exercise)-[:OF_CATEGORY]->(Category)
  (Muscle)-[:IN_REGION]->(Region)
  (Exercise)-[:ALTERNATIVE_OF {shared}]->(Exercise)
  (Exercise)-[:PROGRESSES_TO]->(Exercise)
"""

FEWSHOTS = """\
Q: exercises hitting both triceps and shoulders with no equipment
A: MATCH (e:Exercise)-[:TARGETS]->(:Muscle {name:'triceps'}),
         (e)-[:TARGETS]->(:Muscle {name:'shoulders'})
   WHERE e.equipment IN ['body only','none']
   RETURN DISTINCT e.name, e.equipment LIMIT 15

Q: which equipment can train the chest
A: MATCH (:Muscle {name:'chest'})<-[:TARGETS {role:'primary'}]-(e:Exercise)-[:NEEDS]->(q:Equipment)
   RETURN q.name, count(e) AS n ORDER BY n DESC

Q: beginner compound leg exercises
A: MATCH (e:Exercise)-[:TARGETS {role:'primary'}]->(m:Muscle)-[:IN_REGION]->(:Region {name:'legs'})
   WHERE e.level='beginner' AND e.mechanic='compound'
   RETURN DISTINCT e.name LIMIT 15

Q: count exercises per category
A: MATCH (e:Exercise)-[:OF_CATEGORY]->(c:Category)
   RETURN c.name, count(e) AS n ORDER BY n DESC
"""

_WRITE = re.compile(r"\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP|DETACH|CALL\s+apoc\.\w+\.(?:iterate|commit))\b", re.I)


def _extract_cypher(text: str) -> str:
    text = text.strip()
    if "```" in text:
        # take the first fenced block
        parts = text.split("```")
        for p in parts:
            p = p.replace("cypher", "", 1).strip() if p.lower().startswith("cypher") else p.strip()
            if p.upper().startswith(("MATCH", "CALL", "WITH", "UNWIND")):
                return p
    return text


def generate(question: str) -> str:
    prompt = (
        f"Graph schema:\n{SCHEMA}\nExamples:\n{FEWSHOTS}\n"
        f"Write ONE read-only Cypher query (no comments, no markdown) that answers:\n"
        f'"{question}"\nReturn only the query.'
    )
    return _extract_cypher(complete(prompt, temperature=0.0, max_tokens=400))


def run_text2cypher(question: str) -> dict[str, Any]:
    cypher = generate(question)
    if _WRITE.search(cypher):
        return {"tool": "text2cypher", "rows": [], "error": "refused: query is not read-only", "cypher": cypher}

    try:
        res = run(cypher)
        return {"tool": "text2cypher", "rows": res.records, "cypher": cypher}
    except Exception as e:  # noqa: BLE001 — one retry feeding the error back
        retry_prompt = (
            f"Graph schema:\n{SCHEMA}\nThe query below failed with: {e}\n\n{cypher}\n\n"
            f'Fix it. Return only a corrected read-only Cypher query for: "{question}"'
        )
        cypher2 = _extract_cypher(complete(retry_prompt, temperature=0.0, max_tokens=400))
        if _WRITE.search(cypher2):
            return {"tool": "text2cypher", "rows": [], "error": "refused on retry", "cypher": cypher2}
        try:
            res = run(cypher2)
            return {"tool": "text2cypher", "rows": res.records, "cypher": cypher2, "retried": True}
        except Exception as e2:  # noqa: BLE001
            return {"tool": "text2cypher", "rows": [], "error": str(e2), "cypher": cypher2}
