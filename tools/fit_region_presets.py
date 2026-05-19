"""Region-preset fitting harness (grid search + Bayesian optimization).

Calibrates region-variable parameters per region against four observed
targets:

    1. mean ending match (from docs/data_validation.md section 2-B,
       hardcoded below since the document is hand-maintained markdown)
    2. mean kills of teams that placed 1st in a match
    3. mean kills of teams that placed 20th in a match
    4. mean scored kills per match (sum across 20 placements)

For each candidate parameter combination the harness runs `--sims`
tournaments and measures the same four quantities, then ranks
combinations by a normalized squared error against the observed vector.
The top proposal per region is written to a markdown table; it is up to
a human to copy the values into config.REGION_PROFILES.

Two search methods (cycle 12):

- `--method grid` (legacy, default): a 4-parameter Cartesian grid
  (strength_sigma, lost_kill_rate, placement_kill_sharpness,
  respawn_mean) over 6 x 5 x 6 x 5 = 900 combinations per region. The
  default grid is left as it was in cycles 8-11 so older proposals can
  still be reproduced bit-for-bit.

- `--method bayesian` (cycle 12 onward): a 5-parameter Gaussian-process
  Bayesian search via `skopt.gp_minimize` over continuous ranges. Adds
  `mp_win_penalty` as the 5th fit variable (see note below) and removes
  the grid-resolution constraint that pinned cycle-8/9/11 best solutions
  for Americas and APAC-S at the grid edges (PKF=0.60, respawn_mean=10.0).
  Typical budget: 150 evaluations per region (vs 900 for grid).

Why 5 of the article's main-five factors are fit under bayesian (cycle 12):

- strength_sigma, lost_kill_rate, placement_kill_sharpness, respawn_mean
  carry over from grid (see cycle 8/9 rationale: respawn_mean drives the
  ~10-kills-per-match regional variance in observed scored_kills totals;
  Americas 61.9 / EMEA 56.5 / APAC-N 55.4 / APAC-S 50.5).
- mp_win_penalty: previously excluded because direct estimation requires
  per-region MP-eligible-team win-rate observations, which the data set
  does not provide. Under Bayesian optimization mp_win_penalty is still
  identified — indirectly, via its non-trivial coupling to `mean_end` (a
  stronger penalty restrains MP-eligible teams from closing out, which
  lengthens the tournament). Adding a 5th dimension under grid would
  explode the search space; under gp_minimize the cost is linear-ish in
  n_calls, so the dimension lift is essentially free.
- revive_knock_mean stays excluded for the same reason as cycle 8:
  stored on MatchResult.revived_knocks but never reaches scored_kills
  (see match_sim.allocate_kills), so it cannot move any target.

Champs Group Stage data (originally floated in cycle 11 as a sample-size
booster) was rejected in cycle 12: the Group Stage is a region-mixed
lobby playing fixed-length (non-Match-Point) matches, so its strategic
pressure differs qualitatively from the regional Pro League Finals being
fit here — merging it would distort the very quantities being estimated.

The script is intentionally non-destructive: it never edits config.py.

Usage:
    # Legacy grid search (cycle 8-11 reproduction):
    python tools/fit_region_presets.py --dry-run
    python tools/fit_region_presets.py \\
        --observations data/region_kill_breakdown.csv \\
        --regions americas,emea,apac_n,apac_s \\
        --sims 2000 --workers 0 \\
        --output-md docs/region_refit_proposal.md

    # Bayesian optimization (cycle 12 onward, 5 parameters):
    python tools/fit_region_presets.py --method bayesian --dry-run
    python tools/fit_region_presets.py --method bayesian \\
        --observations data/region_kill_breakdown.csv \\
        --regions americas,emea,apac_n,apac_s \\
        --sims 2000 --bayes-n-calls 150 --bayes-n-initial 15 \\
        --output-md docs/region_refit_proposal.md
"""

from __future__ import annotations

import argparse
import csv
import io
import multiprocessing as mp
import sys
import time
from collections import defaultdict
from dataclasses import replace
from itertools import product
from pathlib import Path

import numpy as np

# Force UTF-8 stdout on Windows so em-dashes / Japanese in log lines don't
# trip cp932. Safe no-op on Linux/macOS.
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                      errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8",
                                      errors="replace")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import REGION_PROFILES, SimulationConfig, apply_region_profile
from tournament_sim import simulate_tournament


