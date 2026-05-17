"""Tests for the format-comparison subsystem (Phase 6 acceptance).

Six checks per the implementation plan:
  1. Lobby split conservation
  2. Score conservation per round
  3. Pair-balance variance bound (RoundRobin)
  4. DE bracket flow (team-set integrity)
  5. Spearman sanity at strength_sigma=0
  6. Reproducibility across formats with fixed seed
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from config import SimulationConfig, apply_region_profile
from formats import (
    DoubleEliminationFormat,
    FixedMatchesFormat,
    MatchPointFormat,
    RoundRobinFormat,
    SwissFormat,
)
from formats.lobby_assignment import (
    pair_balanced_split,
    split_by_score,
    update_pair_history,
)
from formats.runner import run_format_simulations
from format_comparison import compute_format_metrics


def _apac_cfg(**overrides) -> SimulationConfig:
    cfg = apply_region_profile(SimulationConfig(), "apac_n")
    if overrides:
        cfg = replace(cfg, **overrides)
    return cfg


def test_1_lobby_split_conservation():
    """Both lobby strategies must partition the team pool exactly."""
    team_ids = np.arange(30, dtype=int)
    rng = np.random.default_rng(7)
    cumulative = rng.integers(0, 80, size=30)

    score_lobbies = split_by_score(team_ids, cumulative, lobby_size=10)
    union = sorted(t for lobby in score_lobbies for t in lobby)
    assert union == sorted(team_ids.tolist())
    assert len(score_lobbies) == 3
    for lobby in score_lobbies:
        assert len(lobby) == 10

    pair_hist = np.zeros((30, 30), dtype=int)
    rr_lobbies = pair_balanced_split(team_ids, pair_hist, rng, n_lobbies=3)
    union2 = sorted(t for lobby in rr_lobbies for t in lobby)
    assert union2 == sorted(team_ids.tolist())
    assert all(len(lobby) == 10 for lobby in rr_lobbies)


def test_2_score_conservation_swiss_and_round_robin():
    """Sum of all match team_scores equals the final cumulative for both formats."""
    cfg = _apac_cfg()
    for fmt in (SwissFormat(), RoundRobinFormat()):
        rng = np.random.default_rng(11)
        res = fmt.simulate(cfg, rng)
        match_sum = sum(int(mr.team_scores.sum()) for mr in res.match_results)
        cum_sum = int(res.cumulative_scores.sum())
        assert match_sum == cum_sum, f"{fmt.name}: sum mismatch {match_sum} vs {cum_sum}"
        # Each lobby contributes one match's worth of placement points
        # (sum of PLACEMENT_POINTS[0:10] = 12+9+7+5+4+3+3+2+2+2 = 49) plus kills.
        # Per-match lobby score is >= 49, so per-tournament >= 49 * n_matches.
        assert match_sum >= 49 * res.ending_match


def test_3_round_robin_pair_balance():
    """After 6 rounds the pair_history std must be small relative to the mean."""
    cfg = _apac_cfg()
    rng = np.random.default_rng(13)
    res = RoundRobinFormat().simulate(cfg, rng)
    mean = res.extras["pair_history_mean"]
    std = res.extras["pair_history_std"]
    # Mean co-lobby count across pairs should be 6*3*C(10,2)/C(30,2)
    # = 6*3*45/435 = 810/435 ~= 1.86.
    assert 1.5 < mean < 2.2, f"mean co-lobby count out of range: {mean}"
    # Greedy assignment won't be perfect but std should stay under ~1.2.
    assert std < 1.2, f"pair_history std too high: {std}"


def test_4_de_bracket_team_set_integrity():
    """WB, LB, and GF team sets must respect the 30-team pool and have no overlap
    where the spec forbids it."""
    cfg = _apac_cfg()
    for seed in range(5):
        rng = np.random.default_rng(seed)
        res = DoubleEliminationFormat().simulate(cfg, rng)
        wb = set(res.extras["wb_team_ids"])
        lb = set(res.extras["lb_team_ids"])
        gf = set(res.extras["gf_team_ids"])
        # WB is seeds 1-20 (exactly 20 teams).
        assert len(wb) == 20
        # LB is WB-bottom-10 (10 teams) + seeds 21-30 (10 teams) = 20.
        assert len(lb) == 20
        # GF is 20 teams from WB-top-10 + LB-top-10.
        assert len(gf) == 20
        # All ids inside the 30-team pool.
        assert wb.issubset(range(30))
        assert lb.issubset(range(30))
        assert gf.issubset(range(30))
        # WB and LB-initial-10 (seeds 21-30) must not overlap; the 10 LB teams
        # from WB-bottom must be a subset of WB.
        initial_lb = lb - wb
        assert len(initial_lb) == 10
        # Champion is one of the GF teams.
        assert res.champion_team_id in gf


def test_5_spearman_zero_at_equal_strength():
    """With strength_sigma=0 all teams are identical; Spearman correlation
    between composite strength and finish rank should be ~0."""
    cfg = _apac_cfg(strength_sigma=0.0)
    rng = np.random.default_rng(17)
    results = [FixedMatchesFormat(n_matches=6).simulate(cfg, rng) for _ in range(200)]
    metrics = compute_format_metrics(results, format_name="fixed_6", pool_size=20)
    # The strongest team is essentially random; |rho| should be small.
    assert abs(metrics.mean_spearman) < 0.10, (
        f"Spearman not near zero: {metrics.mean_spearman}"
    )


def test_6_reproducibility_across_formats():
    """Same (format, cfg, n_sims, seed, workers) must reproduce results bit-for-bit."""
    cfg = _apac_cfg()
    cases = [
        MatchPointFormat(),
        FixedMatchesFormat(n_matches=6),
        SwissFormat(),
        DoubleEliminationFormat(),
    ]
    for fmt in cases:
        a = run_format_simulations(fmt, cfg, 100, seed=42, workers=1)
        b = run_format_simulations(fmt, cfg, 100, seed=42, workers=1)
        seeds_a = [r.champion_seed for r in a]
        seeds_b = [r.champion_seed for r in b]
        assert seeds_a == seeds_b, (
            f"{fmt.name} not reproducible: champion seed mismatch"
        )


def test_7_pair_history_helper():
    """update_pair_history must add exactly C(lobby_size, 2) increments per lobby."""
    pair_hist = np.zeros((10, 10), dtype=int)
    lobbies = [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]
    update_pair_history(pair_hist, lobbies)
    # Within lobby 1: 5 teams -> C(5,2) = 10 pairs -> 20 increments (symmetric).
    assert int(pair_hist.sum()) == 2 * (10 + 10)
    assert pair_hist[0, 1] == 1
    assert pair_hist[1, 0] == 1
    assert pair_hist[0, 5] == 0
