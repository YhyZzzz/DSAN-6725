"""Specification for the cleaning stage YOU will build (with your AI assistant).

These tests fail in the starter repo because src/pipeline/clean.py does not
exist. They define the contract:

    clean_trips(lf: pl.LazyFrame, year: int) -> pl.LazyFrame

Cleaning rules (each dirty fixture row violates exactly one):
    1. fare_amount, tip_amount, and total_amount must be non-negative
    2. trip_distance must be > 0 and < 200 miles
    3. dropoff must be strictly after pickup
    4. trip duration must be at most 24 hours
    5. pickup year must equal the given data year
    6. passenger_count must be between 1 and 6 (nulls dropped)

The function must stay lazy: LazyFrame in, LazyFrame out, no .collect() inside.
"""

from datetime import timedelta

import polars as pl

# The import below fails until you create src/pipeline/clean.py -- that is the lab.
from pipeline.clean import clean_trips

from .conftest import N_CLEAN_ROWS

DATA_YEAR = 2025


class TestCleanTrips:
    """Tests for clean_trips."""

    def test_stays_lazy(self, trips: pl.LazyFrame):
        """Cleaning must return a LazyFrame, not a collected DataFrame."""
        result = clean_trips(trips, year=DATA_YEAR)

        assert isinstance(result, pl.LazyFrame)

    def test_drops_all_dirty_rows_and_keeps_all_clean_rows(self, trips: pl.LazyFrame):
        """Exactly the 10 dirty fixture rows are removed."""
        n = clean_trips(trips, year=DATA_YEAR).select(pl.len()).collect().item()

        assert n == N_CLEAN_ROWS

    def test_no_negative_money_amounts_remain(self, trips: pl.LazyFrame):
        """All money columns are non-negative after cleaning."""
        df = clean_trips(trips, year=DATA_YEAR).collect()

        for column in ("fare_amount", "tip_amount", "total_amount"):
            assert (df[column] >= 0).all(), f"negative values remain in {column}"

    def test_distances_within_bounds(self, trips: pl.LazyFrame):
        """Trip distances are positive and below 200 miles."""
        df = clean_trips(trips, year=DATA_YEAR).collect()

        assert (df["trip_distance"] > 0).all()
        assert (df["trip_distance"] < 200).all()

    def test_dropoff_after_pickup_within_24_hours(self, trips: pl.LazyFrame):
        """Durations are positive and at most 24 hours."""
        df = clean_trips(trips, year=DATA_YEAR).with_columns(
            duration=(pl.col("tpep_dropoff_datetime") - pl.col("tpep_pickup_datetime"))
        ).collect()

        assert (df["duration"] > timedelta(seconds=0)).all()
        assert (df["duration"] <= timedelta(hours=24)).all()

    def test_pickups_within_data_year(self, trips: pl.LazyFrame):
        """Every remaining pickup is in the configured data year."""
        df = clean_trips(trips, year=DATA_YEAR).collect()

        assert (df["tpep_pickup_datetime"].dt.year() == DATA_YEAR).all()

    def test_passenger_count_between_1_and_6(self, trips: pl.LazyFrame):
        """Passenger counts are 1-6 with no nulls."""
        df = clean_trips(trips, year=DATA_YEAR).collect()

        assert df["passenger_count"].null_count() == 0
        assert (df["passenger_count"] >= 1).all()
        assert (df["passenger_count"] <= 6).all()
