"""Matplotlib plot of the tournament-length distribution."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for batch saving
import matplotlib.pyplot as plt
from matplotlib import rcParams

from stats import SummaryResult

# Force Arial for axis labels / titles regardless of OS defaults.
rcParams["font.family"] = "Arial"
rcParams["axes.unicode_minus"] = False


def plot_ending_match_distribution(
    summary: SummaryResult,
    output_path: str | Path,
    title_suffix: str = "",
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    matches = sorted(summary.ending_match_distribution.keys())
    probs = [summary.ending_match_distribution[m] for m in matches]
    cums = [summary.cumulative_distribution[m] for m in matches]

    fig, ax1 = plt.subplots(figsize=(8.5, 5.0), dpi=140)
    ax1.bar(matches, probs, width=0.85, color="#2563EB", alpha=0.85,
            edgecolor="#1E3A8A", linewidth=0.6, label="P(end at n)")
    ax1.set_xlabel("Ending match")
    ax1.set_ylabel("Probability")
    ax1.set_xticks(matches)
    ax1.set_ylim(0, max(probs) * 1.18 if probs else 1.0)
    ax1.grid(True, axis="y", linestyle=":", alpha=0.4)

    ax1.axvline(summary.mean, color="#DC2626", linestyle="--", linewidth=1.5,
                label=f"mean = {summary.mean:.2f}")
    ax1.axvline(summary.median, color="#059669", linestyle=":", linewidth=1.5,
                label=f"median = {summary.median:.1f}")

    ax2 = ax1.twinx()
    ax2.plot(matches, cums, color="#111827", linewidth=1.4, marker="o",
             markersize=3.5, label="cumulative")
    ax2.set_ylabel("Cumulative probability")
    ax2.set_ylim(0, 1.02)

    region = summary.region_profile
    title = f"ALGS Match Point tournament length ({region}, n={summary.n_sims})"
    if title_suffix:
        title = f"{title} - {title_suffix}"
    ax1.set_title(title)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper right", frameon=False, fontsize=9)

    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_region_comparison(
    summaries: dict[str, SummaryResult],
    output_path: str | Path,
) -> None:
    """Overlay several regions' ending-match distributions."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    colors = ["#2563EB", "#059669", "#DC2626", "#7C3AED", "#D97706"]

    fig, ax = plt.subplots(figsize=(9.0, 5.2), dpi=140)
    for (name, summary), color in zip(summaries.items(), colors):
        matches = sorted(summary.ending_match_distribution.keys())
        probs = [summary.ending_match_distribution[m] for m in matches]
        ax.plot(matches, probs, marker="o", markersize=4, linewidth=1.4,
                color=color, label=f"{name} (mean {summary.mean:.2f})")
    ax.set_xlabel("Ending match")
    ax.set_ylabel("Probability")
    ax.set_title("Tournament length by region profile")
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
