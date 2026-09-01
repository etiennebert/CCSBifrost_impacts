"""
proxy_sensitivity.py -- how much do the results depend on the GLORIA sectors used as proxies?
(Energy Economics revision, Reviewer 1, comment 1)

Principle
---------
The MRIO result is linear in the demand vector:  result = (Q' .* L) * Y.
So the footprint of 710 million USD placed on the row "Denmark - Transport via pipeline" is
710 times the footprint of 1 million USD placed on that row, and the footprint of a whole
demand vector is the sum of the footprints of its cells.

The MATLAB scripts in "5. MRIOs\3. Script\sensitivity_unit" were therefore run ONCE on a
matrix of "unit" demands (Input_Vektor_Unit_USD.csv): one column per (country, candidate
sector), each column containing a single cell of 1,000,000 USD. This script only combines
the resulting unit footprints. It never calls MATLAB again.

    Step 1  read the demand vector of the article and list its cells
            (hypothesis, cost item, country, GLORIA sector, USD)
    Step 2  read the unit footprints and turn them into multipliers per million USD
    Step 3  compute the contribution of every cost item under every candidate sector
    Step 4  check: with the sectors actually used, the sum must reproduce the article
    Step 5  change the sectors: one item at a time, in groups, worst/best case, Monte-Carlo
    Step 6  check the conclusions of the article under every alternative
    Step 7  write the tables (xlsx + csv) and the tornado figure

Units
-----
GLORIA works in thousand USD. The demand vector is in USD (EUR2021 x 1.05, see
Input_Vektor_EUR.csv / Input_Vektor_USD.csv). Results are in million EUR2021, job-years
and kt CO2e.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# %% Settings ----------------------------------------------------------------------------
CCS      = Path(__file__).resolve().parents[2]                          # ...\Documents\CCS
FD_FILE  = CCS / "5. MRIOs" / "2. Input Vektor" / "Input_Vektor_USD.csv"
FD_LABEL = CCS / "4. Costs" / "2_BIFROST_Input_Vektor_Label.csv"
UNIT_DIR = CCS / "5. MRIOs" / "2. Input Vektor" / "Sensitivity_Unit"   # unit demand matrix, its labels, proxy_design.csv
UNIT_OUT = CCS / "5. MRIOs" / "4. Output" / "sensitivity_unit"         # MATLAB outputs of the unit run
ORIG_OUT = CCS / "5. MRIOs" / "4. Output"                              # MATLAB outputs of the article (used for the check)
README   = CCS / "4. Costs" / "0_GLORIA_ReadMe_057.xlsx"
COSTS    = CCS / "4. Costs" / "1_BIFROST_Costs_2021.xlsx"
OUT_DIR  = Path(__file__).resolve().parent

STRESSORS = ["VA_Net_Surplus", "VA_Taxes_Production", "VA_Subsidies_Production",
             "employment_skill_high", "employment_skill_middle", "employment_skill_low", "ghg_ar6"]
ORIG_NAME = {"employment_skill_high": "employment_hs", "employment_skill_middle": "employment_ms",
             "employment_skill_low": "employment_ls"}                  # the article's output files use these short names
HYPS = ["A1", "A2", "A3", "B1", "B2", "B3"]
INDICATORS = ["NOS_glob", "NOS_DNK", "TS_glob", "TS_DNK", "VA_glob", "VA_DNK",
              "JOBS_glob", "JOBS_DNK", "DJOBS_glob", "DJOBS_DNK", "S3"]  # glob = whole world, DNK = Denmark, D = direct (rank 1)
KEY = ["NOS_DNK", "TS_DNK", "VA_DNK", "VA_glob", "JOBS_DNK", "JOBS_glob", "S3"]   # the indicators reported in the tables
N_ROWS = 39360                                                         # 164 regions x 240 sectors
kUSD_TO_MEUR = 1 / 1.05 / 1000                                         # thousand USD -> million EUR2021
CO2_STORED = (3 * 7 + 5 * 8 + 10 * 13) * 1000                          # kt stored over 28 years: 3, 5, 10 Mt/yr for 7, 8, 13 years
N_DRAWS = 10000                                                        # Monte-Carlo draws

# %% Step 1: the demand vector of the article, cell by cell ----------------------------
region_of_row = np.repeat(pd.read_excel(README, sheet_name="Regions")["Region_acronyms"].to_numpy(), 240)
labels = pd.read_csv(FD_LABEL, header=None).iloc[0].tolist()   # 342 labels like 'Scenario 1#Hypothesis 1#Phase 1#Liquefaction#CAPEX'
Y = pd.read_csv(FD_FILE, header=None).to_numpy()               # 39360 rows x 342 columns, USD

cell_list = []
for j in range(Y.shape[1]):
    scenario, hypothesis, phase, activity, cost_type = labels[j].split("#")
    hyp = ("A" if scenario.endswith("1") else "B") + hypothesis[-1]   # 'Scenario 1' + 'Hypothesis 2' -> 'A2'
    item = activity + "#" + cost_type                                  # e.g. 'Pipeline_transport#OPEX'
    for r in np.flatnonzero(Y[:, j]):                                  # the non-zero cells of this column
        cell_list.append([j, hyp, item, region_of_row[r], r % 240 + 1, Y[r, j]])
cells = pd.DataFrame(cell_list, columns=["column", "hypothesis", "item", "country", "sector", "usd"])
items = sorted(cells["item"].unique())                                 # the 18 cost items

baseline_sector = {}                                                   # the GLORIA sector used for each item in the article
for item in items:
    sectors_used = cells.loc[cells["item"] == item, "sector"].unique()
    assert len(sectors_used) == 1, item                                # each cost item sits on exactly one sector
    baseline_sector[item] = int(sectors_used[0])

# Scope 1 and 2 emissions (kt CO2e) come from the bottom-up workbook and do not depend on the proxies
sheet = pd.read_excel(COSTS, sheet_name="CO2 frome Ej", header=None)
r0 = sheet.index[(sheet == "Scopes 1 & 2").any(axis=1)][0]            # the cell that says 'Scopes 1 & 2' ...
c0 = sheet.columns[(sheet.loc[r0] == "Scopes 1 & 2").to_numpy()][0]
S12 = pd.Series(0.0, index=HYPS)
for r in range(r0 + 1, r0 + 7):                                        # ... and the six rows below it, 'Hypothesis A1' ... 'B3'
    S12[str(sheet.loc[r, c0 - 1]).replace("Hypothesis ", "")] = float(sheet.loc[r, c0]) / 1000

# %% Step 2: unit footprints -> multipliers per million USD of demand -------------------
unit_keys = []                                                         # (country, sector) of each column of the unit matrix
for lab in pd.read_csv(UNIT_DIR / "Unit_Label.csv", header=None).iloc[0]:   # 'DNK#103#Transport via pipeline'
    country, sector, name = lab.split("#")
    unit_keys.append((country, int(sector)))
n_units = len(unit_keys)
unit_index = pd.MultiIndex.from_tuples(unit_keys, names=["country", "sector"])

# raw[stressor, kind]: one row per unit column, world total and Danish total of the footprint of 1 million USD
raw = {}
for stressor in STRESSORS:
    for kind in ["Full", "Rank1"]:
        stacked = pd.read_csv(UNIT_OUT / f"2021_{stressor}_T_BIFROST_Unit_{kind}_59_country.csv", header=None).to_numpy()
        matrix = stacked.reshape(n_units, N_ROWS).T                    # MATLAB wrote reshape(result, [], 1): column after column
        raw[stressor, kind] = pd.DataFrame({"glob": matrix.sum(axis=0),
                                            "DNK": matrix[region_of_row == "DNK", :].sum(axis=0)}, index=unit_index)

# M: the multipliers used below. Value added in million EUR, jobs in job-years, GHG in kt CO2e, per million USD of demand
M = pd.DataFrame(index=unit_index)
for where in ["glob", "DNK"]:
    M["NOS_" + where] = raw["VA_Net_Surplus", "Full"][where] * kUSD_TO_MEUR
    M["TS_" + where] = (raw["VA_Taxes_Production", "Full"][where] + raw["VA_Subsidies_Production", "Full"][where]) * kUSD_TO_MEUR
    M["JOBS_" + where] = (raw["employment_skill_high", "Full"][where] + raw["employment_skill_middle", "Full"][where]
                          + raw["employment_skill_low", "Full"][where])
    M["DJOBS_" + where] = (raw["employment_skill_high", "Rank1"][where] + raw["employment_skill_middle", "Rank1"][where]
                           + raw["employment_skill_low", "Rank1"][where])
M["GHG_full"] = raw["ghg_ar6", "Full"]["glob"]                         # whole supply chain
M["GHG_direct"] = raw["ghg_ar6", "Rank1"]["glob"]                      # first tier only

# %% Step 3: contribution of each cost item under each candidate sector -----------------
design = pd.read_csv(UNIT_DIR / "proxy_design.csv")
sector_name = dict(zip(design["gloria_index"], design["gloria_sector"]))
candidates = {}                                                        # item -> [sector used in the article, alternative 1, ...]
for item in items:
    candidates[item] = design.loc[design["item"] == item, "gloria_index"].tolist()
    assert candidates[item][0] == baseline_sector[item], item          # the design file must start with the sector actually used


def contribution(item, sector):
    """Indicators (one row per hypothesis) generated by the spend on `item` when it is placed on `sector`."""
    table = pd.DataFrame(0.0, index=HYPS, columns=INDICATORS)
    for _, cell in cells[cells["item"] == item].iterrows():
        m = M.loc[(cell["country"], sector)]                           # multipliers of that country-sector
        w = cell["usd"] / 1e6                                          # million USD spent in this cell
        h = cell["hypothesis"]
        for k in ["NOS_glob", "NOS_DNK", "TS_glob", "TS_DNK", "JOBS_glob", "JOBS_DNK", "DJOBS_glob", "DJOBS_DNK"]:
            table.loc[h, k] += w * m[k]
        if item.endswith("Energy"):   # energy: the fuel burnt and the electricity bought are Scopes 1-2 (bottom-up);
            table.loc[h, "S3"] += w * (m["GHG_full"] - m["GHG_direct"])   # only the upstream part is Scope 3
        else:                         # equipment and services: the whole supply-chain footprint is Scope 3
            table.loc[h, "S3"] += w * m["GHG_full"]
    table["VA_glob"] = table["NOS_glob"] + table["TS_glob"]
    table["VA_DNK"] = table["NOS_DNK"] + table["TS_DNK"]
    return table


contrib = {}                                                           # (item, sector) -> table hypotheses x indicators
for item in items:
    for sector in candidates[item]:
        contrib[item, sector] = contribution(item, sector)


def results(mapping):
    """Results (one row per hypothesis) for a mapping {item: sector}. Items not in the mapping keep the article's sector."""
    table = pd.DataFrame(0.0, index=HYPS, columns=INDICATORS)
    for item in items:
        sector = mapping.get(item, baseline_sector[item])
        table = table + contrib[item, sector]
    table["Ratio_%"] = 100 * (S12 + table["S3"]) / CO2_STORED          # (Scopes 1+2+3) / CO2 stored
    table.index.name = "H"
    return table


