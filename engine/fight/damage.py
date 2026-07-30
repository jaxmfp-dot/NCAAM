"""Pure math helpers: attribute contests, strike damage, knockdowns, cuts, stamina."""

import math
import random

import config
from engine.fight.state import FighterState


def contest_margin(rng: random.Random, attacker_eff: float, defender_eff: float,
                    variance: float = config.CONTEST_VARIANCE) -> float:
    a = attacker_eff + rng.gauss(0, variance)
    d = defender_eff + rng.gauss(0, variance)
    return a - d


def logistic(x: float, scale: float = config.CONTEST_SCALE) -> float:
    return 1.0 / (1.0 + math.exp(-x / scale))


def compute_strike_damage(rng: random.Random, power: float, defense: float) -> tuple[float, bool]:
    """Returns (damage, is_crit)."""
    margin = power - defense + rng.gauss(0, config.CONTEST_VARIANCE * 0.5)
    crit_chance = min(0.4, config.CRIT_CHANCE_BASE + max(0.0, margin) * config.CRIT_POWER_GAP_SCALE)
    is_crit = rng.random() < crit_chance

    raw = 5.0 + margin * config.DAMAGE_BASE_SCALE
    if is_crit:
        raw *= config.CRIT_DAMAGE_MULT
    ceiling = config.DAMAGE_MAX * (config.CRIT_DAMAGE_MULT if is_crit else 1.0)
    damage = max(config.DAMAGE_MIN, min(ceiling, raw))
    return damage, is_crit


def maybe_open_cut(rng: random.Random, power: float) -> float:
    chance = config.CUT_CHANCE_PER_LANDED_STRIKE * (1 + power / 100)
    if rng.random() < chance:
        return rng.uniform(config.CUT_SEVERITY_MIN, config.CUT_SEVERITY_MAX)
    return 0.0


def stamina_regen_amount(fs: FighterState) -> float:
    cardio_factor = (fs.rating("cardio") + fs.rating("recovery")) / 200.0
    return config.STAMINA_REGEN_PER_EXCHANGE * (0.5 + cardio_factor)


def round_rest_regen_amount(fs: FighterState) -> float:
    return config.ROUND_REST_REGEN_BASE * (0.5 + fs.rating("recovery") / 200.0)


def followup_survives(rng: random.Random, defender: FighterState) -> bool:
    """True if the ref lets the fight continue after an unanswered follow-up shot."""
    toughness_factor = (defender.rating("heart") + defender.rating("composure")) / 200.0
    stoppage_chance = config.TKO_STOPPAGE_CHANCE_PER_FOLLOWUP * (1.3 - toughness_factor)
    return rng.random() >= max(0.05, min(0.85, stoppage_chance))
