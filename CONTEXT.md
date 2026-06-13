# GymBuddy — Project Context

> **Purpose:** This document provides a comprehensive, developer-oriented overview of the
> GymBuddy project — its architecture, design decisions, codebase structure, data pipeline,
> and current status. Read this first before contributing or reviewing.

---

## 1. What Is GymBuddy?

GymBuddy is a **graph-native workout agent** built for the
[Neo4j Aura Agent Hackathon 2026](https://community.neo4j.com). It answers the questions
every gym-goer actually asks:

- _"Bench is taken — what's an equivalent with dumbbells?"_
- _"Build me a push day I can do at home with just bands"_
- _"Give me an easier version of pistol squats"_
- _"I trained chest — what should I balance it with?"_

Every answer is **grounded in a knowledge graph** of 873 real exercises and comes with the
**reasoning path** that justifies it (e.g.
`Barbell Bench Press →TARGETS→ Chest ←TARGETS← Dumbbell Floor Press →NEEDS→ Dumbbell`).

**Deadline:** 2026-06-15 · **Hackathon theme:** Neo4j Aura Agent

---

## 2. Technology Stack

| Layer               | Technology                                                  | Rationale                                                   |
| ------------------- | ----------------------------------------------------------- | ----------------------------------------------------------- |
| **Graph Database**  | Neo4j Aura DB (Free/Pro)                                    | ~1k nodes — under any tier limit                            |
| **LLM (custom)**    | Groq `llama-3.3-70b-versatile`                              | Free tier, fast, strong function-calling support             |
| **LLM (platform)**  | Vertex AI Gemini Flash / OpenAI gpt-4o-mini                 | Required by the Aura Agent platform                         |
| **Embeddings**      | `all-MiniLM-L6-v2` (384-d, sentence-transformers)           | Tiny, free, local; perfect for short exercise descriptions   |
| **Agent Framework** | Groq native function-calling (LangGraph-ready architecture) | Simpler than full LangGraph, same tool contract              |
| **Backend**         | FastAPI (Python 3.11)                                       | Single `/ask` + `/health` endpoint                          |
| **Frontend**        | Vite + React 18 + TypeScript + Cytoscape.js                 | Chat panel + interactive graph visualization                 |
| **Data**            | [`yuhonas/free-exercise-db`](https://github.com/yuhonas/free-exercise-db) | 873 exercises, Public Domain, zero licensing issues |
| **Caching**         | `diskcache`                                                 | Disk-based LLM response cache for free-tier rate limits      |
| **Deployment**      | Vercel (frontend) + Railway (backend)                       | Free tiers                                                   |

---

## 3. Graph Model (Neo4j Schema)

### Nodes

| Label             | Count  | Key Properties                                                                 |
| ----------------- | ------ | ------------------------------------------------------------------------------ |
| `Exercise`        | 873    | `id`, `name`, `level`, `category`, `force`, `mechanic`, `equipment`, `instructions`, `image_url`, `embedding` (384-d) |
| `Muscle`          | 17     | `name`, `recovery_hours`                                                       |
| `Equipment`       | ~13    | `name`                                                                         |
| `Category`        | 7      | `name` (strength, stretching, plyometrics, powerlifting, olympic weightlifting, strongman, cardio) |
| `Region`          | 5      | `name` (push, pull, legs, core, neck)                                          |
| `MovementPattern` | 11     | `name` (squat, hinge, lunge, horizontal_push, vertical_push, horizontal_pull, vertical_pull, carry, core, rotation, isolation) |

### Relationships

```
(Exercise)-[:TARGETS {role: 'primary'|'secondary'}]→(Muscle)
(Exercise)-[:NEEDS]→(Equipment)
(Exercise)-[:OF_CATEGORY]→(Category)
(Exercise)-[:PATTERN]→(MovementPattern)
(Muscle)-[:IN_REGION]→(Region)
(Muscle)-[:ANTAGONIST_OF]→(Muscle)        // symmetric, 7 curated pairs
(Muscle)-[:SYNERGIST_OF]→(Muscle)         // assistive co-activation
(Exercise)-[:ALTERNATIVE_OF {shared}]→(Exercise)   // derived: same primary muscle, different equipment
(Exercise)-[:PROGRESSES_TO]→(Exercise)              // derived: same muscle, level step-up
```

### Indexes

| Index Name          | Type       | On                  | Details                      |
| ------------------- | ---------- | ------------------- | ---------------------------- |
| `exercise_name_ft`  | Fulltext   | `Exercise.name`     | For natural-language exercise resolution |
| `exercise_idx`      | Vector     | `Exercise.embedding`| 384-d, cosine similarity     |
| 5 uniqueness constraints | Constraint | `*.id` / `*.name`  | Exercise, Muscle, Equipment, Category, Region |
| 3 range indexes     | B-tree     | `Exercise.level`, `.category`, `.force` | For filtered queries |

### Region Mapping (Trainer's Split)

```
push : chest, shoulders, triceps
pull : lats, middle back, traps, biceps, forearms, lower back
legs : quadriceps, hamstrings, glutes, calves, adductors, abductors
core : abdominals
neck : neck
```

---

## 4. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         User (Browser)                                   │
│                    http://localhost:5173                                  │
└───────────────┬──────────────────────────────────────────────────────────┘
                │  POST /ask {question, history[]}
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  FastAPI Backend (src/gymbuddy/server/api.py)  — :8000                   │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  graph_agent.answer(question, history)                             │  │
│  │    ┌─────────────┐     ┌──────────────────────────────────────┐   │  │
│  │    │ system_prompt│     │  Groq function-calling loop (≤4 steps)│   │  │
│  │    │   + history  │────►│  ┌──────────┐  ┌──────────────────┐ │   │  │
│  │    └─────────────┘     │  │  Router   │  │  Tool Dispatcher │ │   │  │
│  │                        │  │  (Groq)   │──│  (8 tools)       │ │   │  │
│  │                        │  └──────────┘  └────────┬─────────┘ │   │  │
│  │                        └─────────────────────────┼───────────┘   │  │
│  └──────────────────────────────────────────────────┼───────────────┘  │
│                                                      │                  │
│  ┌──────────────────────────────────────────────────┼───────────────┐  │
│  │  payload.py — builds UI-ready response:          │                │  │
│  │    • exercise cards (images, tags)                │                │  │
│  │    • Cytoscape graph (nodes + edges)              │                │  │
│  └──────────────────────────────────────────────────┼───────────────┘  │
└─────────────────────────────────────────────────────┼──────────────────┘
                                                      │ Parameterized Cypher
                                                      ▼
                              ┌────────────────────────────────────────┐
                              │  Neo4j Aura DB                         │
                              │  915 nodes · 384-d vector index        │
                              │  Fulltext index · Cypher queries       │
                              └────────────────────────────────────────┘
```

---

## 5. Agent Tools (8 total)

The agent has 8 callable tools, each executing parameterized Cypher against the graph:

| #  | Tool                    | Purpose                                              | Query Type    |
| -- | ----------------------- | ---------------------------------------------------- | ------------- |
| 1  | `exercises_for_muscle`  | Exercises for a muscle/region + equipment/level       | Cypher template |
| 2  | `find_alternatives` ★   | Same primary muscle, different equipment (swap)       | Cypher template |
| 3  | `build_split`           | Balanced routine for a region (push/pull/legs/core)   | Cypher template |
| 4  | `progression`           | Easier/harder variants (same muscle+category)         | Cypher template |
| 5  | `similar_exercises`     | Semantic search via 384-d vector index                | Vector search   |
| 6  | `explain_exercise`      | Full profile: muscles, pattern, recovery, variants    | Cypher template |
| 7  | `antagonist_balance` ★  | Multi-hop: opposing muscles → exercises for balance   | Cypher template |
| 8  | `text2cypher`           | LLM-generated Cypher (last resort, read-only guard)   | Text2Cypher     |

★ = Headline reasoning features that demonstrate multi-hop graph traversal.

### Exercise Resolution

User input like _"bench press"_ is resolved to the canonical exercise
(`Barbell Bench Press - Medium Grip`) via the fulltext index + smart ranking
(contiguous phrase match → token overlap → fewest extra words).

---

## 6. ETL Pipeline (scripts/)

The data pipeline is a sequence of numbered scripts, run in order:

| Script               | Phase | What It Does                                                        |
| -------------------- | ----- | ------------------------------------------------------------------- |
| `00_smoke_test.py`   | 0     | Verifies Aura connectivity, Groq API, and MiniLM model loading      |
| `01_download.py`     | 1     | Downloads `exercises.json` (873 records) from GitHub                 |
| `02_transform.py`    | 2     | Transforms JSON → 5 node CSVs + 6 edge CSVs (incl. derived alternatives & progressions) |
| `03_embed.py`        | 3     | Generates 384-d MiniLM embeddings → `exercise_embeddings.parquet`    |
| `04_apply_schema.py` | 4     | Applies constraints, indexes, and vector index from `schema.cypher`  |
| `05_load.py`         | 4     | Loads all CSVs + embeddings into Aura via batched `MERGE` (batch=500)|
| `06_enrich.py`       | 6     | Adds reasoning edges: ANTAGONIST_OF, SYNERGIST_OF, PATTERN, recovery_hours |

### Data Directory Structure

```
data/
├── raw/
│   └── exercises.json          # 873 exercises from free-exercise-db (1 MB)
└── processed/
    ├── nodes_exercise.csv      # 741 KB
    ├── nodes_muscle.csv        # 17 rows
    ├── nodes_equipment.csv     # ~13 rows
    ├── nodes_category.csv      # 7 rows
    ├── nodes_region.csv        # 5 rows
    ├── edges_targets.csv       # Exercise→Muscle (primary/secondary)
    ├── edges_needs.csv         # Exercise→Equipment
    ├── edges_of_category.csv   # Exercise→Category
    ├── edges_in_region.csv     # Muscle→Region
    ├── edges_alternative.csv   # Derived: same muscles, different equipment
    ├── edges_progresses.csv    # Derived: same muscles, level step-up
    └── exercise_embeddings.parquet  # 873 × 384-d vectors (2.4 MB)
```

---

## 7. Codebase Structure

```
gymbuddy/
├── PHASES.md                          # 11-phase implementation roadmap
├── CONTEXT.md                         # ← this file
├── README.md                          # Quick-start guide
├── requirements.txt                   # Python dependencies (pinned)
├── .env.example                       # Environment variable template
├── .gitignore
│
├── src/gymbuddy/                      # Python source package
│   ├── __init__.py                    # Package marker (version 0.1.0)
│   ├── config.py                      # Pydantic Settings singleton (loads from .env)
│   ├── constants.py                   # Domain constants: muscle→region map, equipment
│   │                                  #   aliases, antagonists, synergists, recovery times,
│   │                                  #   movement pattern classifier
│   ├── graph_client.py                # Neo4j driver singleton + run(cypher) helper
│   │
│   ├── agent/                         # LLM agent layer
│   │   ├── cli.py                     # CLI entry point (Rich panels)
│   │   ├── embeddings.py              # MiniLM singleton (cached 384-d vectors)
│   │   ├── graph_agent.py             # Orchestrator: Groq function-calling loop (≤4 steps)
│   │   ├── llm.py                     # Groq wrapper with diskcache
│   │   ├── system_prompt.py           # Agent persona + graph schema + 7 behavioral rules
│   │   ├── text2cypher.py             # Text→Cypher fallback (read-only guard + 1 retry)
│   │   └── tools.py                   # 7 deterministic graph tools (parameterized Cypher)
│   │
│   └── server/                        # FastAPI backend
│       ├── api.py                     # GET /health, POST /ask
│       └── payload.py                 # Transforms tool evidence → exercise cards + Cytoscape graph
│
├── scripts/                           # Numbered ETL entry points (run in order)
│   ├── 00_smoke_test.py
│   ├── 01_download.py
│   ├── 02_transform.py
│   ├── 03_embed.py
│   ├── 04_apply_schema.py
│   ├── 05_load.py
│   └── 06_enrich.py
│
├── aura_agent/                        # Aura Agent platform artifacts
│   ├── schema.cypher                  # Database DDL (constraints + indexes + vector index)
│   ├── system_prompt.md               # Platform agent persona + output contract
│   ├── PLATFORM_PACK.md              # Step-by-step guide for publishing on Aura console
│   └── templates/                     # Cypher query templates
│       ├── 01_exercises_for_muscle.cypher
│       ├── 02_find_alternatives.cypher
│       ├── 03_build_split.cypher
│       └── 04_progression.cypher
│
├── data/                              # Raw + processed data (gitignored)
│   ├── raw/exercises.json
│   └── processed/*.csv + *.parquet
│
├── docs/                              # Developer documentation
│   ├── ADVANCEMENTS.md               # Reasoning enrichment backlog
│   ├── NEXT_STEPS.md                  # Task manual + remaining work
│   └── SETUP_ENV.md                   # Detailed .env setup guide
│
├── tests/                             # (empty, pending Phase 9 eval)
│
└── web/                               # React frontend (Vite)
    ├── package.json                   # react, cytoscape, vite, typescript
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── main.tsx                   # React entry point
        ├── App.tsx                    # Split-panel layout (chat + graph)
        ├── api.ts                     # API client (TypeScript interfaces + fetch)
        ├── styles.css                 # Dark-themed CSS with custom properties
        └── components/
            ├── ChatPanel.tsx          # Chat UI: messages, exercise cards, example chips
            └── GraphPanel.tsx         # Cytoscape.js graph visualization (concentric layout)
```

---

## 8. Key Design Decisions

### Why a Graph?

| User Question                           | Graph Approach                                    |
| --------------------------------------- | ------------------------------------------------- |
| _"Same muscle, different equipment"_    | Literal 2-hop traversal: `Exercise→Muscle←Exercise` |
| _"Push day with dumbbells"_             | `Region←IN_REGION←Muscle←TARGETS←Exercise` + filter |
| _"Easier version of X"_                | Follow `PROGRESSES_TO` edges backward              |
| _"I did chest, what balances it?"_      | Multi-hop: `Muscle→ANTAGONIST_OF→Muscle←TARGETS←Exercise` |

The graph makes these queries **deterministic and explainable** — no hallucination, and the
reasoning path IS the feature.

### Why Groq + Function Calling (Not Full LangGraph)?

The basic agent uses Groq's **native function-calling** API instead of a full LangGraph state
machine. This is simpler, has fewer moving parts, and is easier to debug. The tool contract is
identical, so LangGraph can drop in later without changing the tools.

### Why MiniLM (384-d)?

- **Free and local** — no API costs for embeddings
- 873 exercises embed in **seconds**, not minutes
- Quality is sufficient for short exercise descriptions (name + instructions)
- The 384-d vector index is used by the custom agent only; the Aura platform uses its own
  provider's embeddings if Similarity Search is added

### Caching Strategy

LLM responses (non-tool-call) are cached to disk via `diskcache`. This is critical during
development with Groq's free tier (100k tokens/day limit). Tool-call responses are NOT cached
since they're cheap and state-dependent.

---

## 9. API Contract

### `GET /health`

```json
{ "status": "ok", "nodes": 915 }
```

### `POST /ask`

**Request:**
```json
{
  "question": "Bench is taken — alternative with dumbbells?",
  "history": [
    { "role": "user", "content": "previous message" },
    { "role": "assistant", "content": "previous reply" }
  ]
}
```

**Response:**
```json
{
  "answer": "Try Dumbbell Floor Press. It hits the same primary muscle (chest)...",
  "exercises": [
    {
      "id": "Dumbbell_Floor_Press",
      "name": "Dumbbell Floor Press",
      "equipment": "dumbbell",
      "level": "intermediate",
      "primary_muscles": ["chest"],
      "image_url": "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/Dumbbell_Floor_Press/0.jpg"
    }
  ],
  "graph": {
    "nodes": [{ "data": { "id": "...", "label": "...", "type": "exercise|muscle|equipment" } }],
    "edges": [{ "data": { "id": "...", "source": "...", "target": "...", "label": "TARGETS" } }]
  },
  "reasoning_path": [
    { "node": "Barbell Bench Press", "label": "Exercise" },
    { "edge": "TARGETS", "to": "chest", "label": "Muscle" },
    { "node": "Dumbbell Floor Press", "label": "Exercise", "via": "NEEDS:dumbbell" }
  ],
  "tools_used": ["find_alternatives"],
  "latency_ms": 2340
}
```

---

## 10. Six Question Archetypes

| Archetype          | Example                                                    | Primary Tool           |
| ------------------ | ---------------------------------------------------------- | ---------------------- |
| Muscle + equipment | _"Chest exercises I can do with only dumbbells"_           | `exercises_for_muscle` |
| Alternative swap   | _"Bench is taken — equivalent with dumbbells?"_            | `find_alternatives`    |
| Routine builder    | _"Push day at home with bands, beginner"_                  | `build_split`          |
| Progression        | _"Easier version of pistol squats"_                        | `progression`          |
| Similar / free-text| _"Something like a plank but harder"_                      | `similar_exercises`    |
| Ad-hoc             | _"Exercises hitting both triceps and shoulders, no machine"_| `text2cypher`          |
| Explain / rate     | _"How good is clean deadlift?"_                            | `explain_exercise`     |
| Balance            | _"I trained chest, what should I balance with?"_           | `antagonist_balance`   |

---

## 11. Environment Variables

All configuration is centralized in `src/gymbuddy/config.py` via `pydantic-settings`, loaded
from a `.env` file. See [.env.example](.env.example) for the full template.

| Variable                          | Required | Description                             |
| --------------------------------- | -------- | --------------------------------------- |
| `NEO4J_URI`                       | ✅       | `neo4j+s://xxx.databases.neo4j.io`      |
| `NEO4J_USER`                      | ✅       | Always `neo4j` for Aura                 |
| `NEO4J_PASSWORD`                  | ✅       | From Aura credentials file              |
| `NEO4J_DATABASE`                  |          | Default: `neo4j`                        |
| `GROQ_API_KEY`                    | ✅       | From console.groq.com                   |
| `GROQ_MODEL`                      |          | Default: `llama-3.3-70b-versatile`      |
| `HF_TOKEN`                        |          | Optional: speeds model download         |
| `EMBEDDING_MODEL`                 |          | Default: `sentence-transformers/all-MiniLM-L6-v2` |
| `OPENAI_API_KEY`                  |          | For Aura Agent platform (Option B)      |
| `GOOGLE_APPLICATION_CREDENTIALS`  |          | For Aura Agent platform (Option A)      |
| `GCP_PROJECT_ID`                  |          | For Vertex AI                           |
| `LOG_LEVEL`                       |          | Default: `INFO`                         |
| `DATA_DIR`                        |          | Default: `./data`                       |

---

## 12. Project Status

### Phase Completion

| Phase | Description                        | Status |
| ----- | ---------------------------------- | ------ |
| 0     | Foundation & accounts              | ✅ Done |
| 1     | Download dataset                   | ✅ Done |
| 2     | Transform to nodes & edges         | ✅ Done |
| 3     | Embeddings (384-d MiniLM)          | ✅ Done |
| 4     | Load + vector index                | ✅ Done |
| 5     | Cypher templates (4)               | ✅ Done |
| 6     | Custom LangGraph agent (Groq)      | ✅ Done |
| 6+    | Win-mode enrichment (antagonists, patterns, recovery) | ✅ Done |
| 7     | Aura Agent platform build          | 🔲 Pending (needs OpenAI/Vertex key) |
| 8     | Frontend + deploy                  | ✅ Done (local), 🔲 Deploy pending |
| 9     | Evaluation & tuning                | 🔲 Pending |
| 10    | Demo video + submit                | 🔲 Pending |

### What's Working Now

- **915 nodes** loaded in Neo4j Aura (exercises, muscles, equipment, categories, regions, movement patterns)
- **7 graph tools** with deterministic Cypher queries
- **Multi-turn conversation** with context carryover
- **FastAPI backend** serving on `:8000`
- **React frontend** with chat panel (exercise cards + images) and live Cytoscape graph visualization
- **Reasoning enrichment**: antagonist muscles, synergist muscles, movement patterns, recovery times
- All Aura Agent platform artifacts ready to paste (`aura_agent/PLATFORM_PACK.md`)

### Remaining Work

1. **Phase 7:** Publish agent on Aura console (requires OpenAI/Vertex provider setup)
2. **Phase 9:** Evaluation harness (`tests/eval_questions.yaml`) + tuning
3. **Phase 10:** 90-second demo video + forum submission
4. **Optional:** Deploy to Vercel + Railway for a public live link

---

## 13. Dataset

- **Source:** [`yuhonas/free-exercise-db`](https://github.com/yuhonas/free-exercise-db)
- **License:** Public Domain
- **Records:** 873 exercises
- **Fields:** `id`, `name`, `force`, `level`, `mechanic`, `equipment`, `primaryMuscles`,
  `secondaryMuscles`, `instructions`, `category`, `images`
- **17 muscles:** abdominals, abductors, adductors, biceps, calves, chest, forearms, glutes,
  hamstrings, lats, lower back, middle back, neck, quadriceps, shoulders, traps, triceps
- **3 levels:** beginner (523), intermediate (293), expert (57)
- **7 categories:** strength (581), stretching (123), plyometrics (61), powerlifting (38),
  olympic weightlifting (35), strongman (21), cardio (14)
- **~13 equipment types:** body only, dumbbell, barbell, kettlebells, cable, bands, machine,
  medicine ball, exercise ball, foam roll, e-z curl bar, other, none (null=77)
- **Images:** Hosted in the dataset repo at `exercises/<id>/0.jpg`

---

## 14. Dependency Graph

```
P0 → P1(done) → P2 → P3 → P4 → P5 ─┐
                                     ├── P9 → P10
                            P6 ──────┤
                            P7 ──────┤
                            P8 ──────┘
```

## 15. Cost Ledger

| Item                          | Cost      |
| ----------------------------- | --------- |
| Aura DB (Free or Pro credit)  | $0        |
| Groq (free tier)              | $0        |
| MiniLM + dataset              | $0        |
| Vertex (free trial) / OpenAI  | ≤ $5      |
| Vercel + Railway (free tiers) | $0        |
| **Total**                     | **≤ $5**  |