base = results({})                                                     # the sectors of the article -> the results of the article

# %% Step 4: check -- the unit footprints must reproduce the article's MATLAB outputs ----
check_rows = []
for stressor in STRESSORS:
    for kind in ["Full", "Rank1"]:
        f = ORIG_OUT / f"2021_{ORIG_NAME.get(stressor, stressor)}_T_BIFROST_{kind}_59_country.csv"
        if not f.exists():
            continue
        original = pd.read_csv(f, header=None).to_numpy().reshape(Y.shape[1], N_ROWS).T.sum(axis=0)   # world total of each column
        rebuilt = np.zeros(Y.shape[1])
        for _, cell in cells.iterrows():
            rebuilt[cell["column"]] += cell["usd"] / 1e6 * raw[stressor, kind].loc[(cell["country"], cell["sector"]), "glob"]
        check_rows.append([stressor, kind, original.sum(), rebuilt.sum(), np.abs(rebuilt - original).max() / np.abs(original).max()])
check = pd.DataFrame(check_rows, columns=["stressor", "kind", "original total", "reproduced total", "max relative error"])

# %% Step 5: change the proxies ----------------------------------------------------------
spend_A1 = {}                                                          # million EUR per item, hypothesis A1
spend_avg = {}                                                         # million EUR per item, average of the six hypotheses
for item in items:
    spend_A1[item] = cells.loc[(cells["item"] == item) & (cells["hypothesis"] == "A1"), "usd"].sum() / 1e6 / 1.05
    spend_avg[item] = cells.loc[cells["item"] == item, "usd"].sum() / 1e6 / 1.05 / 6


