# GymBuddy — Implementation Roadmap

> A graph-native workout agent. Ask for exercises by muscle + the equipment you actually have,
> get instant alternatives when a machine is taken, and build balanced routines — each with a "why".
>
> 11 phases · ~11 days (today 2026-06-04 → deadline 2026-06-15) · free stack.

## The pitch (one paragraph)

GymBuddy is a Neo4j Aura Agent that reasons over a knowledge graph of **873 real exercises**
(muscles, equipment, difficulty, movement patterns) to answer the questions every gym-goer
actually asks: *"Bench is taken — what's an equivalent with dumbbells?"*, *"Build me a push day
I can do at home with just bands"*, *"Give me an easier version of pistol squats."* Every answer
comes with the **path through the graph** that justifies it — e.g. *Barbell Bench Press →TARGETS→
Chest ←TARGETS← Dumbbell Floor Press →NEEDS→ Dumbbell* — so the recommendation is transparent,
not a black box.

## Why it wins

- **Graph drives the answer.** "Same muscle, different equipment" is a literal traversal — the core
  judging criterion is satisfied by construction.
- **Universally relatable.** Everyone who has ever set foot in a gym gets it instantly.
- **Explainable by design.** The reasoning path *is* the feature.
- **Original.** None of the ~20 submitted projects touches fitness.
- **Trivial data.** One public-domain JSON file, 873 clean records — no API, no scraping, no licensing.
- **Demo magic.** The "bench is taken → here's your swap in 1 second" moment is memorable.

## Stack (locked)

| Layer            | Choice                                       | Why                                                       |
| ---------------- | -------------------------------------------- | --------------------------------------------------------- |
| Graph DB         | Neo4j Aura DB (Free is enough; Pro via credit) | ~1k nodes — far under any tier limit.                   |
| LLM (custom)     | **Groq** `llama-3.3-70b-versatile`           | Free tier, fast, strong tool-use.                         |
| LLM (Aura Agent) | Vertex AI Gemini Flash (free trial) / OpenAI gpt-4o-mini ($5) | Platform requires OpenAI or Vertex provider.   |
| Embeddings       | **`all-MiniLM-L6-v2`** (384d, sentence-transformers) | Tiny, free, local; perfect for short instruction text. |
| Data             | `yuhonas/free-exercise-db` (Public Domain)   | 873 exercises, JSON, muscles + equipment + level + images. |
| Agent framework  | LangGraph                                    | Router → tools → narrator.                                |
| Backend          | FastAPI                                      | Single `/ask` endpoint.                                   |
| Frontend         | Vite + React + TS + Tailwind + Cytoscape.js  | Chat left, exercise graph + images right.                 |
| Hosting          | Vercel (frontend) + Railway (backend)        | Free tiers.                                               |

## Dataset shape (verified against the real file)

- **873 exercises**, fields: `id, name, force, level, mechanic, equipment, primaryMuscles, secondaryMuscles, instructions, category, images`.
- **17 primary muscles**: abdominals, abductors, adductors, biceps, calves, chest, forearms, glutes, hamstrings, lats, lower back, middle back, neck, quadriceps, shoulders, traps, triceps.
- **3 levels**: beginner (523), intermediate (293), expert (57).
- **7 categories**: strength (581), stretching (123), plyometrics (61), powerlifting (38), olympic weightlifting (35), strongman (21), cardio (14).
- **~13 equipment values**: body only, dumbbell, barbell, kettlebells, cable, bands, machine, medicine ball, exercise ball, foam roll, e-z curl bar, other, (null=77 → treated as "none").
- **Images** hosted in the same repo under `exercises/<id>/0.jpg` — usable directly in the UI.

## Phase-at-a-glance

| # | Phase                          | Days  | Hard deliverable                                  |
| - | ------------------------------ | ----- | ------------------------------------------------- |
| 0 | Foundation & accounts          | 0.5   | Keys in `.env`; smoke test green.                 |
| 1 | Download dataset               | 0.5   | `data/raw/exercises.json` (done ✅).               |
| 2 | Transform to nodes & edges     | 1     | `data/processed/*.csv` (nodes + edges).           |
| 3 | Embeddings                     | 0.5   | `exercise_embeddings.parquet` 873 × 384d.         |
| 4 | Load + vector index            | 1     | Aura populated; vector index queryable.           |
| 5 | Cypher templates (4)           | 1     | Each returns correct exercises < 1 s.             |
| 6 | Custom LangGraph agent (Groq)  | 2     | Answers 6 archetype questions end-to-end.         |
| 7 | Aura Agent platform build      | 1     | Agent live in console; 3 screenshots.             |
| 8 | Frontend + deploy              | 2     | Public URL: chat + graph + images.                |
| 9 | Evaluation & tuning            | 1     | Eval report; zero hallucinated exercises.         |
|10 | Demo video + submit            | 1     | Forum post live with all artifacts.               |

