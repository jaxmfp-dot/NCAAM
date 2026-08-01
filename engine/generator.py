"""Procedural generation of the starter fictional MMA universe.

A fighter's attributes come from blending two per-fighter rolls:
  - `current_skill`: technique/experience, ramps up with age toward `potential`
    then fades past the prime window (drives technique + IQ attributes).
  - `physical_gift`: raw athletic ceiling, correlated with potential but rolled
    independently (drives strength/speed/power attributes, which peak and
    decline faster than technique).
Durability/mental traits (chin, heart, work ethic, ...) are rolled mostly
independently so a green prospect can still have a granite chin, etc.
"""

import math
import random
from datetime import date, timedelta

import config
from engine import namedata
from models.fighter import GRAPPLING_ATTRS, MENTAL_ATTRS, PHYSICAL_ATTRS, STRIKING_ATTRS

TECHNIQUE_ATTRS = [
    "punch_technique", "kick_technique", "knee_technique", "elbow_technique",
    "striking_defense", "head_movement",
    "takedowns", "takedown_defense", "clinch_work", "top_control", "bottom_game",
    "submissions", "submission_defense", "scrambling",
    "fight_iq", "composure", "consistency",
]
PHYSICAL_PEAK_ATTRS = ["strength", "speed", "agility", "punch_power", "kick_power", "cardio"]
STABLE_ATTRS = ["chin", "toughness", "recovery", "heart", "killer_instinct"]

STRIKING_FINISH_SPLIT = (0.65, 0.15)   # (ko_share, sub_share) of finish wins
GRAPPLING_FINISH_SPLIT = (0.15, 0.55)
BALANCED_FINISH_SPLIT = (0.35, 0.25)


def _clamp(value, lo=config.ATTR_MIN, hi=config.ATTR_MAX):
    return max(lo, min(hi, value))


def skill_fraction(age: int, prime_start: int, prime_end: int) -> float:
    if age < prime_start:
        years_experience = max(0, age - config.MIN_DEBUT_AGE)
        ramp = min(1.0, years_experience / config.SKILL_RAMP_YEARS)
        return 0.35 + 0.65 * ramp
    if age <= prime_end:
        return 1.0
    years_past = age - prime_end - config.SKILL_DECLINE_START_BUFFER
    return max(0.4, 1.0 - config.SKILL_DECLINE_PER_YEAR * years_past)


def physical_fraction(age: int, prime_start: int, prime_end: int) -> float:
    physical_prime_start = max(config.MIN_DEBUT_AGE, prime_start - 2)
    if age < physical_prime_start:
        years_experience = max(0, age - config.MIN_DEBUT_AGE)
        ramp = min(1.0, years_experience / max(1, config.SKILL_RAMP_YEARS - 1))
        return 0.4 + 0.6 * ramp
    if age <= prime_end:
        return 1.0
    years_past = age - prime_end
    decline = config.SKILL_DECLINE_PER_YEAR * config.PHYSICAL_DECLINE_MULTIPLIER * years_past
    return max(0.3, 1.0 - decline)


def _weighted_choice(rng: random.Random, weights: dict):
    keys = list(weights.keys())
    values = [weights[k] for k in keys]
    return rng.choices(keys, weights=values, k=1)[0]


def _random_dob(rng: random.Random, age: int, as_of: date) -> str:
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    year = as_of.year - age
    dob = date(year, month, day)
    if (dob.month, dob.day) > (as_of.month, as_of.day):
        dob = date(year - 1, month, day)
    return dob.isoformat()


def _generate_record(rng: random.Random, age: int, current_skill: float, chin: float, archetype: str) -> dict:
    years_pro = max(0, age - config.MIN_DEBUT_AGE - rng.randint(0, 2))
    if years_pro == 0:
        num_fights = 0
    else:
        mean = config.FIGHTS_PER_YEAR_MEAN * years_pro
        stdev = config.FIGHTS_PER_YEAR_STDEV * math.sqrt(years_pro)
        num_fights = max(0, round(rng.gauss(mean, stdev)))
    num_fights = min(num_fights, 40)

    win_prob = _clamp(
        0.5 + (current_skill - config.RECORD_BASELINE_SKILL) * config.RECORD_SKILL_SENSITIVITY,
        0.15, 0.9,
    )

    if archetype in config.STRIKING_ARCHETYPES:
        ko_share, sub_share = STRIKING_FINISH_SPLIT
    elif archetype in config.GRAPPLING_ARCHETYPES:
        ko_share, sub_share = GRAPPLING_FINISH_SPLIT
    else:
        ko_share, sub_share = BALANCED_FINISH_SPLIT

    loss_ko_share = _clamp(0.45 - (chin - 50) * 0.003, 0.15, 0.6)
    loss_sub_share = 0.25

    record = {
        "wins": 0, "losses": 0, "draws": 0, "no_contests": 0,
        "wins_ko": 0, "wins_sub": 0, "wins_dec": 0,
        "losses_ko": 0, "losses_sub": 0, "losses_dec": 0,
    }
    recent_results = []
    for _ in range(num_fights):
        roll = rng.random()
        if roll < 0.03:
            record["draws"] += 1
            recent_results.append("D")
            continue
        if roll < 0.035:
            record["no_contests"] += 1
            continue

        if rng.random() < win_prob:
            record["wins"] += 1
            recent_results.append("W")
            outcome_roll = rng.random()
            if outcome_roll < ko_share:
                record["wins_ko"] += 1
            elif outcome_roll < ko_share + sub_share:
                record["wins_sub"] += 1
            else:
                record["wins_dec"] += 1
        else:
            record["losses"] += 1
            recent_results.append("L")
            outcome_roll = rng.random()
            if outcome_roll < loss_ko_share:
                record["losses_ko"] += 1
            elif outcome_roll < loss_ko_share + loss_sub_share:
                record["losses_sub"] += 1
            else:
                record["losses_dec"] += 1

    record["_recent_results"] = recent_results[-5:]
    return record


