"""CLI entry point for the 6-format fairness comparison.

Runs Match Point / Fixed-6 / Fixed-8 / Swiss / RoundRobin / DoubleElim
side by side under one regional profile and writes JSON, CSV, and PNG
artefacts. Formats are run sequentially (each one uses the parallel
runner internally) so the inner Pool can use all cores without nested
fork churn.

Usage:
    python tools/run_format_comparison.py --sims 30000 --region apac_n --workers 0
"""

from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path

# Allow running as a script from the project root: `python tools/run_format_comparison.py`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import REGION_PROFILES, SimulationConfig, apply_region_profile  # noqa: E402
from format_comparison import (  # noqa: E402
    FormatComparisonResult,
    comparison_to_csv,
    comparison_to_json,
    compute_format_metrics,
    format_comparison_text,
)
from formats import (  # noqa: E402
    DoubleEliminationFormat,
    FixedMatchesFormat,
    MatchPointFormat,
    RoundRobinFormat,
    SwissFormat,
)
from formats.runner import run_format_simulations  # noqa: E402
from plot import (  # noqa: E402
    plot_drama_and_length,
    plot_format_comparison_bars,
    plot_seed_win_heatmap,
)


# Format catalogue: (key, factory, pool_size, default_sims_at_30000_baseline).
# Heavier formats (multi-lobby) auto-down to 60% of base unless overridden.
FORMAT_CATALOGUE: list[tuple[str, object, int, float]] = [
    ("match_point", MatchPointFormat(), 20, 1.0),
    ("fixed_6",     FixedMatchesFormat(n_matches=6), 20, 1.0),
    ("fixed_8",     FixedMatchesFormat(n_matches=8), 20, 1.0),
    ("swiss",       SwissFormat(), 30, 0.6),
    ("round_robin", RoundRobinFormat(), 30, 0.6),
    ("double_elim", DoubleEliminationFormat(), 30, 0.6),
]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_format_comparison",
        description="Compare ALGS tournament formats on fairness / drama / length.",
    )
    p.add_argument("--sims", type=int, default=10000,
                   help="base simulation count; multi-lobby formats scale down")
    p.add_argument("--region", choices=list(REGION_PROFILES.keys()) + ["custom"],
                   default="apac_n")
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--workers", type=int, default=0,
                   help="parallel workers (0=auto, 1=serial)")
    p.add_argument("--output-dir", type=str, default="out/format_comparison")
    p.add_argument("--formats", type=str, default=None,
                   help="comma-separated subset to run (default: all)")
    p.add_argument("--no-plot", dest="make_plot", action="store_false", default=True)
    p.add_argument("--no-scale", dest="scale_heavy", action="store_false", default=True,
                   help="run every format at the full --sims count")
    return p


def main(argv: list[str] | None = None) -> int:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = _build_parser()
    ns = parser.parse_args(argv if argv is not None else sys.argv[1:])

    cfg = apply_region_profile(SimulationConfig(), ns.region)

    requested = (
        {name.strip() for name in ns.formats.split(",") if name.strip()}
        if ns.formats
        else {name for name, *_ in FORMAT_CATALOGUE}
    )

    comp = FormatComparisonResult(region_profile=ns.region, n_sims_per_format={})

    print(f"Running format comparison (region={ns.region}, seed={ns.seed}, "
          f"workers={ns.workers}, base_sims={ns.sims})")
    print()
    total_t0 = time.time()

    for name, fmt, pool_size, scale in FORMAT_CATALOGUE:
        if name not in requested:
            continue
        n_sims = int(ns.sims * scale) if ns.scale_heavy else ns.sims
        t0 = time.time()
        results = run_format_simulations(
            fmt, cfg, n_sims, seed=ns.seed, workers=ns.workers,
        )
        dt = time.time() - t0
        metrics = compute_format_metrics(results, format_name=name, pool_size=pool_size)
        comp.metrics[name] = metrics
        comp.n_sims_per_format[name] = n_sims
        print(f"  {name:<14} {n_sims:>6} sims in {dt:>6.1f}s "
              f"-> seed1={metrics.seed1_win_rate*100:5.2f}% "
              f"avgM={metrics.mean_matches:5.2f} "
              f"rho={metrics.mean_spearman:+5.3f}")

    total_dt = time.time() - total_t0
    print()
    print(f"Total elapsed: {total_dt:.1f}s")
    print()
    print(format_comparison_text(comp))

    out_dir = Path(ns.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "format_comparison.json"
    csv_path = out_dir / "format_comparison.csv"
    comparison_to_json(comp, json_path)
    comparison_to_csv(comp, csv_path)
    print(f"JSON written: {json_path}")
    print(f"CSV  written: {csv_path}")

    if ns.make_plot:
        bars_path = out_dir / "format_comparison_bars.png"
        heatmap_path = out_dir / "seed_win_heatmap.png"
        drama_path = out_dir / "drama_and_length.png"
        plot_format_comparison_bars(comp, bars_path)
        plot_seed_win_heatmap(comp, heatmap_path)
        plot_drama_and_length(comp, drama_path)
        print(f"PNG written: {bars_path}")
        print(f"PNG written: {heatmap_path}")
        print(f"PNG written: {drama_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
