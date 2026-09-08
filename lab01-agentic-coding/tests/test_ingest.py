"""Tests for the implemented ingestion stage. These pass in the starter repo."""

from pathlib import Path

import polars as pl
import pytest

from pipeline.ingest import EXPECTED_COLUMNS, scan_trips, scan_zone_lookup

from .conftest import FIXTURE_DIR, N_CLEAN_ROWS, N_DIRTY_ROWS


class TestScanTrips:
    """Tests for scan_trips."""

    def test_returns_lazyframe_with_expected_columns(self, tmp_path: Path):
        """A directory with one matching file scans to the expected schema."""
        # Arrange
        src = FIXTURE_DIR / "sample.parquet"
        (tmp_path / "yellow_tripdata_2025-01.parquet").write_bytes(src.read_bytes())

        # Act
        lf = scan_trips(tmp_path)

        # Assert
        assert isinstance(lf, pl.LazyFrame)
        assert lf.collect_schema().names() == EXPECTED_COLUMNS

    def test_row_count_matches_fixture(self, tmp_path: Path):
        """All fixture rows are scanned."""
        src = FIXTURE_DIR / "sample.parquet"
        (tmp_path / "yellow_tripdata_2025-01.parquet").write_bytes(src.read_bytes())

        n = scan_trips(tmp_path).select(pl.len()).collect().item()

        assert n == N_CLEAN_ROWS + N_DIRTY_ROWS

    def test_missing_directory_raises(self, tmp_path: Path):
        """An empty directory raises FileNotFoundError with download guidance."""
        with pytest.raises(FileNotFoundError, match="download_data"):
            scan_trips(tmp_path / "nope")


class TestScanZoneLookup:
    """Tests for scan_zone_lookup."""

    def test_returns_lookup_columns(self):
        """The lookup contains LocationID and Borough columns."""
        lf = scan_zone_lookup(FIXTURE_DIR / "taxi_zone_lookup.csv")

        names = lf.collect_schema().names()
        assert "LocationID" in names
        assert "Borough" in names

    def test_missing_file_raises(self, tmp_path: Path):
        """A missing lookup file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            scan_zone_lookup(tmp_path / "absent.csv")
