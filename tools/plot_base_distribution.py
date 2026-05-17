"""Render the equal-strength baseline ending-match distribution as a single PNG.

Companion to tools/plot_equal_sweep.py (which produces overlay sweeps).
This one shows the standalone baseline as a bar chart, annotated with
mean, median, and tail probabilities so it can be dropped into the
article as the "what does the baseline look like" figure.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams

rcParams["font.family"] = "Arial"
rcParams["axes.unicode_minus"] = False

OUT = Path(__file__).resolve().parent.parent / "out"


def main() -> int:
    with (OUT / "sweep_equal_base.json").open("r", encoding="utf-8") as f:
        data = json.load(f)

    dist = data["ending_match_distribution"]
    matches = sorted(int(k) for k in dist.keys())
    probs = [dist[str(m)] * 100 for m in matches]

    mean = data["mean"]
    median = data["median"]
    p_gt_10 = data["prob_exceeds_10"] * 100
    p_gt_12 = data["prob_exceeds_12"] * 100

    fig, ax = plt.subplots(figsize=(9.0, 5.0), dpi=160)
    bars = ax.bar(matches, probs, color="#1D4ED8", edgecolor="white",
                  linewidth=0.6, alpha=0.92, zorder=2)

    # Highlight the long-tail bars (>10 matches) in a warmer color so the
    # P(>10) / P(>12) annotations have a visual anchor.
    for bar, m in zip(bars, matches):
        if m > 10:
            bar.set_color("#DC2626")
            bar.set_alpha(0.85)

    # Mean reference line, with the label placed above the chart's tallest
    # bar so it never collides with per-bar percentage annotations.
    ax.axvline(mean, color="#111827", linestyle="--", linewidth=1.4, zorder=3)
    ymax = max(probs)
    ax.text(mean + 0.18, ymax * 1.08, f"mean = {mean:.2f}",
            fontsize=10, color="#111827", weight="bold")

    ax.set_xlabel("Ending match")
    ax.set_ylabel("Probability (%)")
    ax.set_title(
        "Baseline ending-match distribution "
        "(equal-strength lobby, strength_sigma=0.05, 10000 sims)"
    )
    ax.set_xticks(matches)
    ax.set_ylim(0, ymax * 1.18)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4, zorder=1)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Tail annotation box.
    text = (f"P(> 10 matches) = {p_gt_10:.1f}%\n"
            f"P(> 12 matches) = {p_gt_12:.1f}%")
    ax.text(0.98, 0.96, text, transform=ax.transAxes,
            ha="right", va="top", fontsize=10,
            bbox=dict(facecolor="white", edgecolor="#D1D5DB",
                      boxstyle="round,pad=0.4"))

    # Per-bar probability label (only on bars with prob >= 5%, to keep
    # the chart from being noisy at the tails).
    for bar, p in zip(bars, probs):
        if p >= 5.0:
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + ymax * 0.015,
                    f"{p:.1f}%", ha="center", va="bottom",
                    fontsize=8.5, color="#1F2937")

    fig.tight_layout()
    out_path = OUT / "plot_equal_sweep_base.png"
    fig.savefig(out_path, facecolor="white")
    plt.close(fig)
    print(f"wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
