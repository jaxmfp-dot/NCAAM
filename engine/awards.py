"""Yearly awards: Fighter of the Year, KO/Submission of the Year, Fight of the Year.

Heuristic and explainable, not a hidden formula: Fighter of the Year rewards
winning (and winning by finish, and winning a title), KO/Sub of the Year
reward beating a highly-ranked opponent and finishing them early, Fight of
the Year rewards high output/knockdowns and, for decisions, a close
(split) verdict.
"""

import sqlite3

import config
from engine import rankings
from models import event as event_model
from models.fighter import get_fighter

FINISH_METHODS = ("KO", "TKO", "SUB")
KO_METHODS = ("KO", "TKO")


def _year_range(year: int) -> tuple[str, str]:
    return f"{year}-01-01", f"{year}-12-31"


def _opponent_rank_for_winner(bout: dict) -> int | None:
    return bout["a_faced_rank"] if bout["winner_id"] == bout["fighter_a_id"] else bout["b_faced_rank"]


def _elapsed_seconds(bout: dict) -> int:
    minutes, seconds = (int(x) for x in bout["result_time"].split(":"))
    return (bout["result_round"] - 1) * config.ROUND_SECONDS + minutes * 60 + seconds


def _bout_summary(bout: dict) -> dict:
    is_a_winner = bout["winner_id"] == bout["fighter_a_id"]
    return {
        "winner_name": bout["fighter_a_name"] if is_a_winner else bout["fighter_b_name"],
        "loser_name": bout["fighter_b_name"] if is_a_winner else bout["fighter_a_name"],
        "event_name": bout["event_name"], "event_date": bout["event_date"],
        "method_detail": bout["method_detail"], "round": bout["result_round"], "time": bout["result_time"],
    }


def fighter_of_the_year(conn: sqlite3.Connection, year: int) -> dict | None:
    bouts = event_model.bouts_in_range(conn, *_year_range(year))
    wins, losses, finishes, title_wins = {}, {}, {}, set()
    for b in bouts:
        winner = b["winner_id"]
        if winner is None:
            continue
        loser = b["fighter_b_id"] if winner == b["fighter_a_id"] else b["fighter_a_id"]
        wins[winner] = wins.get(winner, 0) + 1
        losses[loser] = losses.get(loser, 0) + 1
        if b["method"] in FINISH_METHODS:
            finishes[winner] = finishes.get(winner, 0) + 1
        if b["is_title_fight"] and b["title_change"]:
            title_wins.add(winner)

    if not wins:
        return None

    best_id, best_score = None, float("-inf")
    for fighter_id, win_count in wins.items():
        score = (win_count * 10 + finishes.get(fighter_id, 0) * 5 - losses.get(fighter_id, 0) * 8
                 + (15 if fighter_id in title_wins else 0))
        if score > best_score:
            best_id, best_score = fighter_id, score

    fighter = get_fighter(conn, best_id)
    if fighter is None:
        return None
    return {
        "id": best_id, "name": fighter["name"], "weight_class": fighter["weight_class"],
        "gender": fighter["gender"], "wins_this_year": wins[best_id],
        "losses_this_year": losses.get(best_id, 0), "finishes_this_year": finishes.get(best_id, 0),
        "won_title_this_year": best_id in title_wins,
    }


def _finish_of_the_year(conn: sqlite3.Connection, year: int, methods: tuple[str, ...]) -> dict | None:
    bouts = [b for b in event_model.bouts_in_range(conn, *_year_range(year)) if b["method"] in methods]
    if not bouts:
        return None
    best = max(bouts, key=lambda b: rankings.rank_bonus(_opponent_rank_for_winner(b)) - _elapsed_seconds(b) / 30)
    return _bout_summary(best)


def ko_of_the_year(conn: sqlite3.Connection, year: int) -> dict | None:
    return _finish_of_the_year(conn, year, KO_METHODS)


def submission_of_the_year(conn: sqlite3.Connection, year: int) -> dict | None:
    return _finish_of_the_year(conn, year, ("SUB",))


def fight_of_the_year(conn: sqlite3.Connection, year: int) -> dict | None:
    bouts = event_model.bouts_in_range(conn, *_year_range(year))
    if not bouts:
        return None

    def action_score(b: dict) -> float:
        stats_a = b["stats"]["fighter_a"]["stats"]
        stats_b = b["stats"]["fighter_b"]["stats"]
        total_strikes = stats_a["sig_strikes_landed"] + stats_b["sig_strikes_landed"]
        knockdowns = stats_a["knockdowns"] + stats_b["knockdowns"]
        close_bonus = 30 if "Split" in (b["method_detail"] or "") else 0
        finish_bonus = 20 if b["method"] in FINISH_METHODS else 0
        return total_strikes + knockdowns * 15 + close_bonus + finish_bonus

    best = max(bouts, key=action_score)
    return _bout_summary(best)


def yearly_awards(conn: sqlite3.Connection, year: int) -> dict:
    return {
        "year": year,
        "fighter_of_the_year": fighter_of_the_year(conn, year),
        "ko_of_the_year": ko_of_the_year(conn, year),
        "submission_of_the_year": submission_of_the_year(conn, year),
        "fight_of_the_year": fight_of_the_year(conn, year),
    }
