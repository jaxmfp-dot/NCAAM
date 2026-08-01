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

# =========================================================================
# FIGHT ENGINE (Phase 2)
# =========================================================================

# --- Clock -------------------------------------------------------------

ROUND_SECONDS = 300
DEFAULT_ROUNDS = 3
TITLE_ROUNDS = 5
EXCHANGE_SECONDS_MIN = 6
EXCHANGE_SECONDS_MAX = 18
GROUND_EXCHANGE_SECONDS_MIN = 10
GROUND_EXCHANGE_SECONDS_MAX = 26

# --- Contests ------------------------------------------------------------
# Every action is resolved as (attacker_rating + noise) vs (defender_rating + noise).
# CONTEST_VARIANCE is the stdev of that noise -- higher means more upset potential.

CONTEST_VARIANCE = 14
CONTEST_SCALE = 12.0          # divides the margin before it goes through a logistic curve

# A single draw per fighter per fight ("having a night") added on top of their
# ratings for the whole bout. Per-exchange noise alone washes out over the ~50-70
# rolls in a fight (law of large numbers), which crushes upset potential for any
# real skill gap; this is what keeps "on any given night" true across many sims.
FIGHT_NIGHT_VARIANCE_STDEV = 10.0

# --- Action tendency weights (who does what, at range) -------------------
# Raw attribute-derived weights are multiplied by these before a fighter's
# action is picked at distance; higher = fighter leans into it more.

TENDENCY_TAKEDOWN_MULT = 1.15
TENDENCY_CLINCH_MULT = 0.75
TENDENCY_STRIKE_MULT = 1.0

# --- Stamina ---------------------------------------------------------

STAMINA_START = 100.0
STAMINA_REGEN_PER_EXCHANGE = 1.6      # baseline passive regen each exchange, scaled by cardio/recovery
STAMINA_COST_STRIKE_THROWN = 2.5
STAMINA_COST_STRIKE_LANDED_BONUS = 1.0
STAMINA_COST_TAKEDOWN_ATTEMPT = 6.0
STAMINA_COST_TAKEDOWN_LANDED_BONUS = 2.0
STAMINA_COST_CLINCH_EXCHANGE = 3.0
STAMINA_COST_GROUND_EXCHANGE = 4.0
STAMINA_COST_SUB_ATTEMPT = 7.0
ROUND_REST_REGEN_BASE = 34.0          # flat regen between rounds, scaled by recovery attribute
STAMINA_EFFECT_FLOOR = 0.55           # a fully gassed fighter still performs at this fraction

# --- Damage / health -----------------------------------------------------

HEALTH_START = 100.0
DAMAGE_BASE_SCALE = 0.34
DAMAGE_MIN = 1.0
DAMAGE_MAX = 28.0
DAMAGE_ACCUMULATED_DEFENSE_PENALTY = 0.25  # max fraction of defense lost as health nears 0

KNOCKDOWN_HEALTH_THRESHOLD = 42       # health at/below this after a clean shot triggers a knockdown
CRIT_CHANCE_BASE = 0.05
CRIT_POWER_GAP_SCALE = 0.004
CRIT_DAMAGE_MULT = 1.8
FOLLOWUP_STRIKES_MIN = 2
FOLLOWUP_STRIKES_MAX = 4
FOLLOWUP_DEFENSE_MULT = 0.4           # defender's effective defense while dazed on the ground/against the cage
TKO_STOPPAGE_CHANCE_PER_FOLLOWUP = 0.32
MAX_KNOCKDOWNS_BEFORE_TKO = 3         # three-knockdown-rule equivalent

# --- Cuts ------------------------------------------------------------

CUT_CHANCE_PER_LANDED_STRIKE = 0.02
CUT_SEVERITY_MIN, CUT_SEVERITY_MAX = 5, 18
CUT_DOCTOR_STOPPAGE_THRESHOLD = 70
CUT_DOCTOR_STOPPAGE_CHANCE = 0.5      # checked between rounds once severity crosses the threshold

# --- Submissions -----------------------------------------------------

