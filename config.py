"""Simulation configuration and regional presets."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal


RespawnModel = Literal["poisson", "negbin"]
StartingPointsMode = Literal["none", "seeded", "custom"]
RegionProfile = Literal["custom", "americas", "emea", "apac_n", "apac_s"]


# Placement points table (1st .. 20th).
PLACEMENT_POINTS: tuple[int, ...] = (
    12, 9, 7, 5, 4, 3, 3, 2, 2, 2, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0,
)

# Kill weight multiplier by placement (1st .. 20th).
PLACEMENT_KILL_FACTOR: tuple[float, ...] = (
    1.35, 1.25, 1.20, 1.10, 1.10,
    1.00, 1.00, 1.00, 1.00, 1.00,
    0.75, 0.75, 0.75, 0.75, 0.75,
    0.45, 0.45, 0.45, 0.45, 0.45,
)

# Legacy "seeded" starting points. The current ALGS Match Point Finals format
# does NOT carry seed bonuses into the final, so this table is only used when
# the user explicitly opts in via --starting-points seeded. The default mode
# is "none" (everyone starts at 0).
# Values loosely follow earlier ALGS years when seed bonuses did exist.
STARTING_POINTS_SEEDED: tuple[int, ...] = (
    10, 9, 8, 7, 6, 5, 4, 3, 2, 1,  # seeds 1-10
    0, 0, 0, 0, 0,                  # seeds 11-15
    0, 0, 0, 0, 0,                  # seeds 16-20
)


@dataclass
class SimulationConfig:
    """All knobs for the simulator. Sims-count is passed separately."""

    # Rules
    num_teams: int = 20
    players_per_team: int = 3
    max_matches: int = 30
    match_point_threshold: int = 50

    # Starting points. Default "none" matches current ALGS Match Point Finals,
    # which start every team at 0. Use "seeded" only when the user explicitly
    # wants the legacy seed-bonus table from STARTING_POINTS_SEEDED.
    starting_points_mode: StartingPointsMode = "none"
    custom_starting_points: tuple[int, ...] | None = None

    # Team strength
    strength_sigma: float = 0.45
    rank_beta: float = 1.0
    kill_beta: float = 0.8
    win_beta: float = 0.8
    consistency_beta: float = 0.4
    placement_fight_correlation: float = 0.6
    placement_win_correlation: float = 0.5
    base_match_noise: float = 0.8
    volatility_mean: float = 1.0
    volatility_sigma: float = 0.25

    # Respawn model
    respawn_model: RespawnModel = "negbin"
    respawn_mean: float = 6.0
    respawn_dispersion: float = 4.0
    max_respawned_players: int = 30

    # Champion remaining players at match end. Sampled from the inclusive range
    # [champion_remaining_min, champion_remaining_max] using the weights tuple
    # below. In real ALGS finals the champion squad usually finishes with all
    # three alive, so the default heavily favours 3 (about 5% / 20% / 75% for
    # 1 / 2 / 3 alive, mean ≈ 2.7).
    champion_remaining_min: int = 1
    champion_remaining_max: int = 3
    champion_remaining_weights: tuple[float, ...] = (1.0, 4.0, 15.0)

    # Kill credit model
    neutral_death_rate: float = 0.01
    lost_kill_rate: float = 0.03
    transfer_kill_rate: float = 0.05
    revive_knock_mean: float = 10.0
    chaos_multiplier: float = 1.0
    mp_pressure_lost_kill_multiplier: float = 1.25

    # Match Point pressure
    mp_pressure_enabled: bool = True
    mp_win_penalty: float = 0.10
    mp_kill_penalty: float = 0.05

    # Region profile tag (for reporting only; values are already baked in)
    region_profile: RegionProfile = "custom"

    def starting_points(self) -> tuple[int, ...]:
        """Resolve starting points based on mode."""
        if self.starting_points_mode == "none":
            return tuple(0 for _ in range(self.num_teams))
        if self.starting_points_mode == "seeded":
            return STARTING_POINTS_SEEDED
        if self.starting_points_mode == "custom":
            if self.custom_starting_points is None:
                raise ValueError("custom_starting_points must be set when mode='custom'")
            if len(self.custom_starting_points) != self.num_teams:
                raise ValueError(
                    f"custom_starting_points must have length {self.num_teams}, "
                    f"got {len(self.custom_starting_points)}"
                )
            return tuple(self.custom_starting_points)
        raise ValueError(f"unknown starting_points_mode: {self.starting_points_mode}")


# Regional profile presets. The intent is to tune within-region parity,
# chaos and win-conversion patterns -- not absolute regional strength.
REGION_PROFILES: dict[str, dict[str, float | int | bool | str]] = {
    "americas": {
        # Calibrated against 4 historical Americas Pro League finals
        # (2024 S1/S2, 2025 S1/S2): mean 7.50 games.
        "strength_sigma": 0.48,
        "rank_beta": 1.00,
        "kill_beta": 0.85,
        "win_beta": 0.85,
        "consistency_beta": 0.45,
        "placement_fight_correlation": 0.60,
        "placement_win_correlation": 0.50,
        "base_match_noise": 0.75,
        "volatility_mean": 0.95,
        "volatility_sigma": 0.20,
        "respawn_model": "negbin",
        "respawn_mean": 6.0,
        "respawn_dispersion": 4.0,
        "neutral_death_rate": 0.01,
        "lost_kill_rate": 0.025,
        "transfer_kill_rate": 0.05,
        "revive_knock_mean": 9.0,
        "mp_pressure_enabled": True,
        "mp_win_penalty": 0.08,
        "mp_kill_penalty": 0.04,
        "mp_pressure_lost_kill_multiplier": 1.15,
    },
    "emea": {
        # Calibrated against 4 historical EMEA Pro League finals
        # (2024 S1/S2, 2025 S1/S2): mean 8.50 games. EMEA is much more
        # contested than the "structured & low chaos" stereotype, so
        # parity is closer to APAC-N levels.
        "strength_sigma": 0.38,
        "rank_beta": 0.95,
        "kill_beta": 0.80,
        "win_beta": 0.75,
        "consistency_beta": 0.40,
        "placement_fight_correlation": 0.55,
        "placement_win_correlation": 0.45,
        "base_match_noise": 0.95,
        "volatility_mean": 1.05,
        "volatility_sigma": 0.28,
        "respawn_model": "negbin",
        "respawn_mean": 6.5,
        "respawn_dispersion": 3.5,
        "neutral_death_rate": 0.01,
        "lost_kill_rate": 0.035,
        "transfer_kill_rate": 0.05,
        "revive_knock_mean": 10.0,
        "mp_pressure_enabled": True,
        "mp_win_penalty": 0.13,
        "mp_kill_penalty": 0.05,
        "mp_pressure_lost_kill_multiplier": 1.25,
    },
    "apac_n": {
        # Calibrated against 4 historical APAC North Pro League finals
        # (2024 S1/S2, 2025 S1/S2): mean 8.75 games. The previous preset
        # already matched almost exactly (8.81 vs 8.75), so no change.
        "strength_sigma": 0.30,
        "rank_beta": 0.85,
        "kill_beta": 0.75,
        "win_beta": 0.65,
        "consistency_beta": 0.40,
        "placement_fight_correlation": 0.45,
        "placement_win_correlation": 0.35,
        "base_match_noise": 1.00,
        "volatility_mean": 1.10,
        "volatility_sigma": 0.30,
        "respawn_model": "negbin",
        "respawn_mean": 7.0,
        "respawn_dispersion": 3.0,
        "neutral_death_rate": 0.01,
        "lost_kill_rate": 0.04,
        "transfer_kill_rate": 0.06,
        "revive_knock_mean": 12.0,
        "mp_pressure_enabled": True,
        "mp_win_penalty": 0.15,
        "mp_kill_penalty": 0.05,
        "mp_pressure_lost_kill_multiplier": 1.35,
    },
    "apac_s": {
        # Calibrated against 4 historical APAC South Pro League finals
        # (2024 S1/S2, 2025 S1/S2): mean 8.00 games. Slightly shorter
        # than APAC-N, slightly longer than Americas.
        "strength_sigma": 0.42,
        "rank_beta": 0.95,
        "kill_beta": 0.72,
        "win_beta": 0.85,
        "consistency_beta": 0.45,
        "placement_fight_correlation": 0.52,
        "placement_win_correlation": 0.42,
        "base_match_noise": 0.82,
        "volatility_mean": 0.98,
        "volatility_sigma": 0.25,
        "respawn_model": "negbin",
        "respawn_mean": 6.5,
        "respawn_dispersion": 3.5,
        "neutral_death_rate": 0.01,
        "lost_kill_rate": 0.030,
        "transfer_kill_rate": 0.06,
        "revive_knock_mean": 11.0,
        "mp_pressure_enabled": True,
        "mp_win_penalty": 0.12,
        "mp_kill_penalty": 0.06,
        "mp_pressure_lost_kill_multiplier": 1.30,
    },
}


def apply_region_profile(cfg: SimulationConfig, name: str) -> SimulationConfig:
    """Return a new SimulationConfig with the named region's values applied."""
    if name == "custom":
        return replace(cfg, region_profile="custom")
    if name not in REGION_PROFILES:
        raise ValueError(
            f"unknown region profile: {name}. "
            f"choices: custom, {', '.join(REGION_PROFILES.keys())}"
        )
    overrides = REGION_PROFILES[name]
    return replace(cfg, region_profile=name, **overrides)  # type: ignore[arg-type]
