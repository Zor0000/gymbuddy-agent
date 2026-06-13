<p align="center">
  <strong>🏋️ GymBuddy</strong><br>
  <em>A graph-native workout agent powered by Neo4j Aura</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Neo4j-Aura_DB-018BFF?logo=neo4j&logoColor=white" alt="Neo4j Aura" />
  <img src="https://img.shields.io/badge/LLM-Groq_Llama_3.3-orange?logo=groq" alt="Groq" />
  <img src="https://img.shields.io/badge/Embeddings-MiniLM_384d-green" alt="MiniLM" />
  <img src="https://img.shields.io/badge/Frontend-React_+_Cytoscape.js-61DAFB?logo=react" alt="React" />
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Hackathon-Neo4j_Aura_Agent_2026-purple" alt="Hackathon" />
</p>

---

> Tell GymBuddy which muscle you want to train and what equipment you have — it returns the
> right exercises, instant alternatives when a machine is taken, balanced routines, and
> easier/harder progressions. Every recommendation comes with a visible **"why"** — the path
> through the knowledge graph.
>
> Built for the **Neo4j Aura Agent Hackathon 2026**.

---

## ✨ The Hook

> **You:** _The bench is taken — what's an alternative to barbell bench press? I only have dumbbells._
>
> **GymBuddy:** Try **Dumbbell Floor Press**. It hits the same primary muscle (**chest**) and only
> needs **dumbbells**.
>
> _Path: `Barbell Bench Press →TARGETS→ Chest ←TARGETS← Dumbbell Floor Press →NEEDS→ Dumbbell`_

---

## 📋 Table of Contents

