"""Download the raw datasets required by ``project_analysis.ipynb``."""

from pathlib import Path
from zipfile import ZipFile

import requests

PROJECT_ROOT = Path(__file__).resolve().parent
RAW_DATA_ROOT = PROJECT_ROOT / "data" / "raw"

TLC_TRIP_BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
TLC_MISC_BASE_URL = "https://d37ci6vzurychx.cloudfront.net/misc"
NOAA_LCD_BASE_URL = (
    "https://www.ncei.noaa.gov/oa/local-climatological-data/v2/access"
)


def download_file(url: str, destination: Path) -> None:
    """Download a file unless it already exists locally."""
    if destination.exists():
        print(f"[exists] {destination.relative_to(PROJECT_ROOT)}")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        with destination.open("wb") as output_file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                output_file.write(chunk)
    print(f"[downloaded] {destination.relative_to(PROJECT_ROOT)}")


def download_tlc_trip_records() -> None:
    """Download April--December 2025 HVFHV monthly Parquet files."""
    for month in range(4, 13):
        filename = f"fhvhv_tripdata_2025-{month:02d}.parquet"
        download_file(
            f"{TLC_TRIP_BASE_URL}/{filename}",
            RAW_DATA_ROOT / "tlc" / filename,
        )


def download_taxi_zone_geography() -> None:
    """Download the Taxi Zone lookup and extract the official shapefile."""
    tlc_root = RAW_DATA_ROOT / "tlc"
    download_file(
        f"{TLC_MISC_BASE_URL}/taxi_zone_lookup.csv",
        tlc_root / "taxi_zone_lookup.csv",
    )

    shapefile_root = tlc_root / "taxi_zones"
    if shapefile_root.exists():
        print("[exists] data/raw/tlc/taxi_zones/")
        return

    archive_path = tlc_root / "taxi_zones.zip"
    download_file(f"{TLC_MISC_BASE_URL}/taxi_zones.zip", archive_path)
    with ZipFile(archive_path) as zone_archive:
        zone_archive.extractall(tlc_root)
    archive_path.unlink()
    print("[extracted] data/raw/tlc/taxi_zones/")


def download_noaa_lcd() -> None:
    """Download Central Park LCD observations for calendar year 2025."""
    filename = "LCD_USW00094728_2025.csv"
    download_file(
        f"{NOAA_LCD_BASE_URL}/2025/{filename}",
        RAW_DATA_ROOT / "external" / "noaa_lcd" / filename,
    )


def main() -> None:
    """Download all raw datasets used by the project."""
    print("TLC trip records")
    download_tlc_trip_records()

    print("\nTaxi Zone geography")
    download_taxi_zone_geography()

    print("\nNOAA LCD observations")
    download_noaa_lcd()


if __name__ == "__main__":
    main()
