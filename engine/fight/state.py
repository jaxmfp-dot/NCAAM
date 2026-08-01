"""Mutable in-fight state. Static fighter ratings stay untouched in `fighter`;
everything that changes over the course of the fight lives here."""

from dataclasses import dataclass, field

import config
from engine.fight import positions as pos


def _blank_round_stats() -> dict:
    return {
        "sig_strikes_landed": 0, "sig_strikes_attempted": 0,
        "takedowns_landed": 0, "takedowns_attempted": 0,
        "control_seconds": 0, "knockdowns": 0, "sub_attempts": 0,
    }


@dataclass
class FighterState:
    key: str                 # 'A' or 'B'
    fighter: dict             # static ratings/identity from the DB row

    health: float = config.HEALTH_START
    stamina: float = config.STAMINA_START
    cut_severity: float = 0.0
    knockdown_count: int = 0
    night_variance: float = 0.0   # one-time "on any given night" draw, set for the whole fight

    round_stats: list = field(default_factory=lambda: [_blank_round_stats()])

    def cur(self) -> dict:
        return self.round_stats[-1]

    def start_new_round(self):
        self.round_stats.append(_blank_round_stats())

    def totals(self) -> dict:
        out = _blank_round_stats()
        for rs in self.round_stats:
            for k in out:
                out[k] += rs[k]
        return out

    def rating(self, attr: str) -> float:
        return self.fighter[attr] + self.night_variance

    def stamina_mult(self) -> float:
        frac = max(0.0, min(1.0, self.stamina / config.STAMINA_START))
        return config.STAMINA_EFFECT_FLOOR + (1 - config.STAMINA_EFFECT_FLOOR) * frac

    def damage_defense_mult(self) -> float:
        """Accumulated damage erodes defense as health drops."""
        frac_lost = max(0.0, min(1.0, 1 - self.health / config.HEALTH_START))
        return 1 - config.DAMAGE_ACCUMULATED_DEFENSE_PENALTY * frac_lost

    def effective(self, attr: str, on_offense: bool) -> float:
        base = self.rating(attr)
        mult = self.stamina_mult()
        if not on_offense:
            mult *= self.damage_defense_mult()
        return base * mult

    def spend_stamina(self, amount: float):
        self.stamina = max(0.0, self.stamina - amount)

    def regen_stamina(self, amount: float):
        self.stamina = min(config.STAMINA_START, self.stamina + amount)


@dataclass
class FightState:
    fighter_a: FighterState
    fighter_b: FighterState
    rounds_total: int = config.DEFAULT_ROUNDS

    round_num: int = 1
    clock: float = config.ROUND_SECONDS
    position: str = pos.DISTANCE
    top: str | None = None            # 'A' or 'B' while on the ground
    clinch_control: str | None = None  # 'A', 'B', or None (even) while in the clinch

    round_logs: list = field(default_factory=lambda: [[]])
    scorecards: list = field(default_factory=list)   # filled in as rounds complete
    finish: dict | None = None

    def get(self, key: str) -> FighterState:
        return self.fighter_a if key == "A" else self.fighter_b

    def log(self, line: str):
        self.round_logs[-1].append(line)

    def start_new_round(self):
        self.round_num += 1
        self.clock = config.ROUND_SECONDS
        self.position = pos.DISTANCE
        self.top = None
        self.clinch_control = None
        self.fighter_a.start_new_round()
        self.fighter_b.start_new_round()
        self.round_logs.append([])

    def is_over(self) -> bool:
        return self.finish is not None
