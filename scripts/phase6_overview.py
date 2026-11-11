"""Make a four-panel scientific overview from frozen saved evidence."""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
os.environ["MPLCONFIGDIR"] = str(ROOT / ".cache/matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np


def rows(name):
    with (ROOT / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    out = ROOT / "artifacts/phase6/figures"
    out.mkdir(parents=True, exist_ok=True)
    curves = rows("artifacts/phase4/replay/learning_curves.csv")
    evaluation = rows("artifacts/phase4/replay/per_seed_evaluation_metrics.csv")
    generation = json.loads((ROOT / "artifacts/phase4/generation/summary.json").read_text())
    qe = json.loads((ROOT / "artifacts/phase3/qe/summary.json").read_text())
    geometry = json.loads((ROOT / "artifacts/phase3/qe" / qe["accepted_candidate_job_id"] / "final_geometry.json").read_text())
    lattice = np.asarray(geometry["lattice"]["matrix"], dtype=float)
    atom_positions = np.array([site["abc"] for site in geometry["sites"]]) % 1 @ lattice
    species = [site["species"][0]["element"] for site in geometry["sites"]]

    plt.rcParams.update({"font.size": 11, "axes.titlesize": 12, "axes.labelsize": 11,
                         "pdf.fonttype": 42, "ps.fonttype": 42})
    fig = plt.figure(figsize=(12.5, 9.8), layout="constrained")
    grid = fig.add_gridspec(2, 2, height_ratios=[1, 1.08])
    ax = fig.add_subplot(grid[0, 0])
    names = {"random": "Random", "quality": "Quality", "quality_diversity": "Quality + diversity",
             "uncertainty": "Uncertainty", "full": "Full"}
    colors = {"random": "#777777", "quality": "#0072B2", "quality_diversity": "#009E73",
              "uncertainty": "#E69F00", "full": "#CC79A7"}
    for policy, name in names.items():
        values = np.array([[int(next(row["near_stable_hits"] for row in curves
                      if int(row["seed"]) == seed and row["policy"] == policy and int(row["queries"]) == q))
                      for q in range(10, 51, 10)] for seed in range(20261022, 20261027)])
        values = np.column_stack([np.zeros(5), values])
        mean = values.mean(axis=0)
        sd = values.std(axis=0, ddof=1)
        x = np.arange(0, 51, 10)
        ax.plot(x, mean, "o-", ms=4, color=colors[policy], label=name)
        if policy in {"quality", "full"}:
            ax.fill_between(x, mean - sd, mean + sd, color=colors[policy], alpha=.12)
    ax.set(title="(a) Fixed-budget historical label retrieval", xlabel="Queries per policy", ylabel="Near-stable hits (historical target <=0.05 eV/atom)",
           xlim=(0, 51), ylim=(0, 50))
    ax.legend(fontsize=9, loc="upper left", frameon=False)
    ax.grid(alpha=.18)
    ax.text(.98, .97, "Means of 5 overlapping splits; shaded sample SD\nFull minus quality at 50: -11.8 hits", transform=ax.transAxes,
            ha="right", va="top", fontsize=9)

    ax = fig.add_subplot(grid[0, 1])
    for index, policy in enumerate(["initial_shared", "quality", "full"]):
        coverage = [100 * float(next(row["interval_90_empirical_coverage"] for row in evaluation
                    if int(row["seed"]) == seed and row["policy"] == policy and int(row["queries"]) == (0 if index == 0 else 50)))
                    for seed in range(20261022, 20261027)]
        ax.scatter(index + np.linspace(-.12, .12, 5), coverage, s=42, color=["#555555", colors["quality"], colors["full"]][index], zorder=3)
        ax.plot([index - .19, index + .19], [np.mean(coverage)] * 2, color="black", linewidth=2.5, zorder=4)
    ax.axhline(90, color="#aa3333", ls="--", linewidth=1.3, label="Nominal 90%")
    ax.set(title="(b) Empirical uncertainty coverage", ylabel="Held-out interval coverage (%)",
           xticks=range(3), xticklabels=["Initial", "Quality at 50", "Full at 50"], xlim=(-.5, 2.5))
    ax.legend(frameon=False, fontsize=9)
    ax.grid(axis="y", alpha=.18)
    ax.text(.5, .03, "Each dot: 3,418 untouched rows in one split\nBlack bars: means; no arbitrary-OOD guarantee", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=9)
    lower, upper = ax.get_ylim()
    ax.set_ylim(min(lower, 84), max(upper, 95))

    ax = fig.add_subplot(grid[1, 0])
    expected_counts = [7, 0, 6, 1]
    controls = generation["controls"]
    # The frozen source is verified by Phase 6's structure audit; assert the
    # primary counts here as well rather than mix in supplementary samples.
    selected_arms = [("mgo_rocksalt", "nontrivial"), ("mgo_rocksalt", "p1"),
                     ("tio2_rutile", "nontrivial"), ("tio2_rutile", "p1")]
    count_values = [next(row["valid_count"] for row in controls
                        if row["control"] == control and row["arm"] == arm)
                    for control, arm in selected_arms]
    if count_values != expected_counts:
        raise RuntimeError(f"Unexpected primary arm counts: {count_values}")
    bars = ax.bar(range(4), np.array(expected_counts) / 8 * 100,
                  color=["#0072B2", "#E69F00"] * 2, width=.66)
    for bar, count in zip(bars, expected_counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2, f"{count}/8", ha="center", fontsize=11)
    ax.set(title="(c) Primary exact-cell generation validity", ylabel="Exact-cell valid (%)", ylim=(0, 110),
           xticks=range(4), xticklabels=["MgO\nSG225", "MgO\nP1", "TiO2\nSG136", "TiO2\nP1"])
    ax.grid(axis="y", alpha=.18)
    ax.text(.5, .97, "Same symmetry-aware generator; changed conditioning", transform=ax.transAxes,
            ha="center", va="top", fontsize=9)
    ax.text(.5, -.18, "New formulas: 0/48 eligible; larger-cell diagnostics excluded\nSymmetry energy pairs: one per arm, descriptive only", transform=ax.transAxes,
            ha="center", va="top", fontsize=9)

    ax = fig.add_subplot(grid[1, 1], projection="3d")
    for corner in np.ndindex(2, 2, 2):
        origin = np.array(corner)
        for direction in range(3):
            if corner[direction] == 0:
                endpoint = origin.copy(); endpoint[direction] = 1
                points = np.stack([origin @ lattice, endpoint @ lattice])
                ax.plot(*points.T, color="#777777", alpha=.55, linewidth=.8)
    element_colors = {"Mg": "#6699AA", "O": "#CC4444"}
    for element in ["Mg", "O"]:
        points = atom_positions[np.array(species) == element]
        ax.scatter(*points.T, s=160 if element == "Mg" else 100,
                   c=element_colors[element], edgecolor="white", linewidth=.5, alpha=1, depthshade=True)
    ax.set_title("(d) Fresh DFT: known MgO recovery", pad=12)
    ax.set(xlabel="x (angstrom)", ylabel="y (angstrom)", zlabel="z (angstrom)")
    ax.set_box_aspect(np.linalg.norm(lattice, axis=1))
    ax.view_init(elev=22, azim=34)
    ax.legend(handles=[Line2D([0], [0], marker="o", color="w", label=element,
                     markerfacecolor=color, markersize=9) for element, color in element_colors.items()],
              loc="upper right", frameon=False, fontsize=9)
    ax.text2D(.5, -.05, "Ca-Mg-O references: 2/161; complete hull unavailable\nPerturbation check incomplete; no new stable material", transform=ax.transAxes,
              ha="center", va="top", fontsize=9)
    fig.suptitle("A resource-bounded, auditable crystal-discovery prototype", fontsize=15)
    fig.savefig(out / "research_overview.png", dpi=200, bbox_inches="tight")
    fig.savefig(out / "research_overview.pdf", bbox_inches="tight")
    plt.close(fig)
    print("artifacts/phase6/figures/research_overview.png and .pdf")


if __name__ == "__main__":
    main()
