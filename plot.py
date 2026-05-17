"""Matplotlib plot of the tournament-length distribution."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for batch saving
import matplotlib.pyplot as plt
import numpy as np
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


# ----- Format comparison plots ---------------------------------------------

def plot_format_comparison_bars(
    comparison,  # FormatComparisonResult — typed loosely to avoid hard dep
    output_path: str | Path,
) -> None:
    """Grouped bar chart of headline fairness / length / drama metrics."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    metrics = comparison.metrics
    names = list(metrics.keys())
    if not names:
        raise ValueError("comparison has no metrics to plot")

    # 6 panels: seed1, top5, upset, avgM, drama, spearman.
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), dpi=140)

    def _bar(ax, values, ylabel, title, color, percent=False):
        x = np.arange(len(names))
        ax.bar(x, values, width=0.7, color=color, edgecolor="#1E3A8A",
               linewidth=0.6, alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=30, ha="right", fontsize=9)
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=11)
        ax.grid(True, axis="y", linestyle=":", alpha=0.4)
        if percent:
            ax.set_ylim(0, max(values) * 1.2 + 0.01)
            for xi, v in zip(x, values):
                ax.text(xi, v + max(values) * 0.02, f"{v*100:.1f}%",
                        ha="center", fontsize=8)
        else:
            ax.set_ylim(0, max(values) * 1.18 if max(values) > 0 else 1.0)
            for xi, v in zip(x, values):
                ax.text(xi, v + max(values) * 0.02 if max(values) > 0 else 0.02,
                        f"{v:.2f}", ha="center", fontsize=8)

    _bar(axes[0, 0],
         [metrics[n].seed1_win_rate for n in names],
         "P(seed 1 wins)", "Strongest team win rate", "#2563EB", percent=True)
    _bar(axes[0, 1],
         [metrics[n].top5_win_rate for n in names],
         "P(seed 1-5 wins)", "Top-5 win rate", "#059669", percent=True)
    _bar(axes[0, 2],
         [metrics[n].upset_rate for n in names],
         "P(bottom-half seed wins)", "Upset rate", "#DC2626", percent=True)
    _bar(axes[1, 0],
         [metrics[n].mean_matches for n in names],
         "matches", "Mean tournament length", "#7C3AED")
    _bar(axes[1, 1],
         [metrics[n].mean_drama_score for n in names],
         "teams in contention", "Drama score (final match)", "#D97706")
    _bar(axes[1, 2],
         [metrics[n].mean_spearman for n in names],
         "Spearman rho (flipped)", "Strength->Finish correlation", "#0F766E")

    fig.suptitle(
        f"Format comparison ({comparison.region_profile}, "
        f"sims per format: {min(comparison.n_sims_per_format.values())}-"
        f"{max(comparison.n_sims_per_format.values())})",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path)
    plt.close(fig)


def plot_seed_win_heatmap(
    comparison,
    output_path: str | Path,
    max_seeds: int = 30,
) -> None:
    """Heatmap: rows = formats, columns = seed (1..max_seeds), cell = win rate."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    names = list(comparison.metrics.keys())
    n_fmt = len(names)
    matrix = np.zeros((n_fmt, max_seeds), dtype=float)
    for i, name in enumerate(names):
        sw = comparison.metrics[name].seed_win_rate
        for s in range(1, max_seeds + 1):
            matrix[i, s - 1] = sw.get(s, 0.0)

    fig, ax = plt.subplots(figsize=(max(8.0, 0.32 * max_seeds), 0.55 * n_fmt + 2.0),
                           dpi=140)
    im = ax.imshow(matrix, cmap="viridis", aspect="auto",
                   vmin=0, vmax=max(matrix.max(), 0.02))
    ax.set_yticks(np.arange(n_fmt))
    ax.set_yticklabels(names)
    ax.set_xticks(np.arange(max_seeds))
    ax.set_xticklabels([str(s) for s in range(1, max_seeds + 1)], fontsize=8)
    ax.set_xlabel("Seed (1 = strongest)")
    ax.set_title(f"Per-seed win rate ({comparison.region_profile})")
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Win rate")
    # Annotate cells with their values (only if matrix small enough).
    if max_seeds <= 32:
        for i in range(n_fmt):
            for j in range(max_seeds):
                if matrix[i, j] >= 0.01:
                    ax.text(j, i, f"{matrix[i, j]*100:.0f}",
                            ha="center", va="center", color="white", fontsize=7)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_drama_and_length(
    comparison,
    output_path: str | Path,
) -> None:
    """Side-by-side: drama score bar + matches-played bar with p95 whiskers."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    names = list(comparison.metrics.keys())
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=140)

    drama = [comparison.metrics[n].mean_drama_score for n in names]
    ax1.bar(np.arange(len(names)), drama, color="#D97706",
            edgecolor="#92400E", alpha=0.85)
    ax1.set_xticks(np.arange(len(names)))
    ax1.set_xticklabels(names, rotation=30, ha="right", fontsize=9)
    ax1.set_ylabel("Teams in contention (last match)")
    ax1.set_title("Drama score by format")
    ax1.grid(True, axis="y", linestyle=":", alpha=0.4)
    for i, v in enumerate(drama):
        ax1.text(i, v + max(drama) * 0.02, f"{v:.2f}", ha="center", fontsize=8)

    avg = [comparison.metrics[n].mean_matches for n in names]
    p95 = [comparison.metrics[n].p95_matches for n in names]
    median = [comparison.metrics[n].median_matches for n in names]
    x = np.arange(len(names))
    ax2.bar(x, avg, color="#7C3AED", edgecolor="#5B21B6", alpha=0.85,
            label="mean")
    for i, (m, p) in enumerate(zip(median, p95)):
        ax2.plot([i, i], [m, p], color="#1F2937", linewidth=1.6)
        ax2.plot(i, p, marker="_", markersize=14, color="#1F2937")
        ax2.plot(i, m, marker="o", markersize=5, color="#FBBF24",
                 markeredgecolor="#1F2937", linewidth=0)
    ax2.set_xticks(x)
    ax2.set_xticklabels(names, rotation=30, ha="right", fontsize=9)
    ax2.set_ylabel("Matches played")
    ax2.set_title("Tournament length (mean bar, median dot, p95 cap)")
    ax2.grid(True, axis="y", linestyle=":", alpha=0.4)

    fig.suptitle(f"Drama and length ({comparison.region_profile})", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path)
    plt.close(fig)
