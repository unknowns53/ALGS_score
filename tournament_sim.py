"""Full-tournament simulation and batch driver."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from config import SimulationConfig
from match_sim import MatchResult, simulate_match
from teams import Team, generate_teams, teams_to_arrays


@dataclass
class TournamentResult:
    ended: bool
    ending_match: int                       # 1-indexed match number when it ended
    champion_team_id: int | None
    champion_seed: int | None
    teams: list[Team]
    cumulative_scores: np.ndarray
    match_results: list[MatchResult]
    first_match_point_match: int | None      # earliest match where any team was eligible
    teams_reached_match_point: int           # final count with score >= threshold
    eligible_at_ending_match_start: int

    @property
    def number_of_matches(self) -> int:
        return len(self.match_results)


def simulate_tournament(
    cfg: SimulationConfig, rng: np.random.Generator
) -> TournamentResult:
    teams = generate_teams(cfg, rng)
    teams_arr = teams_to_arrays(teams)

    starting = np.asarray(cfg.starting_points(), dtype=int)
    cumulative = starting.copy()

    match_results: list[MatchResult] = []
    first_mp_match: int | None = None
    ended = False
    champion_id: int | None = None
    eligible_at_end: int = 0

    for m in range(1, cfg.max_matches + 1):
        eligible_before = cumulative >= cfg.match_point_threshold
        n_eligible_before = int(eligible_before.sum())
        if first_mp_match is None and n_eligible_before > 0:
            first_mp_match = m

        result = simulate_match(teams_arr, cumulative, m, cfg, rng)
        match_results.append(result)
        cumulative = cumulative + result.team_scores

        winner = result.winner_team_id
        if eligible_before[winner]:
            ended = True
            champion_id = winner
            eligible_at_end = n_eligible_before
            break

    if not ended:
        # tournament hit max_matches without an eligible winner; report cumulative leader
        eligible_at_end = int((cumulative >= cfg.match_point_threshold).sum())
        champion_id = int(np.argmax(cumulative))

    teams_reached = int((cumulative >= cfg.match_point_threshold).sum())
    champion_seed: int | None = None
    if champion_id is not None:
        champion_seed = int(teams[champion_id].seed)

    return TournamentResult(
        ended=ended,
        ending_match=len(match_results),
        champion_team_id=champion_id,
        champion_seed=champion_seed,
        teams=teams,
        cumulative_scores=cumulative,
        match_results=match_results,
        first_match_point_match=first_mp_match,
        teams_reached_match_point=teams_reached,
        eligible_at_ending_match_start=eligible_at_end,
    )


def run_simulations(
    cfg: SimulationConfig,
    n_sims: int,
    seed: int | None = None,
    show_progress: bool = False,
) -> list[TournamentResult]:
    rng = np.random.default_rng(seed)
    iterator = range(n_sims)
    if show_progress:
        try:
            from tqdm import tqdm  # type: ignore
            iterator = tqdm(iterator, total=n_sims, desc="sims")
        except ImportError:
            pass

    results: list[TournamentResult] = []
    for _ in iterator:
        results.append(simulate_tournament(cfg, rng))
    return results
