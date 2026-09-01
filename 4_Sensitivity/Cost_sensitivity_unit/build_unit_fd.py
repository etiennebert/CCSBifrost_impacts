"""
build_unit_fd.py -- unit final-demand matrix for the proxy-sector sensitivity analysis
(Energy Economics revision, Reviewer 1, comment 1).

Idea. The MRIO model is linear in final demand. Instead of re-running MATLAB once per
alternative proxy mapping, we run it ONCE on a matrix of unit demands: one column per
(country, GLORIA industry) that appears in proxy_design.csv, each column containing a
single cell of 1,000,000 USD on that industry row. Every column of the MATLAB output is
then the full supply-chain footprint (VA, employment, GHG) per million USD of final
demand on that country-industry. The footprint of ANY mapping of the BIFROST cost items
to proxy sectors is a weighted sum of these unit footprints, computed in seconds in
proxy_sensitivity.py -- including the exact reproduction of the submitted results.

Row convention (GLORIA v059 ReadMe, sheet 'Sequential region-sector labels'):
    row = (region_index - 1) * 240 + sector_index        sector_index 1..120 = industries
                                                          121..240 = products (not used)
Each row placed here is checked against the label text of the ReadMe before writing.

Inputs  : ../../../4. Costs/0_GLORIA_ReadMe_057.xlsx   (GLORIA labels, unchanged)
          proxy_design.csv                               (cost item -> baseline/alternative proxies)
Outputs : Input_Vektor_Unit_USD.csv   39,360 rows x K columns, no header (same layout as
                                      Input_Vektor_USD.csv, so the MATLAB scripts read it unchanged)
          Unit_Label.csv              one row of K labels 'COUNTRY#sector_index#sector name'
"""
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
CCS = HERE.parents[2]                       # .../Documents/CCS
README = CCS / "4. Costs" / "0_GLORIA_ReadMe_057.xlsx"

# Countries receiving BIFROST expenditure in the baseline vector: Denmark, plus the four
# host countries of the non-Danish liquefaction facilities (1_BIFROST_Costs_2021.xlsx,
# sheet 'Costs_atribution': DEU 0.4, FIN 0.2, POL 0.2, SWE 0.2).
COUNTRIES = ["DNK", "DEU", "FIN", "POL", "SWE"]
UNIT = 1_000_000                            # USD of final demand per column
N_ROWS, BLOCK = 39_360, 240

regions = pd.read_excel(README, sheet_name="Regions")            # Lfd_Nr, Region_acronyms, Region_names
sectors = pd.read_excel(README, sheet_name="Sectors")            # Lfd_Nr, Sector_names (1..120 industries)
seqlab = pd.read_excel(README, sheet_name="Sequential region-sector labels")
labels = seqlab["Sequential_regionSector_labels"].tolist()       # 39,360 row labels
design = pd.read_csv(HERE / "proxy_design.csv")

reg_idx = dict(zip(regions["Region_acronyms"], regions["Lfd_Nr"]))
sec_name = dict(zip(sectors["Lfd_Nr"], sectors["Sector_names"]))
wanted = sorted(set(design["gloria_index"]))

cols, names = [], []
for c in COUNTRIES:
    for s in wanted:
        row = (reg_idx[c] - 1) * BLOCK + s                       # 1-based row in the GLORIA system
        lab = labels[row - 1]
        assert f"({c}) {sec_name[s]} industry" in lab, (c, s, lab)   # traceability check
        cols.append(row)
        names.append(f"{c}#{s}#{sec_name[s]}")

Y = pd.DataFrame(0, index=range(1, N_ROWS + 1), columns=range(len(cols)), dtype="int64")
for k, row in enumerate(cols):
    Y.iat[row - 1, k] = UNIT

Y.to_csv(HERE / "Input_Vektor_Unit_USD.csv", header=False, index=False)
pd.DataFrame([names]).to_csv(HERE / "Unit_Label.csv", header=False, index=False)
print(f"{len(cols)} unit columns written ({len(COUNTRIES)} countries x {len(wanted)} sectors); "
      f"column sums all equal {UNIT}: {bool((Y.sum() == UNIT).all())}")