SUB_CONTEST_VARIANCE = 12
SUB_TAP_MARGIN_THRESHOLD = 16         # contest margin needed before a tap is even possible
SUB_TAP_CHANCE_SCALE = 0.03           # extra margin above threshold -> additional tap probability

# --- Round scoring (10-9 / 10-8) --------------------------------------

EFFECTIVENESS_SIG_STRIKE = 1.0
EFFECTIVENESS_TAKEDOWN = 5.0
EFFECTIVENESS_CONTROL_MINUTE = 3.0
EFFECTIVENESS_KNOCKDOWN = 15.0
EFFECTIVENESS_SUB_ATTEMPT = 4.0

JUDGE_COUNT = 3
JUDGE_SCORE_NOISE = 6.0               # per-judge noise, source of split/majority decisions
ROUND_DOMINANT_MARGIN = 25.0          # effectiveness margin (post-noise) that earns a 10-8
ROUND_DRAW_MARGIN = 3.0               # margin below which a 10-10 round becomes possible
ROUND_DRAW_CHANCE = 0.06

# =========================================================================
# BOOKING / RANKINGS (Phase 3)
# =========================================================================

# --- Ranking points ----------------------------------------------------
# A fighter's ranking score is the recency-weighted sum of points earned
# from their most recent wins. Losses/draws contribute nothing (they don't
# help you climb, but they don't retroactively erase a good win either).

RANKING_WIN_BASE_POINTS = 100.0
RANKING_FINISH_BONUS = 30.0           # bonus for winning by KO/TKO/SUB instead of decision
RANKING_CHAMPION_BEATEN_BONUS = 150.0  # opponent was rank 0 (champion, interim counts too)
RANKING_TOP5_BONUS = 80.0             # opponent was ranked 1-5
RANKING_TOP10_BONUS = 50.0            # opponent was ranked 6-10
RANKING_TOP15_BONUS = 25.0            # opponent was ranked 11-15
RANKING_RECENCY_HALFLIFE_DAYS = 365.0  # a win's point value halves every ~1 year of inactivity
RANKING_MAX_FIGHTS_CONSIDERED = 10    # only a fighter's most recent N wins count toward ranking
RANKING_TOP_N = 15

# A fighter imported with real-world standing but no sim fight history yet gets a
# rank-seed (1-15) instead of points earned in-game. It decays with the same half-life
# as a real win, so the seeded order holds on day one but fades as sim history replaces
# it -- rank 1 is worth SEED_RANK_TOP_POINTS, rank 15 worth SEED_RANK_BOTTOM_POINTS,
# linearly interpolated between.
SEED_RANK_TOP_POINTS = 500.0
SEED_RANK_BOTTOM_POINTS = 150.0

# --- Post-fight momentum / popularity shifts ----------------------------

MOMENTUM_WIN_DELTA = 8
MOMENTUM_WIN_FINISH_BONUS = 4
MOMENTUM_LOSS_DELTA = -10
MOMENTUM_LOSS_FINISH_PENALTY = -4     # losing by finish stings more than a decision loss
MOMENTUM_DRAW_DELTA = -1

POPULARITY_WIN_DELTA = 2.0
POPULARITY_FINISH_BONUS = 3.0
POPULARITY_TITLE_FIGHT_BONUS = 5.0
POPULARITY_LOSS_DELTA = -1.0

# =========================================================================
# LIVING UNIVERSE (Phase 4)
# =========================================================================

# --- Calendar ----------------------------------------------------------

DAYS_PER_WEEK = 7
WEEKS_PER_YEAR = 52

# --- Yearly development (applied on a fighter's birthday) ----------------
# Technique attributes drift toward `potential * skill_fraction(age)`; how much
# of that gap closes in one year depends on work_ethic. Physical attributes
# drift toward `physical_gift * physical_fraction(age)` the same way, but
# aren't work-ethic-gated (athleticism rides the age curve more than habits).

DEVELOPMENT_RATE = 0.35          # fraction of the technique gap-to-target closed per year at 100 work_ethic
DEVELOPMENT_MIN_RATE_FRACTION = 0.25  # even a 0 work_ethic fighter still closes this fraction of DEVELOPMENT_RATE
DEVELOPMENT_NOISE = 2.5
PHYSICAL_DEVELOPMENT_RATE = 0.45
PHYSICAL_DEVELOPMENT_NOISE = 2.5

