"""Round scoring (10-9 / 10-8) and 3-judge decision aggregation."""

from collections import Counter

import config


def round_effectiveness(round_stats: dict) -> float:
    return (
        round_stats["sig_strikes_landed"] * config.EFFECTIVENESS_SIG_STRIKE
        + round_stats["takedowns_landed"] * config.EFFECTIVENESS_TAKEDOWN
        + (round_stats["control_seconds"] / 60) * config.EFFECTIVENESS_CONTROL_MINUTE
        + round_stats["knockdowns"] * config.EFFECTIVENESS_KNOCKDOWN
        + round_stats["sub_attempts"] * config.EFFECTIVENESS_SUB_ATTEMPT
    )


def score_round(a_round_stats: dict, b_round_stats: dict, rng) -> dict:
    """Scores one round from JUDGE_COUNT independent, slightly noisy judges."""
    eff_a = round_effectiveness(a_round_stats)
    eff_b = round_effectiveness(b_round_stats)
    knockdown_edge_a = a_round_stats["knockdowns"] > b_round_stats["knockdowns"]
    knockdown_edge_b = b_round_stats["knockdowns"] > a_round_stats["knockdowns"]

    judges = []
    for _ in range(config.JUDGE_COUNT):
        noisy_a = eff_a + rng.gauss(0, config.JUDGE_SCORE_NOISE)
        noisy_b = eff_b + rng.gauss(0, config.JUDGE_SCORE_NOISE)
        margin = noisy_a - noisy_b

        if abs(margin) <= config.ROUND_DRAW_MARGIN and rng.random() < config.ROUND_DRAW_CHANCE:
            judges.append((10, 10))
        elif margin >= 0:
            dominant = margin >= config.ROUND_DOMINANT_MARGIN or knockdown_edge_a
            judges.append((10, 8) if dominant else (10, 9))
        else:
            dominant = -margin >= config.ROUND_DOMINANT_MARGIN or knockdown_edge_b
            judges.append((8, 10) if dominant else (9, 10))

    return {"judges": judges, "eff_a": round(eff_a, 1), "eff_b": round(eff_b, 1)}


def decide_winner(scorecards: list[dict]) -> dict:
    """Aggregates per-round judge scores into a final decision."""
    totals = [[0, 0] for _ in range(config.JUDGE_COUNT)]
    for rc in scorecards:
        for j, (a, b) in enumerate(rc["judges"]):
            totals[j][0] += a
            totals[j][1] += b

    judge_results = []
    for a, b in totals:
        if a > b:
            judge_results.append("A")
        elif b > a:
            judge_results.append("B")
        else:
            judge_results.append("Draw")

    counts = Counter(judge_results)
    if counts["A"] == config.JUDGE_COUNT:
        winner, decision_type = "A", "Unanimous Decision"
    elif counts["B"] == config.JUDGE_COUNT:
        winner, decision_type = "B", "Unanimous Decision"
    elif counts["A"] == 2 and counts["Draw"] == 1:
        winner, decision_type = "A", "Majority Decision"
    elif counts["B"] == 2 and counts["Draw"] == 1:
        winner, decision_type = "B", "Majority Decision"
    elif counts["A"] == 2 and counts["B"] == 1:
        winner, decision_type = "A", "Split Decision"
    elif counts["B"] == 2 and counts["A"] == 1:
        winner, decision_type = "B", "Split Decision"
    elif counts["Draw"] == config.JUDGE_COUNT:
        winner, decision_type = None, "Unanimous Draw"
    elif counts["Draw"] == 2:
        winner, decision_type = None, "Majority Draw"
    else:
        winner, decision_type = None, "Split Draw"

    return {"winner": winner, "decision_type": decision_type,
            "judge_results": judge_results, "totals": totals}
