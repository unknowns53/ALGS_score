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
    """
    n = n_override if n_override is not None else cfg.num_teams
    cov = _build_covariance(cfg)
    mean = np.zeros(4)
    skills = rng.multivariate_normal(mean, cov, size=n)  # (n, 4)
    placement = skills[:, 0]
    fight = skills[:, 1]
    win_conv = skills[:, 2]
    macro = skills[:, 3]

    vol_raw = rng.normal(cfg.volatility_mean, cfg.volatility_sigma, size=n)
    volatility = np.clip(vol_raw, 0.2, None)

    # Composite ranking score: placement-dominant with win-conversion tiebreak.
    composite = placement + 0.5 * win_conv + 0.2 * fight
    order = np.argsort(-composite)  # strongest first
    seed = np.empty(n, dtype=int)
    seed[order] = np.arange(1, n + 1)

    teams = [
        Team(
            team_id=i,
            seed=int(seed[i]),
            placement_skill=float(placement[i]),
            fight_skill=float(fight[i]),
            win_conversion=float(win_conv[i]),
            macro_consistency=float(macro[i]),
            volatility=float(volatility[i]),
        )
        for i in range(n)
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
