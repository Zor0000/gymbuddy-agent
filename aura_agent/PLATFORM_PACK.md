# GymBuddy — Aura Agent Platform Pack (Phase 7)

Everything you paste into **console.neo4j.io** to publish GymBuddy on the Aura Agent
platform. Provider: **Vertex AI**, GCP project **gymbuddy-498919**.

---

## STEP A — Google Cloud setup (~10 min)

### A1. Enable the RIGHT API
APIs & Services → **Library** → search **"Vertex AI API"** (service `aiplatform.googleapis.com`)
→ **Enable**.
❌ NOT "Vertex AI Search for commerce API" (`retail.googleapis.com`) — wrong product.

### A2. Create a service account
IAM & Admin → **Service Accounts** → **Create service account**
- Name: `gymbuddy-aura`
- Grant role: **Vertex AI User** (`roles/aiplatform.user`)
- Done.

### A3. Download a JSON key
Open the `gymbuddy-aura` service account → **Keys** → **Add key → Create new key → JSON** →
download. Keep this file safe (it's a credential).

### A4. Note these values (you'll paste them into Aura)
- Project ID: `gymbuddy-498919`
- Location/region: `us-central1`
- The downloaded **JSON key** file

---

## STEP B — Configure the provider in Aura (~3 min)

1. console.neo4j.io → your **Organization** (top-left org switcher) → **Settings**.
2. Find **Generative AI assistance** (a.k.a. GenAI / model provider) → **Enable**.
3. Choose provider **Google Vertex AI** → enter:
   - Project ID: `gymbuddy-498919`
   - Location: `us-central1`
   - Credentials: upload/paste the **JSON key** from A3.
4. Save. (This lets the agent use Gemini for reasoning.)

---

## STEP C — Create the agent

console.neo4j.io → open the **Ironlog** instance → **Agents** → **Create agent**.
- Name: `GymBuddy`
- Model: a **Gemini** model (e.g. `gemini-2.0-flash`) via the Vertex provider you just set up.
- Paste the **System instructions** from STEP E.
- Add the **6 tools** from STEP D.
- (Optional) Text2Cypher tool from STEP F.

---

## STEP D — The 6 Cypher Template tools

For each: **Add tool → Cypher template** → set **Name**, **Description**, paste the **Cypher**,
and **— critically — declare every parameter** in the tool's parameter section with a
**name, data type, description**. If a `$param` is referenced in Cypher but not declared
(or not supplied at call time), the platform fails with *"parameter(s) is missing"*.

**Platform rules baked into these queries:**
- Every parameter is **required** (the platform errors on un-supplied params — there are no
  true optionals). For "no filter", the model passes an **empty string** `""`.
- `equipment` is a single **String** (e.g. `"dumbbell"`, `""` for any) — simplest/most reliable.
- Exercise names are resolved inline via the fulltext index, so the model passes plain text.

### D1 · `exercises_for_muscle`
**Description:** Find exercises that primarily train a muscle OR a body region, optionally
filtered by equipment and difficulty level. Accepts a muscle ('chest') or region ('legs','push').
**Parameters to declare:**
- `muscle` — String — "Muscle or region, e.g. 'chest' or 'legs'."
- `equipment` — String — "Equipment filter like 'dumbbell' or 'barbell'. Pass an empty string for any."
- `level` — String — "Difficulty: 'beginner', 'intermediate', or 'expert'. Pass an empty string for any."
```cypher
MATCH (e:Exercise)-[:TARGETS {role:'primary'}]->(m:Muscle)
WHERE (m.name = toLower($muscle)
       OR EXISTS { (m)-[:IN_REGION]->(:Region {name: toLower($muscle)}) })
  AND ($equipment = '' OR toLower(e.equipment) = toLower($equipment))
  AND ($level = '' OR e.level = toLower($level))
RETURN DISTINCT e.name AS exercise, e.equipment AS equipment,
       e.level AS level, e.category AS category
ORDER BY e.name LIMIT 15
```

### D2 · `find_alternatives`  ★ signature feature
**Description:** Given an exercise the user can't do (machine taken, no barbell), find
alternatives that train the SAME primary muscle(s), optionally limited to available equipment.
Prefers the same movement pattern.
**Parameters to declare:**
- `exercise` — String — "The exercise the user named, e.g. 'bench press'."
- `equipment` — String — "Equipment they have, e.g. 'dumbbell'. Pass an empty string for any."
```cypher
CALL db.index.fulltext.queryNodes('exercise_name_ft', $exercise) YIELD node AS orig, score
WITH orig ORDER BY score DESC LIMIT 1
MATCH (orig)-[:TARGETS {role:'primary'}]->(m:Muscle)
OPTIONAL MATCH (orig)-[:PATTERN]->(op:MovementPattern)
WITH orig, collect(DISTINCT m.name) AS muscles, head(collect(op.name)) AS opat
MATCH (alt:Exercise)-[:TARGETS {role:'primary'}]->(m2:Muscle)
WHERE alt.id <> orig.id AND m2.name IN muscles AND alt.equipment <> orig.equipment
  AND ($equipment = '' OR toLower(alt.equipment) = toLower($equipment))
OPTIONAL MATCH (alt)-[:PATTERN]->(ap:MovementPattern)
WITH orig, opat, alt, collect(DISTINCT m2.name) AS shared, muscles, head(collect(ap.name)) AS apat
WHERE size(shared) = size(muscles)
RETURN orig.name AS original, alt.name AS alternative, alt.equipment AS equipment,
       shared AS shared_muscles, (apat = opat) AS same_movement_pattern
ORDER BY same_movement_pattern DESC, alt.name LIMIT 10
```

### D3 · `build_split`
**Description:** Build a balanced routine for a region (push/pull/legs/core/neck) using the
available equipment and difficulty level — one or two exercises per muscle.
**Parameters to declare:**
- `region` — String — "One of: push, pull, legs, core, neck."
- `equipment` — String — "Equipment filter, e.g. 'dumbbell'. Pass an empty string for any."
- `level` — String — "Difficulty: 'beginner', 'intermediate', or 'expert'. Pass an empty string for any."
```cypher
MATCH (r:Region {name: toLower($region)})<-[:IN_REGION]-(m:Muscle)
OPTIONAL MATCH (e:Exercise)-[:TARGETS {role:'primary'}]->(m)
WHERE ($equipment = '' OR toLower(e.equipment) = toLower($equipment))
  AND ($level = '' OR e.level = toLower($level))
WITH m, e ORDER BY CASE e.level WHEN 'beginner' THEN 0 WHEN 'intermediate' THEN 1 ELSE 2 END
WITH m.name AS muscle, collect(e.name)[0..2] AS exercises
RETURN muscle, exercises ORDER BY muscle
```

### D4 · `progression`
**Description:** Easier and harder variants of an exercise (same primary muscle + category,
preferring the same movement pattern).
**Parameters to declare:** `exercise` — String — "The exercise to progress, e.g. 'pistol squat'."
```cypher
CALL db.index.fulltext.queryNodes('exercise_name_ft', $exercise) YIELD node AS orig, score
WITH orig ORDER BY score DESC LIMIT 1
MATCH (orig)-[:TARGETS {role:'primary'}]->(m:Muscle)
WITH orig, collect(DISTINCT m.name) AS muscles,
     CASE orig.level WHEN 'beginner' THEN 0 WHEN 'intermediate' THEN 1 ELSE 2 END AS lvl
MATCH (v:Exercise)-[:TARGETS {role:'primary'}]->(m2:Muscle)
WHERE v.id <> orig.id AND m2.name IN muscles AND v.category = orig.category
WITH orig, lvl, v,
     CASE v.level WHEN 'beginner' THEN 0 WHEN 'intermediate' THEN 1 ELSE 2 END AS vlvl
RETURN orig.name AS exercise,
  [x IN collect(CASE WHEN vlvl < lvl THEN v.name END) WHERE x IS NOT NULL][0..5] AS easier,
  [x IN collect(CASE WHEN vlvl > lvl THEN v.name END) WHERE x IS NOT NULL][0..5] AS harder
```

### D5 · `explain_exercise`
**Description:** Describe/rate one exercise — muscles (primary+secondary), movement pattern,
equipment, difficulty, recovery hours, and how many easier/harder variants exist. Use for
"how good is X", "what does X work".
**Parameters to declare:** `exercise` — String — "The exercise to describe, e.g. 'clean deadlift'."
```cypher
CALL db.index.fulltext.queryNodes('exercise_name_ft', $exercise) YIELD node AS e, score
WITH e ORDER BY score DESC LIMIT 1
OPTIONAL MATCH (e)-[:TARGETS {role:'primary'}]->(pm:Muscle)
OPTIONAL MATCH (e)-[:TARGETS {role:'secondary'}]->(sm:Muscle)
OPTIONAL MATCH (e)-[:PATTERN]->(p:MovementPattern)
OPTIONAL MATCH (e)-[:PROGRESSES_TO]->(h:Exercise)
OPTIONAL MATCH (easier:Exercise)-[:PROGRESSES_TO]->(e)
RETURN e.name AS exercise, e.level AS level, e.equipment AS equipment,
       e.mechanic AS mechanic, e.force AS force,
       collect(DISTINCT pm.name) AS primary_muscles,
       collect(DISTINCT sm.name) AS secondary_muscles,
       max(pm.recovery_hours) AS recovery_hours,
       head(collect(DISTINCT p.name)) AS movement_pattern,
       count(DISTINCT h) AS harder_variants, count(DISTINCT easier) AS easier_variants
```

### D6 · `antagonist_balance`  ★ headline reasoning
**Description:** Given a muscle/region the user just trained, suggest exercises for the OPPOSING
(antagonist) muscles to keep the body balanced. Use for "I did chest, what should I balance with".
**Parameters to declare:**
- `muscle` — String — "The muscle/region the user trained, e.g. 'chest' or 'push'."
- `equipment` — String — "Equipment filter, e.g. 'dumbbell'. Pass an empty string for any."
```cypher
MATCH (m:Muscle)
WHERE m.name = toLower($muscle)
   OR EXISTS { (m)-[:IN_REGION]->(:Region {name: toLower($muscle)}) }
MATCH (m)-[:ANTAGONIST_OF]->(anta:Muscle)
WITH collect(DISTINCT anta.name) AS antas
UNWIND antas AS am
OPTIONAL MATCH (e:Exercise)-[:TARGETS {role:'primary'}]->(:Muscle {name: am})
WHERE ($equipment = '' OR toLower(e.equipment) = toLower($equipment))
WITH am, collect(e.name)[0..4] AS exercises
RETURN am AS antagonist_muscle, exercises
```

---

## STEP E — System instructions (paste into the agent)

> You are **GymBuddy**, a friendly workout assistant reasoning over a Neo4j graph of 873 real
> exercises (muscles, equipment, difficulty, movement patterns, antagonists, recovery times).
> Rules:
> 1. NEVER invent exercises — only use what the tools return. If nothing matches, say so and
>    suggest relaxing one constraint.
> 2. Match the tool to the intent: `exercises_for_muscle` (muscle/region + equipment),
>    `find_alternatives` (swap an exercise), `build_split` (push/pull/leg day),
>    `progression` (easier/harder), `explain_exercise` ("how good is X" — use alone),
>    `antagonist_balance` ("I did X, what balances it").
> 3. Always explain WHY using graph facts: which muscle, equipment, movement pattern,
>    antagonist, or recovery time (e.g. "chest needs ~72h recovery").
> 4. Keep answers friendly, under 6 sentences.
> 5. If a user mentions pain/injury, add a brief "consider a professional" note; never give
>    medical/rehab advice.

---

## STEP F — (Optional) Text2Cypher tool

**Description:** Last resort for unusual multi-constraint questions not covered by the templates.
Provide the agent with the schema below and a few examples (the console has a Text2Cypher tool
type that auto-injects the live schema — just add these examples):

```
Q: exercises hitting both triceps and shoulders with no equipment
A: MATCH (e:Exercise)-[:TARGETS]->(:Muscle {name:'triceps'}),
         (e)-[:TARGETS]->(:Muscle {name:'shoulders'})
   WHERE e.equipment IN ['body only','none'] RETURN DISTINCT e.name LIMIT 15

Q: which equipment can train the chest
A: MATCH (:Muscle {name:'chest'})<-[:TARGETS {role:'primary'}]-(e:Exercise)-[:NEEDS]->(q:Equipment)
   RETURN q.name, count(e) AS n ORDER BY n DESC
```

---

## STEP G — (Optional, BEST) Similarity Search with all 3 tool types

Our custom agent's vector index is 384-d (MiniLM) — the platform embeds queries with Vertex
(`text-embedding-005` = 768-d), so they won't match. To add a *working* Similarity Search tool
on the platform and use **all three** Aura tool types, I'll:
1. run a re-embed script with Vertex `text-embedding-005` (uses your JSON key, ~1¢),
2. create a 768-d index `exercise_vertex_idx`,
3. give you a Similarity Search tool definition pointing at it.
Ask me and I'll prep it. (Without this, the 6 templates + Text2Cypher already qualify — 2 tool types.)

---

## STEP H — Test & publish
Test in the playground:
- "Chest exercises with dumbbells"
- "Bench is taken — alternative with dumbbells?"
- "I just did chest, what should I train to stay balanced?"  ← shows antagonist reasoning
- "How good is clean deadlift for legs?"
Then **Publish** → copy the share URL. Capture **3 screenshots**: agent overview, tool list,
a conversation. These go in the submission.
