"""Yearly prospect generation: a handful of young, varied-potential fighters
per division join the roster each year to keep divisions replenished."""

import random
from datetime import datetime

import config
from engine.generator import generate_fighter
from models.fighter import insert_fighter


def generate_yearly_prospects(conn, as_of_date: str, seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    as_of = datetime.strptime(as_of_date, "%Y-%m-%d").date()

    created = []
    for division in config.WEIGHT_CLASSES:
        count = (config.PROSPECTS_PER_MENS_DIVISION_PER_YEAR if division["gender"] == "M"
                 else config.PROSPECTS_PER_WOMENS_DIVISION_PER_YEAR)
        for _ in range(count):
            fighter = generate_fighter(
                rng, division["key"], division["gender"], as_of,
                age_min=config.PROSPECT_AGE_MIN, age_max=config.PROSPECT_AGE_MAX, age_mode=config.PROSPECT_AGE_MODE,
            )
            fighter_id = insert_fighter(conn, fighter)
            created.append({"id": fighter_id, "name": fighter["name"], "weight_class": division["key"],
                             "gender": division["gender"], "potential": fighter["potential"]})
    conn.commit()
    return created
