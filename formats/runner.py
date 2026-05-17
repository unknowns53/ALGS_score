"""Parallel runner for arbitrary TournamentFormat instances.

Mirrors tournament_sim.run_simulations but is format-agnostic: pass in
any TournamentFormat instance (it must be picklable for the worker
processes) and N simulations.
"""

from __future__ import annotations

import multiprocessing as mp
import os

import numpy as np

from config import SimulationConfig
from formats.base import FormatResult, TournamentFormat


def _resolve_workers(workers: int | None, n_sims: int) -> int:
    if workers is None or workers <= 0:
        cpu = os.cpu_count() or 1
        workers = max(1, cpu - 1) if cpu > 2 else 1
    if workers <= 1:
        return 1
    if n_sims < 1000:
        return 1
    return min(workers, max(1, n_sims))


def _run_format_chunk(
    args: tuple[TournamentFormat, SimulationConfig, int, np.random.SeedSequence],
) -> list[FormatResult]:
    fmt, cfg, n_sims, seed_seq = args
    rng = np.random.default_rng(seed_seq)
    return [fmt.simulate(cfg, rng) for _ in range(n_sims)]


def run_format_simulations(
    fmt: TournamentFormat,
    cfg: SimulationConfig,
    n_sims: int,
    seed: int | None = None,
    show_progress: bool = False,
    workers: int | None = 1,
) -> list[FormatResult]:
    """Run `n_sims` independent tournaments of the given format.

    Reproducibility: identical (fmt, cfg, n_sims, seed, workers) reproduces
    the same FormatResult list (worker-chunked SeedSequence.spawn).
    """
    effective_workers = _resolve_workers(workers, n_sims)

    if effective_workers == 1:
        rng = np.random.default_rng(seed)
        iterator = range(n_sims)
        if show_progress:
            try:
                from tqdm import tqdm  # type: ignore
                iterator = tqdm(iterator, total=n_sims, desc=f"{fmt.name}")
            except ImportError:
                pass
        return [fmt.simulate(cfg, rng) for _ in iterator]

    base_ss = np.random.SeedSequence(seed)
    child_seeds = base_ss.spawn(effective_workers)
    base_chunk = n_sims // effective_workers
    remainder = n_sims % effective_workers
    chunks = [base_chunk + (1 if i < remainder else 0) for i in range(effective_workers)]
    args = [
        (fmt, cfg, chunks[i], child_seeds[i])
        for i in range(effective_workers)
        if chunks[i] > 0
    ]

    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=len(args)) as pool:
        if show_progress:
            try:
                from tqdm import tqdm  # type: ignore
                results_iter = []
                with tqdm(total=n_sims, desc=f"{fmt.name}") as bar:
                    for chunk_results in pool.imap(_run_format_chunk, args):
                        results_iter.append(chunk_results)
                        bar.update(len(chunk_results))
                chunk_lists = results_iter
            except ImportError:
                chunk_lists = pool.map(_run_format_chunk, args)
        else:
            chunk_lists = pool.map(_run_format_chunk, args)

    results: list[FormatResult] = []
    for cl in chunk_lists:
        results.extend(cl)
    return results
