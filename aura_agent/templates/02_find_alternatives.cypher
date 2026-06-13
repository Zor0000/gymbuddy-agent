// Tool: find_alternatives  ★ SIGNATURE FEATURE
// Description: Given an exercise the user can't do (machine taken, no barbell),
//   find alternatives that train the SAME primary muscle(s), optionally limited
//   to available equipment. Prefers the same movement pattern.
// Parameters:
//   $exercise  — String — "The exercise the user named, e.g. 'bench press'."
//   $equipment — String — "Equipment they have, e.g. 'dumbbell'. Empty string for any."

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
