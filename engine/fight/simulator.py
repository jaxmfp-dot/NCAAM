"""Top-level fight simulation: drives the round loop to a finish or decision,
and a batch runner for the "sim N times" debug/balance-checking mode."""

import random
import statistics
from collections import Counter

import config
from engine.fight import damage, exchanges, scoring
from engine.fight.state import FighterState, FightState


def _night_variance_stdev(fighter: dict) -> float:
    """Highly consistent fighters have a narrower "on any given night" spread."""
    consistency = fighter.get("consistency", 50)
    return max(0.5, config.FIGHT_NIGHT_VARIANCE_STDEV * (1 - (consistency - 50) / 100))


def simulate_fight(fighter_a: dict, fighter_b: dict, rounds: int | None = None, seed: int | None = None) -> dict:
    rounds = rounds or config.DEFAULT_ROUNDS
    rng = random.Random(seed)

    fs_a = FighterState(key="A", fighter=fighter_a)
    fs_b = FighterState(key="B", fighter=fighter_b)
    fs_a.night_variance = rng.gauss(0, _night_variance_stdev(fighter_a))
    fs_b.night_variance = rng.gauss(0, _night_variance_stdev(fighter_b))
    match = FightState(fighter_a=fs_a, fighter_b=fs_b, rounds_total=rounds)

    while match.round_num <= rounds and not match.is_over():
        while match.clock > 0 and not match.is_over():
            exchanges.resolve_exchange(match, rng)

        if match.is_over():
            break

        scorecard = scoring.score_round(fs_a.cur(), fs_b.cur(), rng)
        match.scorecards.append(scorecard)

        if exchanges.doctor_stoppage_check(match, rng):
            break
        if match.round_num >= rounds:
            break

        for fs in (fs_a, fs_b):
            fs.regen_stamina(damage.round_rest_regen_amount(fs))
        match.start_new_round()

    if not match.is_over():
        decision = scoring.decide_winner(match.scorecards)
        method = "DEC" if decision["winner"] else "DRAW"
        match.finish = {
            "type": method, "winner": decision["winner"], "round": rounds,
            "time": f"{config.ROUND_SECONDS // 60}:00",
            "method_detail": decision["decision_type"], "decision": decision,
        }

    finish = match.finish
    return {
        "winner_key": finish["winner"],
        "winner_name": match.get(finish["winner"]).fighter["name"] if finish["winner"] else None,
        "method": finish["type"],
        "method_detail": finish["method_detail"],
        "round": finish["round"],
        "time": finish["time"],
        "rounds_scheduled": rounds,
        "fighter_a": {"id": fighter_a.get("id"), "name": fighter_a["name"], "stats": fs_a.totals()},
        "fighter_b": {"id": fighter_b.get("id"), "name": fighter_b["name"], "stats": fs_b.totals()},
        "scorecards": match.scorecards,
        "play_by_play": match.round_logs,
    }


def _elapsed_seconds(result: dict) -> int:
    minutes, seconds = (int(x) for x in result["time"].split(":"))
    return (result["round"] - 1) * config.ROUND_SECONDS + minutes * 60 + seconds


def simulate_many(fighter_a: dict, fighter_b: dict, n: int = 1000,
                   rounds: int | None = None, seed: int | None = None) -> dict:
    rounds = rounds or config.DEFAULT_ROUNDS
    seed_rng = random.Random(seed)

    wins_a = wins_b = draws = 0
    methods_a: Counter = Counter()
    methods_b: Counter = Counter()
    seconds_list = []

    for _ in range(n):
        result = simulate_fight(fighter_a, fighter_b, rounds=rounds, seed=seed_rng.randrange(2**32))
        seconds_list.append(_elapsed_seconds(result))
        if result["winner_key"] == "A":
            wins_a += 1
            methods_a[result["method"]] += 1
        elif result["winner_key"] == "B":
            wins_b += 1
            methods_b[result["method"]] += 1
        else:
            draws += 1

    return {
        "n": n,
        "fighter_a_name": fighter_a["name"],
        "fighter_b_name": fighter_b["name"],
        "wins_a": wins_a, "wins_b": wins_b, "draws": draws,
        "win_pct_a": round(wins_a / n * 100, 1),
        "win_pct_b": round(wins_b / n * 100, 1),
        "draw_pct": round(draws / n * 100, 1),
        "methods_a": dict(methods_a),
        "methods_b": dict(methods_b),
        "avg_fight_seconds": round(statistics.mean(seconds_list), 1),
    }
