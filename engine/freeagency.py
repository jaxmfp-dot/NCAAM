"""Roster management outside the UFC: cutting, signing, the top-20 free agent
list, and off-screen fights that keep non-UFC fighters' records evolving.

"Free agent" here means any active fighter whose promotion != 'UFC' -- whether
truly unsigned ('Free Agent') or under contract elsewhere ('PFL', 'ONE', ...).
The user said all non-UFC fighters are signable, so the availability list ranks
every one of them by the game's own judgment of their worth.
"""

import random
import sqlite3
from datetime import datetime

import config
from engine import titles
from engine.fight.simulator import simulate_fight
from engine.generator import (BALANCED_FINISH_SPLIT, GRAPPLING_FINISH_SPLIT,
                               STRIKING_FINISH_SPLIT)
from models.fighter import compute_age, get_fighter, row_to_dict

# core skill attrs averaged for the judgment score -- deliberately excludes
# durability/mental noise so the list reads like a scouting report
_CORE_SKILL_ATTRS = [
    "punch_technique", "kick_technique", "punch_power", "striking_defense",
    "takedowns", "takedown_defense", "submissions", "top_control",
    "cardio", "speed", "fight_iq",
]


def cut_fighter(conn: sqlite3.Connection, fighter_id: int) -> dict:
    fighter = get_fighter(conn, fighter_id)
    if fighter is None:
        raise ValueError(f"Fighter {fighter_id} not found")
    if fighter["promotion"] != "UFC":
        raise ValueError(f"{fighter['name']} is not on the UFC roster")

    booked = conn.execute(
        "SELECT id FROM bouts WHERE status = 'Scheduled' AND (fighter_a_id = ? OR fighter_b_id = ?)",
        (fighter_id, fighter_id),
    ).fetchone()
    if booked:
        raise ValueError(f"{fighter['name']} has a scheduled bout -- remove it from the card first")

    held = conn.execute("SELECT id FROM titles WHERE champion_id = ?", (fighter_id,)).fetchall()
    for t in held:
        titles.vacate_title(conn, t["id"])

    conn.execute(
        "UPDATE fighters SET promotion = 'Free Agent', manual_rank_seed = NULL, "
        "manual_rank_seed_date = NULL WHERE id = ?",
        (fighter_id,),
    )
    conn.commit()
    return get_fighter(conn, fighter_id)


def sign_fighter(conn: sqlite3.Connection, fighter_id: int) -> dict:
    fighter = get_fighter(conn, fighter_id)
    if fighter is None:
        raise ValueError(f"Fighter {fighter_id} not found")
    if fighter["promotion"] == "UFC":
        raise ValueError(f"{fighter['name']} is already on the UFC roster")
    if fighter["status"] != "Active":
        raise ValueError(f"{fighter['name']} is retired")

    conn.execute("UPDATE fighters SET promotion = 'UFC' WHERE id = ?", (fighter_id,))
    conn.commit()
    return get_fighter(conn, fighter_id)


def judgment_score(fighter: dict, as_of_date: str) -> float:
    skill = sum(fighter[a] for a in _CORE_SKILL_ATTRS) / len(_CORE_SKILL_ATTRS)
    # shrunk toward .500 so a 5-0 record is weaker evidence than a 20-2 one
    k = config.FA_WINRATE_SHRINKAGE
    total_fights = fighter["wins"] + fighter["losses"]
    win_rate = (fighter["wins"] + 0.5 * k) / (total_fights + k)
    age = compute_age(fighter["dob"], datetime.strptime(as_of_date, "%Y-%m-%d").date())
    youth_bonus = max(0, 30 - age) * config.FA_SCORE_YOUTH_BONUS_PER_YEAR

    return (
        skill * config.FA_SCORE_SKILL_WEIGHT
        + fighter["potential"] * config.FA_SCORE_POTENTIAL_WEIGHT
        + win_rate * config.FA_SCORE_WINRATE_WEIGHT
        + fighter["momentum"] * config.FA_SCORE_MOMENTUM_WEIGHT
        + youth_bonus
    )


