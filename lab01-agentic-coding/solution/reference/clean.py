"""Cleaning stage: filter invalid trip rows. REFERENCE SOLUTION - not shipped."""

import polars as pl


def clean_trips(
    lf: pl.LazyFrame,
    year: int,
) -> pl.LazyFrame:
    """Drop invalid trip rows; stays lazy.

    Args:
        lf: Raw trips LazyFrame.
        year: Expected data year for pickups.

    Returns:
        LazyFrame with invalid rows removed.
    """
    duration = pl.col("tpep_dropoff_datetime") - pl.col("tpep_pickup_datetime")
    return lf.filter(
        (pl.col("fare_amount") >= 0)
        & (pl.col("tip_amount") >= 0)
        & (pl.col("total_amount") >= 0)
        & (pl.col("trip_distance") > 0)
        & (pl.col("trip_distance") < 200)
        & (duration > pl.duration(seconds=0))
        & (duration <= pl.duration(hours=24))
        & (pl.col("tpep_pickup_datetime").dt.year() == year)
        & (pl.col("passenger_count").is_between(1, 6))
    )
