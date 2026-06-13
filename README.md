<p align="center">
  <strong>🏋️ GymBuddy</strong><br>
  <em>A graph-native workout agent powered by Neo4j Aura</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Neo4j-Aura_DB-018BFF?logo=neo4j&logoColor=white" alt="Neo4j Aura" />
  <img src="https://img.shields.io/badge/LLM-Groq_Llama_3.3-orange?logo=groq" alt="Groq" />
  <img src="https://img.shields.io/badge/Embeddings-MiniLM_384d-green" alt="MiniLM" />
  <img src="https://img.shields.io/badge/Frontend-React_+_Cytoscape.js-61DAFB?logo=react" alt="React" />
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

## 🎯 Features

- **🔄 Exercise Alternatives** — Swap any exercise for one that hits the same muscles with different equipment
- **💪 Muscle/Region Lookup** — Find exercises by muscle or training region (push/pull/legs/core)
- **📋 Routine Builder** — Generate balanced split-day routines filtered by equipment and difficulty
- **📈 Progression Tracking** — Discover easier/harder variants of any exercise
- **🔍 Semantic Search** — Find exercises from vague descriptions via 384-d vector embeddings
- **⚖️ Antagonist Balance** — Multi-hop reasoning: _"You trained chest → balance with back exercises"_
- **🧠 Text2Cypher** — Ad-hoc natural language queries converted to Cypher
- **📊 Live Graph Visualization** — Interactive Cytoscape.js graph showing reasoning behind each answer

---

## 🛠 Stack

| Layer               | Technology                                                  |
| ------------------- | ----------------------------------------------------------- |
| **Graph DB**        | Neo4j Aura DB (Free tier)                                   |
| **Agent LLM**       | Groq `llama-3.3-70b-versatile` (free tier)                  |
| **Embeddings**      | `all-MiniLM-L6-v2` — 384-d, free, runs locally             |
| **Backend**         | FastAPI (Python 3.11)                                       |
| **Frontend**        | Vite + React 18 + TypeScript + Cytoscape.js                 |
| **Dataset**         | [`yuhonas/free-exercise-db`](https://github.com/yuhonas/free-exercise-db) — 873 exercises, Public Domain |

---

## 🔗 Graph Model

```
(:Exercise)-[:TARGETS {role: 'primary'|'secondary'}]→(:Muscle)
(:Exercise)-[:NEEDS]→(:Equipment)
(:Exercise)-[:OF_CATEGORY]→(:Category)
(:Exercise)-[:PATTERN]→(:MovementPattern)
(:Muscle)-[:IN_REGION]→(:Region)
(:Muscle)-[:ANTAGONIST_OF]→(:Muscle)
(:Muscle)-[:SYNERGIST_OF]→(:Muscle)
(:Exercise)-[:PROGRESSES_TO]→(:Exercise)
```

**915 nodes** · **6 node types** · **9 relationship types** · **384-d vector index** · **Fulltext index**

---

## 🔧 Agent Tools

| #  | Tool                    | Purpose                                                    | Type            |
| -- | ----------------------- | ---------------------------------------------------------- | --------------- |
| 1  | `exercises_for_muscle`  | Find exercises for a muscle/region with filters            | Cypher Template |
| 2  | `find_alternatives` ★   | Swap: same primary muscles, different equipment            | Cypher Template |
| 3  | `build_split`           | Balanced routine for push/pull/legs/core                   | Cypher Template |
| 4  | `progression`           | Easier/harder variants of an exercise                      | Cypher Template |
| 5  | `similar_exercises`     | Semantic vector search (384-d)                             | Vector Search   |
| 6  | `explain_exercise`      | Full profile: muscles, pattern, recovery, variants         | Cypher Template |
| 7  | `antagonist_balance` ★  | Multi-hop: opposing muscles → balancing exercises          | Cypher Template |
| 8  | `text2cypher`           | LLM-generated Cypher for unusual queries                   | Text2Cypher     |

> ★ = Headline features demonstrating multi-hop graph reasoning.

---

## 🚀 Quickstart

### Prerequisites

- Python 3.11+
- Node.js 18+ (for the frontend)
- A [Neo4j Aura](https://console.neo4j.io) instance (free tier works)
- A [Groq API key](https://console.groq.com) (free tier)

### 1. Setup

```bash
cd gymbuddy
python3.11 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
cp .env.example .env
# Edit .env with your NEO4J_URI, NEO4J_PASSWORD, GROQ_API_KEY
```

### 2. Load the Knowledge Graph (ETL — run once)

```bash
PYTHONPATH=src python scripts/00_smoke_test.py      # Verify credentials
PYTHONPATH=src python scripts/01_download.py         # Download dataset
PYTHONPATH=src python scripts/02_transform.py        # JSON → CSVs
PYTHONPATH=src python scripts/03_embed.py            # Generate embeddings
PYTHONPATH=src python scripts/04_apply_schema.py     # Constraints + indexes
PYTHONPATH=src python scripts/05_load.py             # Load into Aura
PYTHONPATH=src python scripts/06_enrich.py           # Add reasoning edges
```

### 3. Run the Application

**Terminal 1 — Backend:**
```bash
PYTHONPATH=src uvicorn gymbuddy.server.api:app --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd web && npm install && npm run dev
```

Open **http://localhost:5173** — the header shows `● 915 nodes live` when connected.

---

## 📊 Dataset

- **Source:** [`yuhonas/free-exercise-db`](https://github.com/yuhonas/free-exercise-db)
- **License:** Public Domain
- **873 exercises** · **17 muscles** · **~13 equipment types** · **7 categories** · **3 difficulty levels**

---

## 📄 License

Dataset: Public Domain ([`yuhonas/free-exercise-db`](https://github.com/yuhonas/free-exercise-db))

---

<p align="center">
  Made with 💪 for the <strong>Neo4j Aura Agent Hackathon 2026</strong>
</p>
