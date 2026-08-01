"""
Phase 1 verification: generate a starter universe, sanity-check the data,
print a roster breakdown, print one full fighter profile, and exercise the
CSV importer against a small sample file. Cleans up its own save slots.
"""

import shutil
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rich.console import Console  # noqa: E402
from rich.table import Table  # noqa: E402

import config  # noqa: E402
from engine.generator import generate_universe  # noqa: E402
from engine.importer import import_fighters  # noqa: E402
from models import db, fighter as fighter_model  # noqa: E402

console = Console()
FAILURES = []


def check(label, condition):
    status = "[green]PASS[/green]" if condition else "[red]FAIL[/red]"
    console.print(f"  {status}  {label}")
    if not condition:
        FAILURES.append(label)


def cleanup(slot):
    p = db.save_path(slot)
    if p.exists():
        p.unlink()
    portraits = db.PORTRAITS_DIR / slot
    if portraits.exists():
        shutil.rmtree(portraits)


def test_generated_universe():
    console.rule("Generated starter universe")
    slot = "_phase1_test_generated"
    cleanup(slot)
    conn = db.create_save(slot, "Phase 1 Test (Generated)", universe_mode="generated")

    fighters = generate_universe(seed=42)
    for f in fighters:
        fighter_model.insert_fighter(conn, f)
    conn.commit()

    expected_total = (
        len([d for d in config.WEIGHT_CLASSES if d["gender"] == "M"]) * config.STARTER_FIGHTERS_PER_MENS_DIVISION
        + len([d for d in config.WEIGHT_CLASSES if d["gender"] == "F"]) * config.STARTER_FIGHTERS_PER_WOMENS_DIVISION
    )
    check(f"Generated {len(fighters)} fighters (expected {expected_total})", len(fighters) == expected_total)

    rows = fighter_model.list_fighters(conn, status="Active", sort="name")
    check(f"All {len(rows)} fighters queryable via list_fighters", len(rows) == expected_total)

    skill_attrs = fighter_model.SKILL_ATTRS
    out_of_range = [
        (r["name"], a, r[a]) for r in rows for a in skill_attrs
        if not (config.ATTR_MIN <= r[a] <= config.ATTR_MAX)
    ]
    check("All skill attributes within [1, 99]", len(out_of_range) == 0)
    if out_of_range:
        console.print(f"    offenders: {out_of_range[:5]}")

    ages = [r["age"] for r in rows]
    check(f"Ages within starter bounds (min={min(ages)}, max={max(ages)})",
          min(ages) >= config.STARTER_AGE_MIN - 1 and max(ages) <= config.STARTER_AGE_MAX + 1)

    divisions = fighter_model.list_divisions(conn)
    table = Table(title="Roster by division")
    table.add_column("Division")
    table.add_column("Gender")
    table.add_column("Count", justify="right")
    table.add_column("Avg Age", justify="right")
    table.add_column("Avg Potential", justify="right")
    table.add_column("Avg Win%", justify="right")
    for d in divisions:
        div_rows = [r for r in rows if r["weight_class"] == d["weight_class"] and r["gender"] == d["gender"]]
        avg_age = statistics.mean(r["age"] for r in div_rows)
        avg_pot = statistics.mean(r["potential"] for r in div_rows)
        win_pcts = [r["wins"] / (r["wins"] + r["losses"]) for r in div_rows if (r["wins"] + r["losses"]) > 0]
        avg_win_pct = statistics.mean(win_pcts) * 100 if win_pcts else 0
        table.add_row(d["weight_class"], d["gender"], str(d["count"]),
                      f"{avg_age:.1f}", f"{avg_pot:.1f}", f"{avg_win_pct:.0f}%")
    console.print(table)

    div_names = {d["key"] for d in config.WEIGHT_CLASSES}
    check("Every configured division has fighters", {d["weight_class"] for d in divisions} == div_names)

    # Skill should correlate with win rate: split into upper/lower half potential, compare win rates
    with_fights = [r for r in rows if (r["wins"] + r["losses"]) >= 5]
    with_fights.sort(key=lambda r: r["potential"])
    half = len(with_fights) // 2
    lower_half, upper_half = with_fights[:half], with_fights[half:]
    lower_wr = statistics.mean(r["wins"] / (r["wins"] + r["losses"]) for r in lower_half)
    upper_wr = statistics.mean(r["wins"] / (r["wins"] + r["losses"]) for r in upper_half)
    check(f"Higher-potential fighters win more often ({lower_wr:.2f} -> {upper_wr:.2f})", upper_wr > lower_wr)

    # Print one full profile
    sample = rows[len(rows) // 2]
    full = fighter_model.get_fighter(conn, sample["id"])
    console.rule(f"Sample profile: {full['name']} \"{full['nickname'] or ''}\"")
    console.print(f"  {full['weight_class']} ({full['gender']}) | Age {full['age']} | "
                   f"Record {full['record']} | Archetype {full['archetype']}")
    console.print(f"  Nationality: {full['nationality']} | Hometown: {full['hometown']}")
    console.print(f"  Potential {full['potential']} | Momentum {full['momentum']} | "
                   f"Prime {full['prime_start_age']}-{full['prime_end_age']} | Popularity {full['popularity']}")
    for group, attrs in fighter_model.ATTRIBUTE_GROUPS.items():
        if group == "career":
            continue
        line = ", ".join(f"{a}={full[a]}" for a in attrs)
        console.print(f"  [{group}] {line}")

    conn.close()
    cleanup(slot)


def test_importer():
    console.rule("CSV importer")
    slot = "_phase1_test_import"
    cleanup(slot)

    tmp_dir = ROOT / "data" / "_phase1_test_import_src"
    tmp_dir.mkdir(exist_ok=True)
    csv_path = tmp_dir / "fighters.csv"
    csv_path.write_text(
        "name,nickname,dob,nationality,hometown,weight_class,gender,"
        "punch_technique,punch_power,takedowns,chin,cardio,potential\n"
        "Jonas Kade,The Anvil,1994-03-11,United States,Reno Nevada,Lightweight,M,"
        "72,68,55,80,75,78\n"
        "Amira Solheim,,1997-07-22,Sweden,Gothenburg Sweden,Women's Bantamweight,F,"
        "60,55,70,65,,\n"  # sparse row: missing cardio + potential to test defaulting
    )

    conn = db.create_save(slot, "Phase 1 Test (Import)", universe_mode="imported")
    summary = import_fighters(conn, csv_path, None, db.PORTRAITS_DIR / slot, seed=7)
    check(f"Imported 2/2 rows (summary={summary})", summary["imported"] == 2 and summary["skipped"] == 0)

    rows = fighter_model.list_fighters(conn, status="Active", sort="name")
    check("Both imported fighters are queryable", len(rows) == 2)

    kade = next((r for r in rows if r["name"] == "Jonas Kade"), None)
    check("Explicit attribute value preserved (punch_technique=72)",
          kade is not None and kade["punch_technique"] == 72)

    solheim = next((r for r in rows if r["name"] == "Amira Solheim"), None)
    check("Missing attribute (cardio) was defaulted into valid range",
          solheim is not None and config.ATTR_MIN <= solheim["cardio"] <= config.ATTR_MAX)
    check("Missing potential was defaulted (>0)", solheim is not None and solheim["potential"] > 0)

    conn.close()
    cleanup(slot)
    shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    test_generated_universe()
    test_importer()
    console.rule("Result")
    if FAILURES:
        console.print(f"[red]{len(FAILURES)} check(s) failed:[/red]")
        for f in FAILURES:
            console.print(f"  - {f}")
        sys.exit(1)
    console.print("[green]All Phase 1 checks passed.[/green]")
