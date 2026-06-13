// =============================================================================
// GymBuddy — schema, indexes, and vector index
// Run once per database (idempotent: every statement is IF NOT EXISTS).
// =============================================================================

// ── Uniqueness constraints (also create lookup indexes) ──────────────────────
CREATE CONSTRAINT exercise_id  IF NOT EXISTS FOR (e:Exercise)  REQUIRE e.id   IS UNIQUE;
CREATE CONSTRAINT muscle_name  IF NOT EXISTS FOR (m:Muscle)    REQUIRE m.name IS UNIQUE;
CREATE CONSTRAINT equip_name   IF NOT EXISTS FOR (q:Equipment) REQUIRE q.name IS UNIQUE;
CREATE CONSTRAINT cat_name     IF NOT EXISTS FOR (c:Category)  REQUIRE c.name IS UNIQUE;
CREATE CONSTRAINT region_name  IF NOT EXISTS FOR (r:Region)    REQUIRE r.name IS UNIQUE;

// ── Range / lookup indexes ───────────────────────────────────────────────────
CREATE INDEX exercise_level IF NOT EXISTS FOR (e:Exercise) ON (e.level);
CREATE INDEX exercise_cat   IF NOT EXISTS FOR (e:Exercise) ON (e.category);
CREATE INDEX exercise_force IF NOT EXISTS FOR (e:Exercise) ON (e.force);

// ── Fulltext for resolving exercise names from natural language ──────────────
CREATE FULLTEXT INDEX exercise_name_ft IF NOT EXISTS
FOR (e:Exercise) ON EACH [e.name];

// ── Vector index — all-MiniLM-L6-v2 embeddings, 384d, cosine ─────────────────
CREATE VECTOR INDEX exercise_idx IF NOT EXISTS
FOR (e:Exercise) ON (e.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: 384,
  `vector.similarity_function`: 'cosine'
}};
