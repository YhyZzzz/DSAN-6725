"""Write the pipeline run report to results.md."""

import logging

import polars as pl

from .config import PipelineConfig

logger = logging.getLogger(__name__)


def _format_elapsed(
    elapsed_seconds: float,
) -> str:
    """Format elapsed seconds as a human-readable duration."""
    minutes = int(elapsed_seconds // 60)
    seconds = elapsed_seconds % 60
    if minutes > 0:
        return f"{minutes} minutes and {seconds:.1f} seconds"
    return f"{seconds:.1f} seconds"


def write_report(
    config: PipelineConfig,
    raw_rows: int,
    clean_rows: int,
    revenue: pl.DataFrame,
    tips: pl.DataFrame,
    elapsed_seconds: float,
) -> None:
    """Write results.md summarizing the pipeline run.

    Args:
        config: Pipeline configuration used for the run.
        raw_rows: Row count before cleaning.
        clean_rows: Row count after cleaning.
        revenue: Revenue-by-borough aggregation result.
        tips: Tip-percentage-by-hour aggregation result.
        elapsed_seconds: Wall-clock duration of the run.
    """
    dropped = raw_rows - clean_rows
    dropped_pct = (dropped / raw_rows * 100) if raw_rows else 0.0

    with pl.Config(tbl_formatting="MARKDOWN", tbl_hide_dataframe_shape=True):
        revenue_table = str(revenue)
        tips_table = str(tips)

    content = f"""# Pipeline Run Report

## Run Summary

- Data directory: `{config.raw_dir}`
- Rows scanned: {raw_rows:,}
- Rows after cleaning: {clean_rows:,} ({dropped:,} dropped, {dropped_pct:.2f}%)
- Wall-clock time: {_format_elapsed(elapsed_seconds)}

## Revenue by Borough

{revenue_table}

## Tip Percentage by Hour of Day

{tips_table}
"""
    config.results_path.write_text(content)
    logger.info(f"Report written to {config.results_path}")
