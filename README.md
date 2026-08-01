# MMA Universe Simulator

A deep, text-based MMA management and universe simulator. Every fight result is
explainable by the numbers; the world keeps moving whether or not you book it.

## Quickstart

```bash
git clone <your-repo-url>
cd NCAAM
git checkout claude/mma-universe-simulator-gttyte

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python run.py                      # opens http://127.0.0.1:8000 in your browser
```

Needs Python 3.11+. Stop the server with Ctrl+C; your save is a file on disk, so
nothing is lost.

## Starting a universe

On the landing screen, name your universe and pick a mode:

- **Real universe** — imports every division file in `data/real/`. Right now that's
  heavyweight: 42 UFC fighters with the real champion and 1–15 rankings seeded, plus
  53 fighters outside the UFC (PFL, ONE, KSW, ACA, RIZIN, regional) who are all
  signable.
- **Generate** — ~200 fictional fighters across 11 divisions, if you want a sandbox.
- **Import** — your own `fighters.csv`/`.json` from `data/import/`.

## The loop

1. **Rankings** — see the division as it stands. Champion up top, 1–15 below.
2. **Events** — create an event (name, date, venue), then book bouts onto the main
   card or prelims. Flag title fights and #1 contender fights. Sim bout-by-bout or
   the whole card at once.
3. Read the **play-by-play**, scorecards, and stats for any completed fight.
4. **Calendar** — advance a week, a month, or a year. Fighters age and develop on
   their birthdays, get injured, retire; non-UFC fighters take fights off-screen so
   their records keep moving.
5. **Free Agents** — the top 20 available fighters by the game's scouting judgment,
   expandable to the full pool. Sign anyone. Cut anyone from their profile page.
6. **Year in Review** — title changes, breakout prospects, retirements, and the
   yearly awards.

**Fight Tester** is a sandbox: pick any two fighters (including non-UFC ones), sim a
single fight for the play-by-play, or run it 1000× to see the win-rate split.

## Tuning it yourself

Everything balance-related lives in `config.py`, commented and grouped: finish rates,
upset variance, aging curves, injury odds, retirement pressure, ranking points,
free-agent scoring. Change a number, restart, done.

Any fighter's attributes are editable in-game — profile page → **Edit Fighter**.

## Adding divisions

Drop a CSV into `data/real/` and it gets imported on the next "Real universe" save.
Copy the header from `data/real/heavyweight.csv`. Key columns:

- `rank` — `C` for champion, `1`–`15` for ranked contenders, blank for unranked
- `skill_hint` — optional 1–99 override for the skill baseline; used for elite
  non-UFC fighters who carry no UFC rank (Ngannou, Malykhin, etc.)
- `promotion` — `UFC`, `Free Agent`, or any promotion name
- Finish breakdowns must sum to the record, or the import fails loudly

Duplicate names across files are skipped (first occurrence wins), so overlapping
source lists are safe.

## Layout

```
engine/          simulation: fight engine, booking, rankings, aging, free agency
  fight/         the round-by-round fight engine
models/          schema + data access
web/             FastAPI backend and the single-page UI
data/real/       real-roster division files
data/saves/      your save files (one SQLite DB each)
scripts/         per-phase test suites
config.py        all tunable constants
```

## Tests

```bash
for p in 1 2 3 4 5 6; do python scripts/test_phase$p.py; done
```

Each phase prints its checks and exits non-zero on failure.
