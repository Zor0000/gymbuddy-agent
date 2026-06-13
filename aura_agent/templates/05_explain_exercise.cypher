// Tool: explain_exercise
// Description: Describe/rate one exercise — muscles (primary+secondary), movement
//   pattern, equipment, difficulty, recovery hours, and how many easier/harder
//   variants exist. Use for "how good is X", "what does X work", "is X good for Y".
// Parameters:
//   $exercise — String — "The exercise to describe, e.g. 'clean deadlift'."

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
