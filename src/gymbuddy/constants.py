"""Shared constants for GymBuddy — region mapping, equipment normalization,
and the canonical vocab pulled from the free-exercise-db dataset.

Single source of truth, imported by the transform script, the agent tools,
and the Text2Cypher schema string.
"""
from __future__ import annotations

# ── Muscle → training region (push / pull / legs / core / neck) ──────────────
# A pragmatic trainer's split so we can build "push day", "leg day", etc.
MUSCLE_TO_REGION: dict[str, str] = {
    # push
    "chest": "push",
    "shoulders": "push",
    "triceps": "push",
    # pull (incl. posterior chain upper)
    "lats": "pull",
    "middle back": "pull",
    "traps": "pull",
    "biceps": "pull",
    "forearms": "pull",
    "lower back": "pull",
    # legs
    "quadriceps": "legs",
    "hamstrings": "legs",
    "glutes": "legs",
    "calves": "legs",
    "adductors": "legs",
    "abductors": "legs",
    # core
    "abdominals": "core",
    # neck (its own small region)
    "neck": "neck",
}

REGIONS: list[str] = ["push", "pull", "legs", "core", "neck"]

ALL_MUSCLES: list[str] = sorted(MUSCLE_TO_REGION.keys())

# ── Equipment normalization ──────────────────────────────────────────────────
# The dataset uses null for ~77 exercises; treat that as "none" (no equipment).
def normalize_equipment(value: str | None) -> str:
    if value is None or str(value).strip() == "":
        return "none"
    return str(value).strip().lower()


# Equipment a person training at home with no gym typically has.
HOME_EQUIPMENT: set[str] = {"none", "body only", "dumbbell", "bands", "kettlebells"}

# Map the many ways a user/LLM might name equipment → the dataset's canonical
# value(s). Exact-match queries fail otherwise (e.g. 'kettlebell' vs 'kettlebells').
EQUIP_ALIASES: dict[str, list[str]] = {
    "kettlebell": ["kettlebells"], "kettlebells": ["kettlebells"], "kettle bell": ["kettlebells"],
    "dumbbell": ["dumbbell"], "dumbbells": ["dumbbell"], "db": ["dumbbell"],
    "barbell": ["barbell"], "barbells": ["barbell"],
    "cable": ["cable"], "cables": ["cable"],
    "band": ["bands"], "bands": ["bands"], "resistance band": ["bands"], "resistance bands": ["bands"],
    "machine": ["machine"], "machines": ["machine"],
    "medicine ball": ["medicine ball"], "med ball": ["medicine ball"],
    "exercise ball": ["exercise ball"], "stability ball": ["exercise ball"], "swiss ball": ["exercise ball"],
    "foam roll": ["foam roll"], "foam roller": ["foam roll"],
    "e-z curl bar": ["e-z curl bar"], "ez bar": ["e-z curl bar"], "ez curl bar": ["e-z curl bar"],
    "body only": ["body only", "none"], "bodyweight": ["body only", "none"],
    "body weight": ["body only", "none"], "calisthenics": ["body only", "none"],
    "none": ["none", "body only"], "no equipment": ["none", "body only"], "no-equipment": ["none", "body only"],
    "other": ["other"],
}