def ordering(table, column):
    """The hypotheses from the highest to the lowest value, e.g. 'B3 > A1 > A3 > A2 > B2 > B1'."""
    return " > ".join(table[column].sort_values(ascending=False).index)


def evaluate(label, mapping):
    """One row of the one-at-a-time / grouped tables: effect of `mapping` on hypothesis A1 and on the ranking."""
    table = results(mapping)
    change = 100 * (table / base - 1)                                  # % change of every indicator for every hypothesis
    row = {"scenario": label, "spend affected A1 (M EUR)": sum(spend_A1[item] for item in mapping)}
    for k in KEY:
        row[f"d{k} A1 (%)"] = change.loc["A1", k]
    row["ratio A1 (%)"] = table.loc["A1", "Ratio_%"]
    row["max |dVA_DNK| over hypotheses (%)"] = change["VA_DNK"].abs().max()
    for h in HYPS:
        row[f"VA_DNK {h} (M EUR)"] = table.loc[h, "VA_DNK"]
    for column in ["VA_DNK", "VA_glob", "Ratio_%"]:
        row["ordering " + column] = ordering(table, column)
        if ordering(table, column) != ordering(base, column):
            row["ordering " + column] += "  (changed)"
    return row


# 5a. one item at a time
oat_rows = []
for item in items:
    for sector in candidates[item][1:]:                                # every alternative of this item, all other items unchanged
        oat_rows.append(evaluate(f"{item}: {sector_name[baseline_sector[item]]} -> {sector_name[sector]}", {item: sector}))
