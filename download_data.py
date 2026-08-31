"""
Download every raw dataset required by the project analysis.

Run this script once after cloning the repository. Existing non-empty files are
validated and skipped by default, so rerunning the script is safe.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from zipfile import ZipFile, is_zipfile

import requests

PROJECT_ROOT = Path(__file__).resolve().parent
RAW_DATA_ROOT = PROJECT_ROOT / "data" / "raw"

TLC_TRIP_BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
TLC_MISC_BASE_URL = "https://d37ci6vzurychx.cloudfront.net/misc"
NOAA_LCD_BASE_URL = (
    "https://www.ncei.noaa.gov/oa/local-climatological-data/v2/access"
)
REQUEST_TIMEOUT_SECONDS = (30, 300)
DOWNLOAD_CHUNK_BYTES = 1024 * 1024


def validate_local_file(
    file_path: Path, *, expected_suffix: str | None = None
) -> None:
    """
    Validate that a downloaded file is non-empty and has the expected format.

    Args:
        file_path: Local file to validate.
        expected_suffix: Optional format suffix when a temporary path is used.

    Raises:
        ValueError: If the file is missing, empty, or fails a format check.
    """
    if not file_path.is_file() or file_path.stat().st_size == 0:
        raise ValueError(f"Missing or empty file: {file_path}")

    file_suffix = expected_suffix or file_path.suffix

    if file_suffix == ".parquet":
        with file_path.open("rb") as parquet_file:
            header = parquet_file.read(4)
            parquet_file.seek(-4, 2)
            footer = parquet_file.read(4)
        if header != b"PAR1" or footer != b"PAR1":
            raise ValueError(f"Invalid Parquet file: {file_path}")

    if file_suffix == ".csv":
        with file_path.open("rb") as csv_file:
            first_bytes = csv_file.read(200).lower()
        if b"<html" in first_bytes or first_bytes.lstrip().startswith(b"<!doctype"):
            raise ValueError(f"HTML response saved as CSV: {file_path}")

    if file_suffix == ".zip" and not is_zipfile(file_path):
        raise ValueError(f"Invalid ZIP archive: {file_path}")

    if file_suffix == ".geojson":
        with file_path.open(encoding="utf-8") as geojson_file:
            geojson_data = json.load(geojson_file)
        if (
            geojson_data.get("type") != "FeatureCollection"
            or not geojson_data.get("features")
        ):
            raise ValueError(f"Invalid GeoJSON feature collection: {file_path}")


def download_file(
    url: str,
    destination: Path,
    *,
    force: bool,
    dry_run: bool,
    query_params: Mapping[str, str] | None = None,
) -> str:
    """
    Download one file atomically and return its final status label.

    Args:
        url: Source URL for the requested file.
        destination: Final local path for the downloaded file.
        force: Whether to replace an existing non-empty file.
        dry_run: Whether to report the planned action without downloading.
        query_params: Optional query parameters sent with the request.

    Returns:
        A status label: ``existing``, ``planned``, or ``downloaded``.

    Raises:
        requests.RequestException: If the HTTP request fails.
        ValueError: If the downloaded content fails validation.
    """
    if destination.is_file() and destination.stat().st_size > 0 and not force:
        validate_local_file(destination)
        print(f"[exists] {destination.relative_to(PROJECT_ROOT)}")
        return "existing"

    if dry_run:
        print(f"[would download] {destination.relative_to(PROJECT_ROOT)}")
        return "planned"

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial_path = Path(f"{destination}.part")

    try:
        with requests.get(
            url,
            params=query_params,
            stream=True,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": "MAST30034-reproducible-download/1.0"},
        ) as response:
            response.raise_for_status()
            with partial_path.open("wb") as output_file:
                for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_BYTES):
                    if chunk:
                        output_file.write(chunk)

        validate_local_file(partial_path, expected_suffix=destination.suffix)
        partial_path.replace(destination)
        size_mb = destination.stat().st_size / 1_000_000
        relative_path = destination.relative_to(PROJECT_ROOT)
        print(f"[downloaded] {relative_path} ({size_mb:.1f} MB)")
        return "downloaded"
    except Exception:
        partial_path.unlink(missing_ok=True)
        raise


def download_tlc_trip_records(*, force: bool, dry_run: bool) -> Counter[str]:
    """
    Download April-December 2025 HVFHV monthly Parquet files.
    """
    status_counts: Counter[str] = Counter()

    for month in range(4, 13):
        filename = f"fhvhv_tripdata_2025-{month:02d}.parquet"
        destination = RAW_DATA_ROOT / "tlc" / filename
        status = download_file(
            f"{TLC_TRIP_BASE_URL}/{filename}",
            destination,
            force=force,
            dry_run=dry_run,
        )
        status_counts[status] += 1

    return status_counts


def download_taxi_zone_geography(*, force: bool, dry_run: bool) -> Counter[str]:
    """
    Download the Taxi Zone lookup and extract the official shapefile archive.
    """
    status_counts: Counter[str] = Counter()
    tlc_root = RAW_DATA_ROOT / "tlc"

    lookup_status = download_file(
        f"{TLC_MISC_BASE_URL}/taxi_zone_lookup.csv",
        tlc_root / "taxi_zone_lookup.csv",
        force=force,
        dry_run=dry_run,
    )
    status_counts[lookup_status] += 1

    shapefile_root = tlc_root / "taxi_zones"
    required_parts = [
        shapefile_root / f"taxi_zones{extension}"
        for extension in (".shp", ".shx", ".dbf", ".prj")
    ]
    shapefile_is_ready = all(
        file_path.is_file() and file_path.stat().st_size > 0
        for file_path in required_parts
    )

    if shapefile_is_ready and not force:
        print("[exists] data/raw/tlc/taxi_zones/")
        status_counts["existing"] += 1
        return status_counts

    archive_path = tlc_root / "taxi_zones.zip"
    archive_status = download_file(
        f"{TLC_MISC_BASE_URL}/taxi_zones.zip",
        archive_path,
        force=force,
        dry_run=dry_run,
    )
    status_counts[archive_status] += 1

    if not dry_run:
        tlc_root.mkdir(parents=True, exist_ok=True)
        with ZipFile(archive_path) as zone_archive:
            zone_archive.extractall(tlc_root)
        for file_path in required_parts:
            validate_local_file(file_path)
        archive_path.unlink()
        print("[extracted] data/raw/tlc/taxi_zones/")

    return status_counts


def download_noaa_lcd(*, force: bool, dry_run: bool) -> Counter[str]:
    """
    Download Central Park LCDv2 observations for calendar year 2025.
    """
    status_counts: Counter[str] = Counter()
    weather_root = RAW_DATA_ROOT / "external" / "noaa_lcd"

    year = 2025
    filename = f"LCD_USW00094728_{year}.csv"
    status = download_file(
        f"{NOAA_LCD_BASE_URL}/{year}/{filename}",
        weather_root / filename,
        force=force,
        dry_run=dry_run,
    )
    status_counts[status] += 1

    return status_counts


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line options for safe repeated downloads.
    """
    parser = argparse.ArgumentParser(
        description="Download the raw data required by project_analysis.ipynb."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List missing downloads without creating or changing files.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing raw files after each replacement is fully downloaded.",
    )
    return parser.parse_args()


def main() -> None:
    """
    Run every download group and print a compact completion summary.
    """
    arguments = parse_arguments()
    status_counts: Counter[str] = Counter()

    print("TLC trip records")
    status_counts.update(
        download_tlc_trip_records(
            force=arguments.force,
            dry_run=arguments.dry_run,
        )
    )

    print("\nTaxi Zone geography")
    status_counts.update(
        download_taxi_zone_geography(
            force=arguments.force,
            dry_run=arguments.dry_run,
        )
    )

    print("\nNOAA LCD observations")
    status_counts.update(
        download_noaa_lcd(
            force=arguments.force,
            dry_run=arguments.dry_run,
        )
    )

    print("\nDownload summary")
    for status_name in ("existing", "downloaded", "planned"):
        print(f"{status_name}: {status_counts[status_name]}")


if __name__ == "__main__":
    main()
