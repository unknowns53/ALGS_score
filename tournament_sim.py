"""Full-tournament simulation and batch driver.

The Match Point logic lives in `formats.match_point.MatchPointFormat`; this
module is a thin compatibility wrapper that converts FormatResult back to
the historical TournamentResult so callers (cli.py, stats.py, tests) keep
working without changes.

For new format-comparison work, prefer `formats.runner.run_format_simulations`.
"""

from __future__ import annotations

import multiprocessing as mp
import os
from dataclasses import dataclass

import numpy as np

from config import SimulationConfig
from formats.base import FormatResult
from formats.match_point import MatchPointFormat
from match_sim import MatchResult, simulate_match  # re-exported for callers
from teams import Team, generate_teams, teams_to_arrays  # re-exported


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


def _format_result_to_tournament_result(fr: FormatResult) -> TournamentResult:
    """Translate the unified FormatResult into the legacy TournamentResult shape."""
    extras = fr.extras
    return TournamentResult(
        ended=fr.ended,
        ending_match=fr.ending_match,
        champion_team_id=fr.champion_team_id,
        champion_seed=fr.champion_seed,
        teams=fr.teams,
        cumulative_scores=fr.cumulative_scores,
        match_results=fr.match_results,
        first_match_point_match=extras.get("first_match_point_match"),
        teams_reached_match_point=int(extras.get("teams_reached_match_point", 0)),
        eligible_at_ending_match_start=int(
            extras.get("eligible_at_ending_match_start", 0)
        ),
    )


_DEFAULT_MP_FORMAT = MatchPointFormat()


def simulate_tournament(
    cfg: SimulationConfig, rng: np.random.Generator
) -> TournamentResult:
    """Run one ALGS Match Point tournament — historical entry point.

    Behaviour-preserving wrapper around MatchPointFormat. New code that
    wants other formats should call MatchPointFormat().simulate(cfg, rng)
    directly (or use formats.runner.run_format_simulations).
    """
    fr = _DEFAULT_MP_FORMAT.simulate(cfg, rng)
    return _format_result_to_tournament_result(fr)


def _run_chunk(
    args: tuple[SimulationConfig, int, np.random.SeedSequence]
) -> list[TournamentResult]:
    """Run a contiguous chunk of simulations in a worker process."""
    cfg, n_sims, seed_seq = args
    rng = np.random.default_rng(seed_seq)
    return [simulate_tournament(cfg, rng) for _ in range(n_sims)]


def _resolve_workers(workers: int | None, n_sims: int) -> int:
    """Decide an effective worker count."""
    if workers is None or workers <= 0:
        # Auto: half of detected CPUs, capped, parallel only if n_sims is big enough.
        cpu = os.cpu_count() or 1
        workers = max(1, cpu - 1) if cpu > 2 else 1
    if workers <= 1:
        return 1
    # Parallel overhead is not worth it for tiny runs.
    if n_sims < 1000:
        return 1
    return min(workers, max(1, n_sims))


def run_simulations(
    cfg: SimulationConfig,
    n_sims: int,
    seed: int | None = None,
    show_progress: bool = False,
    workers: int | None = 1,
) -> list[TournamentResult]:
    """Run `n_sims` independent tournament simulations.

    workers=1 runs serially. workers>=2 splits the work across that many
    processes via multiprocessing.Pool. workers=0 or None picks an automatic
    value (about cpu_count - 1). Reproducibility is preserved: identical
    (seed, n_sims, workers) always produce the identical list of results.
    """
    effective_workers = _resolve_workers(workers, n_sims)

    if effective_workers == 1:
        rng = np.random.default_rng(seed)
        iterator = range(n_sims)
        if show_progress:
            try:
                from tqdm import tqdm  # type: ignore
                iterator = tqdm(iterator, total=n_sims, desc="sims")
            except ImportError:
                pass
        return [simulate_tournament(cfg, rng) for _ in iterator]

    # Parallel path: spawn one independent SeedSequence per worker chunk so the
    # global (seed, workers, n_sims) triple uniquely determines all results.
    base_ss = np.random.SeedSequence(seed)
    child_seeds = base_ss.spawn(effective_workers)

    base_chunk = n_sims // effective_workers
    remainder = n_sims % effective_workers
    chunks = [base_chunk + (1 if i < remainder else 0) for i in range(effective_workers)]
    args = [
        (cfg, chunks[i], child_seeds[i])
        for i in range(effective_workers)
        if chunks[i] > 0
    ]

    ctx = mp.get_context("spawn")  # consistent on Windows + Linux
    with ctx.Pool(processes=len(args)) as pool:
        if show_progress:
            try:
                from tqdm import tqdm  # type: ignore
                results_iter = []
                with tqdm(total=n_sims, desc="sims") as bar:
                    for chunk_results in pool.imap(_run_chunk, args):
                        results_iter.append(chunk_results)
                        bar.update(len(chunk_results))
                chunk_lists = results_iter
            except ImportError:
                chunk_lists = pool.map(_run_chunk, args)
        else:
            chunk_lists = pool.map(_run_chunk, args)

    results: list[TournamentResult] = []
    for cl in chunk_lists:
        results.extend(cl)
    return results