- [Why GymBuddy?](#-why-gymbuddy)
- [Features](#-features)
- [Stack](#-stack)
- [Graph Model](#-graph-model)
- [Architecture](#-architecture)
- [Quickstart](#-quickstart)
- [Running the Demo](#-running-the-demo)
- [Agent Tools](#-agent-tools)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [Dataset](#-dataset)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🏆 Why GymBuddy?

| Strength                      | Details                                                                 |
| ----------------------------- | ----------------------------------------------------------------------- |
| **Graph drives the answer**   | "Same muscle, different equipment" is a literal 2-hop traversal — the core judging criterion is satisfied by construction |
| **Universally relatable**     | Everyone who has ever set foot in a gym gets it instantly                |
| **Explainable by design**     | The reasoning path IS the feature — no black box                        |
| **Multi-hop reasoning**       | Antagonist balance, movement patterns, recovery times — deep graph traversals |
| **Original**                  | A unique fitness use case among hackathon submissions                   |
| **Zero-cost data**            | One public-domain JSON file, 873 clean records — no APIs, no scraping   |
| **Demo magic**                | _"Bench is taken → here's your swap in 1 second"_ — instantly memorable |

---

## 🎯 Features

- **🔄 Exercise Alternatives** — Swap any exercise for one that hits the same muscles with different equipment
- **💪 Muscle/Region Lookup** — Find exercises by muscle or training region (push/pull/legs/core)
- **📋 Routine Builder** — Generate balanced split-day routines filtered by equipment and difficulty
- **📈 Progression Tracking** — Discover easier/harder variants of any exercise
- **🔍 Semantic Search** — Find exercises from vague descriptions via 384-d vector embeddings
- **📊 Exercise Profiles** — Get full breakdowns: muscles, movement pattern, recovery time, variants
- **⚖️ Antagonist Balance** — Multi-hop reasoning: _"You trained chest → balance with back exercises"_
- **🧠 Text2Cypher** — Ad-hoc natural language queries converted to Cypher for unusual questions
- **💬 Multi-turn Conversations** — Context carryover between messages for natural follow-ups
- **📊 Live Graph Visualization** — Interactive Cytoscape.js graph showing the reasoning behind each answer

---

## 🛠 Stack

| Layer               | Technology                                                  |
| ------------------- | ----------------------------------------------------------- |
| **Graph DB**        | Neo4j Aura DB (Free tier sufficient)                        |
| **Custom Agent LLM**| Groq `llama-3.3-70b-versatile` (free tier)                  |
| **Platform LLM**    | Vertex AI Gemini Flash (free trial) **or** OpenAI gpt-4o-mini |
| **Embeddings**      | `all-MiniLM-L6-v2` — 384-d, free, local                    |
| **Agent Framework** | Groq native function-calling (LangGraph-compatible)         |
| **Backend**         | FastAPI (Python 3.11)                                       |
| **Frontend**        | Vite + React 18 + TypeScript + Cytoscape.js                 |
| **Data**            | [`yuhonas/free-exercise-db`](https://github.com/yuhonas/free-exercise-db) — 873 exercises, Public Domain |
| **Caching**         | `diskcache` — disk-based LLM response cache                 |
| **Deployment**      | Vercel (frontend) + Railway (backend) — free tiers          |

---

## 🔗 Graph Model

### Nodes

| Label             | Count | Description                                     |
| ----------------- | ----- | ----------------------------------------------- |
| `Exercise`        | 873   | Name, level, category, force, equipment, embedding (384-d) |
| `Muscle`          | 17    | With `recovery_hours` property                  |
| `Equipment`       | ~13   | From "body only" to "barbell" to "machine"      |
| `Category`        | 7     | strength, stretching, plyometrics, etc.         |
| `Region`          | 5     | push, pull, legs, core, neck                    |
| `MovementPattern` | 11    | squat, hinge, lunge, horizontal_push, etc.      |

### Relationships

```
(Exercise)-[:TARGETS {role: 'primary'|'secondary'}]→(Muscle)
(Exercise)-[:NEEDS]→(Equipment)
(Exercise)-[:OF_CATEGORY]→(Category)
(Exercise)-[:PATTERN]→(MovementPattern)
(Muscle)-[:IN_REGION]→(Region)
(Muscle)-[:ANTAGONIST_OF]→(Muscle)
(Muscle)-[:SYNERGIST_OF]→(Muscle)
(Exercise)-[:ALTERNATIVE_OF {shared}]→(Exercise)
(Exercise)-[:PROGRESSES_TO]→(Exercise)
```

### Indexes

- **Fulltext:** `exercise_name_ft` — resolves user phrasing to real exercise names
- **Vector:** `exercise_idx` — 384-d cosine similarity for semantic search
- **Uniqueness constraints** on Exercise.id, Muscle.name, Equipment.name, Category.name, Region.name

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────┐
│  React Frontend (Vite · :5173)                      │
│  ┌──────────────┐  ┌────────────────────────────┐   │
│  │  Chat Panel   │  │  Cytoscape.js Graph Panel  │   │
│  │  (messages,   │  │  (reasoning visualization) │   │
│  │   cards, chips)│  │                            │   │
│  └──────┬───────┘  └────────────────────────────┘   │
└─────────┼───────────────────────────────────────────┘
          │ POST /ask
          ▼
┌─────────────────────────────────────────────────────┐
│  FastAPI Backend (:8000)                             │
│  ┌──────────────────────────────────────────────┐   │
│  │  Groq Function-Calling Orchestrator           │   │
│  │  (system prompt + ≤4-step tool loop)          │   │
│  │                                                │   │
│  │  8 Tools: exercises_for_muscle │ alternatives  │   │
│  │           build_split │ progression │ similar   │   │
│  │           explain │ antagonist │ text2cypher    │   │
│  └──────────────────────┬───────────────────────┘   │
│  ┌──────────────────────┴───────────────────────┐   │
│  │  Payload Builder → Exercise Cards + Graph     │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────┘
                      │ Parameterized Cypher
                      ▼
            ┌──────────────────────┐
            │  Neo4j Aura DB       │
            │  915 nodes           │
            │  384-d vector index  │
            └──────────────────────┘
```

---

## 🚀 Quickstart

### Prerequisites

- Python 3.11+
- Node.js 18+ (for the frontend)
- A [Neo4j Aura](https://console.neo4j.io) instance (free tier works)
- A [Groq API key](https://console.groq.com) (free tier)

### 1. Setup Python Environment

```bash
cd gymbuddy
python3.11 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env and fill in your keys:
#   NEO4J_URI, NEO4J_PASSWORD, GROQ_API_KEY
```

> 📖 See [docs/SETUP_ENV.md](./docs/SETUP_ENV.md) for a detailed guide on obtaining each key.

### 3. Run the ETL Pipeline

```bash
# Verify credentials
python scripts/00_smoke_test.py         # ✅ Aura, ✅ Groq, ✅ MiniLM

# Load the knowledge graph
python scripts/01_download.py           # → data/raw/exercises.json (873 records)
python scripts/02_transform.py          # → data/processed/*.csv
python scripts/03_embed.py              # → data/processed/exercise_embeddings.parquet
python scripts/04_apply_schema.py       # → Aura constraints + indexes
python scripts/05_load.py               # → Populate Aura + vector index
python scripts/06_enrich.py             # → Add antagonist/synergist/pattern/recovery edges
```

### 4. Test via CLI

```bash
PYTHONPATH=src python -m gymbuddy.agent.cli "Bench is taken, alternative with dumbbells?"
```

---

## 🖥 Running the Demo

### Terminal 1 — Backend (FastAPI on :8000)

```bash
cd gymbuddy
PYTHONPATH=src .venv/bin/uvicorn gymbuddy.server.api:app --port 8000
```

### Terminal 2 — Frontend (Vite on :5173)

```bash
cd gymbuddy/web
npm install        # first time only
npm run dev
```

Then open **http://localhost:5173** in your browser.

The header shows **"● N nodes live"** when the UI successfully connects to the API + Aura.
Try the example chips or ask:

- _"Bench is taken — alternative with dumbbells?"_
- _"Build me a beginner push day at home with dumbbells"_
- _"Something like a plank but harder"_
- _"I trained chest, what should I balance with?"_

---

## 🔧 Agent Tools

| #  | Tool                    | Purpose                                                    | Type            |
| -- | ----------------------- | ---------------------------------------------------------- | --------------- |
| 1  | `exercises_for_muscle`  | Find exercises for a muscle/region with filters            | Cypher Template |
| 2  | `find_alternatives` ★   | Swap: same primary muscles, different equipment            | Cypher Template |
| 3  | `build_split`           | Balanced routine for push/pull/legs/core/neck              | Cypher Template |
| 4  | `progression`           | Easier/harder variants of an exercise                      | Cypher Template |
| 5  | `similar_exercises`     | Semantic vector search (384-d)                             | Vector Search   |
| 6  | `explain_exercise`      | Full profile: muscles, pattern, recovery, variants         | Cypher Template |
| 7  | `antagonist_balance` ★  | Multi-hop: opposing muscles → balancing exercises          | Cypher Template |
| 8  | `text2cypher`           | LLM-generated Cypher for unusual queries (read-only)       | Text2Cypher     |

> ★ = Headline features demonstrating multi-hop graph reasoning.

---

## 📁 Project Structure

```
gymbuddy/
├── README.md                          # This file
├── CONTEXT.md                         # Comprehensive project context
├── PHASES.md                          # 11-phase implementation roadmap
├── requirements.txt                   # Python dependencies (pinned)
├── .env.example                       # Environment variable template
│
├── src/gymbuddy/                      # 🐍 Python source package
│   ├── config.py                      #    Pydantic Settings (loads .env)
│   ├── constants.py                   #    Domain constants & mappings
│   ├── graph_client.py                #    Neo4j driver singleton
│   ├── agent/                         #    🤖 LLM agent layer
│   │   ├── cli.py                     #       CLI entry point
│   │   ├── embeddings.py              #       MiniLM embedding singleton
│   │   ├── graph_agent.py             #       Groq function-calling orchestrator
│   │   ├── llm.py                     #       Groq wrapper + disk cache
│   │   ├── system_prompt.py           #       Agent persona & rules
│   │   ├── text2cypher.py             #       NL→Cypher fallback
│   │   └── tools.py                   #       7 deterministic graph tools
│   └── server/                        #    🌐 FastAPI backend
│       ├── api.py                     #       GET /health, POST /ask
│       └── payload.py                 #       Evidence → UI-ready payloads
│
├── scripts/                           # 🔄 ETL pipeline (run in order)
│   ├── 00_smoke_test.py               #    Verify credentials
│   ├── 01_download.py                 #    Download exercise dataset
│   ├── 02_transform.py                #    JSON → graph-ready CSVs
│   ├── 03_embed.py                    #    Generate 384-d embeddings
│   ├── 04_apply_schema.py             #    Apply Neo4j constraints & indexes
│   ├── 05_load.py                     #    Batch load into Aura
│   └── 06_enrich.py                   #    Add reasoning edges
│
├── aura_agent/                        # 📋 Aura Agent platform artifacts
│   ├── schema.cypher                  #    Database DDL
│   ├── system_prompt.md               #    Platform agent prompt
│   ├── PLATFORM_PACK.md              #    Step-by-step publish guide
│   └── templates/                     #    4 Cypher query templates
│
├── data/                              # 📊 Raw + processed (gitignored)
├── docs/                              # 📖 Developer documentation
│   ├── ADVANCEMENTS.md               #    Reasoning enrichment backlog
│   ├── NEXT_STEPS.md                  #    Task manual
│   └── SETUP_ENV.md                   #    Environment setup guide
├── tests/                             # 🧪 Tests (Phase 9)
└── web/                               # ⚛️ React frontend
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── App.tsx                    #    Split-panel layout
        ├── api.ts                     #    API client
        ├── styles.css                 #    Dark-themed CSS
        └── components/
            ├── ChatPanel.tsx          #    Chat UI + exercise cards
            └── GraphPanel.tsx         #    Cytoscape.js visualization
```

---

## ⚙️ Configuration

All configuration is centralized in `src/gymbuddy/config.py` via `pydantic-settings`.

| Variable            | Required | Default                                    | Description                  |
| ------------------- | -------- | ------------------------------------------ | ---------------------------- |
| `NEO4J_URI`         | ✅       | —                                          | Aura connection URI          |
| `NEO4J_USER`        |          | `neo4j`                                    | Always `neo4j` for Aura      |
| `NEO4J_PASSWORD`    | ✅       | —                                          | From Aura credentials        |
| `GROQ_API_KEY`      | ✅       | —                                          | From console.groq.com        |
| `GROQ_MODEL`        |          | `llama-3.3-70b-versatile`                  | Groq model name              |
| `EMBEDDING_MODEL`   |          | `sentence-transformers/all-MiniLM-L6-v2`   | Embedding model              |
| `LOG_LEVEL`         |          | `INFO`                                     | Python logging level         |
| `DATA_DIR`          |          | `./data`                                   | Data directory path          |

> 📖 Full details in [docs/SETUP_ENV.md](./docs/SETUP_ENV.md)

---

## 📊 Dataset

- **Source:** [`yuhonas/free-exercise-db`](https://github.com/yuhonas/free-exercise-db)
- **License:** Public Domain
- **873 exercises** with: name, force, level, mechanic, equipment, primary/secondary muscles, instructions, category, images
- **17 muscles** · **~13 equipment types** · **7 categories** · **3 difficulty levels**

---

## 🗺 Roadmap

See **[PHASES.md](./PHASES.md)** for the full 11-phase roadmap.

| Phase | Description                 | Status |
| ----- | --------------------------- | ------ |
| 0–6   | ETL + Graph + Agent         | ✅     |
| 6+    | Reasoning enrichment        | ✅     |
| 7     | Aura Agent platform publish | 🔲     |
| 8     | Frontend (local)            | ✅     |
| 8     | Deploy (Vercel + Railway)   | 🔲     |
| 9     | Evaluation & tuning         | 🔲     |
| 10    | Demo video + submission     | 🔲     |

**Deadline:** 2026-06-15

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run the smoke test (`python scripts/00_smoke_test.py`)
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

---

## 📄 License

Dataset: Public Domain ([`yuhonas/free-exercise-db`](https://github.com/yuhonas/free-exercise-db))

---

<p align="center">
  Made with 💪 for the <strong>Neo4j Aura Agent Hackathon 2026</strong>
</p>
