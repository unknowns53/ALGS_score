"""Rule-level tests straight out of 仕様書.md > Tests > Rule tests."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from config import PLACEMENT_POINTS, SimulationConfig
from match_sim import simulate_match
from teams import generate_teams, teams_to_arrays
from tournament_sim import simulate_tournament


def _base_config(**kwargs) -> SimulationConfig:
    cfg = SimulationConfig(starting_points_mode="none")
    if kwargs:
        cfg = replace(cfg, **kwargs)
    return cfg


def test_1_placement_points_table():
    assert PLACEMENT_POINTS == (
        12, 9, 7, 5, 4, 3, 3, 2, 2, 2, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0,
    )
    assert len(PLACEMENT_POINTS) == 20


def test_2_kill_points_added_correctly():
    cfg = _base_config()
    rng = np.random.default_rng(7)
    teams = generate_teams(cfg, rng)
    arrs = teams_to_arrays(teams)
    cumulative = np.zeros(cfg.num_teams, dtype=int)
    for m in range(1, 6):
        result = simulate_match(arrs, cumulative, m, cfg, rng)
        assert np.array_equal(
            result.team_scores, result.placement_points + result.team_kills
        )
        cumulative = cumulative + result.team_scores


def test_3_eligibility_evaluated_at_match_start():
    """Everyone at threshold-1; nobody is eligible at match start so the
    tournament should NOT end inside the first match even though someone
    crosses 50 mid-match."""
    cfg = _base_config(
        starting_points_mode="custom",
        custom_starting_points=tuple([49] * 20),
        max_matches=1,
    )
    for seed in range(20):
        rng = np.random.default_rng(seed)
        tr = simulate_tournament(cfg, rng)
        assert tr.ended is False
        # At least the winner picked up 12 placement points, so they are now >=50:
        assert (tr.cumulative_scores >= 50).any()


def test_4_reach_50_in_same_match_does_not_end():
    """No team starts at >=50, so even after that match someone crosses 50,
    the tournament must continue beyond match 1."""
    cfg = _base_config(
        starting_points_mode="custom",
        custom_starting_points=tuple([49] * 20),
        max_matches=1,
    )
    for seed in range(20):
        rng = np.random.default_rng(seed)
        tr = simulate_tournament(cfg, rng)
        assert tr.ended is False, "tournament must not end if no team starts at >=50"


def test_5_start_with_50_and_win_ends_tournament():
    """If every team starts at >=50, whoever wins match 1 ends the tournament."""
    cfg = _base_config(
        starting_points_mode="custom",
        custom_starting_points=tuple([50] * 20),
        max_matches=5,
    )
    for seed in range(10):
        rng = np.random.default_rng(seed)
        tr = simulate_tournament(cfg, rng)
        assert tr.ended is True
        assert tr.ending_match == 1


def test_6_death_events_invariant():
    cfg = _base_config()
    rng = np.random.default_rng(11)
    teams = generate_teams(cfg, rng)
    arrs = teams_to_arrays(teams)
    cumulative = np.zeros(cfg.num_teams, dtype=int)
    for m in range(1, 101):
        r = simulate_match(arrs, cumulative, m, cfg, rng)
        expected = (
            cfg.num_teams * cfg.players_per_team
            + r.respawned_players
            - r.champion_remaining_players
        )
        assert r.death_events == expected
        cumulative = cumulative + r.team_scores


def test_7_kill_accounting_invariant():
    cfg = _base_config()
    rng = np.random.default_rng(13)
    teams = generate_teams(cfg, rng)
    arrs = teams_to_arrays(teams)
    cumulative = np.zeros(cfg.num_teams, dtype=int)
    for m in range(1, 101):
        r = simulate_match(arrs, cumulative, m, cfg, rng)
        assert r.scored_kills + r.neutral_deaths + r.lost_kill_points == r.death_events
        # team_kills sum to scored_kills (multinomial conservation)
        assert int(r.team_kills.sum()) == r.scored_kills
        cumulative = cumulative + r.team_scores


def test_9_total_knocks_invariant():
    """total_knocks must equal (death_events - neutral_deaths) + revived_knocks."""
    cfg = _base_config()
    rng = np.random.default_rng(41)
    teams = generate_teams(cfg, rng)
    arrs = teams_to_arrays(teams)
    cumulative = np.zeros(cfg.num_teams, dtype=int)
    for m in range(1, 101):
        r = simulate_match(arrs, cumulative, m, cfg, rng)
        expected = max(0, r.death_events - r.neutral_deaths) + r.revived_knocks
        assert r.total_knocks == expected
        cumulative = cumulative + r.team_scores


def test_10_transferred_kills_remove_placement_bias():
    """With transfer_kill_rate=1 every scored kill goes through the steal
    distribution, which ignores placement_kill_factor. With identical team
    fight_skill (strength_sigma=0), first-place and last-place teams should
    therefore receive roughly equal kill shares.
    """
    cfg = _base_config(
        strength_sigma=0.0,
        transfer_kill_rate=1.0,
        mp_pressure_enabled=False,
        chaos_multiplier=1.0,
    )
    rng = np.random.default_rng(31)
    teams = generate_teams(cfg, rng)
    arrs = teams_to_arrays(teams)
    cumulative = np.zeros(cfg.num_teams, dtype=int)
    first_kills = last_kills = total = 0
    for m in range(1, 401):
        r = simulate_match(arrs, cumulative, m, cfg, rng)
        first_tid = int(r.placements[0])
        last_tid = int(r.placements[-1])
        first_kills += int(r.team_kills[first_tid])
        last_kills += int(r.team_kills[last_tid])
        total += int(r.scored_kills)
        cumulative = cumulative + r.team_scores

    first_share = first_kills / total
    last_share = last_kills / total
    # Without placement bias, both should be near 1/20 = 0.05.
    assert abs(first_share - last_share) < 0.03, (
        f"transfer_kill_rate=1 should erase placement bias: "
        f"first={first_share:.4f}, last={last_share:.4f}"
    )


def test_8_revived_knocks_independent_of_kills():
    """Multiplying revive_knock_mean by 5x must not change death_events or scored_kills
    on average."""
    cfg_low = _base_config(revive_knock_mean=2.0)
    cfg_high = _base_config(revive_knock_mean=25.0)

    def collect(cfg, seed):
        rng = np.random.default_rng(seed)
        teams = generate_teams(cfg, rng)
        arrs = teams_to_arrays(teams)
        cumulative = np.zeros(cfg.num_teams, dtype=int)
        de = []
        sk = []
        rk = []
        for m in range(1, 201):
            r = simulate_match(arrs, cumulative, m, cfg, rng)
            de.append(r.death_events)
            sk.append(r.scored_kills)
            rk.append(r.revived_knocks)
            cumulative = cumulative + r.team_scores
        return np.array(de), np.array(sk), np.array(rk)

    de_lo, sk_lo, rk_lo = collect(cfg_low, 21)
    de_hi, sk_hi, rk_hi = collect(cfg_high, 21)

    # Same seed + same team draws + identical match sequence should give
    # identical death_events / scored_kills because revive sampling happens
    # AFTER kill accounting in the RNG stream.
    # ... but revive sampling consumes RNG calls and changes downstream draws,
    # so allow a small statistical tolerance.
    assert abs(de_lo.mean() - de_hi.mean()) < 1.5, (
        f"mean death_events drifted: low={de_lo.mean():.2f} high={de_hi.mean():.2f}"
    )
    assert abs(sk_lo.mean() - sk_hi.mean()) < 1.5, (
        f"mean scored_kills drifted: low={sk_lo.mean():.2f} high={sk_hi.mean():.2f}"
    )
    # Revived knocks themselves should clearly differ
    assert rk_hi.mean() > rk_lo.mean() + 5
