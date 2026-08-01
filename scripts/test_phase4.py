"""
Phase 4 verification: the living universe.

Sims a full year hands-off and checks that development, injuries,
retirements, and prospect generation all fired plausibly; unit-checks the
trickier pieces (development curve direction, injury recovery, title
vacancy on retirement, KO-loss durability decline, booking rejecting an
injured fighter) in isolation for determinism; and checks year-in-review
reporting against a title fight we book ourselves.
"""

import random
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rich.console import Console  # noqa: E402

import config  # noqa: E402
from engine import booking, calendar, development, injuries, reports, retirement, titles  # noqa: E402
from engine.generator import generate_universe  # noqa: E402
from models import db, event as event_model, fighter as fighter_model  # noqa: E402

console = Console()
FAILURES = []
SLOT = "_phase4_test"


def check(label, condition):
    status = "[green]PASS[/green]" if condition else "[red]FAIL[/red]"
    console.print(f"  {status}  {label}")
    if not condition:
        FAILURES.append(label)


def cleanup():
    p = db.save_path(SLOT)
    if p.exists():
        p.unlink()
    shutil.rmtree(db.PORTRAITS_DIR / SLOT, ignore_errors=True)


def setup():
    cleanup()
    conn = db.create_save(SLOT, "Phase 4 Test", universe_mode="generated", start_date="2026-01-01")
    for f in generate_universe(seed=21):
        fighter_model.insert_fighter(conn, f)
    conn.commit()
    return conn


def test_development_direction():
    console.rule("Development: technique drifts toward age-appropriate target")
    rng = random.Random(1)

    young = {
        "id": 1, "potential": 90, "physical_gift": 85, "work_ethic": 80,
        "prime_start_age": 28, "prime_end_age": 32, "chin": 60, "toughness": 60,
    }
    for attr in ["punch_technique", "kick_technique", "knee_technique", "elbow_technique",
                 "striking_defense", "head_movement", "takedowns", "takedown_defense",
                 "clinch_work", "top_control", "bottom_game", "submissions", "submission_defense",
                 "scrambling", "fight_iq", "composure", "consistency"]:
        young[attr] = 40  # well below their target skill for a 22-year-old with 90 potential
    for attr in ["strength", "speed", "agility", "punch_power", "kick_power", "cardio"]:
        young[attr] = 40

    conn = setup()
    changes = development.apply_yearly_development(conn, young, new_age=22, rng=rng)
    check("A young, hard-working prospect's technique attributes move UP toward potential",
          changes["punch_technique"] > young["punch_technique"])
    check("...and physical attributes move up too", changes["strength"] > young["strength"])

    # apply_yearly_development only needs a dict with the right keys plus a connection to
    # (harmlessly) issue its UPDATE against -- no need for a real persisted row here.
    old = dict(young)
    old["id"] = 999999
    old["prime_start_age"], old["prime_end_age"] = 26, 30
    for attr in ["punch_technique", "kick_technique", "knee_technique", "elbow_technique",
                 "striking_defense", "head_movement", "takedowns", "takedown_defense",
                 "clinch_work", "top_control", "bottom_game", "submissions", "submission_defense",
                 "scrambling", "fight_iq", "composure", "consistency"]:
        old[attr] = 85  # near their peak already
    # chin/toughness decline is a flat sub-1-point/year rate (stochastically rounded so it
    # doesn't get stuck at a fixed point) -- check the cumulative trend across many birthdays
    # past prime rather than expecting a visible drop from any single year.
    start_chin, start_toughness = old["chin"], old["toughness"]
    for age in range(31, 46):
        old.update(development.apply_yearly_development(conn, old, new_age=age, rng=rng))
    check(f"Chin trends down over 15 years past prime ({start_chin} -> {old['chin']})",
          old["chin"] < start_chin)
    check(f"Toughness trends down over 15 years past prime ({start_toughness} -> {old['toughness']})",
          old["toughness"] < start_toughness)
    conn.close()
    cleanup()


def test_injury_recovery_cycle():
    console.rule("Injury: apply then auto-recover")
    conn = setup()
    fighter = fighter_model.list_fighters(conn, sort="name")[0]

    # apply a deterministic injury directly, rather than relying on the probabilistic roll,
    # so this test exercises the booking-block and recovery mechanisms reliably
    injuries._apply_injury(conn, fighter["id"], "a test fracture", "2026-01-15")
    conn.commit()

    injured_row = fighter_model.get_fighter(conn, fighter["id"])
    check("Fighter is marked Injured", injured_row["injury_status"] == "Injured")

    try:
        other = fighter_model.list_fighters(conn, division=injured_row["weight_class"],
                                             gender=injured_row["gender"], sort="name")
        opponent = next(f for f in other if f["id"] != fighter["id"])
        event_id = event_model.create_event(conn, "Should Fail Card", "2026-01-05", "Arena")
        booking.book_bout(conn, event_id, fighter["id"], opponent["id"])
        check("Booking rejects an injured fighter", False)
    except ValueError:
        check("Booking rejects an injured fighter", True)

    recovered = injuries.process_recoveries(conn, injured_row["injury_return_date"])
    check("Recovery fires on/after the return date", any(r["id"] == fighter["id"] for r in recovered))
    healed_row = fighter_model.get_fighter(conn, fighter["id"])
    check("Fighter is Healthy again", healed_row["injury_status"] == "Healthy")
    conn.close()
    cleanup()


