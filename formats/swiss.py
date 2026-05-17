"""Swiss-style format: 30 teams, lobby re-seeding by cumulative score.

Each round splits the pool into 3 lobbies of 10 by current cumulative
score (top-10 lobby A, mid-10 lobby B, bottom-10 lobby C) and runs one
match per lobby. Final champion is the cumulative leader after N rounds.

This is the natural "Swiss adaptation" of Apex BR: similarly-scoring
teams face each other in each round, but the matchups happen as 10-team
battle royales rather than 1v1 pairings.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import SimulationConfig
from formats.base import FormatResult, TournamentFormat, compute_leader
from formats.fixed_matches import _resolve_ties
from formats.lobby_assignment import run_lobby_match, split_by_score
from match_sim import MatchResult
from teams import generate_teams, teams_to_arrays


@dataclass
class SwissFormat(TournamentFormat):
    """Swiss-style multi-lobby league with score-based re-seeding each round."""

    name: str = "swiss"
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
        seed_array = teams_arr["seed"]

        cumulative = np.zeros(self.pool_size, dtype=int)
        match_results: list[MatchResult] = []
        leader_history: list[int] = [compute_leader(cumulative)]
        lobby_history: list[list[list[int]]] = []

        for round_idx in range(1, self.n_rounds + 1):
            if round_idx == 1:
                # Round 1: split by seed (use -seed-rank as score proxy).
                # split_by_score sorts descending by "cumulative" — for round 1
                # we want seed 1 → lobby A, seed 30 → lobby C, so feed negative seed.
                pseudo_cum = (-seed_array).astype(int)
                lobbies = split_by_score(team_ids, pseudo_cum, self.lobby_size)
            else:
                lobbies = split_by_score(team_ids, cumulative, self.lobby_size)
            lobby_history.append(lobbies)

            # Each lobby plays one match this round.
            for lobby_team_ids in lobbies:
                match_idx = len(match_results) + 1
                mr = run_lobby_match(
                    teams_arr, lobby_team_ids, match_idx, cfg, rng, self.pool_size
                )
                match_results.append(mr)
                cumulative = cumulative + mr.team_scores
            leader_history.append(compute_leader(cumulative))

        finish_order = _resolve_ties(cumulative, match_results, seed_array)
        champion_id = int(finish_order[0])
        champion_seed = int(teams[champion_id].seed)

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
                "lobby_history": lobby_history,
            },
        )
