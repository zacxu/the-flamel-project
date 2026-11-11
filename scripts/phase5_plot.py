"""Plot saved within-composition CHGNet energies; no numerical jobs."""
import os
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["MPLCONFIGDIR"] = str(ROOT / ".cache/matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    summary = json.loads((ROOT / "artifacts/phase5/chgnet/summary.json").read_text())
    records = {r["candidate_id"]: r for r in summary["results"]}
    pairs = summary["symmetry_pairs"]
    figure, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), constrained_layout=True)
    differences = [r["p1_minus_nontrivial_eV_atom"]*1000 for r in pairs]
    axes[0].barh(["MgO: supplemented pools", "TiO2: primary pools"], differences, color=["#287c8e", "#6c9fac"])
    for y, value in enumerate(differences):
        axes[0].text(value+4, y, f"+{value:.2f}", va="center", fontsize=10)
    axes[0].set_xlim(0, max(differences)*1.24)
    axes[0].set_xlabel("P1 minus nontrivial-group energy (meV/atom)")
    axes[0].set_title("One frozen selected pair per composition", loc="left", fontsize=11)
    axes[0].invert_yaxis()
    rutile = records["reference_rutile"]["energy_eV_per_atom"]
    ti_pair = next(r for r in pairs if r["control"] == "tio2_rutile")
    ids = [ti_pair["nontrivial_id"], ti_pair["p1_id"], "reference_rutile", "reference_anatase"]
    labels = ["Generated SG136", "Generated P1", "Rutile reference", "Anatase reference"]
    values = [(records[name]["energy_eV_per_atom"]-rutile)*1000 for name in ids]
    bars = axes[1].bar(np.arange(4), values, color=["#287c8e", "#d58d34", "#91a6af", "#7e8e9b"])
    for bar, value in zip(bars, values):
        axes[1].text(bar.get_x()+bar.get_width()/2, value+(2 if value >= 0 else -2), f"{value:+.2f}",
                     ha="center", va="bottom" if value >= 0 else "top", fontsize=9)
    axes[1].set_xticks(np.arange(4), labels, rotation=25, ha="right")
    axes[1].set_ylabel("Energy relative to rutile reference (meV/atom)")
    axes[1].set_ylim(min(values)-12, max(values)+15)
    axes[1].axhline(0, color="#555", linewidth=.8)
    axes[1].set_title("TiO2: same composition, same model", loc="left", fontsize=11)
    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="x" if axis is axes[0] else "y", alpha=.2)
        axis.set_axisbelow(True)
    figure.suptitle("CHGNet 0.3.0 relaxed energies: descriptive model comparisons, not DFT stability", fontsize=12)
    out = ROOT / "artifacts/phase5/figures"
    out.mkdir(parents=True, exist_ok=True)
    figure.savefig(out / "within_composition_energies.png", dpi=200)
    figure.savefig(out / "within_composition_energies.pdf")
    plt.close(figure)
    print(json.dumps({"PNG": "artifacts/phase5/figures/within_composition_energies.png", "PDF": "artifacts/phase5/figures/within_composition_energies.pdf"}))


if __name__ == "__main__":
    main()