oat = pd.DataFrame(oat_rows)

# 5b. several items at once
GROUPS = {
    "Vessel-type assets as shipbuilding (FSIU, injection unit and carrier CAPEX -> Other transport equipment)":
        {"Unloading#CAPEX": 88, "Gasification_and_injection#CAPEX": 88, "Shipping_Transport#CAPEX": 88},
    "All plant CAPEX as civil engineering construction":
        {"Liquefaction#CAPEX": 99, "Storage#CAPEX": 99, "Loading#CAPEX": 99, "Unloading#CAPEX": 99, "Gasification_and_injection#CAPEX": 99},
    "All non-energy OPEX as repair and installation of machinery":
        {"Liquefaction#OPEX": 89, "Storage#OPEX": 89, "Loading#OPEX": 89, "Unloading#OPEX": 89, "Gasification_and_injection#OPEX": 89},
    "Transport OPEX alternatives (pipeline -> gas distribution; shipping -> services to transport)":
        {"Pipeline_transport#OPEX": 94, "Shipping_Transport#OPEX": 106},
    "Marine fuels as refined petroleum products":
        {"Shipping_Transport#Energy": 63, "Gasification_and_injection#Energy": 63},
}
grouped_rows = []
for label, mapping in GROUPS.items():
    if all((item, sector) in contrib for item, sector in mapping.items()):   # only if these sectors are in proxy_design.csv
        grouped_rows.append(evaluate(label, mapping))
grouped = pd.DataFrame(grouped_rows)

# 5c. exact worst and best case over ALL combinations of the alternatives (hypothesis A1).
# The contributions are additive, so the minimum is reached when every item takes its lowest candidate, etc.
envelope_rows = []
for k in KEY:
    lowest, highest = 0.0, 0.0
    for item in items:
        values_A1 = [contrib[item, sector].loc["A1", k] for sector in candidates[item]]
        lowest += min(values_A1)
        highest += max(values_A1)
    b = base.loc["A1", k]
    envelope_rows.append([k, lowest, b, highest, 100 * (lowest / b - 1), 100 * (highest / b - 1)])
envelope = pd.DataFrame(envelope_rows, columns=["indicator", "min A1", "baseline A1", "max A1", "min (%)", "max (%)"])

# 5d. Monte-Carlo: 10,000 random combinations, every plausible sector of an item equally likely
rng = np.random.default_rng(1)
pick = {}                                                              # item -> which candidate (0 = article's sector) in each draw
for item in items:
    pick[item] = rng.integers(len(candidates[item]), size=N_DRAWS)
contrib_array = {}
for key in contrib:
    contrib_array[key] = contrib[key][INDICATORS].to_numpy()
draws = np.zeros((N_DRAWS, len(HYPS), len(INDICATORS)))               # results of all six hypotheses in every draw
for n in range(N_DRAWS):
    for item in items:
        draws[n] += contrib_array[item, candidates[item][pick[item][n]]]

