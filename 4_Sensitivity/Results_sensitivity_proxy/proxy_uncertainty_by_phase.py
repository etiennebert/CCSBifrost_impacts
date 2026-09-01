"""
proxy_uncertainty_by_phase.py -- net operating surplus, taxes & subsidies and employment for every
hypothesis and every project phase, with the uncertainty that comes from the choice of proxy sectors.

Same inputs and same principle as proxy_sensitivity.py (spend x unit footprints), with two differences:
  - the results are split by project phase (Phase 1, 2, 3) as well as by hypothesis;
  - the Monte-Carlo can give each classification a probability. Two weightings are available:
        "equal"     every plausible sector of an item equally likely (the convention of the SI; the draws
                    are the same as in proxy_sensitivity.py, so the whole-project ranges match Table S15)
        "50-35-15"  50 % the sector used in the article, 35 % the first alternative, 15 % the second
                    (items with a single alternative: 50 % / 50 %; items without alternative stay as they are)
    Run:  python proxy_uncertainty_by_phase.py            (equal weights)
          python proxy_uncertainty_by_phase.py 50-35-15
The bars of the figures are the results of the article (the sectors actually used); the whiskers are
the 5th-95th percentile range of the Monte-Carlo.

Outputs (same folder, suffix = weighting):
    proxy_uncertainty_by_phase_<w>.csv / .xlsx    one row per geography x indicator x hypothesis x phase
    proxy_uncertainty_weights_<w>.csv             the probability given to each candidate sector
    Figure_phase_uncertainty_DNK_<w>.png          Danish results
    Figure_phase_uncertainty_world_<w>.png        world results
"""
import sys
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
UNIT_DIR = CCS / "5. MRIOs" / "2. Input Vektor" / "Sensitivity_Unit"
UNIT_OUT = CCS / "5. MRIOs" / "4. Output" / "sensitivity_unit"
README   = CCS / "4. Costs" / "0_GLORIA_ReadMe_057.xlsx"
OUT_DIR  = Path(__file__).resolve().parent

WEIGHTING = sys.argv[1] if len(sys.argv) > 1 else "equal"
WEIGHTS_OF = {"equal":    {1: [1.0], 2: [0.50, 0.50], 3: [1 / 3, 1 / 3, 1 / 3]},
              "50-35-15": {1: [1.0], 2: [0.50, 0.50], 3: [0.50, 0.35, 0.15]}}   # probability of [article's sector, alternative 1, alternative 2]
WEIGHTS = WEIGHTS_OF[WEIGHTING]
N_DRAWS = 10000
HYPS = ["A1", "A2", "A3", "B1", "B2", "B3"]
PHASES = ["Phase 1", "Phase 2", "Phase 3"]
PHASE_LABEL = {"Phase 1": "Phase 1 (3 Mt/yr, 7 years)", "Phase 2": "Phase 2 (5 Mt/yr, 8 years)", "Phase 3": "Phase 3 (10 Mt/yr, 13 years)"}
INDICATORS = ["NOS_glob", "NOS_DNK", "TS_glob", "TS_DNK", "JOBS_glob", "JOBS_DNK"]   # glob = whole world, DNK = Denmark
N_ROWS = 39360
kUSD_TO_MEUR = 1 / 1.05 / 1000                                         # thousand USD -> million EUR2021
ROWS = pd.MultiIndex.from_product([HYPS, PHASES], names=["hypothesis", "phase"])

# %% Step 1: the demand vector of the article, cell by cell (now with the phase) ---------
region_of_row = np.repeat(pd.read_excel(README, sheet_name="Regions")["Region_acronyms"].to_numpy(), 240)
labels = pd.read_csv(FD_LABEL, header=None).iloc[0].tolist()
Y = pd.read_csv(FD_FILE, header=None).to_numpy()

cell_list = []
for j in range(Y.shape[1]):
    scenario, hypothesis, phase, activity, cost_type = labels[j].split("#")
    hyp = ("A" if scenario.endswith("1") else "B") + hypothesis[-1]
    item = activity + "#" + cost_type
    for r in np.flatnonzero(Y[:, j]):
        cell_list.append([j, hyp, phase, item, region_of_row[r], r % 240 + 1, Y[r, j]])
cells = pd.DataFrame(cell_list, columns=["column", "hypothesis", "phase", "item", "country", "sector", "usd"])
items = sorted(cells["item"].unique())

baseline_sector = {}
for item in items:
    sectors_used = cells.loc[cells["item"] == item, "sector"].unique()
    assert len(sectors_used) == 1, item
    baseline_sector[item] = int(sectors_used[0])

# %% Step 2: unit footprints -> multipliers per million USD (full supply chain only) ------
unit_keys = []
for lab in pd.read_csv(UNIT_DIR / "Unit_Label.csv", header=None).iloc[0]:
    country, sector, name = lab.split("#")
    unit_keys.append((country, int(sector)))
