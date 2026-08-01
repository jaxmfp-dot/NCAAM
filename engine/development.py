"""Yearly attribute development/decline, applied on a fighter's birthday.

Reuses the same skill/physical curves the Phase 1 generator uses to seed a
fighter's ratings in the first place, so a fighter's trajectory over a career
is continuous with how they were rolled: technique attributes drift toward
`potential * skill_fraction(age)`, physical attributes toward
`physical_gift * physical_fraction(age)`, gated by work_ethic for technique.
Chin/toughness erode slowly once a fighter is past their prime, separate from
the larger one-time hit a bad KO/TKO loss causes (see engine/booking.py).
"""

import math
import random
import sqlite3

import config
from engine.generator import PHYSICAL_PEAK_ATTRS, TECHNIQUE_ATTRS, physical_fraction, skill_fraction


def _clamp(value: float, rng: random.Random) -> int:
    """Stochastic rounding: a flat sub-1 change (e.g. -0.5/year chin decline) needs to
    accumulate over many years on an integer column. Plain round() on a repeated exact
    .5 offset is a fixed point under banker's rounding (round(59.5) == 60, then next
    year is 60 - 0.5 == 59.5 again forever) -- rounding up/down by the fractional part's
    probability keeps the long-run average correct instead of getting stuck."""
    floor_value = math.floor(value)
    frac = value - floor_value
    rounded = floor_value + (1 if rng.random() < frac else 0)
    return max(config.ATTR_MIN, min(config.ATTR_MAX, rounded))


def apply_yearly_development(conn: sqlite3.Connection, fighter_row: dict, new_age: int,
                              rng: random.Random) -> dict:
    """Mutates the fighter's attributes in place for turning `new_age`. Returns the changes made."""
    prime_start, prime_end = fighter_row["prime_start_age"], fighter_row["prime_end_age"]
    target_skill = fighter_row["potential"] * skill_fraction(new_age, prime_start, prime_end)
    target_physical = fighter_row["physical_gift"] * physical_fraction(new_age, prime_start, prime_end)

    work_ethic_mult = (config.DEVELOPMENT_MIN_RATE_FRACTION
                        + (1 - config.DEVELOPMENT_MIN_RATE_FRACTION) * fighter_row["work_ethic"] / 100)

    updates = {}
    for attr in TECHNIQUE_ATTRS:
        gap = target_skill - fighter_row[attr]
        move = gap * config.DEVELOPMENT_RATE * work_ethic_mult + rng.gauss(0, config.DEVELOPMENT_NOISE)
        updates[attr] = _clamp(fighter_row[attr] + move, rng)

    for attr in PHYSICAL_PEAK_ATTRS:
        gap = target_physical - fighter_row[attr]
        move = gap * config.PHYSICAL_DEVELOPMENT_RATE + rng.gauss(0, config.PHYSICAL_DEVELOPMENT_NOISE)
        updates[attr] = _clamp(fighter_row[attr] + move, rng)

    if new_age > prime_end:
        updates["chin"] = _clamp(fighter_row["chin"] - config.CHIN_AGE_DECLINE_PER_YEAR_PAST_PRIME, rng)
        updates["toughness"] = _clamp(fighter_row["toughness"] - config.TOUGHNESS_AGE_DECLINE_PER_YEAR_PAST_PRIME, rng)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(f"UPDATE fighters SET {set_clause} WHERE id = ?", (*updates.values(), fighter_row["id"]))
    return updates
