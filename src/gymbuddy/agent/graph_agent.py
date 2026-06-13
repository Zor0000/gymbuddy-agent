"""GymBuddy orchestrator — Groq function-calling loop over the graph tools.

answer(question) -> {answer, tools_used, evidence, reasoning_path}

Flow:
  system + user  ─►  Groq (with tool schemas)
                      │  if tool_calls: run them, append results, ask again
                      ▼
                   final natural-language answer (grounded in tool rows)

Note: the BASIC build uses Groq's native function-calling rather than LangGraph —
simpler, fewer moving parts, easy to reason about. LangGraph can replace this loop
later without changing the tools.
"""
from __future__ import annotations

import json
from typing import Any

from gymbuddy.agent import tools as T
from gymbuddy.agent.llm import chat
from gymbuddy.agent.system_prompt import SYSTEM_PROMPT
from gymbuddy.agent.text2cypher import run_text2cypher

# ── tool JSON schemas exposed to the model ────────────────────────────────────
_EQUIP = {
    "type": "array",
    "items": {"type": "string"},
    "description": "available equipment, e.g. ['dumbbell','body only']; omit for any",
}
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "exercises_for_muscle",
        "description": "Exercises whose PRIMARY target is a muscle OR a body region, optionally filtered by equipment/level. Accepts a muscle name ('chest','triceps') OR a region word ('legs','push','pull','core','neck').",
        "parameters": {"type": "object", "properties": {
            "muscle": {"type": "string", "description": "a muscle name (e.g. 'chest') or a region word (e.g. 'legs','push')"},
            "equipment": _EQUIP,
            "level": {"type": "string", "enum": ["beginner", "intermediate", "expert"]},
        }, "required": ["muscle"]}}},
    {"type": "function", "function": {
        "name": "find_alternatives",
        "description": "Alternatives to an exercise that train the SAME primary muscle(s), optionally limited to available equipment. Use for 'swap for X', 'X with dumbbells', 'X at home'.",
        "parameters": {"type": "object", "properties": {
            "exercise": {"type": "string", "description": "the exercise the user named (free text is fine)"},
            "equipment": _EQUIP,
        }, "required": ["exercise"]}}},
    {"type": "function", "function": {
        "name": "build_split",
        "description": "Build a balanced routine for a training region using available equipment/level.",
        "parameters": {"type": "object", "properties": {
            "region": {"type": "string", "enum": ["push", "pull", "legs", "core", "neck"]},
            "equipment": _EQUIP,
            "level": {"type": "string", "enum": ["beginner", "intermediate", "expert"]},
        }, "required": ["region"]}}},
    {"type": "function", "function": {
        "name": "progression",
        "description": "Easier and harder variants of an exercise (same primary muscle).",
        "parameters": {"type": "object", "properties": {
            "exercise": {"type": "string"},
        }, "required": ["exercise"]}}},
    {"type": "function", "function": {
        "name": "similar_exercises",
        "description": "Semantic search for exercises similar to a free-text description ('like a plank but harder').",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string"},
            "k": {"type": "integer", "description": "how many (default 8)"},
        }, "required": ["text"]}}},
    {"type": "function", "function": {
        "name": "explain_exercise",
        "description": "Describe/rate a single exercise: which muscles (primary+secondary) it trains, movement pattern, equipment, difficulty, recovery time, and how many easier/harder variants exist. Use for 'how good is X', 'what does X work', 'is X a good exercise for Y'.",
        "parameters": {"type": "object", "properties": {
            "exercise": {"type": "string"},
        }, "required": ["exercise"]}}},
    {"type": "function", "function": {
        "name": "antagonist_balance",
        "description": "Given a muscle or region the user just trained, suggest exercises for the OPPOSING (antagonist) muscles to balance the body. Use for 'I did chest, what should I balance with', 'I trained push, now what', 'opposite muscle to X'.",
        "parameters": {"type": "object", "properties": {
            "muscle": {"type": "string", "description": "muscle ('chest') or region ('push') the user trained"},
            "equipment": _EQUIP,
        }, "required": ["muscle"]}}},
    {"type": "function", "function": {
        "name": "text2cypher",
        "description": "LAST RESORT for unusual multi-constraint questions not covered by the other tools.",
        "parameters": {"type": "object", "properties": {
            "question": {"type": "string"},
        }, "required": ["question"]}}},
]

_DISPATCH = {
    "exercises_for_muscle": lambda a: T.exercises_for_muscle(a["muscle"], a.get("equipment"), a.get("level")),
    "find_alternatives": lambda a: T.find_alternatives(a["exercise"], a.get("equipment")),
    "build_split": lambda a: T.build_split(a["region"], a.get("equipment"), a.get("level")),
    "progression": lambda a: T.progression(a["exercise"]),
    "similar_exercises": lambda a: T.similar_exercises(a["text"], a.get("k", 8)),
    "explain_exercise": lambda a: T.explain_exercise(a["exercise"]),
    "antagonist_balance": lambda a: T.antagonist_balance(a["muscle"], a.get("equipment")),
    "text2cypher": lambda a: run_text2cypher(a["question"]),
}

MAX_STEPS = 4


def _reasoning_path(evidence: list[dict]) -> list[dict]:
    """Build a light reasoning path from find_alternatives evidence (the demo case)."""
    path: list[dict] = []
    for ev in evidence:
        if ev.get("tool") == "find_alternatives" and ev.get("rows"):
            orig = ev.get("args", {}).get("resolved", {})
            row = ev["rows"][0]
            shared = row.get("shared_muscles", [])
            if orig:
                path.append({"node": orig.get("name"), "label": "Exercise"})
            for m in shared:
                path.append({"edge": "TARGETS", "to": m, "label": "Muscle"})
            path.append({"node": row.get("name"), "label": "Exercise", "via": "NEEDS:" + str(row.get("equipment"))})
    return path


def answer(
    question: str,
    history: list[dict] | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    # Prior turns give follow-ups their context ("and what with barbells" → same muscle).
    for h in (history or [])[-8:]:
        role = "assistant" if h.get("role") in ("assistant", "agent") else "user"
        content = h.get("content") or h.get("text") or ""
        if content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})
    evidence: list[dict] = []
    tools_used: list[str] = []

    for _ in range(MAX_STEPS):
        msg = chat(messages, tools=TOOL_SCHEMAS, tool_choice="auto")
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            return {
                "answer": (msg.content or "").strip(),
                "tools_used": tools_used,
                "evidence": evidence,
                "reasoning_path": _reasoning_path(evidence),
            }

        # record the assistant's tool-call turn
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ],
        })
        # execute each requested tool
        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tools_used.append(name)
            if verbose:
                print(f"  → {name}({args})")
            try:
                result = _DISPATCH[name](args)
            except Exception as e:  # noqa: BLE001
                result = {"tool": name, "rows": [], "error": str(e)}
            evidence.append(result)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, default=str)[:6000],
            })

    # ran out of steps — make a final narration attempt without tools
    msg = chat(messages, tool_choice="none")
    return {
        "answer": (msg.content or "").strip(),
        "tools_used": tools_used,
        "evidence": evidence,
        "reasoning_path": _reasoning_path(evidence),
    }