unit_index = pd.MultiIndex.from_tuples(unit_keys, names=["country", "sector"])

raw = {}
for stressor in ["VA_Net_Surplus", "VA_Taxes_Production", "VA_Subsidies_Production",
                 "employment_skill_high", "employment_skill_middle", "employment_skill_low"]:
    stacked = pd.read_csv(UNIT_OUT / f"2021_{stressor}_T_BIFROST_Unit_Full_59_country.csv", header=None).to_numpy()
    matrix = stacked.reshape(len(unit_keys), N_ROWS).T
    raw[stressor] = pd.DataFrame({"glob": matrix.sum(axis=0),
                                  "DNK": matrix[region_of_row == "DNK", :].sum(axis=0)}, index=unit_index)

M = pd.DataFrame(index=unit_index)
for where in ["glob", "DNK"]:
    M["NOS_" + where] = raw["VA_Net_Surplus"][where] * kUSD_TO_MEUR
    M["TS_" + where] = (raw["VA_Taxes_Production"][where] + raw["VA_Subsidies_Production"][where]) * kUSD_TO_MEUR
    M["JOBS_" + where] = (raw["employment_skill_high"][where] + raw["employment_skill_middle"][where]
                          + raw["employment_skill_low"][where])

# %% Step 3: contribution of each cost item under each candidate sector, by hypothesis and phase
design = pd.read_csv(UNIT_DIR / "proxy_design.csv")
sector_name = dict(zip(design["gloria_index"], design["gloria_sector"]))
candidates = {}
for item in items:
    candidates[item] = design.loc[design["item"] == item, "gloria_index"].tolist()
    assert candidates[item][0] == baseline_sector[item], item


def contribution(item, sector):
    """Indicators (one row per hypothesis x phase) generated by the spend on `item` when placed on `sector`."""
    table = pd.DataFrame(0.0, index=ROWS, columns=INDICATORS)
    for _, cell in cells[cells["item"] == item].iterrows():
        m = M.loc[(cell["country"], sector)]
        w = cell["usd"] / 1e6
        for k in INDICATORS:
            table.loc[(cell["hypothesis"], cell["phase"]), k] += w * m[k]
    return table


contrib = {}
for item in items:
    for sector in candidates[item]:
        contrib[item, sector] = contribution(item, sector)

article = pd.DataFrame(0.0, index=ROWS, columns=INDICATORS)            # the sectors of the article
for item in items:
    article = article + contrib[item, baseline_sector[item]]

# %% Step 4: weighted Monte-Carlo -------------------------------------------------------
rng = np.random.default_rng(1)
pick = {}
weight_rows = []
for item in items:
    n = len(candidates[item])
    if WEIGHTING == "equal":
        pick[item] = rng.integers(n, size=N_DRAWS)                    # identical to the draw of proxy_sensitivity.py
    else:
        pick[item] = rng.choice(n, size=N_DRAWS, p=WEIGHTS[n])
    for position, sector in enumerate(candidates[item]):
        weight_rows.append([item, position, sector, sector_name[sector], WEIGHTS[n][position]])
weights = pd.DataFrame(weight_rows, columns=["item", "position (0 = article)", "GLORIA sector", "name", "probability"])

contrib_array = {}
for key in contrib:
    contrib_array[key] = contrib[key].to_numpy()
draws = np.zeros((N_DRAWS, len(ROWS), len(INDICATORS)))
for n in range(N_DRAWS):
    for item in items:
        draws[n] += contrib_array[item, candidates[item][pick[item][n]]]
draws_total = draws.reshape(N_DRAWS, len(HYPS), len(PHASES), len(INDICATORS)).sum(axis=2)   # whole project = sum of the phases

# %% Step 5: table: article value and Monte-Carlo percentiles ----------------------------
GEO = {"glob": "World", "DNK": "Denmark"}
NAME = {"NOS": "Net operating surplus (M EUR)", "TS": "Taxes and subsidies on production (M EUR)", "JOBS": "Employment (job-years)"}
rows_out = []
for k, indicator in enumerate(INDICATORS):
    quantity, where = indicator.split("_")
    for i, hyp in enumerate(HYPS):
        for p, phase in enumerate(PHASES):
            r = i * len(PHASES) + p
            v = article.loc[(hyp, phase), indicator]
            p5, p50, p95 = np.percentile(draws[:, r, k], [5, 50, 95])
            rows_out.append([GEO[where], NAME[quantity], hyp, phase, v, p5, p50, p95, 100 * (p5 / v - 1), 100 * (p95 / v - 1)])
        v = article.loc[hyp, indicator].sum()
        p5, p50, p95 = np.percentile(draws_total[:, i, k], [5, 50, 95])
        rows_out.append([GEO[where], NAME[quantity], hyp, "All phases", v, p5, p50, p95, 100 * (p5 / v - 1), 100 * (p95 / v - 1)])
