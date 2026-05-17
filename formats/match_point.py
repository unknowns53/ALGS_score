"""ALGS Match Point format — the project's original tournament driver.

Behaviour-equivalent to the pre-refactor `tournament_sim.simulate_tournament`.
Encapsulating it as a Strategy keeps the existing test surface untouched
while letting other formats coexist.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import SimulationConfig
from formats.base import FormatResult, TournamentFormat, compute_leader
from match_sim import MatchResult, simulate_match
from teams import generate_teams, teams_to_arrays


@dataclass
class MatchPointFormat(TournamentFormat):
    """Standard ALGS Finals: 20 teams, single lobby, first-to-threshold wins.

    Parameters can override the global SimulationConfig knobs so we can
    instantiate "short MP" variants for things like Double Elimination's
    grand finals stage without mutating the user's config.
    """

    name: str = "match_point"
    threshold_override: int | None = None
    max_matches_override: int | None = None

    def simulate(
        self, cfg: SimulationConfig, rng: np.random.Generator
    ) -> FormatResult:
        teams = generate_teams(cfg, rng)
        teams_arr = teams_to_arrays(teams)

        starting = np.asarray(cfg.starting_points(), dtype=int)
        cumulative = starting.copy()

        threshold = (
            self.threshold_override
            if self.threshold_override is not None
            else cfg.match_point_threshold
        )
        max_matches = (
            self.max_matches_override
            if self.max_matches_override is not None
            else cfg.max_matches
        )

        match_results: list[MatchResult] = []
        leader_history: list[int] = [compute_leader(cumulative)]
        first_mp_match: int | None = None
        ended = False
        champion_id: int | None = None
        eligible_at_end: int = 0

        for m in range(1, max_matches + 1):
            eligible_before = cumulative >= threshold
            n_eligible_before = int(eligible_before.sum())
            if first_mp_match is None and n_eligible_before > 0:
                first_mp_match = m

            result = simulate_match(teams_arr, cumulative, m, cfg, rng)
            match_results.append(result)
            cumulative = cumulative + result.team_scores
            leader_history.append(compute_leader(cumulative))

            winner = result.winner_team_id
            if eligible_before[winner]:
                ended = True
                champion_id = winner
                eligible_at_end = n_eligible_before
                break

        if not ended:
            eligible_at_end = int((cumulative >= threshold).sum())
            champion_id = int(np.argmax(cumulative))

        teams_reached = int((cumulative >= threshold).sum())
        champion_seed: int | None = None
        if champion_id is not None:
            champion_seed = int(teams[champion_id].seed)

        return FormatResult(
            format_name=self.name,
            ended=ended,
            ending_match=len(match_results),
            champion_team_id=champion_id,
            champion_seed=champion_seed,
            teams=teams,
            cumulative_scores=cumulative,
            match_results=match_results,
            leader_history=np.asarray(leader_history, dtype=int),
            extras={
                "first_match_point_match": first_mp_match,
                "teams_reached_match_point": teams_reached,
                "eligible_at_ending_match_start": eligible_at_end,
                "match_point_threshold": int(threshold),
            },
        )
