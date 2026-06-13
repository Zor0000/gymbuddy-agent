// Tool: progression
// Description: Easier and harder variants of an exercise (same primary muscle +
//   category, preferring the same movement pattern). Use for 'easier version of
//   pistol squat', 'make this harder', 'how do I progress from knee push-ups'.
// Parameters:
//   $exercise — String — "The exercise to progress, e.g. 'pistol squat'."

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
