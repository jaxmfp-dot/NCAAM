"""Training and in-fight injuries: occurrence, recovery timelines, auto-healing."""

import random
import sqlite3
from datetime import datetime, timedelta

import config

TRAINING_INJURY_DESCRIPTIONS = [
    "a strained hamstring", "a sprained ankle", "a shoulder impingement", "a rib strain",
    "a knee tweak", "a lower back strain", "a torn calf", "a wrist sprain",
    "a hip flexor strain", "a stress fracture in the foot",
]
FIGHT_INJURY_DESCRIPTIONS = [
    "a broken hand", "a fractured orbital bone", "a torn ACL", "a dislocated shoulder",
    "a broken nose", "a deep cut requiring stitches", "torn rib cartilage",
    "a broken jaw", "ligament damage in the knee", "a separated shoulder",
]


def _weeks_out(rng: random.Random, lo: int, hi: int) -> int:
    return round(rng.triangular(lo, hi, lo))  # skewed toward shorter recoveries


def _apply_injury(conn: sqlite3.Connection, fighter_id: int, description: str, return_date: str):
    conn.execute(
        "UPDATE fighters SET injury_status = 'Injured', injury_description = ?, injury_return_date = ? "
        "WHERE id = ?",
        (description, return_date, fighter_id),
    )


def process_recoveries(conn: sqlite3.Connection, as_of_date: str) -> list[dict]:
    rows = conn.execute(
        "SELECT id, name FROM fighters WHERE injury_status = 'Injured' AND injury_return_date <= ?",
        (as_of_date,),
    ).fetchall()
    for row in rows:
        conn.execute(
            "UPDATE fighters SET injury_status = 'Healthy', injury_description = NULL, "
            "injury_return_date = NULL WHERE id = ?",
            (row["id"],),
        )
    return [dict(r) for r in rows]


def roll_training_injuries(conn: sqlite3.Connection, as_of_date: str, rng: random.Random) -> list[dict]:
    as_of = datetime.strptime(as_of_date, "%Y-%m-%d").date()
    fighters = conn.execute(
        "SELECT id, name, injury_proneness FROM fighters WHERE status = 'Active' AND injury_status = 'Healthy'"
    ).fetchall()

    occurred = []
    for f in fighters:
        chance = (config.TRAINING_INJURY_BASE_WEEKLY_CHANCE
                  + f["injury_proneness"] * config.TRAINING_INJURY_PRONENESS_SCALE)
        if rng.random() >= chance:
            continue
        weeks = _weeks_out(rng, config.TRAINING_INJURY_WEEKS_MIN, config.TRAINING_INJURY_WEEKS_MAX)
        description = rng.choice(TRAINING_INJURY_DESCRIPTIONS)
        return_date = (as_of + timedelta(weeks=weeks)).isoformat()
        _apply_injury(conn, f["id"], description, return_date)
        occurred.append({"id": f["id"], "name": f["name"], "description": description,
                          "weeks": weeks, "return_date": return_date})
    return occurred


def maybe_apply_fight_injury(conn: sqlite3.Connection, fighter_id: int, fighter_name: str,
                              is_loser: bool, was_finish: bool, as_of_date: str,
                              rng: random.Random) -> dict | None:
    chance = config.FIGHT_INJURY_BASE_CHANCE_LOSER if is_loser else config.FIGHT_INJURY_BASE_CHANCE_WINNER
    if was_finish:
        chance *= config.FIGHT_INJURY_FINISH_MULT
    if rng.random() >= chance:
        return None

    as_of = datetime.strptime(as_of_date, "%Y-%m-%d").date()
    weeks = _weeks_out(rng, config.FIGHT_INJURY_WEEKS_MIN, config.FIGHT_INJURY_WEEKS_MAX)
    description = rng.choice(FIGHT_INJURY_DESCRIPTIONS)
    return_date = (as_of + timedelta(weeks=weeks)).isoformat()
    _apply_injury(conn, fighter_id, description, return_date)
    return {"id": fighter_id, "name": fighter_name, "description": description,
            "weeks": weeks, "return_date": return_date}