def normalize_equipment_query(items: list[str] | None) -> list[str] | None:
    """Expand a user/LLM equipment list to canonical dataset values."""
    if not items:
        return items
    out: list[str] = []
    for it in items:
        key = str(it).strip().lower()
        out.extend(EQUIP_ALIASES.get(key, [key]))
    seen: set[str] = set()
    deduped: list[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            deduped.append(x)
    return deduped

# Canonical levels in ascending difficulty (used for PROGRESSES_TO direction).
LEVEL_ORDER: dict[str, int] = {"beginner": 0, "intermediate": 1, "expert": 2}

CATEGORIES: list[str] = [
    "strength",
    "stretching",
    "plyometrics",
    "powerlifting",
    "olympic weightlifting",
    "strongman",
    "cardio",
]

# Base URL for exercise images hosted in the dataset repo.
IMAGE_BASE_URL = (
    "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises"
)


def image_url(exercise_id: str, idx: int = 0) -> str:
    return f"{IMAGE_BASE_URL}/{exercise_id}/{idx}.jpg"


# =============================================================================
# REASONING ENRICHMENT (win-mode) — antagonists, synergists, recovery, patterns
# =============================================================================

# Antagonist muscle pairs (opposing movers). Symmetric — defined once, expanded below.
_ANTAGONIST_PAIRS: list[tuple[str, str]] = [
    ("chest", "lats"),
    ("chest", "middle back"),
    ("shoulders", "lats"),
    ("biceps", "triceps"),
    ("quadriceps", "hamstrings"),
    ("abdominals", "lower back"),
    ("adductors", "abductors"),
]

# Synergist muscles (assist the prime mover in common compound lifts).
SYNERGISTS: dict[str, list[str]] = {
    "chest": ["triceps", "shoulders"],
    "shoulders": ["triceps", "chest"],
    "triceps": ["chest", "shoulders"],
    "lats": ["biceps", "middle back", "forearms"],
    "middle back": ["biceps", "lats"],
    "biceps": ["lats", "forearms"],
    "quadriceps": ["glutes"],
    "hamstrings": ["glutes", "lower back"],
    "glutes": ["hamstrings", "quadriceps", "lower back"],
    "lower back": ["glutes", "hamstrings"],
}

# Approximate recovery windows (hours) before training a muscle hard again.
RECOVERY_HOURS: dict[str, int] = {
    # large muscles
    "chest": 72, "lats": 72, "middle back": 72, "quadriceps": 72,
    "hamstrings": 72, "glutes": 72, "lower back": 72,
    # medium
    "shoulders": 48, "triceps": 48, "biceps": 48, "traps": 48,
    # small / endurance-oriented
    "calves": 24, "forearms": 24, "abdominals": 24,
    "adductors": 24, "abductors": 24, "neck": 24,
}

MOVEMENT_PATTERNS: list[str] = [
    "squat", "hinge", "lunge", "horizontal_push", "vertical_push",
    "horizontal_pull", "vertical_pull", "carry", "core", "rotation", "isolation",
]


def antagonist_map() -> dict[str, list[str]]:
    """Symmetric muscle -> [antagonist muscles]."""
    out: dict[str, list[str]] = {}
    for a, b in _ANTAGONIST_PAIRS:
        out.setdefault(a, []).append(b)
        out.setdefault(b, []).append(a)
    return out


def classify_pattern(name: str, force: str | None, primary: list[str], mechanic: str | None) -> str:
    """Heuristically assign a movement pattern from name + force + primary muscle."""
    n = name.lower()
    pm = set(primary or [])

    def has(*words: str) -> bool:
        return any(w in n for w in words)

    if has("carry", "farmer", "waiter", "suitcase"):
        return "carry"
    if has("twist", "russian", "woodchop", "rotation", "windmill"):
        return "rotation"
    if has("deadlift", "good morning", "hip thrust", "swing", "clean", "snatch",
            "rdl", "romanian", "glute bridge", "back extension", "hyperextension"):
        return "hinge"
    if has("lunge", "split squat", "step up", "step-up", "pistol"):
        return "lunge"
    if has("squat"):
        return "squat"
    if has("pull-up", "pullup", "pull up", "chin", "pulldown", "lat pull"):
        return "vertical_pull"
    if has("row"):
        return "horizontal_pull"
    if has("overhead", "military", "shoulder press", "handstand", "arnold", "push press"):
        return "vertical_push"
    if has("bench", "push-up", "pushup", "push up", "fly", "flye", "dip", "chest press", "floor press"):
        return "horizontal_push"
    # fall back on muscle + force
    if "abdominals" in pm:
        return "core"
    if force == "pull" and pm & {"lats", "middle back", "traps"}:
        return "horizontal_pull"
    if force == "push" and "shoulders" in pm:
        return "vertical_push"
    if force == "push" and "chest" in pm:
        return "horizontal_push"
    if pm & {"quadriceps", "glutes"}:
        return "squat"
    if pm & {"hamstrings", "lower back"}:
        return "hinge"
    if mechanic == "isolation":
        return "isolation"
    return "isolation"
