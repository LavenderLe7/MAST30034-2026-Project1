[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/rGQRVS1B)

# Forecasting Borough-Level Late-Arrival Share for Completed WAV-Requested HVFHV Trips in New York City

This repository contains the complete data-acquisition and analysis workflow for
MAST30034 Project 1. It forecasts short-term service risk among completed New
York City High Volume For-Hire Vehicle (HVFHV) trips for which a
wheelchair-accessible vehicle (WAV) was requested.

The research question is:

> How accurately can the borough-level share of completed WAV-requested HVFHV
> trips whose vehicle arrives more than 10 minutes after the requested pickup
> time be forecast one four-hour period ahead, using only information available
> beforehand?

The forecast is designed as an advance prioritisation signal for HVFHS platform
operations and dispatch teams. It does not measure cancellations, unmet demand,
vehicle supply, regulatory compliance, or profitability, and it does not make
automated allocation decisions.

## Key results

The chronological evaluation covers November--December 2025 and contains 1,731
borough-period observations representing 114,672 completed WAV-requested trips.

| Model | Request-weighted MAE (percentage points) |
| --- | ---: |
| Weighted XGBoost | 2.5885 |
| Grouped-binomial GLM | 2.7757 |
| Matured 24-hour history | 2.9546 |

Weighted XGBoost gives the lowest overall held-out error. The notebook also
reports calibration, borough and time-block performance, high-risk screening,
expanding temporal backtests, permutation importance, and an HRRR feature
ablation. These results should be interpreted with the documented sparse-support
and completed-trip coverage limitations.

## Reproduce from a clean clone

The instructions below are the supported reproduction path. They are written
for a macOS or Linux terminal using `bash` or `zsh`. Run every command in order;
do not run the notebook from a different working directory because it treats the
current directory as the project root.

### Prerequisites

- Git;
- Python 3.13.x (tested with Python 3.13.5);
- Java Development Kit 17 (tested with OpenJDK 17.0.20);
- an uninterrupted internet connection with access to GitHub, the Python
  package index, TLC, NOAA NCEI, and the remote HRRR archive;
- at least 10 GB of free disk space. The downloaded raw inputs alone occupy
  approximately 4.51 GB, and additional space is needed for the Python
  environment, temporary downloads, Spark files, and generated artifacts.

Confirm that the required system tools are available before cloning:

```bash
git --version
python3 --version
java -version
```

`python3 --version` should report Python 3.13.x, and `java -version` should
report Java 17. Install or select those versions before continuing if either
check reports a different major version.

### Run the complete pipeline

Start in the directory in which the repository should be created, then execute
these commands one line at a time:

```bash
git clone https://github.com/MAST30034-AppliedDataScience/project-1-individual-LavenderLe7.git
cd project-1-individual-LavenderLe7
python3 -c 'from pathlib import Path; p=[".gitignore", "requirements.txt", "download_data.py", "project_analysis.ipynb", "data/reference/holiday_calendar.csv"]; m=[x for x in p if not Path(x).is_file() or Path(x).stat().st_size==0]; assert not m, f"Repository is incomplete: {m}"; print("PASS: required repository files are present.")'
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python download_data.py --dry-run
python download_data.py
python download_data.py --dry-run
mkdir -p tmp
jupyter nbconvert --to notebook --execute project_analysis.ipynb --output project_analysis_reproduced.ipynb --output-dir tmp --ExecutePreprocessor.kernel_name=python3 --ExecutePreprocessor.timeout=-1
```

The first downloader dry run should report 12 planned inputs on a clean clone.
After the download, the second dry run should report 12 existing inputs and zero
planned downloads. The notebook command has no per-cell timeout because the
Spark and HRRR stages can take a long time. It writes the executed notebook to
`tmp/project_analysis_reproduced.ipynb`, while all generated datasets, figures,
model summaries, and evidence tables are written to their normal project
locations.

No API key or manual data placement is required. Every notebook run requires
access to remote HRRR metadata. A clean first run also downloads all required
HRRR borough-point subsets; later runs can reuse completed monthly partitions.

### Verify the completed run

Run these commands after `jupyter nbconvert` exits successfully:

```bash
python -c 'import json; n=json.load(open("tmp/project_analysis_reproduced.ipynb")); c=[x for x in n["cells"] if x["cell_type"]=="code"]; e=[o for x in c for o in x.get("outputs", []) if o.get("output_type")=="error"]; assert len(c)==109 and [x.get("execution_count") for x in c]==list(range(1, 110)) and not e; print("PASS: 109 sequential code cells and zero Jupyter error outputs.")'
python -c 'from pathlib import Path; p=["data/standardized/hrrr_forecasts/hrrr_borough_forecasts_standardized.parquet", "data/curated/wav_service_risk/borough_four_hour_panel.parquet", "outputs/tables/wav_model_comparison.csv", "outputs/tables/wav_hrrr_feature_ablation.csv"]; m=[x for x in p if not Path(x).is_file() or Path(x).stat().st_size==0]; assert not m, f"Missing or empty artifacts: {m}"; print("PASS: key generated artifacts exist and are non-empty.")'
python -c 'import pandas as pd; d=pd.read_csv("outputs/tables/wav_model_comparison.csv"); print(d[["model_name", "weighted_mae_percentage_points"]].to_string(index=False))'
```

