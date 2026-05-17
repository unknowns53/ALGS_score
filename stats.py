"""Aggregate simulation results into summary statistics."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from config import SimulationConfig
from teams import composite_strength
from tournament_sim import TournamentResult


@dataclass
class SummaryResult:
    n_sims: int
    region_profile: str
    starting_points_mode: str
    match_point_threshold: int

    # Ending-match distribution
    ending_match_distribution: dict[int, float] = field(default_factory=dict)
    cumulative_distribution: dict[int, float] = field(default_factory=dict)

    mean: float = 0.0
    median: float = 0.0
    mode: int = 0
    p05: int = 0
    p25: int = 0
    p75: int = 0
    p95: int = 0

    prob_exceeds_10: float = 0.0
    prob_exceeds_12: float = 0.0
    prob_exceeds_15: float = 0.0

    # Champion
    champion_seed_distribution: dict[int, float] = field(default_factory=dict)
    champion_strength_percentile_mean: float = 0.0
    champion_strength_percentile_std: float = 0.0

    # Match-point telemetry
    avg_first_mp_match: float = 0.0
    avg_eligible_at_ending_match_start: float = 0.0
    avg_teams_reached_match_point: float = 0.0
    avg_score_of_first_mp_team: float = 0.0

    # Per-match averages
    avg_eligible_at_match_start: float = 0.0
    avg_respawned_players: float = 0.0
    avg_champion_remaining_players: float = 0.0
    avg_death_events: float = 0.0
    avg_scored_kills: float = 0.0
    avg_neutral_deaths: float = 0.0
    avg_lost_kill_points: float = 0.0
    avg_transferred_kills: float = 0.0
    avg_revived_knocks: float = 0.0
    avg_total_knocks: float = 0.0
    avg_total_lobby_score: float = 0.0
    avg_top_team_score: float = 0.0
    avg_score_gap_1st_2nd: float = 0.0

    # Correlations
    corr_respawned_vs_lobby_score: float = 0.0
    corr_lost_kills_vs_lobby_score: float = 0.0
    corr_lost_kills_vs_tournament_length: float = 0.0
    corr_eligible_count_vs_end_probability: float = 0.0


def _composite_strength(team) -> float:
    """Deprecated alias retained for backward compatibility — use teams.composite_strength."""
    return composite_strength(team)


def summarize(results: list[TournamentResult], cfg: SimulationConfig) -> SummaryResult:
    n = len(results)
    if n == 0:
        raise ValueError("no results to summarise")

    lengths = np.array([r.ending_match for r in results], dtype=int)

    counter = Counter(int(x) for x in lengths)
    min_m, max_m = int(lengths.min()), int(lengths.max())
    dist: dict[int, float] = {}
    cum: dict[int, float] = {}
    running = 0.0
    for m in range(min_m, max_m + 1):
        p = counter.get(m, 0) / n
        dist[m] = p
        running += p
        cum[m] = running

    mean = float(lengths.mean())
    median = float(np.median(lengths))
    mode = int(counter.most_common(1)[0][0])
    p05, p25, p75, p95 = (int(np.percentile(lengths, q)) for q in (5, 25, 75, 95))

    prob_exceeds_10 = float((lengths > 10).mean())
    prob_exceeds_12 = float((lengths > 12).mean())
    prob_exceeds_15 = float((lengths > 15).mean())

    # Champion stats
    seed_counter: Counter[int] = Counter()
    champ_strength_percentiles: list[float] = []
    for r in results:
        if r.champion_team_id is None:
            continue
        seed_counter[int(r.champion_seed)] += 1
        strengths = np.array([_composite_strength(t) for t in r.teams])
        rank_pct = (strengths <= strengths[r.champion_team_id]).mean() * 100.0
        champ_strength_percentiles.append(float(rank_pct))

    seed_total = sum(seed_counter.values()) or 1
    champion_seed_distribution = {
        int(s): seed_counter[s] / seed_total for s in sorted(seed_counter)
    }
    champion_strength_percentile_mean = (
        float(np.mean(champ_strength_percentiles)) if champ_strength_percentiles else 0.0
    )
    champion_strength_percentile_std = (
        float(np.std(champ_strength_percentiles)) if champ_strength_percentiles else 0.0
    )

    # MP telemetry
    first_mp_matches = [
        r.first_match_point_match for r in results if r.first_match_point_match is not None
    ]
    avg_first_mp_match = float(np.mean(first_mp_matches)) if first_mp_matches else 0.0
    avg_eligible_at_end = float(np.mean(
        [r.eligible_at_ending_match_start for r in results]
    ))
    avg_teams_reached_mp = float(np.mean([r.teams_reached_match_point for r in results]))

    # Score of first MP team at first eligibility: scan matches for the earliest team
    first_mp_scores: list[int] = []
    for r in results:
        if r.first_match_point_match is None:
            continue
        m_idx = r.first_match_point_match - 1  # 0-based index of that match
        running_scores = np.asarray(cfg.starting_points(), dtype=int).copy()
        # running_scores is the score AT THE START of match 1 (no matches played).
        # The first MP match is the first match where eligible_before has any True,
        # i.e. running_scores >= threshold at the start of that match.
        for k in range(m_idx):
            running_scores = running_scores + r.match_results[k].team_scores
        eligible_mask = running_scores >= cfg.match_point_threshold
        if eligible_mask.any():
            first_mp_scores.append(int(running_scores[eligible_mask].max()))
    avg_score_of_first_mp_team = (
        float(np.mean(first_mp_scores)) if first_mp_scores else 0.0
    )

    # Per-match aggregates: flatten across all matches in all results.
    match_eligibility = []
    match_respawn = []
    match_champ_remaining = []
    match_death_events = []
    match_scored = []
    match_neutral = []
    match_lost = []
    match_transferred = []
    match_revived = []
    match_total_knocks = []
    match_lobby_score = []
    match_top_score = []
    match_score_gap = []
    match_ends_here = []  # 1 if this match was the tournament's last (and an eligible team won)
    # Per-tournament aggregates for length correlations
    per_tour_total_lost = []
    per_tour_length = []

    for r in results:
        per_tour_length.append(r.ending_match)
        per_tour_total_lost.append(sum(m.lost_kill_points for m in r.match_results))
        last_idx = len(r.match_results) - 1  # 0-based
        for i, m in enumerate(r.match_results):
            match_eligibility.append(int(m.eligible_at_start.sum()))
            match_respawn.append(m.respawned_players)
            match_champ_remaining.append(m.champion_remaining_players)
            match_death_events.append(m.death_events)
            match_scored.append(m.scored_kills)
            match_neutral.append(m.neutral_deaths)
            match_lost.append(m.lost_kill_points)
            match_transferred.append(m.transferred_kills)
            match_revived.append(m.revived_knocks)
            match_total_knocks.append(m.total_knocks)
            total_lobby = int(m.team_scores.sum())
            match_lobby_score.append(total_lobby)
            sorted_scores = np.sort(m.team_scores)[::-1]
            match_top_score.append(int(sorted_scores[0]))
            match_score_gap.append(int(sorted_scores[0] - sorted_scores[1]))
            match_ends_here.append(1 if (i == last_idx and r.ended) else 0)

    arr_respawn = np.asarray(match_respawn)
    arr_lobby = np.asarray(match_lobby_score)
    arr_lost = np.asarray(match_lost)
    arr_eligibility = np.asarray(match_eligibility, dtype=float)
    arr_ends_here = np.asarray(match_ends_here, dtype=float)
    arr_tour_lost = np.asarray(per_tour_total_lost, dtype=float)
    arr_tour_length = np.asarray(per_tour_length, dtype=float)

    def _corr(a, b) -> float:
        if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
            return 0.0
        return float(np.corrcoef(a, b)[0, 1])

    summary = SummaryResult(
        n_sims=n,
        region_profile=cfg.region_profile,
        starting_points_mode=cfg.starting_points_mode,
        match_point_threshold=cfg.match_point_threshold,
        ending_match_distribution=dist,
        cumulative_distribution=cum,
        mean=mean,
        median=median,
        mode=mode,
        p05=p05, p25=p25, p75=p75, p95=p95,
        prob_exceeds_10=prob_exceeds_10,
        prob_exceeds_12=prob_exceeds_12,
        prob_exceeds_15=prob_exceeds_15,
        champion_seed_distribution=champion_seed_distribution,
        champion_strength_percentile_mean=champion_strength_percentile_mean,
        champion_strength_percentile_std=champion_strength_percentile_std,
        avg_first_mp_match=avg_first_mp_match,
        avg_eligible_at_ending_match_start=avg_eligible_at_end,
        avg_teams_reached_match_point=avg_teams_reached_mp,
        avg_score_of_first_mp_team=avg_score_of_first_mp_team,
        avg_eligible_at_match_start=float(np.mean(match_eligibility)),
        avg_respawned_players=float(np.mean(match_respawn)),
        avg_champion_remaining_players=float(np.mean(match_champ_remaining)),
        avg_death_events=float(np.mean(match_death_events)),
        avg_scored_kills=float(np.mean(match_scored)),
        avg_neutral_deaths=float(np.mean(match_neutral)),
        avg_lost_kill_points=float(np.mean(match_lost)),
        avg_transferred_kills=float(np.mean(match_transferred)),
        avg_revived_knocks=float(np.mean(match_revived)),
        avg_total_knocks=float(np.mean(match_total_knocks)),
        avg_total_lobby_score=float(np.mean(match_lobby_score)),
        avg_top_team_score=float(np.mean(match_top_score)),
        avg_score_gap_1st_2nd=float(np.mean(match_score_gap)),
        corr_respawned_vs_lobby_score=_corr(arr_respawn, arr_lobby),
        corr_lost_kills_vs_lobby_score=_corr(arr_lost, arr_lobby),
        corr_lost_kills_vs_tournament_length=_corr(arr_tour_lost, arr_tour_length),
        corr_eligible_count_vs_end_probability=_corr(arr_eligibility, arr_ends_here),
    )
    return summary


def to_json(summary: SummaryResult, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(summary)
    # JSON keys must be strings
    data["ending_match_distribution"] = {
        str(k): v for k, v in summary.ending_match_distribution.items()
    }
    data["cumulative_distribution"] = {
        str(k): v for k, v in summary.cumulative_distribution.items()
    }
    data["champion_seed_distribution"] = {
        str(k): v for k, v in summary.champion_seed_distribution.items()
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def to_csv(summary: SummaryResult, path: str | Path) -> None:
    """CSV with the ending-match distribution as the main table."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["match,probability,cumulative_probability"]
    for m in sorted(summary.ending_match_distribution.keys()):
        p = summary.ending_match_distribution[m]
        cp = summary.cumulative_distribution[m]
        lines.append(f"{m},{p:.6f},{cp:.6f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def format_summary_text(summary: SummaryResult) -> str:
    lines: list[str] = []
    lines.append("ALGS Match Point Simulation Summary")
    lines.append("==================================")
    lines.append("")
    lines.append(f"Simulations: {summary.n_sims}")
    lines.append(f"Region profile: {summary.region_profile}")
    lines.append(f"Starting points: {summary.starting_points_mode}")
    lines.append(f"Match Point threshold: {summary.match_point_threshold}")
    lines.append("")
    lines.append("Ending match:")
    lines.append(f"- mean:   {summary.mean:.2f}")
    lines.append(f"- median: {summary.median:.1f}")
    lines.append(f"- mode:   {summary.mode}")
    lines.append(f"- p05:    {summary.p05}")
    lines.append(f"- p25:    {summary.p25}")
    lines.append(f"- p75:    {summary.p75}")
    lines.append(f"- p95:    {summary.p95}")
    lines.append(f"- P(length > 10): {summary.prob_exceeds_10:.3f}")
    lines.append(f"- P(length > 12): {summary.prob_exceeds_12:.3f}")
    lines.append(f"- P(length > 15): {summary.prob_exceeds_15:.3f}")
    lines.append("")
    lines.append("Distribution:")
    lines.append("match, probability, cumulative_probability")
    for m in sorted(summary.ending_match_distribution.keys()):
        p = summary.ending_match_distribution[m]
        cp = summary.cumulative_distribution[m]
        lines.append(f"{m}, {p:.3f}, {cp:.3f}")
    lines.append("")
    lines.append("Champion:")
    if summary.champion_seed_distribution:
        top_seeds = sorted(
            summary.champion_seed_distribution.items(), key=lambda kv: -kv[1]
        )[:5]
        for seed, prob in top_seeds:
            lines.append(f"- seed {seed:>2}: {prob:.3f}")
    lines.append(
        f"- strength percentile: mean {summary.champion_strength_percentile_mean:.1f} "
        f"(sd {summary.champion_strength_percentile_std:.1f})"
    )
    lines.append("")
    lines.append("Telemetry:")
    lines.append(f"- avg first MP match: {summary.avg_first_mp_match:.2f}")
    lines.append(f"- avg eligible teams at ending match start: "
                 f"{summary.avg_eligible_at_ending_match_start:.2f}")
    lines.append(f"- avg teams that reached MP per tournament: "
                 f"{summary.avg_teams_reached_match_point:.2f}")
    lines.append(f"- avg score of first MP team: {summary.avg_score_of_first_mp_team:.1f}")
    lines.append(f"- avg eligible teams per match: "
                 f"{summary.avg_eligible_at_match_start:.2f}")
    lines.append(f"- avg respawned players per match: {summary.avg_respawned_players:.2f}")
    lines.append(f"- avg champion remaining players: "
                 f"{summary.avg_champion_remaining_players:.2f}")
    lines.append(f"- avg death events per match: {summary.avg_death_events:.2f}")
    lines.append(f"- avg scored kills per match: {summary.avg_scored_kills:.2f}")
    lines.append(f"- avg neutral deaths per match: {summary.avg_neutral_deaths:.2f}")
    lines.append(f"- avg lost kill points per match: {summary.avg_lost_kill_points:.2f}")
    lines.append(f"- avg transferred kills per match: {summary.avg_transferred_kills:.2f}")
    lines.append(f"- avg revived knocks per match: {summary.avg_revived_knocks:.2f}")
    lines.append(f"- avg total knocks per match: {summary.avg_total_knocks:.2f}")
    lines.append(f"- avg total lobby score per match: {summary.avg_total_lobby_score:.2f}")
    lines.append(f"- avg top team score per match: {summary.avg_top_team_score:.2f}")
    lines.append(f"- avg score gap 1st-2nd per match: {summary.avg_score_gap_1st_2nd:.2f}")
    lines.append("")
    lines.append("Correlations:")
    lines.append(f"- respawned_players vs total_lobby_score: "
                 f"{summary.corr_respawned_vs_lobby_score:+.3f}")
    lines.append(f"- lost_kill_points vs total_lobby_score: "
                 f"{summary.corr_lost_kills_vs_lobby_score:+.3f}")
    lines.append(f"- lost_kill_points vs tournament_length: "
                 f"{summary.corr_lost_kills_vs_tournament_length:+.3f}")
    lines.append(f"- eligible_count_start vs ending_probability: "
                 f"{summary.corr_eligible_count_vs_end_probability:+.3f}")
    return "\n".join(lines)
