"""Download NYC TLC Yellow Taxi trip data and the taxi zone lookup table.

Files come from the public TLC trip record data CDN. Documentation:
https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

Example usage:
    # Download one month (default: January) -- about 50 MB, fine for development
    uv run python scripts/download_data.py

    # Download the first three months
    uv run python scripts/download_data.py --months 3

    # Download the full year (about 3.5 GB). This may take a while.
    uv run python scripts/download_data.py --months 12
"""

import argparse
import logging
import time
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,p%(process)s,{%(filename)s:%(lineno)d},%(levelname)s,%(message)s",
)
logger = logging.getLogger(__name__)

# TLC trip record data CDN. Docs: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
BASE_URL: str = "https://d37ci6vzurychx.cloudfront.net/trip-data"
ZONE_LOOKUP_URL: str = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
DATA_YEAR: int = 2025
DEFAULT_MONTHS: int = 1
CHUNK_SIZE: int = 1024 * 1024
REQUEST_TIMEOUT: int = 60


def _download_file(
    url: str,
    dest: Path,
) -> None:
    """Stream url to dest, skipping the download if dest already exists."""
    if dest.exists():
        logger.info(f"Already present, skipping: {dest}")
        return

    logger.info(f"Downloading {url}")
    start_time = time.time()
    response = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    tmp_dest = dest.with_suffix(dest.suffix + ".part")
    with open(tmp_dest, "wb") as f:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            f.write(chunk)
    tmp_dest.rename(dest)

    elapsed_time = time.time() - start_time
    size_mb = dest.stat().st_size / (1024 * 1024)
    logger.info(f"Saved {dest} ({size_mb:.1f} MB in {elapsed_time:.1f} seconds)")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download NYC Yellow Taxi trip data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
    uv run python scripts/download_data.py
    uv run python scripts/download_data.py --months 12
""",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=DEFAULT_MONTHS,
        choices=range(1, 13),
        metavar="N",
        help=f"Number of months to download, starting at January (default: {DEFAULT_MONTHS})",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=DATA_YEAR,
        help=f"Data year (default: {DATA_YEAR})",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("data/raw"),
        help="Destination directory (default: data/raw)",
    )
    return parser.parse_args()


def main() -> None:
    """Download the requested months of trip data plus the zone lookup table."""
    args = _parse_args()
    args.dest.mkdir(parents=True, exist_ok=True)

    if args.months == 12:
        logger.warning(
            "Downloading the FULL year (about 3.5 GB). This may take a while."
        )
    else:
        logger.info(f"Downloading {args.months} month(s) of {args.year} data.")

    start_time = time.time()
    for month in range(1, args.months + 1):
        filename = f"yellow_tripdata_{args.year}-{month:02d}.parquet"
        _download_file(f"{BASE_URL}/{filename}", args.dest / filename)

    _download_file(ZONE_LOOKUP_URL, args.dest / "taxi_zone_lookup.csv")

    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = elapsed_time % 60
    if minutes > 0:
        logger.info(f"Completed in {minutes} minutes and {seconds:.1f} seconds")
    else:
        logger.info(f"Completed in {seconds:.1f} seconds")


if __name__ == "__main__":
    main()
