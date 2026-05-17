"""Grid search harness for re-fitting ALGS region presets.

Calibrates four high-leverage parameters per region — strength_sigma,
lost_kill_rate, revive_knock_mean, placement_kill_sharpness — to three
observed targets:

    1. mean ending match (from docs/data_validation.md section 2-B,
       hardcoded below since the document is hand-maintained markdown)
    2. mean kills of teams that placed 1st in a match
    3. mean kills of teams that placed 20th in a match

For each candidate parameter combination the harness runs `--sims`
tournaments and measures the same three quantities, then ranks
combinations by a normalized squared error against the observed vector.
The top proposal per region is written to a markdown table; it is up to
a human to copy the values into config.REGION_PROFILES.

The script is intentionally non-destructive: it never edits config.py.

Usage:
    python tools/fit_region_presets.py --dry-run
    python tools/fit_region_presets.py \\
        --observations data/region_kill_breakdown.csv \\
        --regions americas,emea,apac_n,apac_s \\
        --sims 2000 --workers 0 \\
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
OBSERVED_MEAN_END_MATCH: dict[str, float] = {
    "americas": 7.50,
    "emea": 8.50,
    "apac_n": 8.75,
    "apac_s": 8.00,
}

# Default grid (full run).
GRID_FULL: dict[str, list[float]] = {
    "strength_sigma": [0.20, 0.27, 0.35, 0.43, 0.50],
    "lost_kill_rate": [0.04, 0.06, 0.08, 0.10, 0.12],
    "revive_knock_mean": [7.0, 9.0, 11.0, 13.0],
    "placement_kill_sharpness": [0.6, 0.8, 1.0, 1.2, 1.5],
}

# Reduced grid used by --dry-run so the harness can be smoke-tested in
# under a minute, e.g. while iterating on the script itself.
GRID_DRY: dict[str, list[float]] = {
    "strength_sigma": [0.27, 0.43],
    "lost_kill_rate": [0.06, 0.10],
    "revive_knock_mean": [9.0, 11.0],
    "placement_kill_sharpness": [0.8, 1.2],
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
    """Aggregate per-region p1_kills, p20_kills, kills_per_match from CSV.

    Returns {region: {"p1_kills": x, "p20_kills": y, "kills_per_match": z,
                      "n_matches": int}}.
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
        p20_list: list[int] = []
        per_match_totals: list[int] = []
        for (_t, _m), placement_to_kills in matches.items():
            if 1 in placement_to_kills:
                p1_list.append(placement_to_kills[1])
            if 20 in placement_to_kills:
                p20_list.append(placement_to_kills[20])
            per_match_totals.append(sum(placement_to_kills.values()))
        if not p1_list:
            # Cannot use this region without a 1st-place observation.
            continue
        aggregated[region] = {
            "p1_kills": float(np.mean(p1_list)),
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
) -> tuple[float, float, float, float]:
    """Run `n_sims` tournaments and return (mean_end_match, p1_kills,
    p20_kills, kills_per_match) averaged across all matches in all sims."""
    rng = np.random.default_rng(seed)
    lengths: list[int] = []
    p1_kills: list[int] = []
    p20_kills: list[int] = []
    match_totals: list[int] = []
    for _ in range(n_sims):
        tr = simulate_tournament(cfg, rng)
        lengths.append(tr.ending_match)
        for mr in tr.match_results:
            # placements is team_id ordered 1st..20th
            p1_tid = int(mr.placements[0])
            p20_tid = int(mr.placements[-1])
            p1_kills.append(int(mr.team_kills[p1_tid]))
            p20_kills.append(int(mr.team_kills[p20_tid]))
            match_totals.append(int(mr.scored_kills))
    return (
        float(np.mean(lengths)),
        float(np.mean(p1_kills)),
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
    sim: tuple[float, float, float, float],
    obs: dict[str, float],
) -> float:
    """Normalize each component by its observed magnitude before squaring."""
    sim_mean, sim_p1, sim_p20, _sim_total = sim
    err = 0.0
    # mean ending match: divide by observed value
    err += ((sim_mean - obs["mean_end_match"]) / max(obs["mean_end_match"], 1e-6)) ** 2
    err += ((sim_p1 - obs["p1_kills"]) / max(obs["p1_kills"], 1e-6)) ** 2
    # p20 can be ~0; floor at 0.5 so a single-kill difference is not infinite.
    p20_scale = max(obs["p20_kills"], 0.5)
    err += ((sim_p20 - obs["p20_kills"]) / p20_scale) ** 2
    return err


