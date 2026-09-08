"""Shared fixtures: lazy frames over the committed sample data."""

from pathlib import Path

import polars as pl
import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "data" / "fixtures"

# The fixture contains exactly these counts; see scripts/make_fixture.py.
N_CLEAN_ROWS = 5000
N_DIRTY_ROWS = 10


@pytest.fixture
def trips() -> pl.LazyFrame:
    """LazyFrame over the synthetic trips fixture (clean + dirty rows)."""
    return pl.scan_parquet(FIXTURE_DIR / "sample.parquet")


@pytest.fixture
def zones() -> pl.LazyFrame:
    """LazyFrame over the fixture zone lookup table."""
    return pl.scan_csv(FIXTURE_DIR / "taxi_zone_lookup.csv")
