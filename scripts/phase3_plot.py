"""Publication-style first-seed replay plot; reads completed results only."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
os.environ["MPLCONFIGDIR"] = str(ROOT / ".cache/matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    source = ROOT / "artifacts/phase3/replay/seed_20261022/summary.json"
    summary = json.loads(source.read_text())
    out = ROOT / "artifacts/phase3/figures"
    out.mkdir(parents=True, exist_ok=True)
    names = {"random": "Random", "quality": "Predicted quality", "quality_diversity": "Quality + diversity",
             "uncertainty": "Uncertainty", "full": "Full uncertainty + diversity"}
    colors = {"random": "#777777", "quality": "#0072B2", "quality_diversity": "#009E73",
              "uncertainty": "#E69F00", "full": "#CC79A7"}
    with plt.rc_context({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "pdf.fonttype": 42, "font.family": "DejaVu Sans"}):
        figure, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
        for record in summary["policies"]:
            policy = record["policy"]
            x = [0]+[r["queries"] for r in record["curve"]]
            for axis, key in zip(axes, ["near_stable_hits", "reference_hull_hits"]):
                y = [0]+[r[key] for r in record["curve"]]
                axis.plot(x, y, color=colors[policy], marker="o", markersize=3,
                          linewidth=2 if policy == "full" else 1.6,
                          linestyle="--" if policy == "quality_diversity" else "-",
                          label=names[policy])
                axis.set(xlim=(0, 50), ylim=(0, 50), xlabel="Retrospective label queries", ylabel="Cumulative hits")
                axis.grid(alpha=.18)
        axes[0].set_title("Near-stable: signed hull distance ≤ 0.05 eV/atom")
        axes[1].set_title("On/below historical reference hull: ≤ 0")
        axes[0].legend(frameon=False, fontsize=8, loc="upper left")
        figure.suptitle("First paired replay — seed 20261022 only", fontsize=13)
        figure.savefig(out / "first_seed_acquisition.png", dpi=200)
        figure.savefig(out / "first_seed_acquisition.pdf")
        plt.close(figure)
    print(json.dumps({"png": str(out / "first_seed_acquisition.png"), "single_seed_only": True}))


if __name__ == "__main__":
    main()
