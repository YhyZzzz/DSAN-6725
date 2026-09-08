"""Transform stage: zone enrichment and aggregations. REFERENCE SOLUTION - not shipped."""

import polars as pl


def join_zones(
    trips: pl.LazyFrame,
    zones: pl.LazyFrame,
) -> pl.LazyFrame:
    """Left-join pickup borough and zone names onto trips."""
    lookup = zones.select(
        pl.col("LocationID"),
        pl.col("Borough").alias("pickup_borough"),
        pl.col("Zone").alias("pickup_zone"),
    )
    return trips.join(
        lookup,
        left_on="PULocationID",
        right_on="LocationID",
        how="left",
        coalesce=True,
    )


def revenue_by_borough(
    trips: pl.LazyFrame,
) -> pl.LazyFrame:
    """Total revenue and trip count per pickup borough, highest revenue first."""
    return (
        trips.group_by("pickup_borough")
        .agg(
            pl.col("total_amount").sum().alias("total_revenue"),
            pl.len().alias("trip_count"),
        )
        .sort("total_revenue", descending=True)
    )


def tip_pct_by_hour(
    trips: pl.LazyFrame,
) -> pl.LazyFrame:
    """Average tip percentage (tip/fare * 100) per pickup hour, ascending."""
    return (
        trips.filter(pl.col("fare_amount") != 0)
        .with_columns(
            pl.col("tpep_pickup_datetime").dt.hour().alias("hour"),
            (pl.col("tip_amount") / pl.col("fare_amount") * 100).alias("tip_pct"),
        )
        .group_by("hour")
        .agg(pl.col("tip_pct").mean().alias("avg_tip_pct"))
        .sort("hour")
    )