# ---------------------------------------------------------------------------
# Observed target vector (per region)
# ---------------------------------------------------------------------------
# Mean ending match per region from docs/data_validation.md section 2-B
# (19 ALGS Match Point Finals, Y4-Y5). Hardcoded because that file is a
# hand-curated markdown table; do not change here without updating it.
#
# Cycle 13 (2026-05): added "global" entry. Source is direct computation
# from data/region_kill_breakdown.csv region=global rows (4 events:
# 2024-S1-Playoffs-Finals=8, 2024-S2-Playoffs-Finals=10,
# 2025-Championship-Finals=9, 2025-Midseason-Playoffs-Finals=9 → mean=9.00).
# Not present in docs/data_validation.md (which tracks regional Pro League
# Finals only); update that document when reflecting global results.
OBSERVED_MEAN_END_MATCH: dict[str, float] = {
    "americas": 7.50,
    "emea": 8.50,
    "apac_n": 8.75,
    "apac_s": 8.00,
    "global": 9.00,
}

# Default grid (full run).
# Cycle 9: added respawn_mean (cycle 8 had dropped it as "all-region
# common" but the observed total-kills variance per region demanded it
# back). Also extended strength_sigma upper bound to 0.60 and PKF upper
# bound to 1.8 because cycle 8 best solutions for Americas / APAC-S
# were pinned at the grid boundary. Grid size: 6 x 5 x 6 x 5 = 900
# conditions per region.
GRID_FULL: dict[str, list[float]] = {
    "strength_sigma": [0.20, 0.27, 0.35, 0.43, 0.50, 0.60],
    "lost_kill_rate": [0.04, 0.06, 0.08, 0.10, 0.12],
    "placement_kill_sharpness": [0.6, 0.8, 1.0, 1.2, 1.5, 1.8],
    "respawn_mean": [2.0, 4.0, 6.0, 8.0, 10.0],
}

# Reduced grid used by --dry-run so the harness can be smoke-tested in
# under a minute, e.g. while iterating on the script itself.
GRID_DRY: dict[str, list[float]] = {
    "strength_sigma": [0.27, 0.50],
    "lost_kill_rate": [0.06, 0.10],
    "placement_kill_sharpness": [0.8, 1.5],
    "respawn_mean": [4.0, 8.0],
}

# Cycle 12: continuous search space for --method bayesian. 5 dimensions
# (adds mp_win_penalty over the 4-dim grid). Ranges are deliberately
# wider than the cycle-8/9/11 grid endpoints so previously edge-pinned
# best solutions (Americas / APAC-S at PKF=0.60, respawn_mean=10.0) can
# escape the boundary. The mp_win_penalty range [0.0, 0.50] comfortably
# contains the current REGION_PROFILES values (0.11-0.17) and the
# SimulationConfig default (0.10).
SEARCH_SPACE_BAYES: dict[str, tuple[float, float]] = {
    "strength_sigma": (0.10, 0.70),
    "lost_kill_rate": (0.02, 0.20),
    "placement_kill_sharpness": (0.4, 2.0),
    "respawn_mean": (1.0, 12.0),
    "mp_win_penalty": (0.0, 0.50),
}


# ---------------------------------------------------------------------------
# CSV loader
# ---------------------------------------------------------------------------
def _strip_comment_lines(path: Path) -> list[str]:
    """Read the CSV but skip lines whose first non-whitespace char is '#'."""
    lines = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            stripped = raw.lstrip()
            if stripped.startswith("#") or not stripped.strip():
                continue
            lines.append(raw)
    return lines


