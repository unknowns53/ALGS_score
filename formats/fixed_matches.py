"""Fixed-match-count format: 20 teams, N matches, cumulative-leader wins.

This is the classic "6 game" or "8 game" group-stage format used in
ALGS Pro League weeklies — no Match Point shortcut, every game is played.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import SimulationConfig
from formats.base import FormatResult, TournamentFormat, compute_leader
from match_sim import MatchResult, simulate_match
from teams import generate_teams, teams_to_arrays


def _resolve_ties(
    cumulative: np.ndarray,
    match_results: list[MatchResult],
    teams_arr_seed: np.ndarray,
) -> np.ndarray:
    """Final ranking with ALGS-style tie-breaks.

    Priority (descending):
      1. cumulative score
      2. total kills (sum across all matches)
      3. number of 1st-place finishes
      4. seed (lower seed = stronger, wins the tie)

    Returns team_ids in finish order (winner first).
    """
    n = cumulative.size
    total_kills = np.zeros(n, dtype=int)
    first_places = np.zeros(n, dtype=int)
    for r in match_results:
        total_kills = total_kills + r.team_kills
        first_places[r.winner_team_id] += 1
    # numpy lexsort sorts by LAST key with highest priority -> build accordingly.
    # We want descending on score/kills/firsts and ascending on seed; negate
    # the descending keys so a single ascending sort produces winners first.
    keys = (
        teams_arr_seed.astype(int),     # tertiary tertiary: seed asc
        -first_places,                  # tertiary: more 1st places first
        -total_kills,                   # secondary: more kills first
        -cumulative.astype(int),        # primary: more score first
    )
    return np.lexsort(keys).astype(int)


@dataclass
class FixedMatchesFormat(TournamentFormat):
    """N-match league with cumulative-leader-wins crowning.

    `n_matches` defaults to 6 (a common Pro League weekly length); use 8
    for the extended version, or any positive integer for sweeps.
    """

    name: str = "fixed"
    n_matches: int = 6

    def __post_init__(self) -> None:
        if self.n_matches <= 0:
            raise ValueError(f"n_matches must be positive, got {self.n_matches}")
        # Give instances distinct names so summaries can tell 6/8/etc. apart.
        if self.name == "fixed":
            self.name = f"fixed_{self.n_matches}"

    def simulate(
        self, cfg: SimulationConfig, rng: np.random.Generator
    ) -> FormatResult:
        teams = generate_teams(cfg, rng)
        teams_arr = teams_to_arrays(teams)

        starting = np.asarray(cfg.starting_points(), dtype=int)
        cumulative = starting.copy()

        match_results: list[MatchResult] = []
        leader_history: list[int] = [compute_leader(cumulative)]

        for m in range(1, self.n_matches + 1):
            result = simulate_match(teams_arr, cumulative, m, cfg, rng)
            match_results.append(result)
            cumulative = cumulative + result.team_scores
            leader_history.append(compute_leader(cumulative))

        finish_order = _resolve_ties(cumulative, match_results, teams_arr["seed"])
        champion_id = int(finish_order[0])
        champion_seed = int(teams[champion_id].seed)

        return FormatResult(
            format_name=self.name,
            ended=True,
            ending_match=self.n_matches,
            champion_team_id=champion_id,
            champion_seed=champion_seed,
            teams=teams,
            cumulative_scores=cumulative,
            match_results=match_results,
            leader_history=np.asarray(leader_history, dtype=int),
            extras={
                "finish_order": finish_order.tolist(),
                "n_matches": int(self.n_matches),
            },
        )
