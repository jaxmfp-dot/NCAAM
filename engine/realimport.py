"""Import of real-roster division files (data/real/*.csv) with attribute
synthesis calibrated by ranking standing.

Unlike the generic importer (which defaults unknown attributes around league
average), this treats a fighter's real-world rank as evidence of their current
ability: the champion synthesizes near the top of the scale, ranked contenders
in tiers below, unranked fighters from their record. Archetype offsets shape
the profile (a Brawler gets power/chin, a BJJ Specialist gets the ground game)
and career KO losses dent chin/toughness, so the numbers read like scouting
reports rather than random rolls.

CSV format (one file per division): identity columns + promotion, rank
('C' = champion, 1-15 = seeded contender rank, blank = unranked), full record
with finish breakdown, archetype, popularity, height/reach/stance.
"""

import csv
import random
from datetime import date, datetime
from pathlib import Path

import config
from engine import titles
from engine.generator import PHYSICAL_PEAK_ATTRS, STABLE_ATTRS, TECHNIQUE_ATTRS
from models.fighter import insert_fighter, set_rank_seed

# current-skill baseline by standing
TIER_CHAMPION = 84.0
TIER_RANK_1_5 = 79.0
TIER_RANK_6_10 = 75.0
TIER_RANK_11_15 = 71.0
TIER_UNRANKED_BASE = 56.0
TIER_UNRANKED_WIN_SCALE = 0.45     # + per career win, capped
TIER_UNRANKED_WIN_CAP = 10.0

KO_LOSS_CHIN_DENT = 2.0            # imported chin/toughness reduced per career KO loss
KO_LOSS_TOUGHNESS_DENT = 1.0


def _clamp(v: float) -> int:
    return max(config.ATTR_MIN, min(config.ATTR_MAX, round(v)))


def _tier_for(row: dict) -> float:
    """Current-skill baseline: an explicit skill_hint wins (used for elite non-UFC
    fighters who carry no UFC rank), then UFC ranking tier, then record size."""
    hint = (row.get("skill_hint") or "").strip()
    if hint:
        return float(hint)
    rank = (row.get("rank") or "").strip()
    if rank == "C":
        return TIER_CHAMPION
    if rank:
        r = int(rank)
        if r <= 5:
            return TIER_RANK_1_5
        if r <= 10:
            return TIER_RANK_6_10
        return TIER_RANK_11_15
    return TIER_UNRANKED_BASE + min(TIER_UNRANKED_WIN_CAP, int(row["wins"]) * TIER_UNRANKED_WIN_SCALE)


