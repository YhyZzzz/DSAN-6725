"""Specification for the transform stage YOU will build (with your AI assistant).

These tests fail in the starter repo because src/pipeline/transform.py does not
exist. They define three functions, all LazyFrame -> LazyFrame:

    join_zones(trips, zones)      -> adds pickup_borough and pickup_zone columns
    revenue_by_borough(trips)     -> total_revenue and trip count per pickup_borough,
                                     sorted by total_revenue descending
    tip_pct_by_hour(trips)        -> average tip percentage (0-100, tip/fare) per
                                     pickup hour of day, sorted by hour ascending;
                                     rows with fare_amount == 0 are excluded
"""

from datetime import datetime

import polars as pl

# These imports fail until you create src/pipeline/transform.py -- that is the lab.
from pipeline.transform import join_zones, revenue_by_borough, tip_pct_by_hour


class TestJoinZones:
    """Tests for join_zones."""

    def test_stays_lazy_and_adds_columns(self, trips: pl.LazyFrame, zones: pl.LazyFrame):
        """Join returns a LazyFrame with pickup borough and zone columns added."""
        result = join_zones(trips, zones)

        assert isinstance(result, pl.LazyFrame)
        names = result.collect_schema().names()
        assert "pickup_borough" in names
        assert "pickup_zone" in names

    def test_preserves_row_count(self, trips: pl.LazyFrame, zones: pl.LazyFrame):
        """A lookup join must not add or drop trip rows."""
        before = trips.select(pl.len()).collect().item()

        after = join_zones(trips, zones).select(pl.len()).collect().item()

        assert after == before

    def test_known_location_maps_to_correct_borough(self, zones: pl.LazyFrame):
        """LocationID 132 (JFK Airport) maps to Queens."""
        one_trip = pl.LazyFrame({"PULocationID": [132]})

        df = join_zones(one_trip, zones).collect()

        assert df["pickup_borough"].item() == "Queens"
        assert df["pickup_zone"].item() == "JFK Airport"


class TestRevenueByBorough:
    """Tests for revenue_by_borough."""

    def test_aggregates_and_sorts_descending(self, zones: pl.LazyFrame):
        """Revenue is summed per borough and sorted high to low."""
        trips = pl.LazyFrame(
            {
                "PULocationID": [132, 132, 79, 17],
                "total_amount": [70.0, 30.0, 20.0, 10.0],
            }
        )

        df = revenue_by_borough(join_zones(trips, zones)).collect()

        assert df["pickup_borough"].to_list() == ["Queens", "Manhattan", "Brooklyn"]
        assert df["total_revenue"].to_list() == [100.0, 20.0, 10.0]

    def test_includes_trip_count(self, trips: pl.LazyFrame, zones: pl.LazyFrame):
        """Each borough row includes how many trips produced the revenue."""
        df = revenue_by_borough(join_zones(trips, zones)).collect()

        assert "trip_count" in df.columns
        assert (df["trip_count"] > 0).all()


class TestTipPctByHour:
    """Tests for tip_pct_by_hour."""

    def test_computes_average_tip_percentage_per_hour(self):
        """Two 9am trips with 20% and 0% tips average to 10%."""
        trips = pl.LazyFrame(
            {
                "tpep_pickup_datetime": [
                    datetime(2025, 3, 1, 9, 15, 0),
                    datetime(2025, 3, 1, 9, 45, 0),
                ],
                "fare_amount": [10.0, 10.0],
                "tip_amount": [2.0, 0.0],
            }
        )

        df = tip_pct_by_hour(trips).collect()

        assert df.height == 1
        assert df["hour"].item() == 9
        assert abs(df["avg_tip_pct"].item() - 10.0) < 1e-9

    def test_hours_sorted_ascending_and_bounded(self, trips: pl.LazyFrame):
        """Result has at most 24 rows, sorted by hour, percentages in range."""
        df = tip_pct_by_hour(trips).collect()

        assert df.height <= 24
        assert df["hour"].to_list() == sorted(df["hour"].to_list())
        assert (df["avg_tip_pct"] >= 0).all()

    def test_zero_fare_rows_excluded(self):
        """Zero-fare rows must not produce division errors or infinities."""
        trips = pl.LazyFrame(
            {
                "tpep_pickup_datetime": [datetime(2025, 3, 1, 9, 0, 0)],
                "fare_amount": [0.0],
                "tip_amount": [5.0],
            }
        )

        df = tip_pct_by_hour(trips).collect()

        assert df.height == 0