def grid_search_region(
    region: str,
    observed: dict[str, float],
    grid: dict[str, list[float]],
    n_sims: int,
    workers: int,
    seed: int,
) -> list[tuple[dict, tuple[float, float, float, float], float]]:
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

    results: list[tuple[dict, tuple[float, float, float, float]]] = []
    t0 = time.perf_counter()
    if workers and workers > 1:
        ctx = mp.get_context("spawn")
        with ctx.Pool(processes=workers) as pool:
            for i, (ov, metrics) in enumerate(
                pool.imap_unordered(_worker_eval, args_list), 1
            ):
                results.append((ov, metrics))
                if i % max(1, total // 10) == 0 or i == total:
                    elapsed = time.perf_counter() - t0
                    print(f"    {i}/{total} ({elapsed:.1f}s)", flush=True)
    else:
        for i, args in enumerate(args_list, 1):
            ov, metrics = _worker_eval(args)
            results.append((ov, metrics))
            if i % max(1, total // 10) == 0 or i == total:
                elapsed = time.perf_counter() - t0
                print(f"    {i}/{total} ({elapsed:.1f}s)", flush=True)

    scored = [
        (ov, m, _normalized_squared_error(m, observed))
        for ov, m in results
    ]
    scored.sort(key=lambda x: x[2])
    return scored


# ---------------------------------------------------------------------------
# Proposal-table writer
# ---------------------------------------------------------------------------
def render_proposal_md(
    proposals: dict[str, dict],
    out_path: Path,
    grid: dict[str, list[float]],
    n_sims: int,
    dry_run: bool,
) -> None:
    lines = [
        "# 地域プリセット再校正 — grid search 提案",
        "",
        f"自動生成 (`tools/fit_region_presets.py`). dry_run={dry_run}, "
        f"sims/condition={n_sims}.",
        "",
        "## グリッド範囲",
        "",
        "| パラメータ | 候補値 |",
        "|---|---|",
    ]
    for k, vals in grid.items():
        vs = ", ".join(str(v) for v in vals)
        lines.append(f"| `{k}` | {vs} |")
    lines.append("")
    lines.append("## ベスト解 (各地域)")
    lines.append("")
    lines.append(
        "| region | strength_sigma | lost_kill_rate | revive_knock_mean "
        "| placement_kill_sharpness | obs mean_end | sim mean_end "
        "| obs p1_kills | sim p1_kills | obs p20_kills | sim p20_kills "
        "| n_obs_matches |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for region in ("americas", "emea", "apac_n", "apac_s"):
        if region not in proposals:
            lines.append(
                f"| {region} | [no data] | | | | "
                f"{OBSERVED_MEAN_END_MATCH.get(region, '-')} | "
                f"— | — | — | — | — | 0 |"
            )
            continue
        p = proposals[region]
        ov = p["overrides"]
        sim_m, sim_p1, sim_p20, _ = p["metrics"]
        obs = p["observed"]
        lines.append(
            f"| {region} "
            f"| {ov['strength_sigma']:.3f} "
            f"| {ov['lost_kill_rate']:.3f} "
            f"| {ov['revive_knock_mean']:.1f} "
            f"| {ov['placement_kill_sharpness']:.2f} "
            f"| {obs['mean_end_match']:.2f} | {sim_m:.2f} "
            f"| {obs['p1_kills']:.2f} | {sim_p1:.2f} "
            f"| {obs['p20_kills']:.2f} | {sim_p20:.2f} "
            f"| {p['n_obs_matches']} |"
        )
    lines.append("")
    lines.append("## 上位 3 候補 (各地域、観測との正規化二乗誤差)")
    lines.append("")
    for region in ("americas", "emea", "apac_n", "apac_s"):
        if region not in proposals:
            continue
        lines.append(f"### {region}")
        lines.append("")
        lines.append(
            "| rank | strength_sigma | lost_kill_rate | revive_knock_mean "
            "| placement_kill_sharpness | sim mean_end | sim p1_kills "
            "| sim p20_kills | err |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for rank, (ov, metrics, err) in enumerate(proposals[region]["top3"], 1):
            sim_m, sim_p1, sim_p20, _ = metrics
            lines.append(
                f"| {rank} "
                f"| {ov['strength_sigma']:.3f} "
                f"| {ov['lost_kill_rate']:.3f} "
                f"| {ov['revive_knock_mean']:.1f} "
                f"| {ov['placement_kill_sharpness']:.2f} "
                f"| {sim_m:.2f} | {sim_p1:.2f} | {sim_p20:.2f} "
                f"| {err:.4f} |"
            )
        lines.append("")
    lines.append("## 採用手順 (人間判断)")
    lines.append("")
    lines.append(
        "ベスト解 (上の表) を `config.py:REGION_PROFILES` に反映する際は、"
        "各地域ブロックの該当 4 キーを書き換えた上で `pytest tests/` を実行し、"
        "regression テストが通ることを確認する。`placement_kill_sharpness` は "
        "現状 REGION_PROFILES に未含有なので、新規キーとして追加する形になる。"
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
        "--regions", default="americas,emea,apac_n,apac_s",
        help="comma-separated region names to fit."
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
        help="use a 2x2x2x2 grid and small --sims for a smoke test."
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = _parse_args(argv)

    csv_path = REPO_ROOT / ns.observations
    out_md = REPO_ROOT / ns.output_md
    regions = [r.strip() for r in ns.regions.split(",") if r.strip()]

    grid = GRID_DRY if ns.dry_run else GRID_FULL
    sims = max(100, ns.sims) if not ns.dry_run else min(ns.sims, 200)

    if ns.workers and ns.workers > 0:
        workers = ns.workers
    else:
        cpu = mp.cpu_count() or 1
        workers = max(1, cpu - 1)

    observed_kills = load_observed_kills(csv_path) if csv_path.exists() else {}

    print(f"fit_region_presets: csv={csv_path.name}, grid_size="
          f"{len(grid['strength_sigma']) * len(grid['lost_kill_rate']) * len(grid['revive_knock_mean']) * len(grid['placement_kill_sharpness'])}, "
          f"sims={sims}, workers={workers}, dry_run={ns.dry_run}")

    proposals: dict[str, dict] = {}
    for region in regions:
        if region not in OBSERVED_MEAN_END_MATCH:
            print(f"  [{region}] skip: no observed mean_end_match", flush=True)
            continue
        kills = observed_kills.get(region)
        if kills is None:
            # In dry-run we still want to exercise the grid; fall back to
            # plausible placeholder values so the harness runs end-to-end.
            if ns.dry_run:
                print(f"  [{region}] no kill data — using placeholder for dry-run",
                      flush=True)
                kills = {"p1_kills": 7.4, "p20_kills": 0.7,
                         "kills_per_match": 52.0, "n_matches": 0}
            else:
                print(f"  [{region}] skip: no kill data in CSV", flush=True)
                continue
        observed = {
            "mean_end_match": OBSERVED_MEAN_END_MATCH[region],
            "p1_kills": kills["p1_kills"],
            "p20_kills": kills["p20_kills"],
        }
        scored = grid_search_region(
            region, observed, grid, sims, workers, ns.seed,
        )
        best_ov, best_metrics, best_err = scored[0]
        proposals[region] = {
            "overrides": best_ov,
            "metrics": best_metrics,
            "err": best_err,
            "observed": observed,
            "n_obs_matches": kills.get("n_matches", 0),
            "top3": scored[:3],
        }
        print(
            f"  [{region}] best: sigma={best_ov['strength_sigma']:.2f}, "
            f"lost={best_ov['lost_kill_rate']:.3f}, "
            f"revive={best_ov['revive_knock_mean']:.1f}, "
            f"PKF={best_ov['placement_kill_sharpness']:.2f}  "
            f"-> sim mean={best_metrics[0]:.2f} (obs {observed['mean_end_match']:.2f}), "
            f"err={best_err:.4f}",
            flush=True,
        )

    render_proposal_md(proposals, out_md, grid, sims, ns.dry_run)
    print(f"\nProposal written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
