// Tool: antagonist_balance  ★ HEADLINE REASONING
// Description: Given a muscle/region the user just trained, suggest exercises for
//   the OPPOSING (antagonist) muscles to keep the body balanced. Use for "I did
//   chest, what should I balance with", "opposite of push", "I trained X, now what".
// Parameters:
//   $muscle    — String — "The muscle/region the user trained, e.g. 'chest' or 'push'."
//   $equipment — String — "Equipment filter, e.g. 'dumbbell'. Empty string for any."

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