table = pd.DataFrame(rows_out, columns=["geography", "indicator", "hypothesis", "phase", "article value",
                                        "P5", "P50", "P95", "P5 vs article (%)", "P95 vs article (%)"])
table.to_csv(OUT_DIR / f"proxy_uncertainty_by_phase_{WEIGHTING}.csv", index=False)
weights.to_csv(OUT_DIR / f"proxy_uncertainty_weights_{WEIGHTING}.csv", index=False)
with pd.ExcelWriter(OUT_DIR / f"proxy_uncertainty_by_phase_{WEIGHTING}.xlsx") as writer:
    table.to_excel(writer, sheet_name="by_phase", index=False)
    weights.to_excel(writer, sheet_name="weights", index=False)

# %% Step 6: figures -----------------------------------------------------------------------
PHASE_COLOR = ["#86b6ef", "#2a78d6", "#104281"]                        # light -> dark blue for phase 1 -> 3
TOTAL_COLOR = "#b3b1ab"
INK, INK2 = "#0b0b0b", "#52514e"
SUB = {"A1": "A₁", "A2": "A₂", "A3": "A₃", "B1": "B₁", "B2": "B₂", "B3": "B₃"}


def whisker(ax, x, lo, hi, color="#0b0b0b", halo="#ffffff"):
    """Vertical line from the 5th to the 95th percentile with caps; a white halo keeps it visible on dark bars."""
    cap = 0.11
    for lw, c, z in [(3.6, halo, 3), (1.5, color, 4)]:
        ax.plot([x, x], [lo, hi], color=c, lw=lw, solid_capstyle="butt", zorder=z)
        ax.plot([x - cap, x + cap], [lo, lo], color=c, lw=lw, solid_capstyle="butt", zorder=z)
        ax.plot([x - cap, x + cap], [hi, hi], color=c, lw=lw, solid_capstyle="butt", zorder=z)


for where in ["DNK", "glob"]:
    fig, axes = plt.subplots(3, 2, figsize=(11, 9.5), gridspec_kw={"width_ratios": [3.2, 1.3], "wspace": 0.22, "hspace": 0.32})
    fig.subplots_adjust(top=0.94, bottom=0.05)
    for row, quantity in enumerate(["NOS", "TS", "JOBS"]):
        sub = table[(table["geography"] == GEO[where]) & (table["indicator"] == NAME[quantity])]
        # left: one group of three phase bars per hypothesis
        ax = axes[row, 0]
        for i, hyp in enumerate(HYPS):
            for p, phase in enumerate(PHASES):
                r = sub[(sub["hypothesis"] == hyp) & (sub["phase"] == phase)].iloc[0]
                x = i + (p - 1) * 0.27
                ax.bar(x, r["article value"], width=0.25, color=PHASE_COLOR[p], zorder=2,
                       label=PHASE_LABEL[phase] if i == 0 else None)
                whisker(ax, x, r["P5"], r["P95"])
        ax.set_xticks(range(len(HYPS)))
        ax.set_xticklabels([SUB[h] for h in HYPS], fontsize=10)
        ax.set_title("By phase", loc="left", fontsize=10, color=INK2)
        # right: the whole project
        ax = axes[row, 1]
        for i, hyp in enumerate(HYPS):
            r = sub[(sub["hypothesis"] == hyp) & (sub["phase"] == "All phases")].iloc[0]
            ax.bar(i, r["article value"], width=0.6, color=TOTAL_COLOR, zorder=2)
            whisker(ax, i, r["P5"], r["P95"])
        ax.set_xticks(range(len(HYPS)))
        ax.set_xticklabels([SUB[h] for h in HYPS], fontsize=10)
        ax.set_title("Whole project (28 years)", loc="left", fontsize=10, color=INK2)
        axes[row, 0].set_ylabel(NAME[quantity], fontsize=9, color=INK)
        for ax in axes[row]:
            ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
            ax.grid(axis="y", alpha=0.25, zorder=0)
            ax.set_axisbelow(True)
            ax.tick_params(axis="both", length=0, labelsize=9)
            for side in ["top", "right", "left"]:
                ax.spines[side].set_visible(False)
            ax.axhline(0, color=INK2, lw=0.8)
    handles, labels_ = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels_, loc="upper center", ncol=3, frameon=False, fontsize=9, bbox_to_anchor=(0.5, 0.995))
    fig.savefig(OUT_DIR / f"Figure_phase_uncertainty_{'world' if where == 'glob' else where}_{WEIGHTING}.png", dpi=250, bbox_inches="tight")

pd.set_option("display.width", 250)
print(weights.to_string(index=False))
print(table[table["phase"] == "All phases"].round(1).to_string(index=False))
