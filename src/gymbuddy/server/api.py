"""GymBuddy FastAPI backend.

    uvicorn gymbuddy.server.api:app --reload --port 8000   (from src/ on PYTHONPATH)

Endpoints:
  GET  /health        → {"status":"ok", "nodes": <count>}
  POST /ask {question}→ {answer, exercises, graph, reasoning_path, tools_used}
"""
from __future__ import annotations

import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from gymbuddy.agent.graph_agent import answer as agent_answer
from gymbuddy.server.payload import build as build_payload

app = FastAPI(title="GymBuddy API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # demo only — tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)


class Turn(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str
    history: list[Turn] = []


class AskResponse(BaseModel):
    answer: str
    exercises: list[dict]
    graph: dict
    reasoning_path: list[dict]
    tools_used: list[str]
    latency_ms: int


@app.get("/health")
def health() -> dict:
    from gymbuddy.graph_client import run

    try:
        n = run("MATCH (n) RETURN count(n) AS n").records[0]["n"]
        return {"status": "ok", "nodes": n}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "detail": str(e)}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    t0 = time.time()
    history = [{"role": t.role, "content": t.content} for t in req.history]
    result = agent_answer(req.question, history=history)
    payload = build_payload(result.get("evidence", []))
    return AskResponse(
        answer=result.get("answer", ""),
        exercises=payload["exercises"],
        graph=payload["graph"],
        reasoning_path=result.get("reasoning_path", []),
        tools_used=result.get("tools_used", []),
        latency_ms=int((time.time() - t0) * 1000),
    )