mc_rows = []
for k in KEY:
    d = draws[:, :, INDICATORS.index(k)]                               # N_DRAWS x 6 hypotheses
    b = base[k].to_numpy()
    p5, p50, p95 = np.percentile(100 * (d[:, 0] / b[0] - 1), [5, 50, 95])   # column 0 = A1
    same_order, same_best = 0, 0
    for n in range(N_DRAWS):
        if tuple(np.argsort(-d[n])) == tuple(np.argsort(-b)):
            same_order += 1
        if np.argmax(d[n]) == np.argmax(b):
            same_best += 1
    mc_rows.append([k, p5, p50, p95, 100 * same_order / N_DRAWS, 100 * same_best / N_DRAWS])
mc = pd.DataFrame(mc_rows, columns=["indicator", "P5 dA1 (%)", "P50 dA1 (%)", "P95 dA1 (%)",
                                    "full ordering of the 6 hypotheses preserved (% of draws)", "best hypothesis unchanged (% of draws)"])


# %% Step 6: do the conclusions of the article survive? ----------------------------------
def conclusions_hold(table):
    """The statements of the article, evaluated on one results table (one row per hypothesis). True = still holds."""
    va, nos, jobs = table["VA_DNK"], table["NOS_DNK"], table["JOBS_DNK"]
    emissions = table["S3"] + S12
    return {
        "Danish VA: B1 (all liquefaction abroad) is the lowest of the six hypotheses": va.idxmin() == "B1",
        "Danish VA: A1 > A3 > A2 (the earlier the full switch to pipeline, the better)": va["A1"] > va["A3"] > va["A2"],
        "Danish VA: B3 > B2 > B1 (the more liquefaction sited in Denmark, the better)": va["B3"] > va["B2"] > va["B1"],
        "Danish NOS: A1 is the highest of the six hypotheses": nos.idxmax() == "A1",
        "Global VA: spread between the highest and lowest hypothesis below 10%": table["VA_glob"].max() / table["VA_glob"].min() - 1 < 0.10,
        "Danish jobs: B1 is the lowest of the six hypotheses": jobs.idxmin() == "B1",
        "Emissions: A2 is the lowest and B1 the highest of the six hypotheses": emissions.idxmin() == "A2" and emissions.idxmax() == "B1",
    }


in_base = conclusions_hold(base)
statements = list(in_base.keys())
count_oat = {s: 0 for s in statements}
count_grp = {s: 0 for s in statements}
count_mc = {s: 0 for s in statements}
n_oat, n_grp = 0, 0
for item in items:
    for sector in candidates[item][1:]:
        held = conclusions_hold(results({item: sector}))
        n_oat += 1
        for s in statements:
            count_oat[s] += held[s]
for label, mapping in GROUPS.items():
    if all((item, sector) in contrib for item, sector in mapping.items()):
        held = conclusions_hold(results(mapping))
        n_grp += 1
        for s in statements:
            count_grp[s] += held[s]
for n in range(N_DRAWS):
    held = conclusions_hold(pd.DataFrame(draws[n], index=HYPS, columns=INDICATORS))
    for s in statements:
        count_mc[s] += held[s]
claims_rows = []
for s in statements:
    claims_rows.append([s, bool(in_base[s]), f"{count_oat[s]}/{n_oat}", f"{count_grp[s]}/{n_grp}", 100 * count_mc[s] / N_DRAWS])
claims = pd.DataFrame(claims_rows, columns=["conclusion", "holds in baseline", "holds in one-at-a-time cases",
                                            "holds in grouped cases", "holds in Monte-Carlo draws (%)"])

# %% Step 7: write the tables and the figure ---------------------------------------------
concordance = design[design["role"] == "baseline"][["item", "gloria_index", "gloria_sector", "isic_rev4"]].copy()
concordance["spend A1 (M EUR)"] = [spend_A1.get(item, 0.0) for item in concordance["item"]]
concordance["spend per hypothesis (M EUR, average)"] = [spend_avg.get(item, 0.0) for item in concordance["item"]]

# multipliers of the Danish candidate sectors per million EUR of demand (SI Table S16); 1 million EUR = 1.05 million USD
mult_rows = []
for country, sector in unit_keys:
    if country == "DNK":
        m = M.loc[(country, sector)] * 1.05
        mult_rows.append([sector, sector_name.get(sector, sector),
                          m["NOS_glob"] * 1000, m["NOS_DNK"] * 1000, m["TS_glob"] * 1000, m["TS_DNK"] * 1000,   # thousand EUR
                          m["JOBS_glob"], m["JOBS_DNK"], m["GHG_full"], m["GHG_direct"]])                       # job-years, kt CO2e
