"""Pipeline entry point: ingest -> clean -> transform -> report.

Run with:
    uv run python -m pipeline.main
    uv run python -m pipeline.main --raw-dir data/raw --debug

NOTE: This module imports pipeline.clean and pipeline.transform, which do not
exist in the starter repo. Creating them (driven by your AI assistant, with the
tests as the specification) is the core of the lab. Until then, this entry
point exits with an explanatory error.
"""

import argparse
import logging
import time
from pathlib import Path

import polars as pl

from .config import PipelineConfig
from .ingest import scan_trips, scan_zone_lookup
from .report import write_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,p%(process)s,{%(filename)s:%(lineno)d},%(levelname)s,%(message)s",
)
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="NYC Yellow Taxi data pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
    # Run on whatever months are in data/raw
    uv run python -m pipeline.main

    # Verbose logging
    uv run python -m pipeline.main --debug
""",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=None,
        help="Directory with monthly parquet files (default: data/raw)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def main() -> None:
    """Orchestrate the pipeline; business logic lives in the stage modules."""
    args = _parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    config = PipelineConfig()
    if args.raw_dir is not None:
        config = PipelineConfig(
            raw_dir=args.raw_dir,
            zone_lookup_path=args.raw_dir / "taxi_zone_lookup.csv",
        )
    logger.info(f"Configuration: {config.model_dump()}")

    try:
        from .clean import clean_trips
        from .transform import join_zones, revenue_by_borough, tip_pct_by_hour
    except ImportError as e:
        raise SystemExit(
            "pipeline.clean / pipeline.transform do not exist yet -- building them "
            f"is the lab. See README.md, exercise 4. ({e})"
        ) from e

    start_time = time.time()

    trips = scan_trips(config.raw_dir)
    zones = scan_zone_lookup(config.zone_lookup_path)

    cleaned = clean_trips(trips, year=config.year)
    enriched = join_zones(cleaned, zones)

    revenue = revenue_by_borough(enriched).collect(engine="streaming")
    tips = tip_pct_by_hour(enriched).collect(engine="streaming")

    raw_rows = trips.select(pl.len()).collect(engine="streaming").item()
    clean_rows = cleaned.select(pl.len()).collect(engine="streaming").item()

    elapsed_time = time.time() - start_time
    write_report(
        config=config,
        raw_rows=raw_rows,
        clean_rows=clean_rows,
        revenue=revenue,
        tips=tips,
        elapsed_seconds=elapsed_time,
    )

    minutes = int(elapsed_time // 60)
    seconds = elapsed_time % 60
    if minutes > 0:
        logger.info(f"Pipeline completed in {minutes} minutes and {seconds:.1f} seconds")
    else:
        logger.info(f"Pipeline completed in {seconds:.1f} seconds")


if __name__ == "__main__":
    main()
