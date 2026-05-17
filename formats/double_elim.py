"""Double-elimination format adapted to a 30-team Apex bracket.

Structure (simplified ALGS Playoffs):
  1. Winners Bracket (WB) — seed 1-20 play 4 matches in one 20-team lobby.
     Top 10 by cumulative go to Grand Finals (GF) seeded as winners.
     Bottom 10 fall to the Losers Bracket.
  2. Losers Bracket (LB) — WB bottom 10 plus seed 21-30 (10 teams) play
     4 matches in one 20-team lobby. Top 10 by cumulative qualify for GF.
  3. Grand Finals — 20 teams in one lobby playing a short Match Point
     format (threshold 30, max 8 matches). Cumulative score is RESET
     before GF; WB seeding doesn't carry over to keep GF results
     interpretable.

Champion is decided by the GF stage. Pool-wide finish order is composed
from GF result + LB/WB elimination ordering.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from config import SimulationConfig
from formats.base import FormatResult, TournamentFormat, compute_leader
from formats.fixed_matches import _resolve_ties
from formats.lobby_assignment import run_lobby_match
from match_sim import MatchResult, simulate_match
from teams import generate_teams, teams_to_arrays


def _run_fixed_stage(
    teams_arr: dict[str, np.ndarray],
    stage_team_ids: list[int],
    n_matches: int,
    cfg: SimulationConfig,
    rng: np.random.Generator,
    pool_size: int,
    match_offset: int,
) -> tuple[list[MatchResult], np.ndarray]:
    """Run a fixed N-match stage in a single lobby of `len(stage_team_ids)`.

    Returns (pool-space match results, pool-space cumulative for the stage).
    """
    pool_cum = np.zeros(pool_size, dtype=int)
    match_results: list[MatchResult] = []
    for i in range(n_matches):
        match_idx = match_offset + i + 1
        mr = run_lobby_match(
            teams_arr, stage_team_ids, match_idx, cfg, rng, pool_size
        )
        match_results.append(mr)
        pool_cum = pool_cum + mr.team_scores
    return match_results, pool_cum


def _run_mp_stage(
    teams_arr: dict[str, np.ndarray],
    stage_team_ids: list[int],
    threshold: int,
    max_matches: int,
    cfg: SimulationConfig,
    rng: np.random.Generator,
    pool_size: int,
    match_offset: int,
) -> tuple[list[MatchResult], np.ndarray, int | None, bool]:
    """Run a Match Point stage in a single lobby. Returns:
        (pool-space match results, pool-space stage cumulative,
         champion pool team_id or None, ended flag)
    """
    from formats.lobby_assignment import _subset_teams_arr

    sub_arr, global_ids = _subset_teams_arr(teams_arr, stage_team_ids)
    lobby_size = global_ids.size
    cfg_stage = replace(
        cfg,
        num_teams=lobby_size,
        starting_points_mode="none",
        custom_starting_points=None,
        match_point_threshold=threshold,
    )
    local_cum = np.zeros(lobby_size, dtype=int)
    pool_match_results: list[MatchResult] = []
    pool_cum = np.zeros(pool_size, dtype=int)
    champion_pool_id: int | None = None
    ended = False

    for i in range(max_matches):
        match_idx = match_offset + i + 1
        eligible_before = local_cum >= threshold
        local_mr = simulate_match(sub_arr, local_cum, match_idx, cfg_stage, rng)
        local_cum = local_cum + local_mr.team_scores

        # Map local match result to pool-space.
        full_placement_points = np.zeros(pool_size, dtype=int)
        full_team_kills = np.zeros(pool_size, dtype=int)
        full_team_scores = np.zeros(pool_size, dtype=int)
        full_placement_points[global_ids] = local_mr.placement_points
        full_team_kills[global_ids] = local_mr.team_kills
        full_team_scores[global_ids] = local_mr.team_scores
        full_eligible = np.zeros(pool_size, dtype=bool)
        full_eligible[global_ids] = local_mr.eligible_at_start
        global_placements = global_ids[local_mr.placements]
        pool_mr = MatchResult(
            match_index=match_idx,
            placements=global_placements.astype(int),
            winner_team_id=int(global_placements[0]),
            placement_points=full_placement_points,
            team_kills=full_team_kills,
            team_scores=full_team_scores,
            eligible_at_start=full_eligible,
            respawned_players=local_mr.respawned_players,
            champion_remaining_players=local_mr.champion_remaining_players,
            death_events=local_mr.death_events,
            scored_kills=local_mr.scored_kills,
            neutral_deaths=local_mr.neutral_deaths,
            lost_kill_points=local_mr.lost_kill_points,
            transferred_kills=local_mr.transferred_kills,
            revived_knocks=local_mr.revived_knocks,
            total_knocks=local_mr.total_knocks,
        )
        pool_match_results.append(pool_mr)

        # MP win check: local winner whose pre-match score >= threshold.
        local_winner = int(local_mr.placements[0])
        if eligible_before[local_winner]:
            champion_pool_id = int(global_ids[local_winner])
            ended = True
            break

    pool_cum[global_ids] = local_cum
    if not ended and lobby_size > 0:
        champion_pool_id = int(global_ids[int(np.argmax(local_cum))])
    return pool_match_results, pool_cum, champion_pool_id, ended


@dataclass
class DoubleEliminationFormat(TournamentFormat):
    """30-team double-elimination: WB(4) → LB(4) → GF(short MP)."""

    name: str = "double_elim"
    wb_matches: int = 4
    lb_matches: int = 4
    gf_threshold: int = 30
    gf_max_matches: int = 8
    pool_size: int = 30

    def __post_init__(self) -> None:
        if self.pool_size != 30:
            raise ValueError(
                f"DoubleEliminationFormat assumes pool_size=30, got {self.pool_size}"
            )

    def simulate(
        self, cfg: SimulationConfig, rng: np.random.Generator
    ) -> FormatResult:
        teams = generate_teams(cfg, rng, n_override=self.pool_size)
        teams_arr = teams_to_arrays(teams)
        seed_array = teams_arr["seed"]
        # Map seed -> team_id (seed 1..30, team_ids 0..29).
        seed_to_id = {int(seed_array[t]): int(t) for t in range(self.pool_size)}

        # Stage 1: Winners Bracket — seed 1-20.
        wb_team_ids = [seed_to_id[s] for s in range(1, 21)]
        wb_results, wb_cum = _run_fixed_stage(
            teams_arr, wb_team_ids, self.wb_matches, cfg, rng,
            self.pool_size, match_offset=0,
        )
        # Sort WB teams by stage cumulative descending; top 10 -> GF, bottom 10 -> LB.
        wb_pool_scores = [(tid, int(wb_cum[tid])) for tid in wb_team_ids]
        wb_pool_scores.sort(key=lambda kv: (-kv[1], teams[kv[0]].seed))
        wb_top10 = [tid for tid, _ in wb_pool_scores[:10]]
        wb_bot10 = [tid for tid, _ in wb_pool_scores[10:]]

        # Stage 2: Losers Bracket — WB bottom 10 + seed 21-30.
        lb_initial = [seed_to_id[s] for s in range(21, 31)]
        lb_team_ids = wb_bot10 + lb_initial
        lb_results, lb_cum = _run_fixed_stage(
            teams_arr, lb_team_ids, self.lb_matches, cfg, rng,
            self.pool_size, match_offset=self.wb_matches,
        )
        lb_pool_scores = [(tid, int(lb_cum[tid])) for tid in lb_team_ids]
        lb_pool_scores.sort(key=lambda kv: (-kv[1], teams[kv[0]].seed))
        lb_top10 = [tid for tid, _ in lb_pool_scores[:10]]
        lb_bot10 = [tid for tid, _ in lb_pool_scores[10:]]

        # Stage 3: Grand Finals — 20 teams, short Match Point.
        gf_team_ids = wb_top10 + lb_top10
        gf_offset = self.wb_matches + self.lb_matches
        gf_results, gf_cum, gf_champion_id, gf_ended = _run_mp_stage(
            teams_arr, gf_team_ids,
            threshold=self.gf_threshold,
            max_matches=self.gf_max_matches,
            cfg=cfg,
            rng=rng,
            pool_size=self.pool_size,
            match_offset=gf_offset,
        )

        # Compose overall match list and final pool-wide cumulative.
        match_results = wb_results + lb_results + gf_results
        pool_cum = wb_cum + lb_cum + gf_cum

        # Build leader_history at match boundaries: snapshot after each match
        # in the order they were played (WB, LB, GF).
        leader_history = [compute_leader(np.zeros(self.pool_size, dtype=int))]
        running = np.zeros(self.pool_size, dtype=int)
        for mr in match_results:
            running = running + mr.team_scores
            leader_history.append(compute_leader(running))

        # Finish order: GF teams ranked by GF stage cumulative, then LB bottom
        # ordered by LB stage, then anything left ordered by WB stage.
        gf_order = sorted(gf_team_ids, key=lambda t: (-int(gf_cum[t]), teams[t].seed))
        # GF champion forces position 0.
        if gf_champion_id is not None and gf_champion_id in gf_order:
            gf_order.remove(gf_champion_id)
            gf_order.insert(0, gf_champion_id)
        lb_bot_order = sorted(lb_bot10, key=lambda t: (-int(lb_cum[t]), teams[t].seed))
        finish_order = gf_order + lb_bot_order

        champion_id = gf_champion_id if gf_champion_id is not None else int(finish_order[0])
        champion_seed = int(teams[champion_id].seed)

        return FormatResult(
            format_name=self.name,
            ended=gf_ended,
            ending_match=len(match_results),
            champion_team_id=champion_id,
            champion_seed=champion_seed,
            teams=teams,
            cumulative_scores=pool_cum,
            match_results=match_results,
            leader_history=np.asarray(leader_history, dtype=int),
            extras={
                "finish_order": finish_order,
                "wb_matches": self.wb_matches,
                "lb_matches": self.lb_matches,
                "gf_matches": len(gf_results),
                "gf_ended": gf_ended,
                "gf_threshold": self.gf_threshold,
                "gf_team_ids": gf_team_ids,
                "wb_team_ids": wb_team_ids,
                "lb_team_ids": lb_team_ids,
                "pool_size": self.pool_size,
            },
        )
