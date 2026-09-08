"""Generate the committed test fixture: a small synthetic taxi dataset.

The fixture mimics the Yellow Taxi schema and deliberately injects every kind
of dirty row the cleaning stage must handle. Tests and CI run against this
fixture so they are fast and never require downloading real data.

This script is committed for provenance; students do not need to run it.

Example usage:
    uv run python scripts/make_fixture.py
"""

import logging
import random
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,p%(process)s,{%(filename)s:%(lineno)d},%(levelname)s,%(message)s",
)
logger = logging.getLogger(__name__)

FIXTURE_DIR: Path = Path("data/fixtures")
N_CLEAN_ROWS: int = 5000
DATA_YEAR: int = 2025
RANDOM_SEED: int = 6725

# LocationID -> (Borough, Zone); a small, real subset of the TLC lookup table.
ZONES: dict[int, tuple[str, str]] = {
    4: ("Manhattan", "Alphabet City"),
    13: ("Manhattan", "Battery Park City"),
    41: ("Manhattan", "Central Harlem"),
    43: ("Manhattan", "Central Park"),
    79: ("Manhattan", "East Village"),
    132: ("Queens", "JFK Airport"),
    138: ("Queens", "LaGuardia Airport"),
    7: ("Queens", "Astoria"),
    17: ("Brooklyn", "Bedford"),
    25: ("Brooklyn", "Boerum Hill"),
    18: ("Bronx", "Bedford Park"),
    31: ("Bronx", "Bronx Park"),
    5: ("Staten Island", "Arden Heights"),
    1: ("EWR", "Newark Airport"),
}


def _random_clean_row(
    rng: random.Random,
) -> dict:
    """Generate one valid trip row within the data year."""
    pickup = datetime(DATA_YEAR, rng.randint(1, 12), rng.randint(1, 28), rng.randint(0, 23),
                      rng.randint(0, 59), rng.randint(0, 59))
    duration_minutes = rng.uniform(2, 90)
    distance = max(0.3, rng.gauss(3.5, 2.5))
    fare = 3.0 + 2.5 * distance + rng.uniform(0, 5)
    tip = fare * rng.choice([0.0, 0.15, 0.2, 0.25, rng.uniform(0, 0.3)])
    return {
        "tpep_pickup_datetime": pickup,
        "tpep_dropoff_datetime": pickup + timedelta(minutes=duration_minutes),
        "passenger_count": rng.randint(1, 6),
        "trip_distance": round(distance, 2),
        "PULocationID": rng.choice(list(ZONES)),
        "DOLocationID": rng.choice(list(ZONES)),
        "fare_amount": round(fare, 2),
        "tip_amount": round(tip, 2),
        "total_amount": round(fare + tip, 2),
    }


def _dirty_rows() -> list[dict]:
    """Hand-crafted rows, each violating exactly one cleaning rule."""
    base = {
        "tpep_pickup_datetime": datetime(DATA_YEAR, 6, 15, 12, 0, 0),
        "tpep_dropoff_datetime": datetime(DATA_YEAR, 6, 15, 12, 30, 0),
        "passenger_count": 1,
        "trip_distance": 2.5,
        "PULocationID": 79,
        "DOLocationID": 132,
        "fare_amount": 18.0,
        "tip_amount": 3.0,
        "total_amount": 21.0,
    }
    violations: list[dict] = [
        {"fare_amount": -18.0, "total_amount": -21.0},          # negative fare
        {"tip_amount": -3.0},                                    # negative tip
        {"trip_distance": 0.0},                                  # zero distance
        {"trip_distance": 250.0},                                # absurd distance
        {"tpep_dropoff_datetime": datetime(DATA_YEAR, 6, 15, 11, 0, 0)},  # ends before start
        {"tpep_dropoff_datetime": datetime(DATA_YEAR, 6, 16, 12, 1, 0)},  # > 24h duration
        {"tpep_pickup_datetime": datetime(2001, 1, 1, 0, 0, 0),
         "tpep_dropoff_datetime": datetime(2001, 1, 1, 0, 30, 0)},        # wrong year (past)
        {"tpep_pickup_datetime": datetime(2098, 1, 1, 0, 0, 0),
         "tpep_dropoff_datetime": datetime(2098, 1, 1, 0, 30, 0)},        # wrong year (future)
        {"passenger_count": 0},                                  # no passengers
        {"passenger_count": None},                               # null passengers
    ]
    rows = []
    for violation in violations:
        row = dict(base)
        row.update(violation)
        rows.append(row)
    return rows


def main() -> None:
    """Write sample.parquet and taxi_zone_lookup.csv fixtures."""
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    # Deterministic fixture; not used for security purposes - nosec B311
    rng = random.Random(RANDOM_SEED)  # nosec B311

    clean = [_random_clean_row(rng) for _ in range(N_CLEAN_ROWS)]
    dirty = _dirty_rows()
    df = pl.DataFrame(clean + dirty).with_columns(
        pl.col("passenger_count").cast(pl.Int64),
        pl.col("PULocationID").cast(pl.Int32),
        pl.col("DOLocationID").cast(pl.Int32),
    )
    trips_path = FIXTURE_DIR / "sample.parquet"
    df.write_parquet(trips_path)
    logger.info(f"Wrote {df.height} rows ({len(dirty)} dirty) to {trips_path}")

    zones = pl.DataFrame(
        {
            "LocationID": list(ZONES.keys()),
            "Borough": [b for b, _ in ZONES.values()],
            "Zone": [z for _, z in ZONES.values()],
            "service_zone": ["EWR" if b == "EWR" else "Boro Zone" for b, _ in ZONES.values()],
        }
    ).sort("LocationID")
    zones_path = FIXTURE_DIR / "taxi_zone_lookup.csv"
    zones.write_csv(zones_path)
    logger.info(f"Wrote {zones.height} zones to {zones_path}")


if __name__ == "__main__":
    main()
