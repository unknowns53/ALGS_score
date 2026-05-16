"""Reproducibility tests for the parallel driver in tournament_sim.

These tests are slightly heavier than the rest of the suite because spawning
worker processes on Windows has fixed overhead, so we keep n_sims small.
"""

from __future__ import annotations

import os
import sys

import pytest

from config import SimulationConfig
from tournament_sim import run_simulations


pytestmark = pytest.mark.skipif(
    os.environ.get("ALGS_SKIP_PARALLEL_TESTS") == "1",
    reason="parallel tests opted out via env var",
)


def _length_signature(results) -> tuple[int, ...]:
    return tuple(r.ending_match for r in results)


def test_serial_run_is_deterministic_with_seed():
    cfg = SimulationConfig(starting_points_mode="none")
    a = run_simulations(cfg, n_sims=200, seed=2026, workers=1)
    b = run_simulations(cfg, n_sims=200, seed=2026, workers=1)
    assert _length_signature(a) == _length_signature(b)


def test_parallel_run_is_deterministic_with_same_workers():
    """Same (seed, n_sims, workers) must produce the exact same result list."""
    cfg = SimulationConfig(starting_points_mode="none")
    a = run_simulations(cfg, n_sims=1500, seed=2026, workers=2)
    b = run_simulations(cfg, n_sims=1500, seed=2026, workers=2)
    assert len(a) == 1500
    assert _length_signature(a) == _length_signature(b)


def test_parallel_total_count_matches_request():
    cfg = SimulationConfig(starting_points_mode="none")
    # Use a non-divisible n_sims to exercise the remainder path.
    results = run_simulations(cfg, n_sims=1501, seed=7, workers=3)
    assert len(results) == 1501


def test_small_run_falls_back_to_serial():
    """workers>1 but tiny n_sims should auto-disable the pool overhead."""
    cfg = SimulationConfig(starting_points_mode="none")
    # 50 sims is well below the 1000-sim threshold in _resolve_workers, so
    # workers=8 should collapse to a serial run. This test mainly proves the
    # function still returns the right count and is reproducible.
    a = run_simulations(cfg, n_sims=50, seed=1, workers=8)
    b = run_simulations(cfg, n_sims=50, seed=1, workers=8)
    assert len(a) == 50
    assert _length_signature(a) == _length_signature(b)