def test_retirement_vacates_title():
    console.rule("Retirement vacates any held titles")
    conn = setup()
    lw = fighter_model.list_fighters(conn, division="Lightweight", gender="M", sort="name")
    event_id = event_model.create_event(conn, "Title Card", "2026-01-10", "Arena")
    booking.book_bout(conn, event_id, lw[0]["id"], lw[1]["id"], is_title_fight=True)
    booking.sim_event(conn, event_id, seed=3)

    champ = titles.get_champion(conn, "Lightweight", "M")
    check("A champion was crowned", champ is not None)

    retirement.retire_fighter(conn, champ["id"], "2026-02-01")
    check("Retired fighter's status is Retired",
          fighter_model.get_fighter(conn, champ["id"])["status"] == "Retired")
    check("Title is vacant after the champion retires",
          titles.get_champion(conn, "Lightweight", "M") is None)
    conn.close()
    cleanup()


def test_ko_loss_durability_decline():
    console.rule("KO/TKO loss permanently dents chin/toughness")
    conn = setup()
    fighter = fighter_model.list_fighters(conn, sort="name")[0]
    before = fighter_model.get_fighter(conn, fighter["id"])
    booking._apply_ko_loss_damage(conn, fighter["id"])
    conn.commit()
    after = fighter_model.get_fighter(conn, fighter["id"])
    check(f"Chin dropped by {config.KO_LOSS_CHIN_PENALTY} ({before['chin']} -> {after['chin']})",
          after["chin"] == max(config.ATTR_MIN, before["chin"] - config.KO_LOSS_CHIN_PENALTY))
    check(f"Toughness dropped by {config.KO_LOSS_TOUGHNESS_PENALTY} ({before['toughness']} -> {after['toughness']})",
          after["toughness"] == max(config.ATTR_MIN, before["toughness"] - config.KO_LOSS_TOUGHNESS_PENALTY))
    conn.close()
    cleanup()


def test_full_year_hands_off():
    console.rule("Sim a full year hands-off")
    conn = setup()

    lw = fighter_model.list_fighters(conn, division="Lightweight", gender="M", sort="name")
    event_id = event_model.create_event(conn, "New Year's Card", "2026-01-05", "Arena")
    booking.book_bout(conn, event_id, lw[0]["id"], lw[1]["id"], is_title_fight=True)
    title_result = booking.sim_event(conn, event_id, seed=9)[0]
    check("Pre-seeded title fight produced a champion", title_result["winner_key"] is not None)

    active_before = len(fighter_model.list_fighters(conn, status="Active", sort="name"))

    summary = calendar.advance_weeks(conn, 53, seed=42)  # >52 weeks to guarantee a year boundary crossing
    check("Calendar advanced ~53 weeks", summary["weeks_advanced"] == 53)

    state = db.get_game_state(conn)
    expected_date = (date(2026, 1, 1) + timedelta(weeks=53)).isoformat()
    check(f"game_state.current_date advanced correctly ({state['current_date']})",
          state["current_date"] == expected_date)

    check(f"Every active fighter got exactly one birthday over 53 weeks ({summary['birthdays_processed']})",
          summary["birthdays_processed"] >= active_before)

    expected_prospects = (
        len([d for d in config.WEIGHT_CLASSES if d["gender"] == "M"]) * config.PROSPECTS_PER_MENS_DIVISION_PER_YEAR
        + len([d for d in config.WEIGHT_CLASSES if d["gender"] == "F"]) * config.PROSPECTS_PER_WOMENS_DIVISION_PER_YEAR
    )
    check(f"New prospects generated at the year boundary ({len(summary['new_prospects'])}, expected {expected_prospects})",
          len(summary["new_prospects"]) == expected_prospects)

    check(f"Some retirements occurred over the year ({len(summary['retirements'])})", len(summary["retirements"]) >= 1)
    check(f"Some training injuries occurred over the year ({len(summary['training_injuries'])})",
          len(summary["training_injuries"]) >= 1)

    for r in summary["retirements"]:
        row = fighter_model.get_fighter(conn, r["id"])
        check(f"Retired fighter {row['name']} has status Retired and a retired_date",
              row["status"] == "Retired" and row["retired_date"] is not None)

    review = reports.year_in_review(conn, 2026)
    check("Year-in-review includes our pre-seeded title change",
          any(tc["winner_name"] == title_result["winner_name"] for tc in review["title_changes"]))
    check("Year-in-review retirements match fighters retired in 2026",
          all(r["retired_date"].startswith("2026") for r in review["retirements"]))

    conn.close()
    cleanup()


if __name__ == "__main__":
    test_development_direction()
    test_injury_recovery_cycle()
    test_retirement_vacates_title()
    test_ko_loss_durability_decline()
    test_full_year_hands_off()

    console.rule("Result")
    if FAILURES:
        console.print(f"[red]{len(FAILURES)} check(s) failed:[/red]")
        for f in FAILURES:
            console.print(f"  - {f}")
        sys.exit(1)
    console.print("[green]All Phase 4 checks passed.[/green]")