def load_observed_kills(csv_path: Path) -> dict[str, dict[str, float]]:
    """Aggregate per-region p1_kills, p10_kills, p20_kills, kills_per_match.

    Returns {region: {"p1_kills": x, "p10_kills": w, "p20_kills": y,
                      "kills_per_match": z, "n_matches": int}}.

    Cycle 13 (2026-05): added p10_kills (mid-tier mean) for the 5th err
    component.
    """
    rows = _strip_comment_lines(csv_path)
    if not rows:
        return {}
    reader = csv.DictReader(rows)

    # Per region, per (tournament, match_number), per placement -> kills
    bucket: dict[str, dict[tuple[str, int], dict[int, int]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for row in reader:
        region = row["region"].strip()
        tournament = row["tournament"].strip()
        try:
            match_no = int(row["match_number"])
            placement = int(row["placement"])
            kills = int(row["team_kills"])
        except (ValueError, KeyError):
            continue
        bucket[region][(tournament, match_no)][placement] = kills

    aggregated: dict[str, dict[str, float]] = {}
    for region, matches in bucket.items():
        p1_list: list[int] = []
        p10_list: list[int] = []
        p20_list: list[int] = []
        per_match_totals: list[int] = []
        for (_t, _m), placement_to_kills in matches.items():
            if 1 in placement_to_kills:
                p1_list.append(placement_to_kills[1])
            if 10 in placement_to_kills:
                p10_list.append(placement_to_kills[10])
            if 20 in placement_to_kills:
                p20_list.append(placement_to_kills[20])
            per_match_totals.append(sum(placement_to_kills.values()))
        if not p1_list:
            # Cannot use this region without a 1st-place observation.
            continue
        aggregated[region] = {
            "p1_kills": float(np.mean(p1_list)),
            # Cycle 13 (2026-05): added p10 as a 5th observation component.
            # Constrains the mid-tier of the placement-kill distribution so
            # the bayesian fit cannot satisfy bottom-zero p20 by collapsing
            # PKF / respawn_mean to their extremes (which empties the mid
            # tier as a side-effect).
            "p10_kills": float(np.mean(p10_list)) if p10_list else 0.0,
            "p20_kills": float(np.mean(p20_list)) if p20_list else 0.0,
            "kills_per_match": float(np.mean(per_match_totals)),
            "n_matches": len(matches),
        }
    return aggregated


# ---------------------------------------------------------------------------
# Single-config evaluator
# ---------------------------------------------------------------------------
def _measure_one_config(
    cfg: SimulationConfig, n_sims: int, seed: int
) -> tuple[float, float, float, float, float]:
    """Run `n_sims` tournaments and return (mean_end_match, p1_kills,
    p10_kills, p20_kills, kills_per_match) averaged across all matches.

    Cycle 13 (2026-05): added p10_kills as a 5th component so the
    mid-tier of the placement-kill distribution is constrained too.
    """
    rng = np.random.default_rng(seed)
    lengths: list[int] = []
    p1_kills: list[int] = []
    p10_kills: list[int] = []
    p20_kills: list[int] = []
    match_totals: list[int] = []
    for _ in range(n_sims):
        tr = simulate_tournament(cfg, rng)
        lengths.append(tr.ending_match)
        for mr in tr.match_results:
            # placements is team_id ordered 1st..20th
            p1_tid = int(mr.placements[0])
            p10_tid = int(mr.placements[9])
            p20_tid = int(mr.placements[-1])
            p1_kills.append(int(mr.team_kills[p1_tid]))
            p10_kills.append(int(mr.team_kills[p10_tid]))
            p20_kills.append(int(mr.team_kills[p20_tid]))
            match_totals.append(int(mr.scored_kills))
    return (
        float(np.mean(lengths)),
        float(np.mean(p1_kills)),
        float(np.mean(p10_kills)),
        float(np.mean(p20_kills)),
        float(np.mean(match_totals)),
    )


def _worker_eval(args):
    """Process-pool entry point. Returns (overrides_dict, metrics_tuple)."""
    base_cfg, overrides, n_sims, seed = args
    cfg = replace(base_cfg, **overrides)
    metrics = _measure_one_config(cfg, n_sims, seed)
    return overrides, metrics


# ---------------------------------------------------------------------------
# Grid search per region
# ---------------------------------------------------------------------------
def _normalized_squared_error(
    sim: tuple[float, float, float, float, float],
    obs: dict[str, float],
) -> float:
    """Normalize each component by its observed magnitude before squaring.

    Cycle 8: added the 4th component (kills_per_match). Without it the
    fit only constrains 2 endpoints of the placement distribution (p1
    and p20), leaving lost_kill_rate and respawn_mean (both drive the
    per-match kill supply) un-anchored in their trade-off subspace.

    Cycle 13 (2026-05): added the 5th component (p10_kills). With only
    p1 + p20 + total constraining the placement-kill curve, the bayesian
    fit for region=global pushed PKF / respawn_mean to their bounds in
    pursuit of the global-specific bottom-zero observation (p20=0.08),
    which emptied the mid-tier as a side-effect. Anchoring p10 (regional
    obs 2.4-3.5, zero-rate 11-27%) gives the mid placements a hard
    constraint and prevents that collapse. Floor at 1.0 (p10 is never
    actually < 1.0 in regional/global obs, so the floor only protects
    against pathological sim degeneration).
    """
    sim_mean, sim_p1, sim_p10, sim_p20, sim_total = sim
    err = 0.0
    err += ((sim_mean - obs["mean_end_match"]) / max(obs["mean_end_match"], 1e-6)) ** 2
    err += ((sim_p1 - obs["p1_kills"]) / max(obs["p1_kills"], 1e-6)) ** 2
    p10_scale = max(obs["p10_kills"], 1.0)
    err += ((sim_p10 - obs["p10_kills"]) / p10_scale) ** 2
    # p20 can be ~0; floor at 0.5 so a single-kill difference is not infinite.
    p20_scale = max(obs["p20_kills"], 0.5)
    err += ((sim_p20 - obs["p20_kills"]) / p20_scale) ** 2
    err += ((sim_total - obs["kills_per_match"]) / max(obs["kills_per_match"], 1e-6)) ** 2
    return err


def grid_search_region(
    region: str,
    observed: dict[str, float],
    grid: dict[str, list[float]],
    n_sims: int,
    workers: int,
    seed: int,
) -> list[tuple[dict, tuple[float, float, float, float, float], float]]:
    """Return [(overrides, metrics, err), ...] sorted by err ascending."""
    base_cfg = apply_region_profile(SimulationConfig(), region)

    keys = list(grid.keys())
    combos = [
        dict(zip(keys, values))
        for values in product(*[grid[k] for k in keys])
    ]
    total = len(combos)
    print(f"  [{region}] grid: {total} combinations x {n_sims} sims each ...",
          flush=True)

    args_list = [(base_cfg, ov, n_sims, seed) for ov in combos]

    results: list[tuple[dict, tuple[float, float, float, float, float]]] = []
    t0 = time.perf_counter()
    # 5% progress steps so long fits surface ETA / best_err frequently.
    progress_step = max(1, total // 20)
    best_err_so_far = float("inf")
    best_ov_so_far: dict | None = None

    def _report_progress(i: int) -> None:
        elapsed = time.perf_counter() - t0
        rate = i / max(elapsed, 1e-3)
        eta = (total - i) / max(rate, 1e-6)
        if best_ov_so_far is not None:
            best_str = ", ".join(
                f"{k}={_fmt_param(k, best_ov_so_far[k])}" for k in keys
            )
        else:
            best_str = "—"
        print(
            f"    [{region}] {i}/{total} ({100*i/total:5.1f}%, "
            f"elapsed {elapsed:5.0f}s, ETA {eta:5.0f}s) "
            f"best_err={best_err_so_far:.4f} ({best_str})",
            flush=True,
        )

    def _update_best(ov: dict, metrics: tuple[float, float, float, float, float]) -> None:
        nonlocal best_err_so_far, best_ov_so_far
        cand_err = _normalized_squared_error(metrics, observed)
        if cand_err < best_err_so_far:
            best_err_so_far = cand_err
            best_ov_so_far = ov

    if workers and workers > 1:
        ctx = mp.get_context("spawn")
        with ctx.Pool(processes=workers) as pool:
            for i, (ov, metrics) in enumerate(
                pool.imap_unordered(_worker_eval, args_list), 1
            ):
                results.append((ov, metrics))
                _update_best(ov, metrics)
                if i % progress_step == 0 or i == total:
                    _report_progress(i)
    else:
        for i, args in enumerate(args_list, 1):
            ov, metrics = _worker_eval(args)
            results.append((ov, metrics))
            _update_best(ov, metrics)
            if i % progress_step == 0 or i == total:
                _report_progress(i)

    scored = [
        (ov, m, _normalized_squared_error(m, observed))
        for ov, m in results
    ]
    scored.sort(key=lambda x: x[2])
    return scored


# ---------------------------------------------------------------------------
# Bayesian search per region (cycle 12)
# ---------------------------------------------------------------------------
def bayesian_search_region(
    region: str,
    observed: dict[str, float],
    space: dict[str, tuple[float, float]],
    n_sims: int,
    seed: int,
    n_calls: int,
    n_initial: int,
) -> list[tuple[dict, tuple[float, float, float, float, float], float]]:
    """Gaussian-process Bayesian fit via `skopt.gp_minimize`.

    Returns [(overrides, metrics, err), ...] sorted by err ascending, in
    the same shape that `grid_search_region` returns so downstream code
    (top3 extraction, proposal table rendering) does not have to branch.

    `space` maps parameter name -> (low, high). The objective evaluates
    one configuration via `_measure_one_config` (n_sims tournaments) and
    scores against the 4-component observed vector with
    `_normalized_squared_error`. gp_minimize is sequential (each
    evaluation depends on the GP fit from prior evaluations), so the
    --workers flag is ignored in this code path.
    """
    # Local import: scikit-optimize is only needed for --method bayesian
    # so users running the legacy grid mode don't have to install it.
    try:
        from skopt import gp_minimize
        from skopt.space import Real
    except ImportError as exc:  # pragma: no cover - install-time error
        raise SystemExit(
            "scikit-optimize is required for --method bayesian. "
            "Install it with: pip install scikit-optimize"
        ) from exc

    base_cfg = apply_region_profile(SimulationConfig(), region)
    keys = list(space.keys())
    dimensions = [Real(low, high, name=k) for k, (low, high) in space.items()]

    records: list[tuple[dict, tuple[float, float, float, float, float], float]] = []
    print(
        f"  [{region}] bayes: n_calls={n_calls} (initial={n_initial}) "
        f"x {n_sims} sims/eval, {len(keys)} dims ...",
        flush=True,
    )
    t0 = time.perf_counter()
    # Log on improvement, and a periodic heartbeat so long fits visibly
    # progress between improvements.
    state = {"best_err": float("inf"), "best_ov": None, "next_log": 0}
    heartbeat_step = max(1, n_calls // 10)

    def objective(x: list[float]) -> float:
        overrides = {k: float(v) for k, v in zip(keys, x)}
        cfg = replace(base_cfg, **overrides)
        metrics = _measure_one_config(cfg, n_sims, seed)
        err = _normalized_squared_error(metrics, observed)
        records.append((overrides, metrics, err))
        i = len(records)
        improved = err < state["best_err"]
        if improved:
            state["best_err"] = err
            state["best_ov"] = overrides
        if improved or i >= state["next_log"]:
            state["next_log"] = i + heartbeat_step
            elapsed = time.perf_counter() - t0
            best_ov = state["best_ov"] or overrides
            best_str = ", ".join(
                f"{k}={_fmt_param(k, best_ov[k])}" for k in keys
            )
            tag = "★" if improved else " "
            print(
                f"    [{region}] {tag} eval {i}/{n_calls} "
                f"(elapsed {elapsed:5.0f}s) "
                f"best_err={state['best_err']:.4f} ({best_str})",
                flush=True,
            )
        return err

    gp_minimize(
        objective,
        dimensions,
        n_calls=n_calls,
        n_initial_points=n_initial,
        random_state=seed,
        verbose=False,
    )

    records.sort(key=lambda r: r[2])
    return records


def _fit_region_bayes_worker(args):
    """multiprocessing entry point: fit one region under bayesian method.

    Cycle 13 (2026-05): added so --parallel-regions can run N region
    bayesian fits in parallel processes. gp_minimize itself is sequential
    inside one region, so the only available parallelism is across
    regions. Each worker spends ~ (n_calls * sims/eval) compute on
    its own process; with 5 regions on a 16+ thread CPU the wall time
    drops from N x T to ~ T.
    """
    region, observed, space, sims, seed, n_calls, n_initial = args
    scored = bayesian_search_region(
        region, observed, space, sims, seed, n_calls, n_initial,
    )
    return region, scored


# ---------------------------------------------------------------------------
# Proposal-table writer
# ---------------------------------------------------------------------------
_PARAM_FORMAT: dict[str, str] = {
    "strength_sigma": "{:.3f}",
    "lost_kill_rate": "{:.3f}",
    "placement_kill_sharpness": "{:.2f}",
    "respawn_mean": "{:.1f}",
    "mp_win_penalty": "{:.3f}",
    # legacy keys, kept so we can still render older proposals if needed
    "revive_knock_mean": "{:.1f}",
}


def _fmt_param(name: str, value: float) -> str:
    return _PARAM_FORMAT.get(name, "{:.3f}").format(value)


def render_proposal_md(
    proposals: dict[str, dict],
    out_path: Path,
    search: dict[str, list[float]] | dict[str, tuple[float, float]],
    n_sims: int,
    dry_run: bool,
    method: str = "grid",
    bayes_meta: dict | None = None,
) -> None:
    """Write the per-region proposal table.

    `search` is the grid dict for method=grid (param -> list of values)
    or the Bayesian space dict for method=bayesian (param -> (low, high)
    tuple). `bayes_meta` carries {n_calls, n_initial} when method=bayesian
    so the report can record the budget.

    Display order: the canonical 4-region set first (with `[no data]`
    placeholders if a region wasn't fit this run), followed by any extra
    regions present in `proposals` (e.g. cycle-13 added "global").
    """

    def _display_region_order(props: dict) -> list[str]:
        canonical = ["americas", "emea", "apac_n", "apac_s"]
        extras = [r for r in props if r not in canonical]
        return canonical + sorted(extras)

    keys = list(search.keys())
    title_suffix = "ベイズ最適化提案" if method == "bayesian" else "grid search 提案"
    method_blurb = (
        f"`gp_minimize` ベイズ最適化、n_calls={bayes_meta['n_calls']} "
        f"(initial={bayes_meta['n_initial']}), {n_sims} sims/eval"
        if method == "bayesian" and bayes_meta
        else f"grid search, sims/condition={n_sims}"
    )
    lines = [
        f"# 地域プリセット再フィッティング — {title_suffix}",
        "",
        f"自動生成 (`tools/fit_region_presets.py --method {method}`). "
        f"dry_run={dry_run}, {method_blurb}.",
        "",
    ]
    if method == "bayesian":
        lines.extend([
            "## 探索範囲",
            "",
            "| パラメータ | 下限 | 上限 |",
            "|---|---|---|",
        ])
        for k in keys:
            low, high = search[k]
            lines.append(f"| `{k}` | {_fmt_param(k, low)} | {_fmt_param(k, high)} |")
    else:
        lines.extend([
            "## グリッド範囲",
            "",
            "| パラメータ | 候補値 |",
            "|---|---|",
        ])
        for k in keys:
            vs = ", ".join(str(v) for v in search[k])
            lines.append(f"| `{k}` | {vs} |")
    lines.append("")
    lines.append("## ベスト解 (各地域)")
    lines.append("")
    header_cols = ["region"] + keys + [
        "obs mean_end", "sim mean_end",
        "obs p1_kills", "sim p1_kills",
        "obs p10_kills", "sim p10_kills",
        "obs p20_kills", "sim p20_kills",
        "obs total_kills", "sim total_kills",
        "err", "n_obs_matches",
    ]
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("|" + "---|" * len(header_cols))
    for region in _display_region_order(proposals):
        if region not in proposals:
            placeholder = (
                ["[no data]"] + [""] * len(keys)
                + [f"{OBSERVED_MEAN_END_MATCH.get(region, '-')}"]
                + ["—"] * 9 + ["0"]
            )
            lines.append(f"| {region} | " + " | ".join(placeholder) + " |")
            continue
        p = proposals[region]
        ov = p["overrides"]
        sim_m, sim_p1, sim_p10, sim_p20, sim_total = p["metrics"]
        obs = p["observed"]
        row = [region]
        for k in keys:
            row.append(_fmt_param(k, ov[k]))
        row += [
            f"{obs['mean_end_match']:.2f}", f"{sim_m:.2f}",
            f"{obs['p1_kills']:.2f}", f"{sim_p1:.2f}",
            f"{obs['p10_kills']:.2f}", f"{sim_p10:.2f}",
            f"{obs['p20_kills']:.2f}", f"{sim_p20:.2f}",
            f"{obs['kills_per_match']:.2f}", f"{sim_total:.2f}",
            f"{p['err']:.4f}", str(p['n_obs_matches']),
        ]
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append("## 上位 3 候補 (各地域、観測との正規化二乗誤差 — 5 成分)")
    lines.append("")
    lines.append(
        "err = (Δmean_end/obs)² + (Δp1/obs_p1)² + (Δp10/max(obs_p10,1.0))² "
        "+ (Δp20/max(obs_p20,0.5))² + (Δtotal/obs_total)². "
        "各成分は観測値で割って正規化した二乗差。"
    )
    lines.append("")
    for region in _display_region_order(proposals):
        if region not in proposals:
            continue
        lines.append(f"### {region}")
        lines.append("")
        top_cols = (["rank"] + keys
                    + ["sim mean_end", "sim p1_kills", "sim p10_kills",
                       "sim p20_kills", "sim total_kills", "err"])
        lines.append("| " + " | ".join(top_cols) + " |")
        lines.append("|" + "---|" * len(top_cols))
        for rank, (ov, metrics, err) in enumerate(proposals[region]["top3"], 1):
            sim_m, sim_p1, sim_p10, sim_p20, sim_total = metrics
            row = [str(rank)]
            for k in keys:
                row.append(_fmt_param(k, ov[k]))
            row += [
                f"{sim_m:.2f}", f"{sim_p1:.2f}", f"{sim_p10:.2f}",
                f"{sim_p20:.2f}", f"{sim_total:.2f}", f"{err:.4f}",
            ]
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
    lines.append("## 採用手順 (人間判断)")
    lines.append("")
    lines.append(
        "ベスト解 (上の表) を `config.py:REGION_PROFILES` に反映する際は、"
        f"各地域ブロックの該当 {len(keys)} キー ({', '.join('`' + k + '`' for k in keys)}) "
        "を書き換えた上で `pytest tests/` を実行し、regression テストが通ることを確認する。"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--observations", default="data/region_kill_breakdown.csv",
        help="CSV of per-match per-placement kills."
    )
    p.add_argument(
        "--regions", default="americas,emea,apac_n,apac_s,global",
        help="comma-separated region names to fit."
    )
    p.add_argument(
        "--parallel-regions", action="store_true",
        help="run bayesian fits for multiple regions in parallel "
             "(one process per region). Ignored under --method grid "
             "(grid already parallelizes per-config inside one region)."
    )
    p.add_argument("--sims", type=int, default=2000,
                   help="tournaments per grid condition.")
    p.add_argument("--workers", type=int, default=0,
                   help="parallel processes (0 = cpu_count - 1).")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--output-md", default="docs/region_refit_proposal.md",
        help="markdown output file with the proposal tables."
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="use a 2x2x2x2 grid (or reduced bayes budget) and small --sims "
             "for a smoke test."
    )
    p.add_argument(
        "--method", choices=["grid", "bayesian"], default="grid",
        help="search method: grid (4-dim, 900 conditions, legacy) or "
             "bayesian (5-dim incl. mp_win_penalty, skopt gp_minimize)."
    )
    p.add_argument(
        "--bayes-n-calls", type=int, default=150,
        help="total evaluations per region for --method bayesian "
             "(ignored under --method grid)."
    )
    p.add_argument(
        "--bayes-n-initial", type=int, default=15,
        help="random-initial evaluations before the GP surrogate kicks in "
             "(--method bayesian only)."
    )
    return p.parse_args(argv)


# Cycle 13 (2026-05): canonical regional proposal file is rebuilt only
# when the full 4-region cycle-9 set is fit at once. Partial runs
# (e.g. --regions global, or a single-region re-fit) are auto-redirected
# to a per-run filename so the canonical file's cycle-9 contents are
# never silently clobbered. Pass --output-md explicitly to override.
DEFAULT_OUTPUT_MD = "docs/region_refit_proposal.md"
CANONICAL_REGION_SET = ("americas", "apac_n", "apac_s", "emea", "global")
# Default --regions value advertised in --help. Cycle 13 (2026-05)
# expanded the canonical set from 4 to 5 by adding cross-regional
# Global Finals as a sigma-distinct lobby.
CANONICAL_REGIONS_CSV = ",".join(CANONICAL_REGION_SET)


def main(argv: list[str] | None = None) -> int:
    ns = _parse_args(argv)

    csv_path = REPO_ROOT / ns.observations
    regions = [r.strip() for r in ns.regions.split(",") if r.strip()]

    # Side-effect guard for the canonical proposal file (cycle 13:
    # docs/region_refit_proposal.md represents the 5-region cycle-13
    # production fit). Two paths redirect away from canonical:
    #   1. --dry-run: results are by definition throwaway; never let a
    #      smoke test silently overwrite the real proposal.
    #   2. --regions != canonical set: a partial-region run would
    #      replace the full table with a one-line subset.
    # Pass --output-md explicitly to override either redirect.
    output_md_arg = ns.output_md
    if output_md_arg == DEFAULT_OUTPUT_MD:
        redirect_reason: str | None = None
        if ns.dry_run:
            output_md_arg = "docs/region_refit_proposal__dryrun.md"
            redirect_reason = "--dry-run output is non-production"
        elif tuple(sorted(regions)) != CANONICAL_REGION_SET:
            suffix = "_".join(sorted(regions))
            output_md_arg = f"docs/region_refit_proposal__{suffix}.md"
            redirect_reason = "--regions != canonical set"
        if redirect_reason:
            print(
                f"  [guard] {redirect_reason}; redirecting --output-md "
                f"to {output_md_arg} to protect {DEFAULT_OUTPUT_MD}",
                flush=True,
            )
    out_md = REPO_ROOT / output_md_arg

    sims = max(100, ns.sims) if not ns.dry_run else min(ns.sims, 200)

    if ns.workers and ns.workers > 0:
        workers = ns.workers
    else:
        cpu = mp.cpu_count() or 1
        workers = max(1, cpu - 1)

    # Method-specific setup -------------------------------------------------
    if ns.method == "grid":
        grid = GRID_DRY if ns.dry_run else GRID_FULL
        search_keys = list(grid.keys())
        grid_size = 1
        for _vs in grid.values():
            grid_size *= len(_vs)
        method_summary = (
            f"grid_size={grid_size} "
            f"({' x '.join(str(len(v)) for v in grid.values())})"
        )
        bayes_meta: dict | None = None
    else:  # bayesian
        space = SEARCH_SPACE_BAYES
        search_keys = list(space.keys())
        # Reduce the Bayesian budget under --dry-run so smoke tests stay
        # under a minute, mirroring how GRID_DRY shrinks the grid path.
        n_calls = min(ns.bayes_n_calls, 25) if ns.dry_run else ns.bayes_n_calls
        n_initial = min(ns.bayes_n_initial, 8) if ns.dry_run else ns.bayes_n_initial
        if n_initial > n_calls:
            n_initial = max(1, n_calls // 2)
        method_summary = f"n_calls={n_calls} (initial={n_initial})"
        bayes_meta = {"n_calls": n_calls, "n_initial": n_initial}
        # gp_minimize is sequential — warn loudly if the user asked for
        # parallel workers under bayesian so the discrepancy is obvious.
        if ns.workers and ns.workers > 1:
            print(
                f"  [warn] --workers={ns.workers} is ignored under "
                "--method bayesian (gp_minimize is sequential).",
                flush=True,
            )

    observed_kills = load_observed_kills(csv_path) if csv_path.exists() else {}

    print(f"fit_region_presets: method={ns.method}, csv={csv_path.name}, "
          f"{method_summary}, sims={sims}, workers={workers}, "
          f"dry_run={ns.dry_run}")
    print(f"  fit params ({len(search_keys)}): {', '.join(search_keys)}")

    # Stage 1: build per-region job list (skip regions with no obs).
    jobs: list[tuple[str, dict, dict]] = []  # (region, observed, kills_meta)
    for region in regions:
        if region not in OBSERVED_MEAN_END_MATCH:
            print(f"  [{region}] skip: no observed mean_end_match", flush=True)
            continue
        kills = observed_kills.get(region)
        if kills is None:
            # In dry-run we still want to exercise the search; fall back to
            # plausible placeholder values so the harness runs end-to-end.
            if ns.dry_run:
                print(f"  [{region}] no kill data — using placeholder for dry-run",
                      flush=True)
                kills = {"p1_kills": 7.4, "p10_kills": 2.7, "p20_kills": 0.7,
                         "kills_per_match": 52.0, "n_matches": 0}
            else:
                print(f"  [{region}] skip: no kill data in CSV", flush=True)
                continue
        observed = {
            "mean_end_match": OBSERVED_MEAN_END_MATCH[region],
            "p1_kills": kills["p1_kills"],
            "p10_kills": kills["p10_kills"],
            "p20_kills": kills["p20_kills"],
            "kills_per_match": kills["kills_per_match"],
        }
        jobs.append((region, observed, kills))

    # Stage 2: execute fits (parallel if requested, else sequential).
    use_parallel = (
        ns.parallel_regions
        and ns.method == "bayesian"
        and len(jobs) > 1
    )
    region_to_scored: dict[str, list] = {}
    if use_parallel:
        pool_size = min(len(jobs), mp.cpu_count() or 1)
        print(
            f"  [parallel] fitting {len(jobs)} regions across "
            f"{pool_size} worker processes (bayesian, "
            f"n_calls={bayes_meta['n_calls']} each)",
            flush=True,
        )
        worker_args = [
            (region, observed, SEARCH_SPACE_BAYES, sims, ns.seed,
             bayes_meta["n_calls"], bayes_meta["n_initial"])
            for region, observed, _ in jobs
        ]
        with mp.Pool(pool_size) as pool:
            for region_done, scored in pool.imap_unordered(
                _fit_region_bayes_worker, worker_args
            ):
                region_to_scored[region_done] = scored
                print(f"  [parallel] {region_done} done "
                      f"({len(region_to_scored)}/{len(jobs)})", flush=True)
    else:
        for region, observed, _ in jobs:
            if ns.method == "grid":
                scored = grid_search_region(
                    region, observed, grid, sims, workers, ns.seed,
                )
            else:
                scored = bayesian_search_region(
                    region, observed, SEARCH_SPACE_BAYES, sims, ns.seed,
                    bayes_meta["n_calls"], bayes_meta["n_initial"],
                )
            region_to_scored[region] = scored

    # Stage 3: build proposals dict and log best for each region.
    proposals: dict[str, dict] = {}
    for region, observed, kills in jobs:
        scored = region_to_scored[region]
        best_ov, best_metrics, best_err = scored[0]
        proposals[region] = {
            "overrides": best_ov,
            "metrics": best_metrics,
            "err": best_err,
            "observed": observed,
            "n_obs_matches": kills.get("n_matches", 0),
            "top3": scored[:3],
        }
        params_str = ", ".join(
            f"{k}={_fmt_param(k, best_ov[k])}" for k in search_keys
        )
        sim_m, sim_p1, sim_p10, sim_p20, sim_total = best_metrics
        print(
            f"  [{region}] best: {params_str}  -> sim mean_end={sim_m:.2f} "
            f"(obs {observed['mean_end_match']:.2f}), "
            f"sim p1={sim_p1:.2f}/p10={sim_p10:.2f}/p20={sim_p20:.2f}/"
            f"total={sim_total:.2f}, err={best_err:.4f}",
            flush=True,
        )

    search_for_render = grid if ns.method == "grid" else SEARCH_SPACE_BAYES
    render_proposal_md(
        proposals, out_md, search_for_render, sims, ns.dry_run,
        method=ns.method, bayes_meta=bayes_meta,
    )
    print(f"\nProposal written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