def generate_fighter(rng: random.Random, weight_class: str, gender: str, as_of: date,
                      age_min: int | None = None, age_max: int | None = None, age_mode: int | None = None) -> dict:
    nationality = rng.choice(list(namedata.NATIONALITIES))
    pool = namedata.NATIONALITIES[nationality]
    first = rng.choice(pool["m_first"] if gender == "M" else pool["f_first"])
    last = rng.choice(pool["last"])
    nickname = rng.choice(namedata.NICKNAMES) if rng.random() < 0.6 else None
    hometown = rng.choice(pool["cities"])

    age_min = config.STARTER_AGE_MIN if age_min is None else age_min
    age_max = config.STARTER_AGE_MAX if age_max is None else age_max
    age_mode = config.STARTER_AGE_MODE if age_mode is None else age_mode
    age = round(rng.triangular(age_min, age_max, age_mode))
    dob = _random_dob(rng, age, as_of)

    potential = round(rng.triangular(config.POTENTIAL_LOW, config.POTENTIAL_HIGH, config.POTENTIAL_MODE))
    archetype = _weighted_choice(rng, config.ARCHETYPE_WEIGHTS)
    offsets = config.ARCHETYPES[archetype]

    prime_start = rng.randint(config.PRIME_START_MIN, config.PRIME_START_MAX)
    prime_end = prime_start + rng.randint(config.PRIME_LENGTH_MIN, config.PRIME_LENGTH_MAX)

    current_skill = potential * skill_fraction(age, prime_start, prime_end)
    physical_gift = _clamp(potential + rng.gauss(0, config.PHYSICAL_GIFT_NOISE_STDEV))
    physical_skill = physical_gift * physical_fraction(age, prime_start, prime_end)

    attrs = {}
    for attr in TECHNIQUE_ATTRS:
        attrs[attr] = round(_clamp(current_skill + offsets.get(attr, 0) + rng.gauss(0, config.ATTR_NOISE_STDEV)))
    for attr in PHYSICAL_PEAK_ATTRS:
        attrs[attr] = round(_clamp(physical_skill + offsets.get(attr, 0) + rng.gauss(0, config.ATTR_NOISE_STDEV)))
    for attr in STABLE_ATTRS:
        attrs[attr] = round(_clamp(physical_gift + offsets.get(attr, 0) + rng.gauss(0, config.ATTR_NOISE_STDEV + 2)))

    attrs["work_ethic"] = round(_clamp(rng.gauss(config.WORK_ETHIC_MEAN, config.WORK_ETHIC_STDEV)))
    attrs["injury_proneness"] = round(_clamp(
        rng.gauss(config.INJURY_PRONENESS_BASE + max(0, age - 32) * config.INJURY_PRONENESS_AGE_FACTOR, 15)
    ))

    missing = (set(STRIKING_ATTRS + GRAPPLING_ATTRS + PHYSICAL_ATTRS + MENTAL_ATTRS) - set(attrs))
    assert not missing, f"generator left attributes unset: {missing}"

    record = _generate_record(rng, age, current_skill, attrs["chin"], archetype)
    recent = record.pop("_recent_results")
    momentum = _clamp(sum(1 if r == "W" else -1 if r == "L" else 0 for r in recent) * 6
                       + rng.gauss(0, 4), config.MOMENTUM_MIN, config.MOMENTUM_MAX)

    finishes = record["wins_ko"] + record["wins_sub"]
    popularity = _clamp(
        config.POPULARITY_BASE + record["wins"] * 1.2 + finishes * 2 + potential * 0.3 + rng.gauss(0, 8),
        1, 99,
    )

    avg_height, height_stdev = config.DIVISION_PHYSICALS[weight_class]
    height_in = round(rng.gauss(avg_height, height_stdev), 1)
    reach_in = round(height_in + rng.gauss(1.0, 2.0), 1)
    stance = _weighted_choice(rng, config.STANCE_WEIGHTS)

    fighter = {
        "name": f"{first} {last}",
        "nickname": nickname,
        "dob": dob,
        "nationality": nationality,
        "hometown": hometown,
        "weight_class": weight_class,
        "gender": gender,
        "height_in": height_in,
        "reach_in": reach_in,
        "stance": stance,
        "portrait_filename": None,
        "potential": potential,
        "physical_gift": round(physical_gift),
        "momentum": round(momentum),
        "prime_start_age": prime_start,
        "prime_end_age": prime_end,
        "popularity": round(popularity),
        "contract_status": "Signed",
        "promotion": "UFC",
        "status": "Active",
        "archetype": archetype,
        **attrs,
        **record,
    }
    return fighter


def generate_universe(seed: int | None = None, as_of: date | None = None) -> list[dict]:
    rng = random.Random(seed)
    as_of = as_of or date.today()
    fighters = []
    for division in config.WEIGHT_CLASSES:
        count = (config.STARTER_FIGHTERS_PER_MENS_DIVISION if division["gender"] == "M"
                 else config.STARTER_FIGHTERS_PER_WOMENS_DIVISION)
        for _ in range(count):
            fighters.append(generate_fighter(rng, division["key"], division["gender"], as_of))
    return fighters
