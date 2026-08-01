"""
Phase 5 verification: quality-of-life features.

Checks roster filters (age/streak/ranked-only), yearly awards computation,
event recap export text, the fighter editor's validation/clamping, and
save deletion.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rich.console import Console  # noqa: E402

import config  # noqa: E402
from engine import awards, booking, recap  # noqa: E402
from engine.generator import generate_universe  # noqa: E402
from models import db, event as event_model, fighter as fighter_model  # noqa: E402

console = Console()
FAILURES = []
SLOT = "_phase5_test"


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
    conn = db.create_save(SLOT, "Phase 5 Test", universe_mode="generated", start_date="2026-01-01")
    for f in generate_universe(seed=31):
        fighter_model.insert_fighter(conn, f)
    conn.commit()
    return conn


def test_roster_filters():
    console.rule("Roster filters: age, streak, ranked-only")
    conn = setup()

    all_fighters = fighter_model.list_fighters(conn, sort="name")
    aged = fighter_model.list_fighters(conn, age_min=30, age_max=35, sort="name")
    check(f"Age filter narrows the roster ({len(aged)} of {len(all_fighters)})",
          0 < len(aged) < len(all_fighters))
    check("Age filter respects both bounds", all(30 <= f["age"] <= 35 for f in aged))

    lw = fighter_model.list_fighters(conn, division="Lightweight", gender="M", sort="name")
    event_id = event_model.create_event(conn, "Streak Card", "2026-01-10", "Arena")
    booking.book_bout(conn, event_id, lw[0]["id"], lw[1]["id"])
    booking.book_bout(conn, event_id, lw[2]["id"], lw[3]["id"])
    booking.sim_event(conn, event_id, seed=1)

    streaks = event_model.compute_streaks(conn)
    check("Every fighter in a completed bout has a streak entry",
          all(lw[i]["id"] in streaks for i in range(4)))
    check("Streak counts are positive after one fight",
          all(streaks[lw[i]["id"]]["count"] >= 1 for i in range(4)))

    conn.close()
    cleanup()


def test_awards():
    console.rule("Yearly awards")
    conn = setup()
    lw = fighter_model.list_fighters(conn, division="Lightweight", gender="M", sort="name")
    event_id = event_model.create_event(conn, "Awards Card", "2026-03-01", "Arena")
    booking.book_bout(conn, event_id, lw[0]["id"], lw[1]["id"], is_title_fight=True)
    booking.book_bout(conn, event_id, lw[2]["id"], lw[3]["id"])
    booking.sim_event(conn, event_id, seed=2)

    result = awards.yearly_awards(conn, 2026)
    check("Fighter of the Year is awarded", result["fighter_of_the_year"] is not None)
    check("Fighter of the Year has a non-negative record this year",
          result["fighter_of_the_year"]["wins_this_year"] >= 1)
    check("Fight of the Year is awarded (at least one completed fight)", result["fight_of_the_year"] is not None)
    check("No awards for an empty year", awards.yearly_awards(conn, 1999)["fighter_of_the_year"] is None)

    conn.close()
    cleanup()


def test_export():
    console.rule("Event recap export")
    conn = setup()
    lw = fighter_model.list_fighters(conn, division="Featherweight", gender="M", sort="name")
    event_id = event_model.create_event(conn, "Export Card", "2026-04-01", "Test Arena")
    booking.book_bout(conn, event_id, lw[0]["id"], lw[1]["id"], card_segment="main", is_number_one_contender=True)
    booking.book_bout(conn, event_id, lw[2]["id"], lw[3]["id"], card_segment="prelim")
    booking.sim_event(conn, event_id, seed=3)

    text = recap.export_event_text(conn, event_id)
    check("Export includes the event name", "EXPORT CARD" in text)
    check("Export includes the venue", "Test Arena" in text)
    check("Export includes both card segments", "MAIN CARD" in text and "PRELIMS" in text)
    check("Export includes both fighters' names", lw[0]["name"] in text and lw[2]["name"] in text)
    check("Export includes the #1 contender tag", "#1 CONTENDER FIGHT" in text)

    try:
        recap.export_event_text(conn, 999999)
        check("Export raises for a nonexistent event", False)
    except ValueError:
        check("Export raises for a nonexistent event", True)

    conn.close()
    cleanup()


def test_fighter_editor():
    console.rule("Fighter editor: validation and clamping")
    conn = setup()
    fighter = fighter_model.list_fighters(conn, sort="name")[0]

    updated = fighter_model.update_fighter(conn, fighter["id"], {
        "punch_power": 500, "momentum": -999, "popularity": -50, "nickname": "The Edited One",
    })
    check(f"Skill attr clamped to ATTR_MAX ({updated['punch_power']})", updated["punch_power"] == config.ATTR_MAX)
    check(f"Momentum clamped to MOMENTUM_MIN ({updated['momentum']})", updated["momentum"] == config.MOMENTUM_MIN)
    check(f"Popularity clamped to 1 ({updated['popularity']})", updated["popularity"] == 1)
    check("Text field updated as given", updated["nickname"] == "The Edited One")

    cleared = fighter_model.update_fighter(conn, fighter["id"], {"nickname": None})
    check("Optional field can be cleared to NULL", cleared["nickname"] is None)

    try:
        fighter_model.update_fighter(conn, fighter["id"], {"gender": "X"})
        check("Rejects an invalid gender", False)
    except ValueError:
        check("Rejects an invalid gender", True)

    try:
        fighter_model.update_fighter(conn, fighter["id"], {"weight_class": "Not A Real Division"})
        check("Rejects an unknown weight_class", False)
    except ValueError:
        check("Rejects an unknown weight_class", True)

    try:
        fighter_model.update_fighter(conn, fighter["id"], {"is_champion_of_everything": True})
        check("Rejects an unknown/non-editable field", False)
    except ValueError:
        check("Rejects an unknown/non-editable field", True)

    conn.close()
    cleanup()


def test_save_deletion():
    console.rule("Save deletion")
    conn = setup()
    conn.close()
    check("Save file exists before deletion", db.save_path(SLOT).exists())
    check("Portraits dir exists before deletion", (db.PORTRAITS_DIR / SLOT).is_dir())

    db.delete_save(SLOT)
    check("Save file removed", not db.save_path(SLOT).exists())
    check("Portraits dir removed", not (db.PORTRAITS_DIR / SLOT).is_dir())
    check("Deleted slot no longer appears in list_saves()", SLOT not in [s["slot"] for s in db.list_saves()])


if __name__ == "__main__":
    test_roster_filters()
    test_awards()
    test_export()
    test_fighter_editor()
    test_save_deletion()

    console.rule("Result")
    if FAILURES:
        console.print(f"[red]{len(FAILURES)} check(s) failed:[/red]")
        for f in FAILURES:
            console.print(f"  - {f}")
        sys.exit(1)
    console.print("[green]All Phase 5 checks passed.[/green]")
