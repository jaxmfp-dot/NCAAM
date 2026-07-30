"""
Central config for game balance / tunable constants.

Everything here is meant to be adjusted without touching engine/model code.
Later phases (fight engine, aging, injuries) will add their tunables to this
same file, grouped in the same style.
"""

# --- Paths -------------------------------------------------------------

DATA_DIR = "data"
SAVES_DIR = "data/saves"
IMPORT_DIR = "data/import"
IMPORT_PORTRAITS_DIR = "data/import/portraits"
PORTRAITS_DIR = "data/portraits"          # per-save portrait copies live under PORTRAITS_DIR/<slot>/
SCHEMA_PATH = "models/schema.sql"

# --- Attribute scale -----------------------------------------------------

ATTR_MIN = 1
ATTR_MAX = 99

# --- Weight classes --------------------------------------------------
# Real-world MMA division names/cutoffs. `key` is the value stored on the
# fighter row; weights are upper limit in lbs. Women's divisions share
# lower-bound names with men's but are kept distinct via the "Women's" prefix
# so a fighter can never be miscounted into the wrong division's rankings.

WEIGHT_CLASSES = [
    {"key": "Flyweight",          "gender": "M", "limit_lbs": 125},
    {"key": "Bantamweight",       "gender": "M", "limit_lbs": 135},
    {"key": "Featherweight",      "gender": "M", "limit_lbs": 145},
    {"key": "Lightweight",        "gender": "M", "limit_lbs": 155},
    {"key": "Welterweight",       "gender": "M", "limit_lbs": 170},
    {"key": "Middleweight",       "gender": "M", "limit_lbs": 185},
    {"key": "Light Heavyweight",  "gender": "M", "limit_lbs": 205},
    {"key": "Heavyweight",        "gender": "M", "limit_lbs": 265},
    {"key": "Women's Strawweight",  "gender": "F", "limit_lbs": 115},
    {"key": "Women's Flyweight",    "gender": "F", "limit_lbs": 125},
    {"key": "Women's Bantamweight", "gender": "F", "limit_lbs": 135},
]

# how many fighters to generate per division for the starter universe
STARTER_FIGHTERS_PER_MENS_DIVISION = 20
STARTER_FIGHTERS_PER_WOMENS_DIVISION = 14

# --- Archetypes -------------------------------------------------------
# Each archetype nudges certain attribute groups up/down when generating a
# fighter. Values are additive offsets applied on top of the fighter's base
# skill roll, before clamping to [ATTR_MIN, ATTR_MAX].

ARCHETYPES = {
    "Boxer":            {"punch_technique": 14, "punch_power": 10, "head_movement": 8, "takedown_defense": 4,
                          "takedowns": -12, "submissions": -10},
    "Kickboxer":         {"kick_technique": 14, "kick_power": 12, "knee_technique": 8, "punch_technique": 4,
                           "takedowns": -10, "submissions": -10},
    "Muay Thai":         {"knee_technique": 14, "elbow_technique": 12, "clinch_work": 10, "kick_power": 6,
                           "submissions": -10, "bottom_game": -6},
    "Wrestler":          {"takedowns": 16, "takedown_defense": 14, "top_control": 12, "clinch_work": 6,
                           "punch_technique": -6, "submission_defense": 4},
    "BJJ Specialist":    {"submissions": 18, "submission_defense": 14, "bottom_game": 12, "scrambling": 8,
                           "punch_power": -8, "takedown_defense": -4},
    "Wrestle-Boxer":     {"takedowns": 10, "punch_technique": 8, "top_control": 8, "punch_power": 6,
                           "submissions": -6},
    "Brawler":           {"punch_power": 16, "chin": 8, "killer_instinct": 10, "head_movement": -10,
                           "fight_iq": -6, "cardio": -6},
    "Well-Rounded":      {},  # no bias; balanced across the board
    "Volume Striker":    {"punch_technique": 10, "cardio": 10, "consistency": 8, "punch_power": -6},
    "Ground Control":    {"top_control": 16, "takedowns": 10, "scrambling": 6, "submissions": 4,
                           "punch_power": -8},
}

