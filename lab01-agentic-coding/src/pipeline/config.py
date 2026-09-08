"""Pipeline configuration."""

from pathlib import Path

from pydantic import BaseModel, Field

DATA_YEAR: int = 2025


class PipelineConfig(BaseModel):
    """Configuration for the taxi data pipeline.

    Attributes:
        raw_dir: Directory containing downloaded monthly parquet files.
        zone_lookup_path: Path to the taxi zone lookup CSV.
        year: Data year being processed; rows outside it are invalid.
        results_path: Where the pipeline report is written.
    """

    raw_dir: Path = Field(default=Path("data/raw"))
    zone_lookup_path: Path = Field(default=Path("data/raw/taxi_zone_lookup.csv"))
    year: int = Field(default=DATA_YEAR, ge=2009, le=2100)
    results_path: Path = Field(default=Path("results.md"))
