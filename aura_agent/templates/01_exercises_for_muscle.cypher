// Tool: exercises_for_muscle
// Description: Find exercises that primarily train a muscle OR a body region,
//   optionally filtered by equipment and level. Accepts a muscle ('chest') or
//   region ('legs','push','pull','core','neck').
// Parameters:
//   $muscle    — String — "Muscle or region, e.g. 'chest' or 'legs'."
//   $equipment — String — "Equipment filter like 'dumbbell'. Empty string for any."
//   $level     — String — "Difficulty: 'beginner','intermediate','expert'. Empty string for any."

MATCH (e:Exercise)-[:TARGETS {role:'primary'}]->(m:Muscle)
WHERE (m.name = toLower($muscle)
       OR EXISTS { (m)-[:IN_REGION]->(:Region {name: toLower($muscle)}) })
  AND ($equipment = '' OR toLower(e.equipment) = toLower($equipment))
  AND ($level = '' OR e.level = toLower($level))
RETURN DISTINCT e.name AS exercise, e.equipment AS equipment,
       e.level AS level, e.category AS category
ORDER BY e.name LIMIT 15
