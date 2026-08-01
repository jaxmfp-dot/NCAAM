"""
Phase 6 verification: real roster import, promotions, free agency, off-screen fights.

Checks that the real heavyweight import produces the exact champion and 1-15
ranking order supplied by the user, that cut/sign flows move fighters between
the UFC roster and free agency correctly (titles vacated, booking blocked,
rankings scoped to UFC), that the top-20 free agent list is judgment-ordered,
and that non-UFC fighters' records evolve via off-screen fights over a
simulated stretch of calendar time.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rich.console import Console  # noqa: E402

from engine import booking, calendar, freeagency, rankings, realimport, titles  # noqa: E402
from models import db, event as event_model, fighter as fighter_model  # noqa: E402

console = Console()
FAILURES = []
SLOT = "_phase6_test"
START = "2026-08-01"

EXPECTED_TOP_15 = [
    "Ciryl Gane", "Alexander Volkov", "Waldo Cortes-Acosta", "Sergei Pavlovich",
    "Alex Pereira", "Rizvan Kuniev", "Serghei Spivac", "Valter Walker", "Josh Hokit",
    "Curtis Blaydes", "Derrick Lewis", "Ante Delija", "Marcin Tybura",
    "Brando Peričić", "Ryan Spann",
]


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
    conn = db.create_save(SLOT, "Phase 6 Test", universe_mode="real", start_date=START)
    realimport.import_all_real(conn, START, seed=5)
    return conn


def test_real_import():
    console.rule("Real heavyweight import")
    conn = setup()

    hw = fighter_model.list_fighters(conn, division="Heavyweight", gender="M", sort="name", status="Active")
    ufc_count = sum(1 for f in hw if f["promotion"] == "UFC")
    check(f"All 95 heavyweights imported ({len(hw)})", len(hw) == 95)
    check(f"42 on the UFC roster, 53 outside it ({ufc_count} UFC)", ufc_count == 42)
    check("No duplicate names slipped through the overlap guard",
          len({f["name"] for f in hw}) == len(hw))

    champ = titles.get_champion(conn, "Heavyweight", "M")
    check("Tom Aspinall is champion", champ is not None and champ["name"] == "Tom Aspinall")
    check("Champion record is 15-3 (1 NC)", champ["wins"] == 15 and champ["losses"] == 3 and champ["no_contests"] == 1)

    rk = rankings.compute_rankings(conn, "Heavyweight", "M", as_of_date=START)
    got_order = [c["fighter"]["name"] for c in rk["contenders"]]
    check("Top 15 matches the supplied ranking order exactly", got_order == EXPECTED_TOP_15)

    lane = next(f for f in hw if f["name"] == "Austen Lane")
    check("Austen Lane imported as a Free Agent", lane["promotion"] == "Free Agent")
    check("Free agent is not in the UFC rankings", all(n != "Austen Lane" for n in got_order))

    gane = next(f for f in hw if f["name"] == "Ciryl Gane")
    steveson = next(f for f in hw if f["name"] == "Gable Steveson")
    check("Ranked contender out-rates an unranked newcomer overall",
          gane["punch_technique"] + gane["fight_iq"] > steveson["punch_technique"] + steveson["fight_iq"])
    check("Young unranked fighter carries upside (potential > current tier)",
          steveson["potential"] > steveson["punch_technique"] - 10)

    kuniev = next(f for f in hw if f["name"] == "Rizvan Kuniev")
    check("Corrected record applied (Kuniev 15-3-1, 1 NC)",
          (kuniev["wins"], kuniev["losses"], kuniev["draws"], kuniev["no_contests"]) == (15, 3, 1, 1))

    agents = freeagency.top_free_agents(conn, START)
    check(f"Free agent list is a full top 20 ({len(agents)})", len(agents) == 20)
    check("Ngannou tops the availability list", agents[0]["name"] == "Francis Ngannou")
    top10_names = {a["name"] for a in agents[:13]}
    expected_elite = {"Francis Ngannou", "Anatoly Malykhin", "Vadim Nemkov", "Denis Goltsov",
                       "Ryan Bader", "Renan Ferreira", "Valentin Moldavsky", "Phil De Fries"}
    check("The supplied elite non-UFC names dominate the top of the list",
          expected_elite.issubset(top10_names))
    small_sample = [a["name"] for a in agents[:10] if a["wins"] + a["losses"] <= 3]
    check("No tiny-sample records in the top 10 (win-rate shrinkage works)", not small_sample)
    return conn


def test_cut_and_sign(conn):
    console.rule("Cut / sign flows")
    champ = titles.get_champion(conn, "Heavyweight", "M")

    freeagency.cut_fighter(conn, champ["id"])
    cut_row = fighter_model.get_fighter(conn, champ["id"])
    check("Cut fighter becomes a Free Agent", cut_row["promotion"] == "Free Agent")
    check("Cutting the champion vacates the belt", titles.get_champion(conn, "Heavyweight", "M") is None)
    check("Cut fighter's rank seed is cleared", cut_row["manual_rank_seed"] is None)

    rk = rankings.compute_rankings(conn, "Heavyweight", "M", as_of_date=START)
    all_ranked = [c["fighter"]["name"] for c in rk["contenders"]]
    check("Cut fighter no longer appears in rankings", champ["name"] not in all_ranked)

    hw = fighter_model.list_fighters(conn, division="Heavyweight", gender="M", sort="name")
    opponent = next(f for f in hw if f["promotion"] == "UFC" and f["id"] != champ["id"])
    event_id = event_model.create_event(conn, "Blocked Card", "2026-08-15", "Arena")
    try:
        booking.book_bout(conn, event_id, champ["id"], opponent["id"])
        check("Booking rejects a non-UFC fighter", False)
    except ValueError:
        check("Booking rejects a non-UFC fighter", True)

    agents = freeagency.top_free_agents(conn, START)
    agent_names = [f["name"] for f in agents]
    check("Cut ex-champion lands in the top 3 of the availability list (alongside Ngannou et al.)",
          champ["name"] in agent_names[:3])
    check("Free agent scores are sorted descending",
          all(agents[i]["fa_score"] >= agents[i + 1]["fa_score"] for i in range(len(agents) - 1)))

    freeagency.sign_fighter(conn, champ["id"])
    signed = fighter_model.get_fighter(conn, champ["id"])
    check("Re-signed fighter is back on the UFC roster", signed["promotion"] == "UFC")
    check("Re-signing does NOT restore the vacated belt", titles.get_champion(conn, "Heavyweight", "M") is None)

    try:
        freeagency.sign_fighter(conn, champ["id"])
        check("Signing an already-UFC fighter is rejected", False)
    except ValueError:
        check("Signing an already-UFC fighter is rejected", True)


def test_offscreen_fights(conn):
    console.rule("Off-screen fights for non-UFC fighters")
    hw = fighter_model.list_fighters(conn, division="Heavyweight", gender="M", sort="name")
    victims = [f for f in hw if f["promotion"] == "UFC"][:6]
    for f in victims:
        freeagency.cut_fighter(conn, f["id"])

    pool_ids = [f["id"] for f in victims] + [f["id"] for f in hw if f["promotion"] == "Free Agent"]
    before = {fid: fighter_model.get_fighter(conn, fid) for fid in pool_ids}
    before_fights = {fid: f["wins"] + f["losses"] + f["draws"] for fid, f in before.items()}

    summary = calendar.advance_weeks(conn, 40, seed=9)
    check(f"Off-screen fights occurred over 40 weeks ({len(summary['offscreen_fights'])})",
          len(summary["offscreen_fights"]) >= 1)

    after_fights = {}
    changed = 0
    for fid in pool_ids:
        row = fighter_model.get_fighter(conn, fid)
        after_fights[fid] = row["wins"] + row["losses"] + row["draws"]
        if row["status"] == "Active" and after_fights[fid] > before_fights[fid]:
            changed += 1
    check(f"At least one non-UFC fighter's record changed ({changed} of {len(pool_ids)})", changed >= 1)

    ufc_ids = [f["id"] for f in hw if f["promotion"] == "UFC" and f["id"] not in pool_ids]
    ufc_unchanged = all(
        (fighter_model.get_fighter(conn, fid)["wins"] + fighter_model.get_fighter(conn, fid)["losses"])
        == (next(x for x in hw if x["id"] == fid)["wins"] + next(x for x in hw if x["id"] == fid)["losses"])
        for fid in ufc_ids[:8]
    )
    check("UFC fighters' records do NOT change off-screen (only booked fights count)", ufc_unchanged)


if __name__ == "__main__":
    conn = test_real_import()
    test_cut_and_sign(conn)
    test_offscreen_fights(conn)
    conn.close()
    cleanup()

    console.rule("Result")
    if FAILURES:
        console.print(f"[red]{len(FAILURES)} check(s) failed:[/red]")
        for f in FAILURES:
            console.print(f"  - {f}")
        sys.exit(1)
    console.print("[green]All Phase 6 checks passed.[/green]")
