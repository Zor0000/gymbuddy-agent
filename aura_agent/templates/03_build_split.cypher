// Tool: build_split
// Description: Build a balanced routine for a training region (push, pull, legs,
//   core, neck) using only the available equipment and difficulty level. Returns
//   one or two exercises per muscle in that region.
// Parameters:
//   $region    — String — "One of: push, pull, legs, core, neck."
//   $equipment — String — "Equipment filter, e.g. 'dumbbell'. Empty string for any."
//   $level     — String — "Difficulty: 'beginner','intermediate','expert'. Empty string for any."

MATCH (r:Region {name: toLower($region)})<-[:IN_REGION]-(m:Muscle)
OPTIONAL MATCH (e:Exercise)-[:TARGETS {role:'primary'}]->(m)
WHERE ($equipment = '' OR toLower(e.equipment) = toLower($equipment))
  AND ($level = '' OR e.level = toLower($level))
WITH m, e ORDER BY CASE e.level WHEN 'beginner' THEN 0 WHEN 'intermediate' THEN 1 ELSE 2 END
WITH m.name AS muscle, collect(e.name)[0..2] AS exercises
RETURN muscle, exercises ORDER BY muscle