---

## Phase 0 — Foundation & accounts (~0.5 day)

1. **Aura DB** at console.neo4j.io → save `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`.
2. **Groq** at console.groq.com → `GROQ_API_KEY`.
3. **HuggingFace** token (optional, speeds model pulls) → `HF_TOKEN`.
4. **Aura Agent provider** (for Phase 7): GCP free trial (Vertex) *or* OpenAI ($5).
5. Venv: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
6. `cp .env.example .env`, fill keys.
7. **`python scripts/00_smoke_test.py`** → "✅ Aura, ✅ Groq, ✅ MiniLM".

**Done when:** smoke test exits 0.

---

## Phase 1 — Download dataset (~0.5 day) ✅ DONE

`scripts/01_download.py` fetches `dist/exercises.json` from the free-exercise-db repo to
`data/raw/exercises.json`. Already validated: 873 records.

**Done when:** `data/raw/exercises.json` exists and parses to 873 objects.

---

## Phase 2 — Transform to nodes & edges (~1 day)

`scripts/02_transform.py` reads the JSON and writes CSVs to `data/processed/`:

**Node files**
- `nodes_exercise.csv` — id, name, level, category, force, mechanic, equipment, instructions (joined), image_url
- `nodes_muscle.csv` — name (17)
- `nodes_equipment.csv` — name (~13, null → "none")
- `nodes_category.csv` — name (7)
- `nodes_region.csv` — name (push, pull, legs, core, neck)

**Edge files**
- `edges_targets.csv` — exercise_id, muscle, role (primary|secondary)
- `edges_needs.csv` — exercise_id, equipment
- `edges_of_category.csv` — exercise_id, category
- `edges_in_region.csv` — muscle, region  (static mapping below)
- `edges_alternative.csv` — **derived**: pairs sharing ≥1 primary muscle AND same category, different equipment; weight = shared-muscle count
- `edges_progresses.csv` — **derived**: same primary-muscle set + same force, level beginner→intermediate→expert