def top_free_agents(conn: sqlite3.Connection, as_of_date: str, n: int | None = None) -> list[dict]:
    n = n or config.FREE_AGENT_LIST_SIZE
    rows = conn.execute(
        "SELECT * FROM fighters WHERE status = 'Active' AND promotion != 'UFC'"
    ).fetchall()
    scored = []
    for row in rows:
        f = row_to_dict(row)
        f["fa_score"] = round(judgment_score(f, as_of_date), 1)
        scored.append(f)
    scored.sort(key=lambda f: f["fa_score"], reverse=True)
    return scored[:n]


# --- Off-screen fights ---------------------------------------------------

def _finish_split(archetype: str | None) -> tuple[float, float]:
    if archetype in config.STRIKING_ARCHETYPES:
        return STRIKING_FINISH_SPLIT
    if archetype in config.GRAPPLING_ARCHETYPES:
        return GRAPPLING_FINISH_SPLIT
    return BALANCED_FINISH_SPLIT


def _record_result(conn: sqlite3.Connection, fighter_id: int, won: bool, method: str):
    prefix = "wins" if won else "losses"
    col = {"KO": f"{prefix}_ko", "TKO": f"{prefix}_ko", "SUB": f"{prefix}_sub"}.get(method, f"{prefix}_dec")
    momentum_delta = config.MOMENTUM_WIN_DELTA if won else config.MOMENTUM_LOSS_DELTA
    conn.execute(
        f"UPDATE fighters SET {prefix} = {prefix} + 1, {col} = {col} + 1, "
        f"momentum = MAX(?, MIN(?, momentum + ?)) WHERE id = ?",
        (config.MOMENTUM_MIN, config.MOMENTUM_MAX, momentum_delta, fighter_id),
    )


def _synthetic_opponent_fight(conn: sqlite3.Connection, fighter: dict, rng: random.Random) -> dict:
    """Resolve a fight against an unseen regional opponent from a skill-based win probability."""
    skill = sum(fighter[a] for a in _CORE_SKILL_ATTRS) / len(_CORE_SKILL_ATTRS)
    win_prob = max(0.2, min(0.92,
        0.5 + (skill - config.OFFSCREEN_REGIONAL_OPPONENT_SKILL) * config.RECORD_SKILL_SENSITIVITY))
    won = rng.random() < win_prob

    ko_share, sub_share = _finish_split(fighter.get("archetype"))
    roll = rng.random()
    method = "KO" if roll < ko_share else ("SUB" if roll < ko_share + sub_share else "DEC")
    _record_result(conn, fighter["id"], won, method)
    return {"id": fighter["id"], "name": fighter["name"], "won": won, "method": method,
            "opponent_name": "regional opponent"}


def run_offscreen_fights(conn: sqlite3.Connection, rng: random.Random) -> list[dict]:
    """Weekly tick: some non-UFC fighters take fights outside the promotion.
    Same-division pairs use the real fight engine; odd ones out face synthetic
    regional opposition. Only records/momentum change -- no bout rows."""
    rows = conn.execute(
        "SELECT * FROM fighters WHERE status = 'Active' AND promotion != 'UFC' "
        "AND injury_status = 'Healthy'"
    ).fetchall()

    fighting = [dict(r) for r in rows if rng.random() < config.OFFSCREEN_WEEKLY_FIGHT_CHANCE]
    if not fighting:
        return []

    results = []
    by_division: dict[tuple, list[dict]] = {}
    for f in fighting:
        by_division.setdefault((f["weight_class"], f["gender"]), []).append(f)

    for pool in by_division.values():
        rng.shuffle(pool)
        while len(pool) >= 2:
            a, b = pool.pop(), pool.pop()
            outcome = simulate_fight(a, b, rounds=3, seed=rng.randrange(2**32))
            winner_id = {"A": a["id"], "B": b["id"]}.get(outcome["winner_key"])
            for f in (a, b):
                if winner_id is None:
                    conn.execute("UPDATE fighters SET draws = draws + 1 WHERE id = ?", (f["id"],))
                else:
                    _record_result(conn, f["id"], f["id"] == winner_id, outcome["method"])
            results.append({
                "a_name": a["name"], "b_name": b["name"],
                "winner_name": outcome["winner_name"], "method": outcome["method"],
            })
        if pool:  # odd one out fights someone off the map
            results.append(_synthetic_opponent_fight(conn, pool.pop(), rng))
    return results