def _synthesize_fighter(row: dict, as_of: date, rng: random.Random) -> dict:
    rank = (row.get("rank") or "").strip()
    wins, losses = int(row["wins"]), int(row["losses"])
    losses_ko = int(row["losses_ko"])
    base = _tier_for(row)

    age = (as_of - datetime.strptime(row["dob"], "%Y-%m-%d").date()).days // 365
    archetype = (row.get("archetype") or "Well-Rounded").strip()
    offsets = config.ARCHETYPES.get(archetype, {})

    # physical baseline sits near skill but fades for fighters deep past athletic prime
    phys_base = base + rng.gauss(0, 4) - max(0, age - 35) * 1.2

    attrs = {}
    for attr in TECHNIQUE_ATTRS:
        attrs[attr] = _clamp(base + offsets.get(attr, 0) + rng.gauss(0, 4))
    for attr in PHYSICAL_PEAK_ATTRS:
        attrs[attr] = _clamp(phys_base + offsets.get(attr, 0) + rng.gauss(0, 4))
    for attr in STABLE_ATTRS:
        attrs[attr] = _clamp(base + offsets.get(attr, 0) + rng.gauss(0, 5))

    # accumulated head trauma shows up in the numbers
    attrs["chin"] = _clamp(attrs["chin"] - losses_ko * KO_LOSS_CHIN_DENT)
    attrs["toughness"] = _clamp(attrs["toughness"] - losses_ko * KO_LOSS_TOUGHNESS_DENT)

    # experience sharpens fight IQ regardless of tier
    attrs["fight_iq"] = _clamp(attrs["fight_iq"] + min(8, (wins + losses) * 0.2))
    attrs["work_ethic"] = _clamp(rng.gauss(config.WORK_ETHIC_MEAN, 12))
    attrs["injury_proneness"] = _clamp(rng.gauss(
        config.INJURY_PRONENESS_BASE + max(0, age - 32) * config.INJURY_PRONENESS_AGE_FACTOR, 12))

    prime_start = rng.randint(config.PRIME_START_MIN, config.PRIME_START_MAX)
    prime_end = prime_start + rng.randint(config.PRIME_LENGTH_MIN, config.PRIME_LENGTH_MAX)

    # potential: young fighters carry upside above their current tier; veterans are at/near theirs
    upside = max(0.0, (29 - age)) * 1.2 + rng.uniform(0, 4)
    potential = _clamp(base + upside)

    fighter = {
        "name": row["name"].strip(),
        "nickname": (row.get("nickname") or "").strip() or None,
        "dob": row["dob"],
        "nationality": (row.get("nationality") or "").strip() or None,
        "hometown": None,
        "weight_class": row["weight_class"],
        "gender": row["gender"],
        "height_in": float(row["height_in"]) if row.get("height_in") else None,
        "reach_in": float(row["reach_in"]) if row.get("reach_in") else None,
        "stance": (row.get("stance") or "Orthodox").strip(),
        "portrait_filename": None,
        "wins": wins, "losses": losses,
        "draws": int(row.get("draws") or 0), "no_contests": int(row.get("no_contests") or 0),
        "wins_ko": int(row["wins_ko"]), "wins_sub": int(row["wins_sub"]), "wins_dec": int(row["wins_dec"]),
        "losses_ko": losses_ko, "losses_sub": int(row["losses_sub"]), "losses_dec": int(row["losses_dec"]),
        "potential": potential,
        "physical_gift": _clamp(phys_base + rng.gauss(0, 3)),
        "momentum": rng.randint(2, 10) if rank else 0,
        "prime_start_age": prime_start,
        "prime_end_age": prime_end,
        "popularity": _clamp(float(row.get("popularity") or config.POPULARITY_BASE)),
        "contract_status": "Signed",
        "promotion": (row.get("promotion") or "UFC").strip(),
        "status": "Active",
        "archetype": archetype,
        **attrs,
    }
    return fighter


def import_division_csv(conn, csv_path: Path, start_date: str, seed: int | None = None) -> dict:
    rng = random.Random(seed)
    as_of = datetime.strptime(start_date, "%Y-%m-%d").date()

    imported, champions, seeded, skipped = 0, [], 0, []
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            record_ok = (int(row["wins_ko"]) + int(row["wins_sub"]) + int(row["wins_dec"]) == int(row["wins"])
                          and int(row["losses_ko"]) + int(row["losses_sub"]) + int(row["losses_dec"]) == int(row["losses"]))
            if not record_ok:
                raise ValueError(f"{row['name']}: finish breakdown doesn't sum to the record")

            # source lists overlap (a fighter can appear in both a UFC and a non-UFC
            # file, or twice within one) -- first occurrence wins
            exists = conn.execute(
                "SELECT id FROM fighters WHERE name = ? AND weight_class = ? AND gender = ?",
                (row["name"].strip(), row["weight_class"], row["gender"]),
            ).fetchone()
            if exists:
                skipped.append(row["name"].strip())
                continue

            fighter = _synthesize_fighter(row, as_of, rng)
            fighter_id = insert_fighter(conn, fighter)

            rank = (row.get("rank") or "").strip()
            if rank == "C":
                title_id = titles.ensure_title(conn, fighter["weight_class"], fighter["gender"])
                conn.execute("UPDATE titles SET champion_id = ?, won_date = ?, defenses = 0 WHERE id = ?",
                             (fighter_id, start_date, title_id))
                champions.append(fighter["name"])
            elif rank:
                set_rank_seed(conn, fighter_id, int(rank), start_date)
                seeded += 1
            imported += 1

    conn.commit()
    return {"file": csv_path.name, "imported": imported, "champions": champions,
            "rank_seeded": seeded, "skipped_duplicates": skipped}


def import_all_real(conn, start_date: str, seed: int | None = None) -> list[dict]:
    real_dir = Path(__file__).resolve().parent.parent / "data" / "real"
    summaries = []
    rng = random.Random(seed)
    for csv_path in sorted(real_dir.glob("*.csv")):
        summaries.append(import_division_csv(conn, csv_path, start_date, seed=rng.randrange(2**32)))
    return summaries
