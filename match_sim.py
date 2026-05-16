"""Single-match simulation: placement, respawn, kill accounting, kill allocation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import (
    PLACEMENT_KILL_FACTOR,
    PLACEMENT_POINTS,
    SimulationConfig,
)


@dataclass
class MatchResult:
    match_index: int
    placements: np.ndarray         # shape (num_teams,), team_id ordered 1st .. last
    winner_team_id: int
    placement_points: np.ndarray   # shape (num_teams,), per-team placement points
    team_kills: np.ndarray         # shape (num_teams,), per-team scored kill count
    team_scores: np.ndarray        # shape (num_teams,), placement + kills
    eligible_at_start: np.ndarray  # shape (num_teams,), bool
    respawned_players: int
    champion_remaining_players: int
    death_events: int
    scored_kills: int
    neutral_deaths: int
    lost_kill_points: int
    transferred_kills: int
    revived_knocks: int
    # Total knockdowns in the match, derived from the others as
    #   total_knocks = (death_events - neutral_deaths) + revived_knocks
    # Neutral deaths are not knock-derived (ring/fall/etc), so they are
    # excluded from the knock count.
    total_knocks: int


def _sample_negbin_mean_dispersion(
    mean: float, dispersion: float, rng: np.random.Generator
) -> int:
    """NegBin parameterised by (mean, dispersion=k) where var = mean + mean^2/k."""
    if dispersion <= 0:
        raise ValueError("dispersion must be positive")
    # p = k / (k + mu), n = k
    p = dispersion / (dispersion + mean)
    n = dispersion
    return int(rng.negative_binomial(n, p))


def sample_respawned_players(cfg: SimulationConfig, rng: np.random.Generator) -> int:
    if cfg.respawn_model == "poisson":
        value = int(rng.poisson(cfg.respawn_mean))
    elif cfg.respawn_model == "negbin":
        value = _sample_negbin_mean_dispersion(
            cfg.respawn_mean, cfg.respawn_dispersion, rng
        )
    else:
        raise ValueError(f"unknown respawn_model: {cfg.respawn_model}")
    return int(min(max(value, 0), cfg.max_respawned_players))


def sample_champion_remaining(cfg: SimulationConfig, rng: np.random.Generator) -> int:
    """Weighted sample of the champion squad's living-player count at match end.

    The weights tuple has one entry per value in [min, max] (inclusive). The
    default config skews heavily to the maximum (3), reflecting that ALGS
    champion squads usually finish with all three players alive.
    """
    lo = cfg.champion_remaining_min
    hi = cfg.champion_remaining_max
    values = np.arange(lo, hi + 1)
    weights = np.asarray(cfg.champion_remaining_weights, dtype=float)
    if weights.shape[0] != values.shape[0]:
        raise ValueError(
            f"champion_remaining_weights length {weights.shape[0]} does not match "
            f"range [{lo}, {hi}] ({values.shape[0]} values)"
        )
    if (weights < 0).any() or weights.sum() <= 0:
        raise ValueError("champion_remaining_weights must be non-negative and sum > 0")
    probs = weights / weights.sum()
    return int(rng.choice(values, p=probs))


def sample_death_events(respawned: int, champion_remaining: int, num_teams: int = 20,
                        players_per_team: int = 3) -> int:
    """death_events = total_players + respawned - champion_remaining."""
    total = num_teams * players_per_team
    return int(total + respawned - champion_remaining)


def sample_kill_credit(
    death_events: int,
    eligible_count: int,
    cfg: SimulationConfig,
    rng: np.random.Generator,
) -> tuple[int, int, int, int]:
    """Returns (scored_kills, neutral_deaths, lost_kill_points, transferred_kills)."""
    if death_events <= 0:
        return 0, 0, 0, 0

    neutral = int(rng.binomial(death_events, np.clip(cfg.neutral_death_rate, 0.0, 1.0)))

    mp_factor = 1.0
    if cfg.mp_pressure_enabled and eligible_count > 0:
        mp_factor = cfg.mp_pressure_lost_kill_multiplier

    lost_rate = cfg.lost_kill_rate * cfg.chaos_multiplier * mp_factor
    lost_rate = float(np.clip(lost_rate, 0.0, 1.0))

    remaining = death_events - neutral
    lost = int(rng.binomial(remaining, lost_rate)) if remaining > 0 else 0

    scored = death_events - neutral - lost
    transferred = (
        int(rng.binomial(scored, np.clip(cfg.transfer_kill_rate, 0.0, 1.0)))
        if scored > 0 else 0
    )
    return scored, neutral, lost, transferred


def sample_revived_knocks(cfg: SimulationConfig, rng: np.random.Generator) -> int:
    """Revived knocks are independent of death_events and scored_kills.

    The spec gives revive_knock_mean but no separate dispersion parameter,
    so we reuse respawn_dispersion (clamped to >=1) as a reasonable proxy
    for "how chaotic the lobby is" -- revives correlate with overall chaos.
    """
    if cfg.respawn_model == "poisson":
        return int(rng.poisson(cfg.revive_knock_mean))
    return _sample_negbin_mean_dispersion(
        cfg.revive_knock_mean, max(cfg.respawn_dispersion, 1.0), rng
    )


def _softmax_weights(log_weights: np.ndarray) -> np.ndarray:
    """Numerically stable softmax. Returns a probability vector (sums to 1)."""
    log_weights = np.asarray(log_weights, dtype=np.float64)
    log_weights = log_weights - log_weights.max()
    w = np.exp(log_weights)
    s = w.sum()
    if s <= 0 or not np.isfinite(s):
        # degenerate -- fall back to uniform
        return np.full_like(w, 1.0 / len(w))
    return w / s


def compute_placement(
    teams_arr: dict,
    cfg: SimulationConfig,
    rng: np.random.Generator,
    eligible_mask: np.ndarray,
) -> np.ndarray:
    """Plackett-Luce style sampling. Returns team_id array (1st .. 20th)."""
    n = len(teams_arr["placement_skill"])
    placement_skill = teams_arr["placement_skill"]
    macro = teams_arr["macro_consistency"]
    volatility = teams_arr["volatility"]
    win_conv = teams_arr["win_conversion"]

    noise = rng.normal(0.0, cfg.base_match_noise * volatility, size=n)
    log_placement_w = (
        cfg.rank_beta * placement_skill
        + cfg.consistency_beta * macro
        + noise
    )

    # Winner weights extend placement weights with win_conversion and MP pressure.
    log_winner_w = log_placement_w + cfg.win_beta * win_conv
    if cfg.mp_pressure_enabled:
        log_winner_w = log_winner_w - cfg.mp_win_penalty * eligible_mask.astype(np.float64)

    team_ids = teams_arr["team_id"]
    order: list[int] = []
    remaining = np.ones(n, dtype=bool)

    # 1st place uses winner weights
    p = _softmax_weights(np.where(remaining, log_winner_w, -np.inf))
    first_idx = int(rng.choice(n, p=p))
    order.append(int(team_ids[first_idx]))
    remaining[first_idx] = False

    # Subsequent places use placement weights (without win_conversion bonus)
    for _ in range(1, n):
        masked = np.where(remaining, log_placement_w, -np.inf)
        p = _softmax_weights(masked)
        idx = int(rng.choice(n, p=p))
        order.append(int(team_ids[idx]))
        remaining[idx] = False

    return np.array(order, dtype=int)


def allocate_kills(
    teams_arr: dict,
    placements: np.ndarray,
    scored_kills: int,
    transferred_kills: int,
    cfg: SimulationConfig,
    rng: np.random.Generator,
    eligible_mask: np.ndarray,
) -> np.ndarray:
    """Multinomial allocation across teams, indexed by team_id.

    Of the `scored_kills` total, `transferred_kills` are treated as 漁夫
    (third-party-kill steals) and allocated using a separate weight that drops
    the placement factor -- third-party kills depend on aggression / lobby
    positioning, not on the team's final placement. The remaining
    (scored_kills - transferred_kills) kills go through the standard
    placement-weighted distribution.

    The sum of returned team_kills equals scored_kills (conservation).
    """
    n = len(teams_arr["fight_skill"])
    fight = teams_arr["fight_skill"]
    team_ids = teams_arr["team_id"]

    # placement_position[team_id] = rank (0=1st, 19=20th)
    placement_position = np.empty(n, dtype=int)
    for rank, tid in enumerate(placements):
        placement_position[tid] = rank

    placement_factor = np.array(
        [PLACEMENT_KILL_FACTOR[placement_position[tid]] for tid in team_ids]
    )
    log_w_base = cfg.kill_beta * fight + np.log(placement_factor)
    log_w_steal = cfg.kill_beta * fight  # third-party kills: ignore placement
    if cfg.mp_pressure_enabled:
        penalty = cfg.mp_kill_penalty * eligible_mask.astype(np.float64)
        log_w_base = log_w_base - penalty
        log_w_steal = log_w_steal - penalty

    base_probs = _softmax_weights(log_w_base)
    steal_probs = _softmax_weights(log_w_steal)

    if scored_kills <= 0:
        return np.zeros(n, dtype=int)

    transferred_kills = max(0, min(int(transferred_kills), int(scored_kills)))
    base_count = int(scored_kills) - transferred_kills

    if base_count > 0:
        base_alloc = rng.multinomial(base_count, base_probs)
    else:
        base_alloc = np.zeros(n, dtype=int)
    if transferred_kills > 0:
        steal_alloc = rng.multinomial(transferred_kills, steal_probs)
    else:
        steal_alloc = np.zeros(n, dtype=int)

    return (base_alloc + steal_alloc).astype(int)


def simulate_match(
    teams_arr: dict,
    cumulative_scores: np.ndarray,
    match_index: int,
    cfg: SimulationConfig,
    rng: np.random.Generator,
) -> MatchResult:
    """Run one match and return the result."""
    n = len(teams_arr["team_id"])
    eligible_at_start = cumulative_scores >= cfg.match_point_threshold
    eligible_count = int(eligible_at_start.sum())

    placements = compute_placement(teams_arr, cfg, rng, eligible_at_start)
    respawned = sample_respawned_players(cfg, rng)
    champ_remaining = sample_champion_remaining(cfg, rng)
    death_events = sample_death_events(respawned, champ_remaining,
                                       cfg.num_teams, cfg.players_per_team)

    scored, neutral, lost, transferred = sample_kill_credit(
        death_events, eligible_count, cfg, rng
    )
    revived = sample_revived_knocks(cfg, rng)

    team_kills = allocate_kills(
        teams_arr, placements, scored, transferred,
        cfg, rng, eligible_at_start,
    )

    # Total knockdowns in the match (knock-derived deaths + revived knocks).
    total_knocks = max(0, death_events - neutral) + revived

    placement_points_per_team = np.zeros(n, dtype=int)
    for rank, tid in enumerate(placements):
        placement_points_per_team[tid] = PLACEMENT_POINTS[rank]

    team_scores = placement_points_per_team + team_kills

    return MatchResult(
        match_index=match_index,
        placements=placements,
        winner_team_id=int(placements[0]),
        placement_points=placement_points_per_team,
        team_kills=team_kills,
        team_scores=team_scores,
        eligible_at_start=eligible_at_start.copy(),
        respawned_players=int(respawned),
        champion_remaining_players=int(champ_remaining),
        death_events=int(death_events),
        scored_kills=int(scored),
        neutral_deaths=int(neutral),
        lost_kill_points=int(lost),
        transferred_kills=int(transferred),
        revived_knocks=int(revived),
        total_knocks=int(total_knocks),
    )
