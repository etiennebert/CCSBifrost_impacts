# Expected Value Added and Employment Impacts of Offshore CCS in Denmark

Replication code for:

> Berthet, E., Soytas, U., Ladenburg, J., & Morris, J. (2025). *Expected Value Added and Employment Impacts of Climate-Related Offshore CCS in Denmark.*

## Overview

This repository contains the **code** used to estimate the direct and indirect value added (VA), employment, and greenhouse-gas impacts of the Danish BIFROST offshore Carbon Capture and Storage (CCS) project. The analysis couples bottom-up cost estimation with Multi-Regional Input-Output (MRIO) modelling based on the GLORIA database (v59, year 2021).

All **input data and output results** (cost vectors, MRIO outputs, figures, and Tableau workbooks) are archived on Zenodo:

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18666671.svg)](https://doi.org/10.5281/zenodo.18666671)

## Repository Structure

```
.
├── 1_BIFROST_Costs_Estimation/
│   ├── 2_Input_Vektor_Creation.yxmd    # Alteryx workflow: builds the BIFROST cost input vector
│   └── 3_Costs_Visualisation.yxmd      # Alteryx workflow: visualises cost breakdown (Figure 2)
│
├── 2_MRIOs/
│   └── Matlab_Scripts/
│       ├── GLORIA_extraction_VA.m       # Extracts VA stressor matrices from GLORIA raw results
│       ├── GLORIA_BIFROST_Full.m        # Full Leontief inverse (L) multiplier analysis
│       └── GLORIA_BIFROST_Rank1.m       # First-order (rank-1, A matrix) approximation
│
├── 3_Results/
│   └── Alteryx_Flows/
│       ├── Agregation_Results.yxmd      # Aggregates full-model MRIO output
│       ├── Agregation_Results_Rank1.yxmd# Aggregates rank-1 MRIO output
│       └── Visualisation_results.yxmd   # Prepares data for Tableau visualisation
│
├── LICENSE
└── README.md
```

## Workflow

The replication pipeline has three stages. Each stage reads the outputs of the previous one.

1. **Cost estimation** — Alteryx workflows in `1_BIFROST_Costs_Estimation/` construct the BIFROST project cost vector from engineering estimates and map expenditures to GLORIA sectors and countries. Input data are available on [Zenodo](https://doi.org/10.5281/zenodo.18666671) under `1. BIFROST Costs estimation/`.

2. **MRIO analysis** — Matlab scripts in `2_MRIOs/Matlab_Scripts/` load the GLORIA Leontief inverse (or technology matrix) and stressor satellite accounts, then multiply the cost vector through the global supply chain to obtain VA, employment, and GHG footprints per sector per country. The scripts compute results for both the full Leontief inverse (`GLORIA_BIFROST_Full.m`) and the first-order approximation (`GLORIA_BIFROST_Rank1.m`). `GLORIA_extraction_VA.m` pre-processes the value-added stressor matrices from the raw GLORIA results.

3. **Results aggregation and visualisation** — Alteryx flows in `3_Results/Alteryx_Flows/` aggregate the raw MRIO output into summary tables and prepare data for Tableau figures. Output databases and figures are available on [Zenodo](https://doi.org/10.5281/zenodo.18666671) under `3. Results/`.

## How to Reproduce

### Step 1 — Obtain the data

1. Download the input data and output results from the Zenodo archive: <https://doi.org/10.5281/zenodo.18666671>.
2. Download the GLORIA MRIO database (v59) from <https://ielab.info/resources/gloria>.

### Step 2 — Configure local paths

The Matlab scripts contain hardcoded paths that must be adapted to your local environment. In each `.m` file, update the following variables:

| Variable | Description |
|----------|-------------|
| `wd.hd` | Root directory of your GLORIA MRIO data |
| `y.bifrost` | Directory containing the BIFROST cost input vector |
| `wd.hd_sa` | Directory for MRIO output files |

Similarly, the Alteryx workflows (`.yxmd`) contain input/output paths that must be adjusted to match your local directory structure.

### Step 3 — Run the pipeline

1. Run the Alteryx workflows in `1_BIFROST_Costs_Estimation/` to generate the cost input vector.
2. Run `GLORIA_extraction_VA.m` to prepare the value-added stressor matrices (if not using pre-computed `.mat` files from the GLORIA database).
3. Run `GLORIA_BIFROST_Full.m` and `GLORIA_BIFROST_Rank1.m` to obtain the MRIO results.
4. Run the Alteryx flows in `3_Results/Alteryx_Flows/` to aggregate results and prepare visualisation data.
5. Open the Tableau workbooks (available on [Zenodo](https://doi.org/10.5281/zenodo.18666671)) to generate Figures 3–6.

## Data Requirements

| Dataset | Source | Notes |
|---------|--------|-------|
| GLORIA MRIO v59 (year 2021) | <https://ielab.info/resources/gloria> | Freely available; required for Step 2 |
| BIFROST cost data & MRIO outputs | [Zenodo (DOI: 10.5281/zenodo.18666671)](https://doi.org/10.5281/zenodo.18666671) | Input vectors, labels, output CSVs, and figures |

## Software

| Tool | Version | Purpose |
|------|---------|---------|
| Matlab | R2023b+ | MRIO matrix computations |
| Alteryx Designer | 2024.1+ | Data wrangling and cost vector construction |
| Tableau Desktop | 2024.1+ | Figure generation |

## License

This code is provided under the [MIT License](LICENSE).

## Citation

If you use this code or data, please cite the accompanying paper and the Zenodo data archive:

**Paper:**
> Berthet, E., Soytas, U., Ladenburg, J., & Morris, J. (2025). Expected Value Added and Employment Impacts of Climate-Related Offshore CCS in Denmark. *Energy Economics*.

**Data and code:**
> Berthet, E., Soytas, U., Ladenburg, J., & Morris, J. (2025). Replication data and code for: Expected Value Added and Employment Impacts of Climate-Related Offshore CCS in Denmark [Data set]. Zenodo. <https://doi.org/10.5281/zenodo.18666671>
