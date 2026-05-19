"""Team strength generation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import SimulationConfig


@dataclass(frozen=True)
class Team:
    team_id: int
    seed: int  # 1 = strongest, 20 = weakest, derived from composite strength
    placement_skill: float
    fight_skill: float
    win_conversion: float
    macro_consistency: float
    volatility: float


def _build_covariance(cfg: SimulationConfig) -> np.ndarray:
    """4x4 cov for (placement, fight, win_conversion, macro_consistency)."""
    sigma = cfg.strength_sigma
    pf = cfg.placement_fight_correlation
    pw = cfg.placement_win_correlation
    # Conservative weaker correlations for the remaining pairs.
    fw = 0.5 * min(pf, pw)
    pc = 0.20
    fc = 0.10
    wc = 0.10

    corr = np.array([
        [1.0, pf,  pw,  pc],
        [pf,  1.0, fw,  fc],
        [pw,  fw,  1.0, wc],
        [pc,  fc,  wc,  1.0],
    ])
    cov = corr * (sigma ** 2)
    # Symmetrise and nudge to PSD just in case.
    cov = 0.5 * (cov + cov.T)
    eigvals = np.linalg.eigvalsh(cov)
    if eigvals.min() < 1e-9:
        cov = cov + np.eye(4) * (1e-9 - eigvals.min())
    return cov


def composite_strength(team: "Team") -> float:
    """Single source of truth for the composite strength score used for seeding."""
    return team.placement_skill + 0.5 * team.win_conversion + 0.2 * team.fight_skill


def generate_teams(
    cfg: SimulationConfig,
    rng: np.random.Generator,
    n_override: int | None = None,
) -> list[Team]:
    """Sample N teams' latent strengths and assign seeds.

    Pass `n_override` to generate a pool that differs from cfg.num_teams,
    e.g. 30 teams for Swiss / RoundRobin / DoubleElim formats while keeping
    the per-match num_teams at the lobby size.

    Cycle 14 (2026-05): when `cfg.lobby_composition == "wb_eb"`, the
    function instead samples a `cfg.pool_size`-team population from the
    same multivariate normal, then selects the composite-top
    (cfg.wb_top_n + cfg.eb_top_n) teams as the finals lobby. This
    models the ALGS Global Finals lobby being drawn from the Group
    Stage population's top survivors. `n_override` is ignored in
    wb_eb mode (lobby size is fixed by wb_top_n + eb_top_n) — pass
    "normal" composition if a custom pool size is required.
    """
    if cfg.lobby_composition == "wb_eb":
        return _generate_teams_wb_eb(cfg, rng)
    n = n_override if n_override is not None else cfg.num_teams
    return _sample_and_pack(cfg, rng, n_to_sample=n, n_to_keep=n)


def _generate_teams_wb_eb(
    cfg: SimulationConfig, rng: np.random.Generator
) -> list[Team]:
    """Pool sampling: draw cfg.pool_size, keep top (wb_top_n + eb_top_n).

    The lobby is the composite-ranked top of a larger population, so
    the lobby's strength distribution is the upper order statistic of
    a normal — naturally narrower than the underlying normal and shifted
    upward. This is the cycle-14 physical model for Global Finals.

    The WB / EB split is currently stored as separate config knobs but
    not used here — both groups feed into the same finals lobby, and
    the bracket-routing nuance (which 10 went via WB vs EB) is left
    out of the strength model in this minimum implementation. The
    fields are reserved for a future cycle that may shift mean
    strength between WB and EB survivors.
    """
    lobby_size = cfg.wb_top_n + cfg.eb_top_n
    if cfg.pool_size < lobby_size:
        raise ValueError(
            f"lobby_composition='wb_eb' requires pool_size "
            f"({cfg.pool_size}) >= wb_top_n + eb_top_n ({lobby_size})"
        )
    return _sample_and_pack(
        cfg, rng, n_to_sample=cfg.pool_size, n_to_keep=lobby_size,
    )


def _sample_and_pack(
    cfg: SimulationConfig,
    rng: np.random.Generator,
    n_to_sample: int,
    n_to_keep: int,
) -> list[Team]:
    """Sample n_to_sample teams, rank by composite, keep top n_to_keep.

    Setting n_to_keep == n_to_sample reproduces the legacy "normal"
    behavior (sample = lobby).
    """
    cov = _build_covariance(cfg)
    mean = np.zeros(4)
    skills = rng.multivariate_normal(mean, cov, size=n_to_sample)  # (n, 4)
    placement = skills[:, 0]
    fight = skills[:, 1]
    win_conv = skills[:, 2]
    macro = skills[:, 3]

    vol_raw = rng.normal(cfg.volatility_mean, cfg.volatility_sigma,
                         size=n_to_sample)
    volatility = np.clip(vol_raw, 0.2, None)

    # Composite ranking score: placement-dominant with win-conversion tiebreak.
    composite = placement + 0.5 * win_conv + 0.2 * fight
    order = np.argsort(-composite)  # strongest first across the whole pool
    keep_idx = order[:n_to_keep]
    # Re-seed within the kept lobby: seed 1 = strongest survivor, etc.
    seed = np.empty(n_to_keep, dtype=int)
    keep_composite = composite[keep_idx]
    local_order = np.argsort(-keep_composite)
    seed[local_order] = np.arange(1, n_to_keep + 1)

    teams = [
        Team(
            team_id=i,
            seed=int(seed[i]),
            placement_skill=float(placement[keep_idx[i]]),
            fight_skill=float(fight[keep_idx[i]]),
            win_conversion=float(win_conv[keep_idx[i]]),
            macro_consistency=float(macro[keep_idx[i]]),
            volatility=float(volatility[keep_idx[i]]),
        )
        for i in range(n_to_keep)
    ]
    return teams


def teams_to_arrays(teams: list[Team]) -> dict[str, np.ndarray]:
    """Vectorise team properties for fast per-match math."""
    return {
        "placement_skill": np.array([t.placement_skill for t in teams]),
        "fight_skill": np.array([t.fight_skill for t in teams]),
        "win_conversion": np.array([t.win_conversion for t in teams]),
        "macro_consistency": np.array([t.macro_consistency for t in teams]),
        "volatility": np.array([t.volatility for t in teams]),
        "seed": np.array([t.seed for t in teams]),
        "team_id": np.array([t.team_id for t in teams]),
    }
