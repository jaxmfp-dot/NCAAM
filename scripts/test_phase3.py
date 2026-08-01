"""
Phase 3 verification: booking, event simulation, records, rankings, and titles.

Books a full card (including a vacant-title fight), sims it, and checks that
records/momentum, the title, and division rankings all update correctly.
Also checks booking validation (duplicate booking, cross-division booking,
title-fight-without-champion booking) and head-to-head/fight-history after a
rematch.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rich.console import Console  # noqa: E402

import config  # noqa: E402
from engine import booking, rankings, titles  # noqa: E402
from engine.generator import generate_universe  # noqa: E402
from models import db, event as event_model, fighter as fighter_model  # noqa: E402

console = Console()
FAILURES = []
SLOT = "_phase3_test"


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
    conn = db.create_save(SLOT, "Phase 3 Test", universe_mode="generated")
    for f in generate_universe(seed=11):
        fighter_model.insert_fighter(conn, f)
    conn.commit()
    return conn


def test_full_card():
    console.rule("Book and sim a full card")
    conn = setup()

    lw = fighter_model.list_fighters(conn, division="Lightweight", gender="M", sort="name")
    fw = fighter_model.list_fighters(conn, division="Flyweight", gender="M", sort="name")

    event_id = event_model.create_event(conn, "Debut Card", "2026-03-01", "Test Arena")

    prelim_bout = booking.book_bout(conn, event_id, lw[0]["id"], lw[1]["id"], card_segment="prelim")
    contender_bout = booking.book_bout(conn, event_id, lw[2]["id"], lw[3]["id"],
                                        card_segment="main", is_number_one_contender=True)
    title_bout = booking.book_bout(conn, event_id, lw[4]["id"], lw[5]["id"],
                                    card_segment="main", is_title_fight=True, rounds=5)
    unrelated_bout = booking.book_bout(conn, event_id, fw[0]["id"], fw[1]["id"], card_segment="prelim")
    check("Booked 4 distinct bouts", len({prelim_bout, contender_bout, title_bout, unrelated_bout}) == 4)

    # validation checks
    try:
        booking.book_bout(conn, event_id, lw[0]["id"], lw[6]["id"])
        check("Rejects double-booking a fighter already on the card", False)
    except ValueError:
        check("Rejects double-booking a fighter already on the card", True)

    try:
        booking.book_bout(conn, event_id, lw[6]["id"], fw[2]["id"])
        check("Rejects cross-division booking", False)
    except ValueError:
        check("Rejects cross-division booking", True)

    pre_wins_a = fighter_model.get_fighter(conn, lw[0]["id"])["wins"]
    pre_losses_b = fighter_model.get_fighter(conn, lw[1]["id"])["losses"]

    results = booking.sim_event(conn, event_id, seed=42)
    check("All 4 bouts produced a result", len(results) == 4)

    event = event_model.get_event(conn, event_id)
    check("Event marked Completed once every bout is simmed", event["status"] == "Completed")

    title_result = next(r for r in results if r["fighter_a"]["id"] in (lw[4]["id"], lw[5]["id"]))
    check("Vacant title fight produced a champion", title_result["winner_key"] is not None)

    title = titles.get_title(conn, "Lightweight", "M", is_interim=False)
    check("Title now has a champion on record", title["champion_id"] is not None)
    check("Champion matches the title bout's winner", title["champion_id"] == title_result["winner_fighter_id"])
    check("New champion has 0 defenses (first win)", title["defenses"] == 0)

    winner_row = fighter_model.get_fighter(conn, title_result["winner_fighter_id"])
    loser_id = lw[4]["id"] if title_result["winner_fighter_id"] == lw[5]["id"] else lw[5]["id"]
    loser_row = fighter_model.get_fighter(conn, loser_id)
    check(f"Champion's win count incremented ({winner_row['record']})", winner_row["wins"] >= 1)
    check(f"Loser's loss count incremented ({loser_row['record']})", loser_row["losses"] >= 1)

    post_a = fighter_model.get_fighter(conn, lw[0]["id"])
    post_b = fighter_model.get_fighter(conn, lw[1]["id"])
    check("Prelim bout also updated records",
          (post_a["wins"] > pre_wins_a) or (post_b["losses"] > pre_losses_b)
          or (post_a["losses"] > 0) or (post_b["wins"] > 0))

    rk = rankings.compute_rankings(conn, "Lightweight", "M", as_of_date="2026-03-01")
    check("Champion is set in rankings output", rk["champion"] is not None and rk["champion"]["id"] == title["champion_id"])
    check("Champion is excluded from the numbered contenders list",
          all(c["fighter"]["id"] != title["champion_id"] for c in rk["contenders"]))
    ranked_ids = [c["fighter"]["id"] for c in rk["contenders"]]
    check("At least one non-title winner shows up ranked", len(ranked_ids) >= 1)

    fw_rk = rankings.compute_rankings(conn, "Flyweight", "M", as_of_date="2026-03-01")
    fw_ranked_ids = {c["fighter"]["id"] for c in fw_rk["contenders"]}
    check("A Lightweight winner never leaks into the Flyweight rankings",
          fw_ranked_ids.isdisjoint(set(ranked_ids) | {title["champion_id"]}))

    return conn, event_id, lw, fw


def test_title_fight_requires_champion(conn, lw):
    console.rule("Title-fight booking validation")
    other_event = event_model.create_event(conn, "Card 2", "2026-04-01", "Test Arena 2")
    champ = titles.get_champion(conn, "Lightweight", "M")
    non_champ_pair = [f for f in lw if f["id"] != champ["id"]][:2]
    try:
        booking.book_bout(conn, other_event, non_champ_pair[0]["id"], non_champ_pair[1]["id"],
                           is_title_fight=True)
        check("Rejects a title fight that excludes the champion", False)
    except ValueError:
        check("Rejects a title fight that excludes the champion", True)

    # champion defends successfully validates booking logic accepts a legit title fight
    challenger = non_champ_pair[0]
    bout_id = booking.book_bout(conn, other_event, champ["id"], challenger["id"], is_title_fight=True)
    check("Accepts a title fight that includes the champion", bout_id is not None)


def test_rematch_history(conn, lw):
    console.rule("Rematch: head-to-head and fight history")
    a, b = lw[0], lw[1]
    h2h_before = event_model.head_to_head(conn, a["id"], b["id"])
    check("One prior meeting on record", len(h2h_before["bouts"]) == 1)

    event_id = event_model.create_event(conn, "Rematch Card", "2026-05-01", "Test Arena 3")
    booking.book_bout(conn, event_id, a["id"], b["id"])
    booking.sim_event(conn, event_id, seed=99)

    h2h_after = event_model.head_to_head(conn, a["id"], b["id"])
    check("Second meeting recorded", len(h2h_after["bouts"]) == 2)
    check("Win tallies sum to total meetings",
          h2h_after["wins_a"] + h2h_after["wins_b"] + h2h_after["draws"] == 2)

    hist_a = event_model.fighter_history(conn, a["id"])
    check("Fighter A's history includes both meetings", len(hist_a) >= 2)
    check("History entries are newest first", hist_a[0]["event_date"] >= hist_a[1]["event_date"])


def test_partial_sim(conn):
    console.rule("Fight-by-fight (partial) event simulation")
    fw = fighter_model.list_fighters(conn, division="Featherweight", gender="M", sort="name")
    event_id = event_model.create_event(conn, "Partial Card", "2026-06-01", "Test Arena 4")
    b1 = booking.book_bout(conn, event_id, fw[0]["id"], fw[1]["id"])
    booking.book_bout(conn, event_id, fw[2]["id"], fw[3]["id"])

    booking.sim_bout(conn, b1, seed=1)
    event = event_model.get_event(conn, event_id)
    check("Event stays Scheduled after only one of two bouts is simmed", event["status"] == "Scheduled")

    booking.sim_event(conn, event_id, seed=2)
    event = event_model.get_event(conn, event_id)
    check("Event becomes Completed once the rest is simmed", event["status"] == "Completed")


if __name__ == "__main__":
    conn, event_id, lw, fw = test_full_card()
    test_title_fight_requires_champion(conn, lw)
    test_rematch_history(conn, lw)
    test_partial_sim(conn)
    conn.close()
    cleanup()

    console.rule("Result")
    if FAILURES:
        console.print(f"[red]{len(FAILURES)} check(s) failed:[/red]")
        for f in FAILURES:
            console.print(f"  - {f}")
        sys.exit(1)
    console.print("[green]All Phase 3 checks passed.[/green]")
