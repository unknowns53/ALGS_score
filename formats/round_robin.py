"""Round-robin-ish format: 30 teams, pair-balanced random lobby shuffling.

A true 30-team all-vs-all is impossible in a 20-team battle royale, so
the analogue is: keep a pair_history matrix and on each round assign
teams to 3 lobbies of 10 such that pairs that have least co-lobbied
together so far are preferred. After enough rounds every pair should
have shared a lobby roughly the same number of times.

Final champion is the cumulative leader after N matches per lobby.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import SimulationConfig
from formats.base import FormatResult, TournamentFormat, compute_leader
from formats.fixed_matches import _resolve_ties
from formats.lobby_assignment import (
    pair_balanced_split,
    run_lobby_match,
    update_pair_history,
)
from match_sim import MatchResult
from teams import generate_teams, teams_to_arrays


@dataclass
class RoundRobinFormat(TournamentFormat):
    """Pair-balanced multi-lobby format approximating an Apex round-robin."""

    name: str = "round_robin"
    n_rounds: int = 6
    lobby_size: int = 10
    pool_size: int = 30

    def __post_init__(self) -> None:
        if self.pool_size % self.lobby_size != 0:
            raise ValueError(
                f"pool_size {self.pool_size} not divisible by lobby_size "
                f"{self.lobby_size}"
            )
        if self.n_rounds <= 0:
            raise ValueError(f"n_rounds must be positive, got {self.n_rounds}")

    def simulate(
        self, cfg: SimulationConfig, rng: np.random.Generator
    ) -> FormatResult:
        teams = generate_teams(cfg, rng, n_override=self.pool_size)
        teams_arr = teams_to_arrays(teams)
        team_ids = np.arange(self.pool_size, dtype=int)
        n_lobbies = self.pool_size // self.lobby_size

        cumulative = np.zeros(self.pool_size, dtype=int)
        match_results: list[MatchResult] = []
        leader_history: list[int] = [compute_leader(cumulative)]
        pair_history = np.zeros((self.pool_size, self.pool_size), dtype=int)

        for round_idx in range(1, self.n_rounds + 1):
            lobbies = pair_balanced_split(team_ids, pair_history, rng, n_lobbies)
            update_pair_history(pair_history, lobbies)

            for lobby_team_ids in lobbies:
                match_idx = len(match_results) + 1
                mr = run_lobby_match(
                    teams_arr, lobby_team_ids, match_idx, cfg, rng, self.pool_size
                )
                match_results.append(mr)
                cumulative = cumulative + mr.team_scores
            leader_history.append(compute_leader(cumulative))

        finish_order = _resolve_ties(cumulative, match_results, teams_arr["seed"])
        champion_id = int(finish_order[0])
        champion_seed = int(teams[champion_id].seed)

        # Pair-balance diagnostic: off-diagonal stddev.
        off_diag = pair_history[np.triu_indices(self.pool_size, k=1)]
        pair_std = float(off_diag.std())
        pair_mean = float(off_diag.mean())

        return FormatResult(
            format_name=self.name,
            ended=True,
            ending_match=len(match_results),
            champion_team_id=champion_id,
            champion_seed=champion_seed,
            teams=teams,
            cumulative_scores=cumulative,
            match_results=match_results,
            leader_history=np.asarray(leader_history, dtype=int),
            extras={
                "finish_order": finish_order.tolist(),
                "n_rounds": int(self.n_rounds),
                "lobby_size": int(self.lobby_size),
                "pool_size": int(self.pool_size),
                "pair_history_mean": pair_mean,
                "pair_history_std": pair_std,
            },
        )
