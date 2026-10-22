"""Membuat figur laporan dari hasil eksperimen.

Contoh:
  python experiments/make_figures.py --results-dir experiments/results/final_review
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def resolve(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default="experiments/results/final_review")
    parser.add_argument("--dpi", type=int, default=180)
    args = parser.parse_args()

    results_dir = resolve(args.results_dir)
    summary = pd.read_csv(results_dir / "ringkasan_a_b.csv", encoding="utf-8-sig")
    per_query = pd.read_csv(results_dir / "perbandingan_a_b.csv", encoding="utf-8-sig")

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
            "axes.titlesize": 12,
            "axes.labelsize": 10,
        }
    )

    # Figur 1: metrik agregat
    labels = ["P@5", "R@5", "F1@5", "MAP", "nDCG@5"]
    x = range(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    ax.bar([i - width / 2 for i in x], summary["versi_a"], width, label="Versi A (baseline)", color="#1f4e79")
    ax.bar([i + width / 2 for i in x], summary["versi_b"], width, label="Versi B (+ query expansion)", color="#c55a11")
    for i, (a, b) in enumerate(zip(summary["versi_a"], summary["versi_b"])):
        ax.text(i - width / 2, a + 0.012, f"{a:.3f}", ha="center", va="bottom", fontsize=8)
        ax.text(i + width / 2, b + 0.012, f"{b:.3f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(list(x), labels)
    ax.set_ylim(0, 1.06)
    ax.set_ylabel("Skor")
    ax.set_title("Perbandingan Metrik Agregat: Baseline vs Query Expansion")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    fig.tight_layout()
    fig.savefig(results_dir / "fig_metrik_agregat.png", dpi=args.dpi, bbox_inches="tight")
    plt.close(fig)

    # Figur 2: AP per query
    fig, ax = plt.subplots(figsize=(5.8, 5.6))
    ax.scatter(per_query["AP_A"], per_query["AP_B"], s=42, alpha=0.8, color="#2f5597", edgecolor="white", linewidth=0.6)
    ax.plot([0, 1], [0, 1], linestyle="--", color="#7f7f7f", linewidth=1)
    ax.set_xlim(-0.02, 1.04)
    ax.set_ylim(-0.02, 1.04)
    ax.set_aspect("equal")
    ax.set_xlabel("AP Versi A (baseline)")
    ax.set_ylabel("AP Versi B (+ query expansion)")
    ax.set_title("AP per Query: Baseline vs Query Expansion")
    ax.grid(alpha=0.2)
    for label in ["Q03", "Q07", "Q20", "Q25"]:
        row = per_query[per_query["query_id"] == label]
        if not row.empty:
            ax.annotate(
                label,
                (float(row["AP_A"].iloc[0]), float(row["AP_B"].iloc[0])),
                textcoords="offset points",
                xytext=(6, -10),
                fontsize=8,
                color="#333333",
            )
    fig.tight_layout()
    fig.savefig(results_dir / "fig_perbandingan_ap.png", dpi=args.dpi)
    plt.close(fig)

    print(f"Figur disimpan di {results_dir}")


if __name__ == "__main__":
    main()
