"""Format-level comparison metrics for cross-format fairness analysis.

Aggregates a list of FormatResult into a FormatMetrics dataclass that
captures fairness (does the strongest team win?), unpredictability
(upset rate), tournament length, and dramatic tension (how many teams
could still win on the final match).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr  # type: ignore

from formats.base import FormatResult
from teams import composite_strength


# Maximum points a single team can plausibly score in one Apex match:
#   12 placement points (1st) + ~10 kills (top of empirical distribution).
# Used by drama_score to decide which teams could still catch the leader.
MAX_SINGLE_MATCH_GAIN: int = 22


@dataclass
class FormatMetrics:
    """All comparison metrics for one tournament format."""

    format_name: str
    n_sims: int
    pool_size: int = 20

    # Fairness
    seed1_win_rate: float = 0.0
    top3_podium_rate: float = 0.0           # any of seed 1-3 on the podium
    top5_win_rate: float = 0.0              # seed 1-5 wins
    upset_rate: float = 0.0                 # champion seed >= bottom-half cutoff
    upset_threshold: int = 11               # seed at/above which counts as upset

    # Length
    mean_matches: float = 0.0
    median_matches: float = 0.0
    p95_matches: float = 0.0

    # Drama
    mean_drama_score: float = 0.0           # teams still in contention at last match
    median_lead_changes: float = 0.0        # cumulative-leader swaps during tournament

    # Strength vs result correlation
    mean_spearman: float = 0.0              # mean Spearman over sims (composite vs final rank)

    # Per-seed win distribution: dict[seed -> win_rate]. Keys are str for JSON.
    seed_win_rate: dict[int, float] = field(default_factory=dict)


@dataclass
class FormatComparisonResult:
    """Side-by-side metrics for every format compared in one run."""

    region_profile: str
    n_sims_per_format: dict[str, int]
    metrics: dict[str, FormatMetrics] = field(default_factory=dict)


def _finish_ranks(result: FormatResult) -> np.ndarray:
    """Return rank (1=best) per team_id.

    Uses extras['finish_order'] when the format provides one (Fixed / Swiss
    / RoundRobin / DE); falls back to cumulative-score descending for MP.
    """
    n = len(result.teams)
    ranks = np.empty(n, dtype=int)
    finish_order = result.extras.get("finish_order")
    if finish_order is not None:
        for rank, tid in enumerate(finish_order):
            ranks[int(tid)] = rank + 1
        # Sanity: every team_id should appear once.
        return ranks
    # MP: champion in front, then the rest by cumulative descending.
    cum = result.cumulative_scores
    if result.champion_team_id is None:
        order = np.argsort(-cum, kind="stable")
    else:
        rest = [t for t in range(n) if t != result.champion_team_id]
        rest.sort(key=lambda t: (-int(cum[t]), int(t)))
        order = np.array([result.champion_team_id] + rest, dtype=int)
    for rank, tid in enumerate(order):
        ranks[int(tid)] = rank + 1
    return ranks


def _drama_score(result: FormatResult) -> int:
    """Teams still able to catch the leader before the final match.

    Uses cumulative-before-the-last-match and a fixed MAX_SINGLE_MATCH_GAIN
    of 22 (12 placement + ~10 kills). A team is "in contention" if its
    pre-final cumulative is within MAX_SINGLE_MATCH_GAIN of the leader.
    Always includes the leader themselves (count >= 1).
    """
    if not result.match_results:
        return 0
    cum_before = result.cumulative_scores - result.match_results[-1].team_scores
    top = int(cum_before.max())
    contenders = int((cum_before >= top - MAX_SINGLE_MATCH_GAIN).sum())
    return max(1, contenders)


def _lead_changes(result: FormatResult) -> int:
    lh = result.leader_history
    if lh.size < 2:
        return 0
    return int((lh[1:] != lh[:-1]).sum())


def _per_result_spearman(result: FormatResult) -> float:
    """Spearman correlation between composite strength and final rank.

    Negative value means stronger teams finish better (as we want for
    fairness, since rank=1 is best). We flip the sign so positive ==
    fairness, matching the intuition "higher is fairer".
    """
    composite = np.array([composite_strength(t) for t in result.teams])
    ranks = _finish_ranks(result).astype(float)
    if composite.std() == 0 or ranks.std() == 0:
        return 0.0
    rho, _ = spearmanr(composite, ranks)
    if np.isnan(rho):
        return 0.0
    return float(-rho)  # flip so positive = strong teams finish high


def compute_format_metrics(
    results: list[FormatResult],
    format_name: str | None = None,
    pool_size: int | None = None,
) -> FormatMetrics:
    """Aggregate one format's simulation list into a FormatMetrics record.

    Upset threshold is the bottom-half of the pool: for a 20-team format
    that's seed >= 11, for a 30-team format that's seed >= 16. This keeps
    "upset rate" comparable across pool sizes (always the probability that
    the weaker half wins).
    """
    if not results:
        raise ValueError("compute_format_metrics requires at least one result")

    name = format_name or results[0].format_name
    n = len(results)

    if pool_size is None:
        pool_size = len(results[0].teams)
    upset_threshold = pool_size // 2 + 1  # bottom-half seed cutoff

    champion_seeds = np.array([r.champion_seed for r in results], dtype=int)
    seed1 = float((champion_seeds == 1).mean())
    top5 = float((champion_seeds <= 5).mean())
    upset = float((champion_seeds >= upset_threshold).mean())

    # Podium: top-3 finishers per result. Use _finish_ranks for consistency.
    podium_hits = 0
    for r in results:
        ranks = _finish_ranks(r)
        podium_ids = np.where(ranks <= 3)[0]
        seeds = {int(r.teams[tid].seed) for tid in podium_ids}
        if seeds & {1, 2, 3}:
            podium_hits += 1
    top3_podium = podium_hits / n

    matches = np.array([r.ending_match for r in results], dtype=int)
    mean_matches = float(matches.mean())
    median_matches = float(np.median(matches))
    p95_matches = float(np.percentile(matches, 95))

    drama_arr = np.array([_drama_score(r) for r in results], dtype=int)
    mean_drama = float(drama_arr.mean())

    lead_changes_arr = np.array([_lead_changes(r) for r in results], dtype=int)
    median_lc = float(np.median(lead_changes_arr))

    spearman_arr = np.array([_per_result_spearman(r) for r in results], dtype=float)
    mean_spearman = float(spearman_arr.mean())

    seed_counter = np.zeros(pool_size + 1, dtype=int)  # 1-indexed
    for cs in champion_seeds:
        if 1 <= int(cs) <= pool_size:
            seed_counter[int(cs)] += 1
    seed_win_rate = {s: float(seed_counter[s] / n) for s in range(1, pool_size + 1)}

    return FormatMetrics(
        format_name=name,
        n_sims=n,
        pool_size=int(pool_size),
        seed1_win_rate=seed1,
        top3_podium_rate=float(top3_podium),
        top5_win_rate=top5,
        upset_rate=upset,
        upset_threshold=int(upset_threshold),
        mean_matches=mean_matches,
        median_matches=median_matches,
        p95_matches=p95_matches,
        mean_drama_score=mean_drama,
        median_lead_changes=median_lc,
        mean_spearman=mean_spearman,
        seed_win_rate=seed_win_rate,
    )


def comparison_to_json(comp: FormatComparisonResult, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "region_profile": comp.region_profile,
        "n_sims_per_format": comp.n_sims_per_format,
        "metrics": {
            name: {**asdict(m), "seed_win_rate": {str(k): v for k, v in m.seed_win_rate.items()}}
            for name, m in comp.metrics.items()
        },
    }
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def comparison_to_csv(comp: FormatComparisonResult, path: str | Path) -> None:
    """Wide CSV: one row per format, columns are the headline metrics."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    cols = [
        "format", "n_sims",
        "seed1_win_rate", "top3_podium_rate", "top5_win_rate", "upset_rate",
        "mean_matches", "median_matches", "p95_matches",
        "mean_drama_score", "median_lead_changes", "mean_spearman",
    ]
    lines = [",".join(cols)]
    for name, m in comp.metrics.items():
        row = [
            name, str(m.n_sims),
            f"{m.seed1_win_rate:.4f}", f"{m.top3_podium_rate:.4f}",
            f"{m.top5_win_rate:.4f}", f"{m.upset_rate:.4f}",
            f"{m.mean_matches:.3f}", f"{m.median_matches:.1f}", f"{m.p95_matches:.1f}",
            f"{m.mean_drama_score:.3f}", f"{m.median_lead_changes:.1f}",
            f"{m.mean_spearman:+.4f}",
        ]
        lines.append(",".join(row))
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def format_comparison_text(comp: FormatComparisonResult) -> str:
    """Human-readable comparison table."""
    lines = []
    lines.append("ALGS Tournament Format Comparison")
    lines.append("=" * 60)
    lines.append(f"Region profile: {comp.region_profile}")
    lines.append("")
    header = (
        f"{'format':<14} {'sims':>6} "
        f"{'seed1%':>7} {'top5%':>7} {'upset%':>7} "
        f"{'avgM':>6} {'drama':>6} {'lc':>4} {'rho':>7}"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for name, m in comp.metrics.items():
        lines.append(
            f"{name:<14} {m.n_sims:>6} "
            f"{m.seed1_win_rate*100:>6.2f}% "
            f"{m.top5_win_rate*100:>6.2f}% "
            f"{m.upset_rate*100:>6.2f}% "
            f"{m.mean_matches:>6.2f} "
            f"{m.mean_drama_score:>6.2f} "
            f"{int(m.median_lead_changes):>4} "
            f"{m.mean_spearman:>+6.3f}"
        )
    lines.append("")
    lines.append("Legend:")
    lines.append("  seed1%      probability the rank-1 (strongest) team wins")
    lines.append("  top5%       probability one of seeds 1-5 wins")
    lines.append("  upset%      probability bottom-half seed (>= pool_size/2 + 1) wins")
    lines.append("  avgM        mean total matches played")
    lines.append("  drama       mean number of teams still in contention on last match")
    lines.append("  lc          median cumulative-leader changes")
    lines.append("  rho         mean Spearman(composite strength, finish rank) - higher = fairer")
    return "\n".join(lines)
