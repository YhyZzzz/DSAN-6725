"""Data ingestion: lazily scan monthly trip parquet files.

This module is fully implemented and serves as the reference for how the rest
of the pipeline should use polars: lazy scans, no eager loads of the full
dataset, and explicit schema expectations.
"""

import logging
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

# Core columns the pipeline depends on; the raw files contain more.
EXPECTED_COLUMNS: list[str] = [
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "PULocationID",
    "DOLocationID",
    "fare_amount",
    "tip_amount",
    "total_amount",
]


def _validate_columns(
    lf: pl.LazyFrame,
    source: str,
) -> None:
    """Raise ValueError if any expected column is missing from the schema."""
    schema_columns = set(lf.collect_schema().names())
    missing = [c for c in EXPECTED_COLUMNS if c not in schema_columns]
    if missing:
        raise ValueError(
            f"Missing expected columns {missing} in {source}. "
            "Check that you downloaded Yellow Taxi (not Green/FHV) data. "
            "Data dictionary: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page"
        )


def scan_trips(
    raw_dir: Path,
) -> pl.LazyFrame:
    """Lazily scan all monthly trip parquet files in raw_dir.

    Uses a glob so one month or twelve months are handled identically, and
    returns a LazyFrame so no data is read until the query is collected.

    Args:
        raw_dir: Directory containing yellow_tripdata_*.parquet files.

    Returns:
        LazyFrame over all monthly files, selected to EXPECTED_COLUMNS.

    Raises:
        FileNotFoundError: If no matching parquet files exist in raw_dir.
        ValueError: If expected columns are missing.
    """
    pattern = raw_dir / "yellow_tripdata_*.parquet"
    matches = sorted(raw_dir.glob("yellow_tripdata_*.parquet"))
    if not matches:
        raise FileNotFoundError(
            f"No trip files matching {pattern}. "
            "Run: uv run python scripts/download_data.py"
        )

    logger.info(f"Scanning {len(matches)} monthly file(s) from {raw_dir}")
    lf = pl.scan_parquet(pattern)
    _validate_columns(lf, str(pattern))
    return lf.select(EXPECTED_COLUMNS)


def scan_zone_lookup(
    zone_lookup_path: Path,
) -> pl.LazyFrame:
    """Lazily scan the taxi zone lookup table.

    Args:
        zone_lookup_path: Path to taxi_zone_lookup.csv.

    Returns:
        LazyFrame with columns LocationID, Borough, Zone, service_zone.

    Raises:
        FileNotFoundError: If the lookup file does not exist.
    """
    if not zone_lookup_path.exists():
        raise FileNotFoundError(
            f"Zone lookup not found at {zone_lookup_path}. "
            "Run: uv run python scripts/download_data.py"
        )
    return pl.scan_csv(zone_lookup_path)
