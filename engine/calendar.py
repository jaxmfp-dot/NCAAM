"""Weekly calendar advancement: the tick that makes the universe feel alive
whether or not the player books anything. Ties together injury recovery,
training injuries, birthday-triggered development/retirement checks, momentum
decay, and yearly prospect generation.
"""

import random
import sqlite3
from datetime import date, datetime, timedelta

import config
from engine import development, freeagency, injuries, prospects, retirement
from models import db
from models.fighter import compute_age


def _fighters_with_birthday_in_range(conn: sqlite3.Connection, current: date, new_date: date) -> list[dict]:
    rows = conn.execute("SELECT * FROM fighters WHERE status = 'Active'").fetchall()
    due = []
    for row in rows:
        f = dict(row)
        try:
            dob = datetime.strptime(f["dob"], "%Y-%m-%d").date()
        except ValueError:
            continue

        def _birthday_in(year: int) -> date | None:
            try:
                return date(year, dob.month, dob.day)
            except ValueError:
                return date(year, 2, 28) if dob.month == 2 else None  # Feb 29 dob fallback

        candidate = _birthday_in(current.year)
        if candidate is None:
            continue
        if candidate <= current:
            candidate = _birthday_in(current.year + 1)
            if candidate is None:
                continue
        if current < candidate <= new_date:
            due.append(f)
    return due


def advance_week(conn: sqlite3.Connection, seed: int | None = None) -> dict:
    rng = random.Random(seed)
    state = db.get_game_state(conn)
    current = datetime.strptime(state["current_date"], "%Y-%m-%d").date()
    new_date = current + timedelta(days=config.DAYS_PER_WEEK)
    new_date_str = new_date.isoformat()

    summary = {
        "from": current.isoformat(), "to": new_date_str,
        "recoveries": [], "training_injuries": [], "retirements": [], "new_prospects": [],
        "offscreen_fights": [], "birthdays_processed": 0,
    }

    summary["recoveries"] = injuries.process_recoveries(conn, new_date_str)
    summary["training_injuries"] = injuries.roll_training_injuries(conn, new_date_str, rng)
    summary["offscreen_fights"] = freeagency.run_offscreen_fights(conn, rng)

    birthday_fighters = _fighters_with_birthday_in_range(conn, current, new_date)
    summary["birthdays_processed"] = len(birthday_fighters)
    for f in birthday_fighters:
        new_age = compute_age(f["dob"], new_date)
        development.apply_yearly_development(conn, f, new_age, rng)
        if retirement.should_retire(conn, f, new_date_str, rng):
            retirement.retire_fighter(conn, f["id"], new_date_str)
            summary["retirements"].append({"id": f["id"], "name": f["name"]})

    conn.execute(
        "UPDATE fighters SET momentum = CAST(momentum * ? AS INTEGER) WHERE status = 'Active'",
        (config.MOMENTUM_WEEKLY_DECAY,),
    )

    if new_date.year != current.year:
        summary["new_prospects"] = prospects.generate_yearly_prospects(conn, new_date_str, seed=rng.randrange(2**32))

    db.set_current_date(conn, new_date_str)
    conn.commit()
    return summary


def advance_weeks(conn: sqlite3.Connection, weeks: int, seed: int | None = None) -> dict:
    rng = random.Random(seed)
    aggregate = {
        "from": None, "to": None, "weeks_advanced": weeks,
        "recoveries": [], "training_injuries": [], "retirements": [], "new_prospects": [],
        "offscreen_fights": [], "birthdays_processed": 0,
    }
    for _ in range(weeks):
        week_summary = advance_week(conn, seed=rng.randrange(2**32))
        if aggregate["from"] is None:
            aggregate["from"] = week_summary["from"]
        aggregate["to"] = week_summary["to"]
        for key in ("recoveries", "training_injuries", "retirements", "new_prospects", "offscreen_fights"):
            aggregate[key].extend(week_summary[key])
        aggregate["birthdays_processed"] += week_summary["birthdays_processed"]
    return aggregate
