"""Ad-hoc: per-placement mean kills under different placement_kill_sharpness.

Question we are answering: "how does the kill distribution change as we
move PKF sharpness from flat (0.0) to extreme top-heavy (2.0)?"

Approach: for each sharpness value, run a fixed-config Match Point
tournament many times and collect (placement, team_kills) pairs from
every match. Bucket by placement (1..20), average kills.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams

from config import SimulationConfig
from match_sim import simulate_match
from teams import generate_teams, teams_to_arrays

rcParams["font.family"] = "Arial"
rcParams["axes.unicode_minus"] = False

OUT_DIR = Path(__file__).resolve().parents[1] / "out"

# We sweep sharpness across the same 5 levels as the article.
SHARPNESS_LEVELS = [0.0, 0.5, 1.0, 1.5, 2.0]

N_TOURNAMENTS = 1500     # repeats per sharpness
MATCHES_PER_TOURNAMENT = 9  # close to baseline mean ending match


def collect_placement_kills(sharpness: float, n_tournaments: int,
                            matches_per_tournament: int,
                            seed: int = 42) -> np.ndarray:
    """Return mean kills per placement (length 20)."""
    cfg = SimulationConfig(
        starting_points_mode="none",
        strength_sigma=0.05,
        placement_kill_sharpness=sharpness,
    )
    rng = np.random.default_rng(seed)

    bucket_sum = np.zeros(20, dtype=np.float64)
    bucket_n = np.zeros(20, dtype=np.int64)

    for _ in range(n_tournaments):
        teams = generate_teams(cfg, rng)
        arrs = teams_to_arrays(teams)
        cumulative = np.zeros(cfg.num_teams, dtype=int)
        for m in range(1, matches_per_tournament + 1):
            r = simulate_match(arrs, cumulative, m, cfg, rng)
            # placements is team_id ordered 1st..last
            for rank, tid in enumerate(r.placements):
                bucket_sum[rank] += r.team_kills[tid]
                bucket_n[rank] += 1
            cumulative = cumulative + r.team_scores

    return bucket_sum / np.maximum(bucket_n, 1)


def main() -> int:
    results: dict[float, np.ndarray] = {}
    print(f"Sampling {N_TOURNAMENTS} tournaments x {MATCHES_PER_TOURNAMENT} "
          f"matches per sharpness level...")
    for s in SHARPNESS_LEVELS:
        mean_kills = collect_placement_kills(
            s, N_TOURNAMENTS, MATCHES_PER_TOURNAMENT
        )
        results[s] = mean_kills
        # Print a compact table to stdout
        head = f"sharpness={s:.1f}: total={mean_kills.sum():.2f}"
        per = ", ".join(f"{v:.2f}" for v in mean_kills[[0, 4, 9, 14, 19]])
        print(f"  {head} | 1st/5th/10th/15th/20th = [{per}]")
        print(f"    full 20-vector: {mean_kills.round(2)}")

    # Plot
    fig, ax = plt.subplots(figsize=(9.5, 5.5), dpi=140)
    colors = ["#1D4ED8", "#0891B2", "#059669", "#D97706", "#DC2626"]
    placements = np.arange(1, 21)
    for s, color in zip(SHARPNESS_LEVELS, colors):
        mean_kills = results[s]
        label = f"sharpness={s:.1f}"
        if s == 1.0:
            label += " [base]"
            lw, ms = 2.6, 7.0
        else:
            lw, ms = 1.6, 5.0
        ax.plot(placements, mean_kills, marker="o", markersize=ms,
                linewidth=lw, color=color, label=label, alpha=0.95)

    ax.set_xlabel("Placement (1 = 1st, 20 = 20th)")
    ax.set_ylabel("Mean scored kills per match")
    ax.set_title(
        "Per-placement mean kills under placement_kill_sharpness sweep "
        "(equal-strength lobby)"
    )
    ax.set_xticks(placements)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.legend(frameon=False, fontsize=10, loc="upper right")
    ax.set_ylim(bottom=0)
    fig.tight_layout()

    out_path = OUT_DIR / "plot_pkf_per_placement_kills.png"
    fig.savefig(out_path, facecolor="white")
    plt.close(fig)
    print(f"\nwrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