# durability erodes gradually once a fighter is past prime, on top of any
# damage-driven decline from KO/TKO losses (below)
CHIN_AGE_DECLINE_PER_YEAR_PAST_PRIME = 0.5
TOUGHNESS_AGE_DECLINE_PER_YEAR_PAST_PRIME = 0.4

# a KO/TKO loss permanently chips away at durability -- "punch drunk" over a career
KO_LOSS_CHIN_PENALTY = 4
KO_LOSS_TOUGHNESS_PENALTY = 2

# --- Injuries ----------------------------------------------------------

TRAINING_INJURY_BASE_WEEKLY_CHANCE = 0.0015    # at injury_proneness = 50 (roster average)
TRAINING_INJURY_PRONENESS_SCALE = 0.00003      # additional weekly chance per point of injury_proneness
TRAINING_INJURY_WEEKS_MIN = 1
TRAINING_INJURY_WEEKS_MAX = 16

FIGHT_INJURY_BASE_CHANCE_LOSER = 0.06
FIGHT_INJURY_BASE_CHANCE_WINNER = 0.015
FIGHT_INJURY_FINISH_MULT = 1.8                 # losing by finish raises injury odds
FIGHT_INJURY_WEEKS_MIN = 2
FIGHT_INJURY_WEEKS_MAX = 26

# --- Retirement ----------------------------------------------------------
# Weighted score -> probability; checked on a fighter's birthday and
# immediately after any loss.

RETIREMENT_HARD_AGE = 45              # near-guaranteed retirement past this age
RETIREMENT_AGE_PAST_PRIME_FACTOR = 2.5   # score per year past prime_end_age
RETIREMENT_LOSING_STREAK_FACTOR = 9.0    # score per fight in an active losing streak
RETIREMENT_KO_LOSSES_FACTOR = 3.0        # score per career KO/TKO loss (accumulated damage)
RETIREMENT_MOMENTUM_RELIEF = 0.2         # positive momentum subtracts from the score
RETIREMENT_SCORE_TO_PROB_SCALE = 0.01    # probability = clamp(score * this, 0, cap)
RETIREMENT_PROB_CAP = 0.92

# --- Momentum decay ----------------------------------------------------

MOMENTUM_WEEKLY_DECAY = 0.97          # applied to every active fighter each week (fades toward 0 if inactive)

# --- Prospect generation ------------------------------------------------

PROSPECT_AGE_MIN = 19
PROSPECT_AGE_MAX = 24
PROSPECT_AGE_MODE = 21
PROSPECTS_PER_MENS_DIVISION_PER_YEAR = 2
PROSPECTS_PER_WOMENS_DIVISION_PER_YEAR = 1

# --- Year in review ------------------------------------------------------

BREAKOUT_PROSPECT_MAX_AGE = 25
BREAKOUT_PROSPECT_MIN_WINS = 2

# --- Free agency / off-screen fights -----------------------------------
# Fighters outside the UFC keep fighting "off-screen": each week an active,
# healthy non-UFC fighter has a small chance of having taken a fight, resolved
# with the real fight engine when a same-division non-UFC opponent exists, or
# against a synthetic regional opponent otherwise. Only records/momentum update
# (no bout rows -- these fights happen outside the promotion you control).

OFFSCREEN_WEEKLY_FIGHT_CHANCE = 0.05      # ~2.6 fights/year per non-UFC fighter
OFFSCREEN_REGIONAL_OPPONENT_SKILL = 55.0  # baseline skill of a synthetic regional opponent
FREE_AGENT_LIST_SIZE = 20

# free-agent judgment score weights: what "the game thinks" a fighter is worth
FA_SCORE_SKILL_WEIGHT = 0.6       # core skill average
FA_SCORE_POTENTIAL_WEIGHT = 0.25
FA_SCORE_WINRATE_WEIGHT = 25.0    # scaled by career win rate
FA_SCORE_MOMENTUM_WEIGHT = 0.3
FA_SCORE_YOUTH_BONUS_PER_YEAR = 0.6  # bonus per year under 30 (age curve upside)