The final command should reproduce the three headline MAE values shown in the
results table above, subject to the same upstream data snapshots remaining
available. The downloader retrieves public files at run time and the repository
does not freeze those external files with a checksum manifest; therefore exact
byte-for-byte reproducibility also depends on the upstream providers not
replacing their published data.

To inspect the reproduced notebook interactively after validation, run:

```bash
jupyter lab tmp/project_analysis_reproduced.ipynb
```

## Data acquisition and generated artifacts

`download_data.py` retrieves every non-HRRR raw input required by the final
pipeline:

- nine TLC HVFHV monthly Parquet files for April--December 2025;
- the TLC Taxi Zone lookup table and shapefile;
- NOAA Local Climatological Data for Central Park station `USW00094728` for
  2025.

The NOAA observations support descriptive weather EDA only; they are not formal
model predictors. The small 2025 federal holiday calendar is version-controlled
at `data/reference/holiday_calendar.csv` and is not downloaded.

The notebook derives the borough-to-HRRR grid mapping from the TLC geography,
opens the archived HRRR forecast dataset through `dynamical-catalog`, and caches
completed monthly borough-point partitions under
`data/standardized/hrrr_forecasts/`. It then creates:

- nine standardised monthly WAV-request files;
- the combined standardised HRRR forecast data;
- the curated borough-by-four-hour modelling panel;
- five analytical figures in both PNG and PDF formats;
- two model-summary CSV files;
- five final evidence-table CSV files.

Raw, standardised, and curated datasets are intentionally excluded from Git.
Small reference inputs, source code, documentation, report material, figures,
and final summary tables remain eligible for version control.

## Method summary

The modelling period is April--December 2025. The chronological split is:

- training: April--August 2025;
- validation: September--October 2025;
- held-out evaluation: November--December 2025.

The evaluation period is not used for model fitting, early stopping, or
XGBoost tree-count selection. All service-history features use only outcomes
that have matured before the forecast is issued. Formal weather predictors are
HRRR forecasts available at issue time, with a three-hour availability buffer;
realised target-period weather is never used as a predictor.

The final comparison evaluates a matured-history benchmark, a grouped-binomial
GLM, and request-weighted XGBoost using the same chronological information
contract and request-weighted error metrics.

## Troubleshooting and safe recovery

### Java or Spark does not start

Run `java -version` again inside the terminal used for the analysis and confirm
that Java 17 is selected. PySpark will fail before preprocessing if Java is
missing or incompatible.

### A raw download is interrupted or invalid

Downloads are first written to `.part` files and moved into place only after a
basic format check. Rerun `python download_data.py`; completed non-empty inputs
that pass the basic check are skipped. If one existing input is reported as
invalid, remove only that named file and rerun the normal downloader.

Do not use `--force` for routine recovery. It applies to the complete download
set and will re-download all raw inputs, not only one file.

### An HRRR monthly cache is corrupt

The notebook reuses a monthly HRRR partition when that file already exists. If
reading a specific partition fails, remove only the named corrupt monthly file
from `data/standardized/hrrr_forecasts/` and rerun the notebook. Do not delete
the entire data directory.

### Spark prints an `EOFError` while shutting down

A Spark accumulator/RPC `EOFError` can appear in the final cell's `stderr`
during shutdown even after successful computation. Treat it as a non-fatal
shutdown warning only when the `jupyter nbconvert` command returns exit code
zero and the verification above confirms 109 sequential code cells with zero
Jupyter `error` outputs. Otherwise, treat the run as failed and inspect the
earlier notebook output.

## Repository layout

```text
project-1-individual-LavenderLe7/
├── .gitignore
├── README.md
├── requirements.txt
├── download_data.py
├── project_analysis.ipynb
├── data/
│   ├── raw/                         # downloaded; ignored by Git
│   ├── reference/
│   │   ├── holiday_calendar.csv     # tracked input
│   │   └── hrrr_borough_grid_points.csv  # generated; ignored by Git
│   ├── standardized/                # generated; ignored by Git
│   └── curated/                     # generated; ignored by Git
├── outputs/
│   ├── figures/
│   ├── model_results/
│   └── tables/
└── report/
    └── MAST30034_Project_1_Template_2024/
        ├── main.tex
        ├── references.bib
        └── main.pdf
```

The reproduction commands regenerate the analytical datasets and outputs; they
do not rewrite the manually authored report prose. The final analysis is in
`project_analysis.ipynb`, while the report source and compiled PDF are in
`report/MAST30034_Project_1_Template_2024/`.
