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
# Calibrated from 4 Pro League / Championship Finals: winning teams average
# ~7.4 kills in matches they place 1st and ~0.7 kills when finishing 16th-20th.
# Lobby average is ~52 kills / 20 teams = 2.6 kills/team, so 1st-place
# coefficient should be ~7.4/2.6 ≈ 2.85 and bottom ~0.7/2.6 ≈ 0.27.
PLACEMENT_KILL_FACTOR: tuple[float, ...] = (
    2.50, 2.00, 1.70, 1.40, 1.20,
    1.00, 0.90, 0.80, 0.70, 0.60,
    0.50, 0.45, 0.40, 0.35, 0.30,
    0.25, 0.25, 0.20, 0.20, 0.20,
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

    # Team pool for multi-lobby formats (Swiss, RoundRobin, DoubleElim).
    # Match Point and FixedMatches use num_teams; the 30-team formats read
    # this field instead so the two configurations can coexist.
    tournament_team_pool: int = 30

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

    # Kill credit model.
    # neutral_death_rate raised from 0.01 to 0.03 after empirical lobby-kill
    # check: per-game total kills in 4 Pro League / Champs finals averaged
    # ~52 (range 46-66), while the previous defaults predicted ~60. Per-region
    # lost_kill_rate is tuned in REGION_PROFILES (americas 0.06, emea 0.07,
    # apac_n 0.10, apac_s 0.065) to land on the regional kill-total target.
    neutral_death_rate: float = 0.03
    lost_kill_rate: float = 0.06
    transfer_kill_rate: float = 0.05
    revive_knock_mean: float = 10.0
    chaos_multiplier: float = 1.0
    mp_pressure_lost_kill_multiplier: float = 1.25
    # Sharpness of the per-placement kill allocation gradient.
    # 1.0 keeps PLACEMENT_KILL_FACTOR as-is (1st:20th ~ 12:1).
    # 0.0 = uniform across placements (kills proportional to fight skill only).
    # >1.0 = even steeper top-heavy distribution. Implemented by log-space
    # scaling around the geometric mean of the base tuple.
    placement_kill_sharpness: float = 1.0

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
        # Cycle 5 (2026-05): grid search against per-match standings
        # (30 matches) re-set the 4 fittable knobs to
        # strength_sigma=0.35, lost_kill_rate=0.04, revive_knock_mean=13.0,
        # placement_kill_sharpness=0.60 (new key). The fit picks the
        # shortest sim achievable in the grid (sim 8.14 vs obs 7.50) — the
        # 30-match sample is dominated by 2025 S2 long lobbies, so the
        # observed mean drifts above the docs/data_validation.md baseline
        # but this is the best in-grid solution.
        "strength_sigma": 0.35,
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
        "neutral_death_rate": 0.03,
        "lost_kill_rate": 0.04,
        "transfer_kill_rate": 0.05,
        "revive_knock_mean": 13.0,
        "placement_kill_sharpness": 0.60,
        "mp_pressure_enabled": True,
        "mp_win_penalty": 0.11,
        "mp_kill_penalty": 0.04,
        "mp_pressure_lost_kill_multiplier": 1.15,
    },
    "emea": {
        # Calibrated against 4 historical EMEA Pro League finals
        # (2024 S1/S2, 2025 S1/S2): mean 8.50 games. EMEA is much more
        # contested than the "structured & low chaos" stereotype, so
        # parity is closer to APAC-N levels.
        # Cycle 5 (2026-05): grid search (34 matches) confirmed
        # strength_sigma=0.27 (tighter than previous 0.30) but bumped
        # lost_kill_rate 0.07 -> 0.12 (top of grid) and PKF to 1.20.
        # Excellent fit (err 0.0006): sim 8.61 vs obs 8.50, p1 9.64 vs 9.44,
        # p20 0.56 vs 0.56. EMEA is the cleanest fit of all four regions.
        "strength_sigma": 0.27,
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
        "neutral_death_rate": 0.03,
        "lost_kill_rate": 0.12,
        "transfer_kill_rate": 0.05,
        "revive_knock_mean": 7.0,
        "placement_kill_sharpness": 1.20,
        "mp_pressure_enabled": True,
        "mp_win_penalty": 0.17,
        "mp_kill_penalty": 0.05,
        "mp_pressure_lost_kill_multiplier": 1.25,
    },
    "apac_n": {
        # Calibrated against 4 historical APAC North Pro League finals
        # (2024 S1/S2, 2025 S1/S2): mean 8.75 games.
        # Cycle 5 (2026-05): grid search (35 matches) re-set
        # strength_sigma 0.27 -> 0.35 (more parity than previously
        # estimated — the 13-game outlier overstated parity in cycle 4),
        # lost_kill_rate 0.10 -> 0.04, revive_knock_mean 12.0 -> 9.0,
        # PKF=1.00. sim 8.39 vs obs 8.75 (err 0.012). The PKF=1.00 result
        # is interesting: APAC-N's long tournaments are NOT driven by a
        # flatter kill distribution but by tighter parity (strength_sigma).
        "strength_sigma": 0.35,
        "rank_beta": 0.85,
        "kill_beta": 0.75,
        "win_beta": 0.55,
        "consistency_beta": 0.40,
        "placement_fight_correlation": 0.45,
        "placement_win_correlation": 0.35,
        "base_match_noise": 1.00,
        "volatility_mean": 1.10,
        "volatility_sigma": 0.30,
        "respawn_model": "negbin",
        "respawn_mean": 7.0,
        "respawn_dispersion": 3.0,
        "neutral_death_rate": 0.03,
        "lost_kill_rate": 0.04,
        "transfer_kill_rate": 0.06,
        "revive_knock_mean": 9.0,
        "placement_kill_sharpness": 1.00,
        "mp_pressure_enabled": True,
        "mp_win_penalty": 0.15,
        "mp_kill_penalty": 0.05,
        "mp_pressure_lost_kill_multiplier": 1.35,
    },
    "apac_s": {
        # Calibrated against 4 historical APAC South Pro League finals
        # (2024 S1/S2, 2025 S1/S2): mean 8.00 games. Slightly shorter
        # than APAC-N, slightly longer than Americas.
        # Cycle 5 (2026-05): grid search (27 matches, 20 complete — the
        # 2024 S1 Games 6-10 and 2024 S2 Game 7 standings are missing in
        # Liquipedia coverage) suggests strength_sigma=0.27,
        # lost_kill_rate=0.04, revive_knock_mean=7.0, PKF=0.60.
        # sim 8.65 vs obs 8.00 (err 0.097). Smallest data set of the four
        # regions — the fit drifts long, but in-grid the closest solution.
        "strength_sigma": 0.27,
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
        "neutral_death_rate": 0.03,
        "lost_kill_rate": 0.04,
        "transfer_kill_rate": 0.06,
        "revive_knock_mean": 7.0,
        "placement_kill_sharpness": 0.60,
        "mp_pressure_enabled": True,
        "mp_win_penalty": 0.14,
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
