"""
Phase 2 verification: fight engine balance and structural sanity checks.

Verifies (via the "sim N times" debug mode) that favorites win at believable
rates that scale with the skill gap, that real upset potential survives even
for lopsided matchups, that a single fight's play-by-play/scorecards are
internally consistent, and that finishes happen at a plausible rate across a
spread of random matchups.
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rich.console import Console  # noqa: E402
from rich.table import Table  # noqa: E402

from engine.generator import generate_universe  # noqa: E402
from engine.fight.simulator import simulate_fight, simulate_many  # noqa: E402

console = Console()
FAILURES = []


def check(label, condition):
    status = "[green]PASS[/green]" if condition else "[red]FAIL[/red]"
    console.print(f"  {status}  {label}")
    if not condition:
        FAILURES.append(label)


def test_balance():
    console.rule("Balance: win rate vs. skill gap")
    fighters = generate_universe(seed=1)
    lw = sorted([f for f in fighters if f["weight_class"] == "Lightweight"], key=lambda f: f["potential"])
    for i, f in enumerate(lw):
        f["id"] = i

    matchups = [
        ("big gap", lw[17], lw[3]),      # clear favorite, not the artificial best-vs-worst extreme
        ("moderate gap", lw[15], lw[4]),
        ("small gap", lw[12], lw[8]),
        ("close", lw[9], lw[10]),
    ]

    table = Table(title="Sim 3000x per matchup")
    table.add_column("Matchup")
    table.add_column("Potential gap", justify="right")
    table.add_column("Favorite win%", justify="right")
    table.add_column("Draw%", justify="right")
    table.add_column("Avg fight length", justify="right")

    results = []
    for label, a, b in matchups:
        r = simulate_many(a, b, n=3000, seed=5)
        gap = a["potential"] - b["potential"]
        results.append((label, gap, r))
        table.add_row(label, str(gap), f"{r['win_pct_a']:.1f}%", f"{r['draw_pct']:.1f}%",
                       f"{r['avg_fight_seconds']:.0f}s")
    console.print(table)

    win_pcts = [r["win_pct_a"] for _, _, r in results]
    check(f"Win% decreases as the gap narrows ({win_pcts})",
          all(win_pcts[i] >= win_pcts[i + 1] - 5 for i in range(len(win_pcts) - 1)))

    big_result = results[0][2]
    check(f"Even a big favorite doesn't win literally every time ({big_result['win_pct_a']}%)",
          big_result["wins_b"] + big_result["draws"] >= 1)
    check("Big favorite still wins the clear majority (>=90%)", big_result["win_pct_a"] >= 90)

    close_result = results[-1][2]
    check(f"Closely matched fighters land near a toss-up (40-60%, got {close_result['win_pct_a']}%)",
          40 <= close_result["win_pct_a"] <= 60)

    moderate_result = results[1][2]
    check(f"Moderate favorite wins often but not overwhelmingly (65-97%, got {moderate_result['win_pct_a']}%)",
          65 <= moderate_result["win_pct_a"] <= 97)

    all_methods = {}
    for _, _, r in results:
        for m, c in r["methods_a"].items():
            all_methods[m] = all_methods.get(m, 0) + c
        for m, c in r["methods_b"].items():
            all_methods[m] = all_methods.get(m, 0) + c
    total = sum(all_methods.values())
    finish_rate = 1 - (all_methods.get("DEC", 0) + all_methods.get("DRAW", 0)) / total
    console.print(f"  Method breakdown across all sims: {all_methods}")
    check(f"Overall finish rate is plausible (15%-85%, got {finish_rate * 100:.1f}%)", 0.15 <= finish_rate <= 0.85)
    check("Both KOs and submissions occur", all_methods.get("KO", 0) > 0 and all_methods.get("SUB", 0) > 0)


def test_single_fight_structure():
    console.rule("Single-fight structural sanity")
    fighters = generate_universe(seed=2)
    ww = [f for f in fighters if f["weight_class"] == "Welterweight"]
    for i, f in enumerate(ww):
        f["id"] = i
    a, b = ww[3], ww[7]

    result = simulate_fight(a, b, rounds=3, seed=123)
    console.print(f"  {a['name']} vs {b['name']} -> {result['winner_name']} by "
                  f"{result['method_detail']} (R{result['round']} {result['time']})")

    check("Play-by-play has at least one round", len(result["play_by_play"]) >= 1)
    check("Every round has commentary lines", all(len(rnd) > 0 for rnd in result["play_by_play"]))
    check("Method is one of KO/TKO/SUB/DEC/DRAW", result["method"] in ("KO", "TKO", "SUB", "DEC", "DRAW"))

    for key in ("fighter_a", "fighter_b"):
        stats = result[key]["stats"]
        check(f"{key}: strikes landed <= attempted", stats["sig_strikes_landed"] <= stats["sig_strikes_attempted"])
        check(f"{key}: takedowns landed <= attempted", stats["takedowns_landed"] <= stats["takedowns_attempted"])
        check(f"{key}: no negative stats", all(v >= 0 for v in stats.values()))

    for i, sc in enumerate(result["scorecards"]):
        for judge_a, judge_b in sc["judges"]:
            valid = (judge_a, judge_b) in ((10, 9), (9, 10), (10, 8), (8, 10), (10, 10))
            check(f"Round {i + 1} judge score is a valid MMA scorecard tuple ({judge_a}-{judge_b})", valid)

    if result["method"] == "DEC":
        check("Decision has 3 judges' worth of scorecards for all scheduled rounds",
              len(result["scorecards"]) == result["rounds_scheduled"])


def test_finish_variety():
    console.rule("Finish variety across random matchups")
    fighters = generate_universe(seed=3)
    mw = [f for f in fighters if f["weight_class"] == "Middleweight"]
    for i, f in enumerate(mw):
        f["id"] = i

    methods = {}
    n = 60
    for i in range(n):
        a, b = mw[i % len(mw)], mw[(i + 7) % len(mw)]
        if a is b:
            continue
        result = simulate_fight(a, b, rounds=3, seed=1000 + i)
        methods[result["method"]] = methods.get(result["method"], 0) + 1

    console.print(f"  {n} varied fights -> {methods}")
    check("At least 3 distinct outcome methods appear", len(methods) >= 3)
    check("No single method is 100% of outcomes", max(methods.values()) < sum(methods.values()))


def test_performance():
    console.rule("Performance")
    fighters = generate_universe(seed=4)
    hw = [f for f in fighters if f["weight_class"] == "Heavyweight"]
    for i, f in enumerate(hw):
        f["id"] = i
    start = time.time()
    simulate_many(hw[0], hw[1], n=1000, seed=1)
    elapsed = time.time() - start
    console.print(f"  1000 sims took {elapsed:.2f}s")
    check("1000 sims complete in under 10 seconds", elapsed < 10)


if __name__ == "__main__":
    test_balance()
    test_single_fight_structure()
    test_finish_variety()
    test_performance()
    console.rule("Result")
    if FAILURES:
        console.print(f"[red]{len(FAILURES)} check(s) failed:[/red]")
        for f in FAILURES:
            console.print(f"  - {f}")
        sys.exit(1)
    console.print("[green]All Phase 2 checks passed.[/green]")