ARCHETYPE_WEIGHTS = {
    "Boxer": 1.0, "Kickboxer": 0.8, "Muay Thai": 0.8, "Wrestler": 1.0,
    "BJJ Specialist": 1.0, "Wrestle-Boxer": 1.1, "Brawler": 0.9,
    "Well-Rounded": 1.3, "Volume Striker": 1.0, "Ground Control": 0.8,
}

# --- Age / career curve -----------------------------------------------

MIN_DEBUT_AGE = 19
STARTER_AGE_MIN = 21
STARTER_AGE_MAX = 38
STARTER_AGE_MODE = 27          # triangular distribution peak

PRIME_START_MIN = 26
PRIME_START_MAX = 30
PRIME_LENGTH_MIN = 3
PRIME_LENGTH_MAX = 6

# skill multiplier applied to a fighter's potential based on where `age`
# sits relative to their prime window; used by the generator (and later by
# the aging system in Phase 4) to decide how much of a fighter's potential
# is currently expressed as skill.
SKILL_RAMP_YEARS = 6           # years to go from debut to full potential
SKILL_DECLINE_START_BUFFER = 0  # years after prime_end before decline begins
SKILL_DECLINE_PER_YEAR = 0.035  # fraction of potential lost per year past prime

# --- Potential distribution ---------------------------------------------

POTENTIAL_LOW = 45
POTENTIAL_MODE = 72
POTENTIAL_HIGH = 99

# --- Record generation -----------------------------------------------

FIGHTS_PER_YEAR_MEAN = 2.1
FIGHTS_PER_YEAR_STDEV = 0.6
RECORD_SKILL_SENSITIVITY = 0.014  # how strongly skill gap shifts win probability

# finish-rate baseline by archetype family (fraction of wins that are
# finishes, split between KO and Sub via the archetype's own bias)
BASE_FINISH_RATE = 0.55
STRIKING_ARCHETYPES = {"Boxer", "Kickboxer", "Muay Thai", "Brawler", "Volume Striker"}
GRAPPLING_ARCHETYPES = {"Wrestler", "BJJ Specialist", "Ground Control"}

# --- Physical measurements by division (inches) ------------------------
# (avg_height, height_stdev, avg_reach_offset_from_height)
DIVISION_PHYSICALS = {
    "Flyweight": (66.5, 2.0), "Bantamweight": (67.5, 2.0), "Featherweight": (69.0, 2.2),
    "Lightweight": (70.5, 2.2), "Welterweight": (72.0, 2.3), "Middleweight": (73.5, 2.3),
    "Light Heavyweight": (75.0, 2.4), "Heavyweight": (76.5, 2.8),
    "Women's Strawweight": (63.5, 2.0), "Women's Flyweight": (65.0, 2.0),
    "Women's Bantamweight": (66.5, 2.1),
}

STANCE_WEIGHTS = {"Orthodox": 0.55, "Southpaw": 0.30, "Switch": 0.15}

# --- Momentum / popularity ------------------------------------------

MOMENTUM_MIN, MOMENTUM_MAX = -20, 20
POPULARITY_BASE = 20

# --- Generator attribute noise / blending --------------------------------

ATTR_NOISE_STDEV = 6              # noise applied to technique-based attributes
PHYSICAL_GIFT_NOISE_STDEV = 12    # spread of a fighter's raw athletic ceiling vs. potential
PHYSICAL_DECLINE_MULTIPLIER = 1.3  # physical attrs fade faster than technique past prime
RECORD_BASELINE_SKILL = 69        # "average roster" skill level used as the 50/50 win-prob anchor
INJURY_PRONENESS_BASE = 30
INJURY_PRONENESS_AGE_FACTOR = 1.5
WORK_ETHIC_MEAN, WORK_ETHIC_STDEV = 60, 18