mult = pd.DataFrame(mult_rows, columns=["GLORIA sector", "name", "NOS global (thousand EUR)", "NOS Denmark (thousand EUR)",
                                        "T&S global (thousand EUR)", "T&S Denmark (thousand EUR)", "jobs global", "jobs Denmark",
                                        "GHG global (kt CO2e)", "GHG first tier (kt CO2e)"])

tables = [("concordance", concordance, False), ("baseline_reproduced", base, True), ("baseline_check", check, False),
          ("one_at_a_time", oat, False), ("grouped", grouped, False), ("envelope", envelope, False),
          ("monte_carlo", mc, False), ("conclusions_check", claims, False), ("unit_multipliers_DNK", mult, False)]
with pd.ExcelWriter(OUT_DIR / "proxy_sensitivity_results.xlsx") as writer:
    for sheet_name, table, with_index in tables:
        table.to_excel(writer, sheet_name=sheet_name, index=with_index)
        table.to_csv(OUT_DIR / f"proxy_sensitivity_{sheet_name}.csv", index=with_index)

# tornado figure: the one-at-a-time cases, sorted by their effect on Danish value added
ITEM_NAME = {"Liquefaction": "Liquefaction", "Storage": "Harbour storage", "Loading": "Loading", "Pipeline_transport": "Pipeline transport",
             "Shipping_Transport": "Shipping", "Unloading": "FSIU / unloading", "Gasification_and_injection": "Injection"}
o = oat.copy()
o["key"] = o["dVA_DNK A1 (%)"].abs()
o = o.sort_values("key")
tick_labels = []
for scenario in o["scenario"]:
    item, change_text = scenario.split(": ", 1)                        # 'Pipeline_transport#OPEX', 'Transport via pipeline -> ...'
    activity, cost_type = item.split("#")
    tick_labels.append(f"{ITEM_NAME.get(activity, activity)} {cost_type.lower()}\n→ {change_text.split(' -> ')[1]}")
fig, ax = plt.subplots(figsize=(8.0, 0.46 * len(o) + 1.5))
y = np.arange(len(o))
ax.barh(y + 0.19, o["dNOS_DNK A1 (%)"], 0.36, color="#1f4e79", label="Net operating surplus, Denmark")
ax.barh(y - 0.19, o["dVA_DNK A1 (%)"], 0.36, color="#9dc3e6", label="Value added, Denmark")
ax.set_yticks(y)
ax.set_yticklabels(tick_labels, fontsize=7.5, linespacing=1.3)
for k, v in enumerate(o["dNOS_DNK A1 (%)"]):
    ax.text(v + (0.6 if v >= 0 else -0.6), k + 0.19, f"{v:+.1f}%", va="center", ha="left" if v >= 0 else "right", fontsize=6.5, color="#1f4e79")
ax.axvline(0, color="k", lw=0.8)
ax.grid(axis="x", alpha=0.25)
ax.set_axisbelow(True)
ax.tick_params(axis="y", length=0)
for side in ["top", "right", "left"]:
    ax.spines[side].set_visible(False)
lim = max(6, 1.25 * o[["dNOS_DNK A1 (%)", "dVA_DNK A1 (%)"]].abs().to_numpy().max())
ax.set_xlim(-lim, lim)
ax.set_xlabel("Change relative to the classification used in the article, hypothesis A₁ (%)", fontsize=9)
ax.legend(fontsize=8, frameon=False, loc="lower right", bbox_to_anchor=(1.0, 1.005), ncol=2, handlelength=1.2, columnspacing=1.2)
fig.tight_layout()
fig.savefig(OUT_DIR / "Figure_S_proxy_tornado.png", dpi=300, bbox_inches="tight")

pd.set_option("display.width", 250)
print(check.to_string(index=False))
print(oat[["scenario"] + [f"d{k} A1 (%)" for k in KEY]].round(1).to_string(index=False))
print(grouped[["scenario"] + [f"d{k} A1 (%)" for k in KEY]].round(1).to_string(index=False))
print(envelope.round(2).to_string(index=False))
print(mc.round(1).to_string(index=False))
print(claims.round(1).to_string(index=False))