**Region mapping (trainer's split)**
```
push : chest, shoulders, triceps
pull : lats, middle back, traps, biceps, forearms, lower back
legs : quadriceps, hamstrings, glutes, calves, adductors, abductors
core : abdominals
neck : neck
```

**Done when:** all CSVs exist; `edges_alternative.csv` is non-empty and spot-checks make sense
(e.g. Barbell Bench Press ↔ Dumbbell Bench Press appear as alternatives).

---

## Phase 3 — Embeddings (~0.5 day)

`scripts/03_embed.py`:
- `model = SentenceTransformer("all-MiniLM-L6-v2")`
- text = `f"{name}. {' '.join(instructions)}"`
- `model.encode(texts, normalize_embeddings=True)` → 384d
- save `data/processed/exercise_embeddings.parquet` (exercise_id, embedding)

Runs in **seconds** for 873 rows. Sanity: "Barbell Bench Press" nearest neighbours should include
other chest presses.

**Done when:** parquet has 873 × 384d.

---

## Phase 4 — Load + vector index (~1 day)

- `scripts/04_apply_schema.py` → `aura_agent/schema.cypher` (constraints, indexes, 384d vector index).
- `scripts/05_load.py` → load nodes (Region, Category, Equipment, Muscle, Exercise+embedding) then edges via the neo4j driver in batches; derived edges already in CSVs.
- **Validation** queries:
  - `MATCH (e:Exercise) RETURN count(e);` → 873
  - `MATCH (:Exercise)-[t:TARGETS {role:'primary'}]->(:Muscle) RETURN count(t);`
  - `CALL db.index.vector.queryNodes('exercise_idx', 5, <vec>) YIELD node RETURN node.name;`

**Done when:** counts match; vector query returns sensible neighbours.

---

## Phase 5 — Cypher templates (~1 day)

Saved in `aura_agent/templates/`:
- `01_exercises_for_muscle.cypher` — exercises with primary TARGETS a muscle, filtered to available equipment.
- `02_find_alternatives.cypher` — **the killer demo**: alternatives to an exercise (same primary muscle, different/available equipment).
- `03_build_split.cypher` — for a region + equipment + level, return a balanced set covering each muscle in the region.
- `04_progression.cypher` — easier / harder variants of an exercise.

Each tested in the console with 3 param sets, < 1 s.

**Done when:** each template has a green sample run (screenshot).

---

## Phase 6 — Custom LangGraph agent with Groq (~2 days)

```
user msg → router(Groq) → [4 templates | text2cypher | similar_exercises(vector)] → narrator(Groq)
        → {answer, reasoning_path, vis_payload}
```
- `src/gymbuddy/agent/llm.py` — Groq wrapper + JSON mode + disk cache.
- `src/gymbuddy/agent/embeddings.py` — MiniLM singleton; `embed(text) -> list[float]`.
- `src/gymbuddy/agent/tools.py` — 6 tools with Pydantic input schemas.
- `src/gymbuddy/agent/text2cypher.py` — schema string + 4 few-shots + validate/retry.
- `src/gymbuddy/agent/graph_agent.py` — LangGraph state machine.
- `src/gymbuddy/agent/system_prompt.py` — persona (see `aura_agent/system_prompt.md`).

**Done when:** `python -m gymbuddy.agent.cli "Bench is taken, alternative with dumbbells?"`
returns Dumbbell Floor/Bench Press with a path of ≥ 3 nodes.

---

## Phase 7 — Aura Agent platform build (~1 day)

1. Configure provider (Vertex / OpenAI) in the Aura Organization.
2. Create agent; paste the 4 templates with descriptions from `aura_agent/system_prompt.md`.
3. Add a Text2Cypher tool (schema + few-shots).
4. Add a Similarity Search tool on `exercise_idx`.
   - **Embedding-dim note**: the platform embeds the query with its configured provider. To keep
     384-d consistency, either (A) re-embed with the platform provider, or (B) keep MiniLM for the
     custom agent and have the platform agent use a fulltext template for "similar" instead.
     Default to **(B)** for speed.
5. Paste system prompt; test in playground; publish.

**Done when:** agent answers in the console; 3 screenshots captured.

---

## Phase 8 — Frontend + deploy (~2 days)

- Backend `src/gymbuddy/server/api.py`: `POST /ask` → JSON contract.
- Frontend `web/`: chat left, **Cytoscape graph + exercise images** right. Images pulled straight
  from the dataset repo (`exercises/<id>/0.jpg`).
- Deploy backend on Railway, frontend on Vercel; set CORS + `VITE_API_URL`.

**Done when:** public URL answers a question with answer + graph + images < 4 s.

---

## Phase 9 — Evaluation & tuning (~1 day)

- 15–20 questions in `tests/eval_questions.yaml` across 6 archetypes.
- `scripts/eval.py`: correctness (right exercises returned), hallucinated-exercise count (target 0),
  P50/P95 latency, LLM-as-judge faithfulness.
- Tune tool descriptions + few-shots until: correctness good, hallucinations 0, P95 < 3 s.

**Done when:** `tests/eval_report.md` committed, metrics hit.

---

## Phase 10 — Demo video + submit (~1 day)

- 90-second video; hook = "bench is taken" swap.
- 3 Aura console screenshots.
- Forum post (`docs/submission.md`): agent name + description, dataset source + why-graph-fits,
  console screenshot, demo, live link. Post to the Aura Agent Hackathon 2026 category.

**Done when:** forum post URL captured.

---

## Six question archetypes the agent must nail

| Archetype          | Example                                                   | Primary tool          |
| ------------------ | --------------------------------------------------------- | --------------------- |
| Muscle + equipment | "Chest exercises I can do with only dumbbells"            | exercises_for_muscle  |
| Alternative swap   | "Bench is taken — equivalent with dumbbells?"             | find_alternatives     |
| Routine builder    | "Push day at home with bands, beginner"                   | build_split           |
| Progression        | "Easier version of pistol squats"                         | progression           |
| Similar / free-text| "Something like a plank but harder"                       | similar_exercises     |
| Ad-hoc             | "Exercises hitting both triceps and shoulders, no machine"| text2cypher           |

## Dependency graph

```
P0 → P1(done) → P2 → P3 → P4 → P5 ─┐
                                     ├── P9 → P10
                            P6 ──────┤
                            P7 ──────┤
                            P8 ──────┘
```

## Cost ledger

| Item                         | Estimate    |
| ---------------------------- | ----------- |
| Aura DB (Free or Pro credit) | $0          |
| Groq                         | $0          |
| MiniLM + dataset             | $0          |
| Vertex (free trial)/OpenAI   | ≤ $5        |
| Vercel + Railway             | $0          |
| **Total**                    | **≤ $5**    |
