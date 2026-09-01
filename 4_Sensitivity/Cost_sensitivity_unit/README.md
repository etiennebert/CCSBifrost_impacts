# Proxy-sector sensitivity analysis (Reviewer 1, comment 1) — how it works and how to run it

## Idea (one MATLAB run instead of one per alternative)

The MRIO model is linear in final demand. For any cost item mapped to a proxy sector, its footprint is
`spend x (footprint per unit of final demand on that country-sector)`. So we run the usual MATLAB scripts
ONCE on a matrix of *unit demands* (1,000,000 USD on one country-industry per column) and obtain the unit
footprint of every candidate proxy sector. Any mapping of the 18 cost items to proxies — the submitted one,
each alternative one at a time, all combinations, a Monte-Carlo over combinations — is then a weighted sum
computed in seconds by `proxy_sensitivity.py`. The submitted results are reproduced exactly as a check.

## Files (all in this folder unless stated)

| File | What it is |
|---|---|
| `proxy_design.csv` | The concordance: for each cost item (activity#type) the baseline GLORIA industry actually used in the submitted vector, and the alternative(s) tested, with ISIC Rev.4 reference and rationale. Edit this file to add/remove alternatives. |
| `build_unit_fd.py` | Builds `Input_Vektor_Unit_USD.csv` (39,360 x 65, one 1e6-USD cell per column) and `Unit_Label.csv` from the GLORIA ReadMe. Each row is checked against the ReadMe label text (region acronym + sector name + "industry"). |
| `Input_Vektor_Unit_USD.csv`, `Unit_Label.csv` | The unit demand matrix and its column labels `COUNTRY#sector_index#sector_name` (5 countries x 13 sectors). |
| `../../3. Script/sensitivity_unit/GLORIA_BIFROST_Unit_Full.m`, `..._Rank1.m` | Copies of the headline scripts; only three lines differ (input folder/file, output folder/tag). `run_unit.bat` runs both in MATLAB batch mode. |
| `../../4. Output/sensitivity_unit/` | MATLAB outputs `2021_<stressor>_T_BIFROST_Unit_{Full,Rank1}_59_country.csv` (same stacked-column format as the headline outputs, 65 columns instead of 342). |
| `../../../6. Results/4. Sensitivity_Proxy/proxy_sensitivity.py` | Post-processing: reproduces the baseline (check vs `4. Output/*.csv`), evaluates all alternatives, writes `proxy_sensitivity_results.xlsx` (+ csv per sheet) and `Figure_S_proxy_tornado.png`. |

## Run (about 10–15 minutes, of which MATLAB ~10)

1. `python build_unit_fd.py` (already run; re-run only if `proxy_design.csv` changes).
2. Double-click `5. MRIOs\3. Script\sensitivity_unit\run_unit.bat` (or run the two .m files in MATLAB).
   Needs the GLORIA matrices on `D:\GLORIA_MRIOS_59` exactly like the headline scripts.
3. `python "6. Results\4. Sensitivity_Proxy\proxy_sensitivity.py"` (needs pandas, numpy, matplotlib, openpyxl).

## Conventions kept identical to the headline analysis

* Final demand placed on GLORIA *industry* rows; Y divided by 1000 in MATLAB (GLORIA in '000 USD); EUR2021 x 1.05 = USD.
* VA = net operating surplus + taxes on production + subsidies on production (negative); Denmark = GLORIA region DNK of the supplying sector.
* Employment = high + middle + low skill (job-years); direct = Rank1 script.
* GHG: Scopes 1 & 2 bottom-up (sheet 'CO2 frome Ej' of 1_BIFROST_Costs_2021.xlsx, unchanged by proxy choice);
  Scope 3 = full footprint of CAPEX and OPEX items + indirect (rank 2–n) footprint of energy items; stored CO2 = 191 Mt.

## Note on the April 2026 `Sensitivity_Proxy` folder

The earlier alternative vectors (`Input_Vektor_USD_Alt_1..7.csv`) shifted spend between 0-based row offsets that
were mislabelled in their README (offset 85 is *Machinery and equipment*, 103 is *Water transport* — a service, not
shipbuilding; 105 is *Services to transport*). They are superseded by this folder.
