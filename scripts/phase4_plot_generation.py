"""Render primary generation results without mixing supplementary attempts."""
import os
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
os.environ["MPLCONFIGDIR"] = str(ROOT / ".cache/matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    data = json.loads((ROOT / "artifacts/phase4/generation/summary.json").read_text())
    controls = data["controls"]
    formulas = data["new_compositions"]
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.7), constrained_layout=True)
    width = .32
    x = np.arange(2)
    for offset, arm, color, label in [(-width/2, "nontrivial", "#287c8e", "Nontrivial group"),
                                      (width/2, "p1", "#d58d34", "P1")]:
        rows = [next(r for r in controls if r["control"] == name and r["arm"] == arm)
                for name in ["mgo_rocksalt", "tio2_rutile"]]
        heights = [r["valid_count"] for r in rows]
        bars = axes[0].bar(x+offset, heights, width, label=label, color=color)
        for bar, row in zip(bars, rows):
            axes[0].text(bar.get_x()+bar.get_width()/2, bar.get_height()+.12,
                         f'{row["valid_count"]}/8\n({row["valid_unique_count"]} unique)', ha="center", fontsize=8)
    axes[0].set_xticks(x, ["Mg4O4: SG225 vs P1", "Ti2O4: SG136 vs P1"])
    axes[0].set_title("Primary matched conditioning: exact-cell validity", loc="left", fontsize=11)
    axes[0].legend(loc="upper right", frameon=False, fontsize=8)
    axes[0].set_ylabel("Structures passing frozen eligibility")
    names = [r["formula"] for r in formulas]
    x = np.arange(len(names))
    diagnostic = [r["reduced_formula_geometry_valid_within_atom_cap_diagnostic_only"] for r in formulas]
    axes[1].bar(x-width/2, [r["valid_count"] for r in formulas], width, color="#287c8e", label="Exact cell: primary")
    bars = axes[1].bar(x+width/2, diagnostic, width, color="#9babb7", label="Reduced formula: diagnostic only")
    for bar, value in zip(bars, diagnostic):
        axes[1].text(bar.get_x()+bar.get_width()/2, value+.12, str(value), ha="center", fontsize=9)
    axes[1].set_xticks(x, names, rotation=30, ha="right")
    axes[1].set_title("Six new-to-catalog formulas: eight attempts each", loc="left", fontsize=11)
    axes[1].legend(loc="upper right", frameon=False, fontsize=8)
    for axis in axes:
        axis.set_ylim(0, 9)
        axis.set_yticks(range(0, 9, 2))
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=.2)
        axis.set_axisbelow(True)
    figure.suptitle("Frozen primary generation results; supplementary MgO draws reported separately", fontsize=12)
    out = ROOT / "artifacts/phase4/figures"
    out.mkdir(parents=True, exist_ok=True)
    figure.savefig(out / "primary_generation.png", dpi=200)
    figure.savefig(out / "primary_generation.pdf")
    plt.close(figure)
    print(json.dumps({"PNG": "artifacts/phase4/figures/primary_generation.png", "PDF": "artifacts/phase4/figures/primary_generation.pdf"}))


if __name__ == "__main__":
    main()
