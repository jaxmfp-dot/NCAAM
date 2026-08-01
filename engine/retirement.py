"""Retirement: a weighted score (age past prime, losing streak, accumulated
head trauma, momentum) turned into a probability, checked on a fighter's
birthday and immediately after any loss."""

import random
import sqlite3
from datetime import datetime

import config
from engine import titles
from models import event as event_model
from models.fighter import compute_age


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _losing_streak(conn: sqlite3.Connection, fighter_id: int) -> int:
    history = event_model.fighter_history(conn, fighter_id)
    streak = 0
    for bout in history:
        if bout["outcome"] != "Loss":
            break
        streak += 1
    return streak


def should_retire(conn: sqlite3.Connection, fighter_row: dict, as_of_date: str, rng: random.Random) -> bool:
    as_of = datetime.strptime(as_of_date, "%Y-%m-%d").date()
    age = compute_age(fighter_row["dob"], as_of)

    score = 0.0
    if age > fighter_row["prime_end_age"]:
        score += (age - fighter_row["prime_end_age"]) * config.RETIREMENT_AGE_PAST_PRIME_FACTOR
    if age >= config.RETIREMENT_HARD_AGE:
        score += 100.0
    score += _losing_streak(conn, fighter_row["id"]) * config.RETIREMENT_LOSING_STREAK_FACTOR
    score += fighter_row["losses_ko"] * config.RETIREMENT_KO_LOSSES_FACTOR
    score -= max(0, fighter_row["momentum"]) * config.RETIREMENT_MOMENTUM_RELIEF

    probability = _clamp(score * config.RETIREMENT_SCORE_TO_PROB_SCALE, 0.0, config.RETIREMENT_PROB_CAP)
    return rng.random() < probability


def retire_fighter(conn: sqlite3.Connection, fighter_id: int, as_of_date: str):
    conn.execute("UPDATE fighters SET status = 'Retired', retired_date = ? WHERE id = ?",
                 (as_of_date, fighter_id))
    held_titles = conn.execute("SELECT id FROM titles WHERE champion_id = ?", (fighter_id,)).fetchall()
    for t in held_titles:
        titles.vacate_title(conn, t["id"])
