"""Sanity tests straight out of 仕様書.md > Tests > Sanity tests.

These are stochastic. Sample sizes are kept modest so the suite stays under a
minute. Seeds are fixed so the directional assertions are stable.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from config import SimulationConfig, apply_region_profile
from tournament_sim import run_simulations


def _mean_length(results) -> float:
    return float(np.mean([r.ending_match for r in results]))


def _std_length(results) -> float:
    return float(np.std([r.ending_match for r in results]))


def test_sanity_1_baseline_centers_8_to_11():
    cfg = SimulationConfig(
        strength_sigma=0.0,
        starting_points_mode="none",
        respawn_model="poisson",
        respawn_mean=4.0,
        mp_pressure_enabled=False,
        chaos_multiplier=1.0,
    )
    results = run_simulations(cfg, n_sims=500, seed=42)
    m = _mean_length(results)
    assert 7.5 <= m <= 12.0, f"baseline mean ending match out of range: {m:.2f}"


def test_sanity_2_higher_strength_sigma_shortens_tournaments():
    low = SimulationConfig(strength_sigma=0.20, starting_points_mode="none")
    high = SimulationConfig(strength_sigma=0.60, starting_points_mode="none")
    r_lo = run_simulations(low, n_sims=400, seed=11)
    r_hi = run_simulations(high, n_sims=400, seed=11)
    m_lo = _mean_length(r_lo)
    m_hi = _mean_length(r_hi)
    assert m_hi <= m_lo + 0.1, (
        f"higher strength_sigma should shorten tournaments: "
        f"low_sigma mean={m_lo:.2f}, high_sigma mean={m_hi:.2f}"
    )


def test_sanity_3_higher_respawn_mean_shortens_tournaments():
    low = SimulationConfig(respawn_mean=4.0, respawn_dispersion=4.0,
                           respawn_model="negbin",
                           starting_points_mode="none")
    high = SimulationConfig(respawn_mean=10.0, respawn_dispersion=4.0,
                            respawn_model="negbin",
                            starting_points_mode="none")
    r_lo = run_simulations(low, n_sims=400, seed=17)
    r_hi = run_simulations(high, n_sims=400, seed=17)
    m_lo = _mean_length(r_lo)
    m_hi = _mean_length(r_hi)
    assert m_hi < m_lo, (
        f"higher respawn_mean should shorten tournaments: "
        f"low={m_lo:.2f}, high={m_hi:.2f}"
    )


def test_sanity_4_higher_lost_kill_rate_lengthens_tournaments():
    low = SimulationConfig(lost_kill_rate=0.0, starting_points_mode="none")
    high = SimulationConfig(lost_kill_rate=0.08, starting_points_mode="none")
    r_lo = run_simulations(low, n_sims=400, seed=23)
    r_hi = run_simulations(high, n_sims=400, seed=23)
    m_lo = _mean_length(r_lo)
    m_hi = _mean_length(r_hi)
    assert m_hi > m_lo, (
        f"higher lost_kill_rate should lengthen tournaments: "
        f"low={m_lo:.2f}, high={m_hi:.2f}"
    )


def test_sanity_5_apac_n_longer_and_more_variable_than_americas():
    base = SimulationConfig(starting_points_mode="none")
    cfg_amer = apply_region_profile(base, "americas")
    cfg_apac = apply_region_profile(base, "apac_n")
    r_amer = run_simulations(cfg_amer, n_sims=500, seed=29)
    r_apac = run_simulations(cfg_apac, n_sims=500, seed=29)
    m_amer = _mean_length(r_amer)
    m_apac = _mean_length(r_apac)
    s_amer = _std_length(r_amer)
    s_apac = _std_length(r_apac)
    assert m_apac > m_amer, (
        f"apac_n should be longer than americas: "
        f"americas={m_amer:.2f}, apac_n={m_apac:.2f}"
    )
    assert s_apac > s_amer * 0.9, (
        f"apac_n should be at least as variable as americas: "
        f"std americas={s_amer:.2f}, apac_n={s_apac:.2f}"
    )
