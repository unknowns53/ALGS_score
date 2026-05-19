"""Simulation configuration and regional presets."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal


RespawnModel = Literal["poisson", "negbin"]
StartingPointsMode = Literal["none", "seeded", "custom"]
RegionProfile = Literal["custom", "americas", "emea", "apac_n", "apac_s", "global"]
# Cycle 14 (2026-05): "wb_eb" composes the finals lobby as the top
# (wb_top_n + eb_top_n) teams of a larger pool_size population — the
# physical analogue of ALGS Global Finals where 20 finalists are the
# survivors of a Winners Bracket (top 10) and Elimination Bracket
# (next 10) stage drawn from a ~40-team Group Stage pool. "normal" is
# the legacy direct-sample mode used by all regional Pro League finals.
LobbyComposition = Literal["normal", "wb_eb"]


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
    # Cycle 14 (2026-05): lobby composition model.
    #   "normal" — direct multivariate-normal sample of num_teams teams.
    #             Used by regional Pro League finals.
    #   "wb_eb"  — sample a `pool_size`-team population, then select the
    #             composite top (wb_top_n + eb_top_n) into the finals
    #             lobby. Models the ALGS Global Finals where 20 finalists
    #             come from the Group Stage's top 20 (10 via Winners
    #             Bracket, 10 via Elimination Bracket).
    lobby_composition: LobbyComposition = "normal"
    pool_size: int = 40
    wb_top_n: int = 10
    eb_top_n: int = 10
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
        # Cycle 14 (2026-05): 5-component bayesian fit re-run under the
        # new err function with common k_scale = obs_total / 20 (replaces
        # the per-component normalize that gave p20 ~360x weight). Best:
        #   sigma=0.307, lost_kill=0.031, PKF=0.85, respawn=11.6,
        #   mp_win=0.000.
        # sim mean_end=7.74 vs obs 7.50, p1=8.99 vs 9.03, p10=2.62 vs
        # 2.37, p20=1.04 vs 1.60, total=64.52 vs 61.90. err=0.0429.
        # lost_kill moved off its cycle-13 lower edge (0.020 → 0.031);
        # mp_win_penalty stays at lower edge (0.000); respawn_mean=11.6
        # near but no longer at the upper edge. Americas remains the
        # highest-total-kill region (obs 61.90), so respawn supply
        # naturally sits near the upper end of the search space.
        "strength_sigma": 0.307,
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
        "respawn_mean": 11.6,
        "respawn_dispersion": 4.0,
        "neutral_death_rate": 0.03,
        "lost_kill_rate": 0.031,
        "transfer_kill_rate": 0.05,
        "revive_knock_mean": 13.0,
        "placement_kill_sharpness": 0.85,
        "mp_pressure_enabled": True,
        "mp_win_penalty": 0.000,
        "mp_kill_penalty": 0.04,
        "mp_pressure_lost_kill_multiplier": 1.15,
    },
    "emea": {
        # Calibrated against 4 historical EMEA Pro League finals
        # (2024 S1/S2, 2025 S1/S2): mean 8.50 games. EMEA is much more
        # contested than the "structured & low chaos" stereotype, so
        # parity is closer to APAC-N levels.
        # Cycle 14 (2026-05): 5-component bayesian fit re-run with new
        # err (common k_scale). Best:
        #   sigma=0.349, lost_kill=0.035, PKF=1.02, respawn=7.2,
        #   mp_win=0.468.
        # sim mean_end=8.46 vs obs 8.50, p1=9.44 vs 9.44, p10=2.28 vs
        # 2.53, p20=0.78 vs 0.56, total=60.11 vs 56.50. err=0.0181 —
        # the best fit across all five regions in this cycle.
        # All five params now interior; cycle-13's mp_win=0.500 upper
        # edge resolved (now 0.468).
        "strength_sigma": 0.349,
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
        "respawn_mean": 7.2,
        "respawn_dispersion": 3.5,
        "neutral_death_rate": 0.03,
        "lost_kill_rate": 0.035,
        "transfer_kill_rate": 0.05,
        "revive_knock_mean": 7.0,
        "placement_kill_sharpness": 1.02,
        "mp_pressure_enabled": True,
        "mp_win_penalty": 0.468,
        "mp_kill_penalty": 0.05,
        "mp_pressure_lost_kill_multiplier": 1.25,
    },
    "apac_n": {
        # Calibrated against 4 historical APAC North Pro League finals
        # (2024 S1/S2, 2025 S1/S2): mean 8.75 games.
        # Cycle 14 (2026-05): 5-component bayesian fit re-run with new
        # err (common k_scale). Best:
        #   sigma=0.268, lost_kill=0.020, PKF=0.98, respawn=12.0,
        #   mp_win=0.277.
        # sim mean_end=8.40 vs obs 8.75, p1=9.80 vs 9.97, p10=2.56 vs
        # 3.51, p20=0.96 vs 0.80, total=65.47 vs 55.40. err=0.1615 —
        # the largest of the five regions in this cycle.
        # APAC-N's residual is concentrated in p10 (sim 2.56 = 73% of
        # observed 3.51) and total kills (sim 65.47 vs obs 55.40, +18%).
        # The fit traded mid-tier under-prediction for over-supply of
        # bottom kills via the upper-bound respawn_mean. Two edge-pins
        # remain: respawn_mean=12.0 (upper) and lost_kill_rate=0.020
        # (lower). mp_win_penalty moved well off cycle-13's 0.500 edge.
        # The p10 vs total tension here likely needs a non-normal team
        # distribution (top-cluster) to resolve cleanly; see the global
        # preset note below.
        "strength_sigma": 0.268,
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
        "respawn_mean": 12.0,
        "respawn_dispersion": 3.0,
        "neutral_death_rate": 0.03,
        "lost_kill_rate": 0.020,
        "transfer_kill_rate": 0.06,
        "revive_knock_mean": 9.0,
        "placement_kill_sharpness": 0.98,
        "mp_pressure_enabled": True,
        "mp_win_penalty": 0.277,
        "mp_kill_penalty": 0.05,
        "mp_pressure_lost_kill_multiplier": 1.35,
    },
    "apac_s": {
        # Calibrated against 4 historical APAC South Pro League finals
        # (2024 S1/S2, 2025 S1/S2): mean 8.00 games. Slightly shorter
        # than APAC-N, slightly longer than Americas. The 2024 S1/S2
        # data was backfilled from Liquipedia wikitext in efe9597
        # (200 + 140 rows, full top-20 coverage).
        # Cycle 14 (2026-05): 5-component bayesian fit re-run with new
        # err (common k_scale). Best:
        #   sigma=0.402, lost_kill=0.054, PKF=0.95, respawn=9.8,
        #   mp_win=0.359.
        # sim mean_end=7.96 vs obs 8.00, p1=9.14 vs 9.22, p10=2.40 vs
        # 2.69, p20=0.87 vs 0.59, total=61.06 vs 57.91. err=0.0225.
        # All five params interior; cycle-13's mp_win=0.500 edge fully
        # resolved (now 0.359), and lost_kill dropped from 0.091 to
        # 0.054 under the rebalanced err.
        "strength_sigma": 0.402,
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
        "respawn_mean": 9.8,
        "respawn_dispersion": 3.5,
        "neutral_death_rate": 0.03,
        "lost_kill_rate": 0.054,
        "transfer_kill_rate": 0.06,
        "revive_knock_mean": 7.0,
        "placement_kill_sharpness": 0.95,
        "mp_pressure_enabled": True,
        "mp_win_penalty": 0.359,
        "mp_kill_penalty": 0.06,
        "mp_pressure_lost_kill_multiplier": 1.30,
    },
    "global": {
        # Cross-regional Global Finals lobbies (Y4 Split 1/Split 2 Playoffs
        # Finals, 2025 Championship, 2025 Midseason Playoffs Finals — 4
        # events, 36 matches total). 20 finalists come from the Group
        # Stage's top survivors (Winners Bracket 10 + Elimination
        # Bracket 10 out of a ~40-team Group Stage pool). Cycle 14
        # (2026-05) introduces lobby_composition="wb_eb" to model this
        # pool→top-20 selection — see LobbyComposition above.
        # Earlier cycles assumed an invitation-only top-cluster, but
        # that was incorrect; the lobby is the order-statistic top of
        # a larger Group Stage population.
        #
        # Cycle 14 (2026-05): 5-component bayesian fit re-run with both
        # (a) the new err function (common k_scale = obs_total / 20),
        # which removed the 360x weighting imbalance that pinned earlier
        # cycles to bottom-zero, and (b) the wb_eb lobby composition,
        # which narrows the lobby strength distribution naturally via
        # order-statistic selection. Best:
        #   sigma=0.265, lost_kill=0.052, PKF=1.08, respawn=6.8,
        #   mp_win=0.442.
        # sim mean_end=9.08 vs obs 9.00, p1=9.51 vs 9.47, p10=2.15 vs
        # 2.53, p20=0.73 vs 0.08, total=58.50 vs 57.47. err=0.0681 —
        # cycle-13's 0.4419 (sigma=0.700 upper-edge pin) is fully
        # resolved; sigma now sits cleanly interior at 0.265, and all
        # five params are interior.
        #
        # Residual: p20 sim 0.73 vs obs 0.08. p20 is the
        # most volatile observable (driven by single-match wipe-and-
        # third-party events at the lobby bottom) and is not expected
        # to be exactly fit by a smooth strength/PKF model; the new
        # err weights it on the common scale so its residual no longer
        # distorts the rest of the fit.
        "lobby_composition": "wb_eb",
        "pool_size": 40,
        "wb_top_n": 10,
        "eb_top_n": 10,
        "strength_sigma": 0.265,
        "rank_beta": 0.95,
        "kill_beta": 0.80,
        "win_beta": 0.80,
        "consistency_beta": 0.42,
        "placement_fight_correlation": 0.55,
        "placement_win_correlation": 0.45,
        "base_match_noise": 0.85,
        "volatility_mean": 1.00,
        "volatility_sigma": 0.25,
        "respawn_model": "negbin",
        "respawn_mean": 6.8,
        "respawn_dispersion": 3.5,
        "neutral_death_rate": 0.03,
        "lost_kill_rate": 0.052,
        "transfer_kill_rate": 0.05,
        "revive_knock_mean": 9.0,
        "placement_kill_sharpness": 1.08,
        "mp_pressure_enabled": True,
        "mp_win_penalty": 0.442,
        "mp_kill_penalty": 0.05,
        "mp_pressure_lost_kill_multiplier": 1.25,
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
