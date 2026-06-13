"""Turn the agent's tool evidence into UI-ready payloads:
  - a flat, deduped list of exercise cards (with images)
  - a Cytoscape graph (nodes + edges) that visualises the reasoning

Kept defensive: every tool's row shape is handled, with a generic fallback.
"""
from __future__ import annotations

from typing import Any


class _Graph:
    def __init__(self) -> None:
        self.nodes: dict[str, dict] = {}
        self.edges: dict[str, dict] = {}

    def node(self, _id: str, label: str, ntype: str, **extra: Any) -> str:
        if _id not in self.nodes:
            self.nodes[_id] = {"data": {"id": _id, "label": label, "type": ntype, **extra}}
        return _id

    def edge(self, src: str, tgt: str, label: str) -> None:
        key = f"{src}|{label}|{tgt}"
        if key not in self.edges and src and tgt:
            self.edges[key] = {"data": {"id": key, "source": src, "target": tgt, "label": label}}

    def exercise(self, ex: dict) -> str:
        return self.node(
            ex["id"], ex.get("name", ex["id"]), "exercise",
            equipment=ex.get("equipment"), level=ex.get("level"),
            image_url=ex.get("image_url"),
        )

    def muscle(self, name: str) -> str:
        return self.node(f"muscle:{name}", name, "muscle")

    def equipment(self, name: str | None) -> str | None:
        if not name:
            return None
        return self.node(f"equip:{name}", name, "equipment")

    def to_dict(self) -> dict:
        return {"nodes": list(self.nodes.values()), "edges": list(self.edges.values())}


def _add_exercise_card(cards: dict[str, dict], ex: dict) -> None:
    if not ex or "id" not in ex:
        return
    cards.setdefault(ex["id"], {
        "id": ex["id"],
        "name": ex.get("name", ex["id"]),
        "equipment": ex.get("equipment"),
        "level": ex.get("level"),
        "primary_muscles": ex.get("primary_muscles") or ex.get("shared_muscles") or [],
        "image_url": ex.get("image_url"),
    })


# Specific tools first so their exercises lead the card list; broad "list all
# exercises for a muscle" dumps go last (and get truncated by the UI).
_TOOL_PRIORITY = {
    "explain_exercise": 0,
    "find_alternatives": 1,
    "progression": 2,
    "antagonist_balance": 3,
    "build_split": 4,
    "exercises_for_muscle": 5,
    "similar_exercises": 6,
    "text2cypher": 7,
}
_MAX_CARDS = 12


def build(evidence: list[dict]) -> dict[str, Any]:
    g = _Graph()
    cards: dict[str, dict] = {}

    for ev in sorted(evidence, key=lambda e: _TOOL_PRIORITY.get(e.get("tool"), 9)):
        tool = ev.get("tool")
        rows = ev.get("rows") or []
        args = ev.get("args") or {}

        if tool == "find_alternatives":
            origin = args.get("resolved") or {}
            o_id = g.exercise(origin) if origin.get("id") else None
            if origin.get("id"):
                _add_exercise_card(cards, {**origin, "primary_muscles": []})
            for r in rows:
                a_id = g.exercise(r)
                _add_exercise_card(cards, r)
                for m in r.get("shared_muscles", []):
                    mid = g.muscle(m)
                    if o_id:
                        g.edge(o_id, mid, "TARGETS")
                    g.edge(a_id, mid, "TARGETS")
                eq = g.equipment(r.get("equipment"))
                if eq:
                    g.edge(a_id, eq, "NEEDS")

        elif tool == "build_split":
            for r in rows:
                mid = g.muscle(r.get("muscle", "?"))
                for ex in r.get("exercises", []):
                    xid = g.exercise(ex)
                    _add_exercise_card(cards, {**ex, "primary_muscles": [r.get("muscle")]})
                    g.edge(xid, mid, "TARGETS")
                    eq = g.equipment(ex.get("equipment"))
                    if eq:
                        g.edge(xid, eq, "NEEDS")

        elif tool == "progression":
            origin = args.get("resolved") or {}
            o_id = g.exercise(origin) if origin.get("id") else None
            if origin.get("id"):
                _add_exercise_card(cards, origin)
            for r in rows:
                for ex in r.get("easier", []) or []:
                    xid = g.exercise(ex)
                    _add_exercise_card(cards, ex)
                    if o_id:
                        g.edge(xid, o_id, "PROGRESSES_TO")
                for ex in r.get("harder", []) or []:
                    xid = g.exercise(ex)
                    _add_exercise_card(cards, ex)
                    if o_id:
                        g.edge(o_id, xid, "PROGRESSES_TO")

        elif tool in ("exercises_for_muscle", "similar_exercises"):
            target = args.get("muscle")
            tnode = g.muscle(target) if target else None
            for r in rows:
                xid = g.exercise(r)
                _add_exercise_card(cards, r)
                muscles = r.get("primary_muscles") or ([target] if target else [])
                for m in muscles:
                    if m:
                        mid = g.muscle(m)
                        g.edge(xid, mid, "TARGETS")
                if tnode and not muscles:
                    g.edge(xid, tnode, "TARGETS")
                eq = g.equipment(r.get("equipment"))
                if eq:
                    g.edge(xid, eq, "NEEDS")

        elif tool == "explain_exercise":
            for r in rows:
                xid = g.exercise(r)
                _add_exercise_card(cards, {**r, "primary_muscles": r.get("primary_muscles", [])})
                for m in r.get("primary_muscles", []) or []:
                    g.edge(xid, g.muscle(m), "TARGETS")
                for m in r.get("secondary_muscles", []) or []:
                    g.edge(xid, g.muscle(m), "assists")
                eq = g.equipment(r.get("equipment"))
                if eq:
                    g.edge(xid, eq, "NEEDS")

        elif tool == "antagonist_balance":
            for r in rows:
                mid = g.muscle(r.get("antagonist_muscle", "?"))
                for ex in r.get("exercises", []) or []:
                    xid = g.exercise(ex)
                    _add_exercise_card(cards, {**ex, "primary_muscles": [r.get("antagonist_muscle")]})
                    g.edge(xid, mid, "TARGETS")
                    eq = g.equipment(ex.get("equipment"))
                    if eq:
                        g.edge(xid, eq, "NEEDS")

        else:  # text2cypher / unknown — best-effort: any row that looks like an exercise
            for r in rows:
                if isinstance(r, dict) and "id" in r and "name" in r:
                    g.exercise(r)
                    _add_exercise_card(cards, r)

    return {"exercises": list(cards.values())[:_MAX_CARDS], "graph": g.to_dict()}
