"""Shared utilities for formats that split a 30-team pool across lobbies.

Apex is a 20-team battle royale, so multi-lobby formats (Swiss, RoundRobin,
DoubleElim) need a way to:
  1. choose which teams play in which 10-team lobby for a given round, and
  2. run one battle royale match inside that lobby while keeping the global
     cumulative-score bookkeeping straight.

Lobby assignment strategies live here; per-match scoring stays in match_sim.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from config import SimulationConfig
from match_sim import MatchResult, simulate_match
from teams import Team


def split_by_score(
    team_ids: np.ndarray,
    cumulative: np.ndarray,
    lobby_size: int = 10,
) -> list[list[int]]:
    """Swiss-style split: sort by cumulative score descending, slice into lobbies.

    Ties are broken by team_id ascending so the assignment is reproducible.
    """
    ids = np.asarray(team_ids, dtype=int)
    scores = np.asarray(cumulative, dtype=int)
    # Lexsort: primary key descending score (negate), secondary ascending id.
    order = np.lexsort((ids, -scores))
    sorted_ids = ids[order]
    n_lobbies = len(sorted_ids) // lobby_size
    return [
        sorted_ids[i * lobby_size : (i + 1) * lobby_size].tolist()
        for i in range(n_lobbies)
    ]


def pair_balanced_split(
    team_ids: np.ndarray,
    pair_history: np.ndarray,
    rng: np.random.Generator,
    n_lobbies: int = 3,
) -> list[list[int]]:
    """Greedy round-robin assignment minimising repeated co-lobbying.

    For each team in a randomised order, drop it into the lobby that
    minimises its summed pair_history with the lobby's current members.
    The pair_history matrix is symmetric and updated by the caller after
    the round runs.
    """
    ids = np.asarray(team_ids, dtype=int)
    n_teams = ids.size
    if n_teams % n_lobbies != 0:
        raise ValueError(
            f"team count {n_teams} not divisible by n_lobbies {n_lobbies}"
        )
    lobby_size = n_teams // n_lobbies

    order = ids[rng.permutation(n_teams)]
    lobbies: list[list[int]] = [[] for _ in range(n_lobbies)]
    for tid in order:
        tid_int = int(tid)
        best_lobby = -1
        best_cost = None
        # Randomise tie-break order between lobbies so we don't always
        # collapse to lobby 0 on a fresh history.
        for lid in rng.permutation(n_lobbies):
            lid_int = int(lid)
            if len(lobbies[lid_int]) >= lobby_size:
                continue
            cost = int(sum(pair_history[tid_int, other] for other in lobbies[lid_int]))
            if best_cost is None or cost < best_cost:
                best_cost = cost
                best_lobby = lid_int
        lobbies[best_lobby].append(tid_int)
    return lobbies


def update_pair_history(
    pair_history: np.ndarray, lobbies: list[list[int]]
) -> None:
    """Increment pair_history[i,j] for every co-lobby pair (in place)."""
    for lobby in lobbies:
        for i_idx, i in enumerate(lobby):
            for j in lobby[i_idx + 1 :]:
                pair_history[i, j] += 1
                pair_history[j, i] += 1


def _subset_teams_arr(
    teams_arr: dict[str, np.ndarray], lobby_team_ids: list[int]
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Build a teams_arr restricted to lobby members with REMAPPED ids 0..k-1.

    `simulate_match` assumes team_id values index into PLACEMENT_KILL_FACTOR
    and the placement_position array, so we must hand it a contiguous local
    index space. Returns (sub_arr, global_ids) where global_ids[local] gives
    the original team_id.
    """
    global_ids = np.asarray(lobby_team_ids, dtype=int)
    k = global_ids.size
    sub_arr: dict[str, np.ndarray] = {}
    for key in (
        "placement_skill", "fight_skill", "win_conversion",
        "macro_consistency", "volatility", "seed",
    ):
        sub_arr[key] = teams_arr[key][global_ids].copy()
    sub_arr["team_id"] = np.arange(k, dtype=int)
    return sub_arr, global_ids


def run_lobby_match(
    teams_arr: dict[str, np.ndarray],
    lobby_team_ids: list[int],
    match_idx: int,
    cfg: SimulationConfig,
    rng: np.random.Generator,
    pool_size: int,
) -> MatchResult:
    """Run one match within a lobby and return a pool-sized MatchResult.

    The returned MatchResult uses GLOBAL team_ids (0..pool_size-1). Teams
    not in the lobby get zero placement_points, zero kills, zero score,
    and are absent from `placements`. Match Point eligibility flags are
    set to False — multi-lobby formats don't carry MP pressure into a
    sub-lobby.
    """
    sub_arr, global_ids = _subset_teams_arr(teams_arr, lobby_team_ids)
    lobby_size = global_ids.size
    cfg_lobby = replace(
        cfg,
        num_teams=lobby_size,
        starting_points_mode="none",
        custom_starting_points=None,
    )
    sub_cum = np.zeros(lobby_size, dtype=int)
    local_result = simulate_match(sub_arr, sub_cum, match_idx, cfg_lobby, rng)

    # Map local team_ids back to global pool-sized arrays.
    full_placement_points = np.zeros(pool_size, dtype=int)
    full_team_kills = np.zeros(pool_size, dtype=int)
    full_team_scores = np.zeros(pool_size, dtype=int)
    full_placement_points[global_ids] = local_result.placement_points
    full_team_kills[global_ids] = local_result.team_kills
    full_team_scores[global_ids] = local_result.team_scores

    global_placements = global_ids[local_result.placements]
    full_eligible = np.zeros(pool_size, dtype=bool)

    return MatchResult(
        match_index=match_idx,
        placements=global_placements.astype(int),
        winner_team_id=int(global_placements[0]),
        placement_points=full_placement_points,
        team_kills=full_team_kills,
        team_scores=full_team_scores,
        eligible_at_start=full_eligible,
        respawned_players=local_result.respawned_players,
        champion_remaining_players=local_result.champion_remaining_players,
        death_events=local_result.death_events,
        scored_kills=local_result.scored_kills,
        neutral_deaths=local_result.neutral_deaths,
        lost_kill_points=local_result.lost_kill_points,
        transferred_kills=local_result.transferred_kills,
        revived_knocks=local_result.revived_knocks,
        total_knocks=local_result.total_knocks,
    )


def lobby_summary(teams: list[Team], lobbies: list[list[int]]) -> str:
    """Compact human-readable description of a lobby assignment (for debug)."""
    lines = []
    for i, lobby in enumerate(lobbies):
        seeds = sorted(int(teams[t].seed) for t in lobby)
        lines.append(f"  lobby {chr(ord('A') + i)}: seeds {seeds}")
    return "\n".join(lines)
