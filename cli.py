"""Command-line + interactive entry point."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from config import REGION_PROFILES, SimulationConfig, apply_region_profile
from plot import plot_ending_match_distribution
from stats import format_summary_text, summarize, to_csv, to_json
from tournament_sim import run_simulations


REGION_CHOICES = ["custom", "americas", "emea", "apac_n", "apac_s"]
STARTING_CHOICES = ["none", "seeded", "custom"]
DEFAULT_OUT_DIR = Path("out")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="algs_sim",
        description="ALGS Match Point Finals Monte Carlo simulator",
    )
    # Top-level run config
    p.add_argument("--sims", type=int, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--max-matches", type=int, default=None)
    p.add_argument("--match-point-threshold", type=int, default=None)

    # Team strength
    p.add_argument("--strength-sigma", type=float, default=None)
    p.add_argument("--rank-beta", type=float, default=None)
    p.add_argument("--kill-beta", type=float, default=None)
    p.add_argument("--win-beta", type=float, default=None)
    p.add_argument("--consistency-beta", type=float, default=None)
    p.add_argument("--placement-fight-correlation", type=float, default=None)
    p.add_argument("--placement-win-correlation", type=float, default=None)
    p.add_argument("--base-match-noise", type=float, default=None)
    p.add_argument("--volatility-mean", type=float, default=None)
    p.add_argument("--volatility-sigma", type=float, default=None)

    # Respawn
    p.add_argument("--respawn-model", choices=["poisson", "negbin"], default=None)
    p.add_argument("--respawn-mean", type=float, default=None)
    p.add_argument("--respawn-dispersion", type=float, default=None)
    p.add_argument("--max-respawned-players", type=int, default=None)

    # Kill credit
    p.add_argument("--neutral-death-rate", type=float, default=None)
    p.add_argument("--lost-kill-rate", type=float, default=None)
    p.add_argument("--transfer-kill-rate", type=float, default=None)
    p.add_argument("--revive-knock-mean", type=float, default=None)
    p.add_argument("--chaos-multiplier", type=float, default=None)
    p.add_argument("--mp-pressure-lost-kill-multiplier", type=float, default=None)

    # MP pressure
    p.add_argument("--mp-pressure-enabled", dest="mp_pressure_enabled",
                   action="store_true", default=None)
    p.add_argument("--no-mp-pressure", dest="mp_pressure_enabled",
                   action="store_false")
    p.add_argument("--mp-win-penalty", type=float, default=None)
    p.add_argument("--mp-kill-penalty", type=float, default=None)

    # Region & starting points
    p.add_argument("--region-profile", choices=REGION_CHOICES, default=None)
    p.add_argument("--starting-points", choices=STARTING_CHOICES, default=None)
    p.add_argument("--custom-starting-points", type=str, default=None,
                   help="comma-separated 20 integers (only with --starting-points custom)")

    # Output
    p.add_argument("--output-csv", type=str, default=None)
    p.add_argument("--output-json", type=str, default=None)
    p.add_argument("--output-plot", type=str, default=None)
    p.add_argument("--no-plot", dest="make_plot", action="store_false", default=True)
    p.add_argument("--print-summary", action="store_true", default=True)
    p.add_argument("--quiet", dest="print_summary", action="store_false")
    p.add_argument("--show-progress", action="store_true", default=False)
    return p


def _prompt(label: str, default: str) -> str:
    """Prompt with [default] suffix; empty input returns the default."""
    raw = input(f"{label} [{default}]: ").strip()
    return raw if raw else default


def _interactive_inputs() -> dict:
    print("=" * 50)
    print("ALGS Match Point スコアシミュレーター")
    print("=" * 50)
    print("（Enter キーで [] 内のデフォルトを使用）")
    print()

    out: dict = {}
    out["sims"] = int(_prompt("シミュレーション回数", "10000"))
    seed_raw = _prompt("乱数シード（空欄でランダム）", "")
    out["seed"] = int(seed_raw) if seed_raw else None

    print()
    print("リージョンプロファイル:")
    print("  1) americas   2) emea   3) apac_n   4) apac_s   5) custom")
    choice = _prompt("選択 (1-5)", "3")
    region_map = {
        "1": "americas", "2": "emea", "3": "apac_n", "4": "apac_s", "5": "custom",
        "americas": "americas", "emea": "emea", "apac_n": "apac_n",
        "apac_s": "apac_s", "custom": "custom",
    }
    out["region_profile"] = region_map.get(choice, "apac_n")

    print()
    print("出発点設定: none / seeded / custom")
    sp = _prompt("選択", "seeded")
    out["starting_points"] = sp if sp in STARTING_CHOICES else "seeded"
    if out["starting_points"] == "custom":
        cs = _prompt("20個の整数をカンマ区切りで入力", "0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
        out["custom_starting_points"] = cs

    print()
    out["output_csv"] = _prompt("CSV 出力先", str(DEFAULT_OUT_DIR / "summary.csv"))
    out["output_json"] = _prompt("JSON 出力先", str(DEFAULT_OUT_DIR / "summary.json"))
    out["output_plot"] = _prompt("PNG 出力先", str(DEFAULT_OUT_DIR / "histogram.png"))
    print()
    return out


def _build_config(ns: argparse.Namespace, interactive: dict | None) -> tuple[
    SimulationConfig, int, int | None, str, str, str | None, bool
]:
    """Compose final SimulationConfig and run-level settings."""
    base = SimulationConfig()

    region = ns.region_profile
    if region is None and interactive is not None:
        region = interactive["region_profile"]
    region = region or "custom"
    cfg = apply_region_profile(base, region)

    # Build overrides dict from CLI args (only non-None entries override)
    override_map = {
        "max_matches": ns.max_matches,
        "match_point_threshold": ns.match_point_threshold,
        "strength_sigma": ns.strength_sigma,
        "rank_beta": ns.rank_beta,
        "kill_beta": ns.kill_beta,
        "win_beta": ns.win_beta,
        "consistency_beta": ns.consistency_beta,
        "placement_fight_correlation": ns.placement_fight_correlation,
        "placement_win_correlation": ns.placement_win_correlation,
        "base_match_noise": ns.base_match_noise,
        "volatility_mean": ns.volatility_mean,
        "volatility_sigma": ns.volatility_sigma,
        "respawn_model": ns.respawn_model,
        "respawn_mean": ns.respawn_mean,
        "respawn_dispersion": ns.respawn_dispersion,
        "max_respawned_players": ns.max_respawned_players,
        "neutral_death_rate": ns.neutral_death_rate,
        "lost_kill_rate": ns.lost_kill_rate,
        "transfer_kill_rate": ns.transfer_kill_rate,
        "revive_knock_mean": ns.revive_knock_mean,
        "chaos_multiplier": ns.chaos_multiplier,
        "mp_pressure_lost_kill_multiplier": ns.mp_pressure_lost_kill_multiplier,
        "mp_pressure_enabled": ns.mp_pressure_enabled,
        "mp_win_penalty": ns.mp_win_penalty,
        "mp_kill_penalty": ns.mp_kill_penalty,
    }
    overrides = {k: v for k, v in override_map.items() if v is not None}
    if overrides:
        cfg = replace(cfg, **overrides)

    # Starting points
    starting_points_mode = ns.starting_points
    custom_sp_raw = ns.custom_starting_points
    if starting_points_mode is None and interactive is not None:
        starting_points_mode = interactive["starting_points"]
        if starting_points_mode == "custom" and interactive.get("custom_starting_points"):
            custom_sp_raw = interactive["custom_starting_points"]
    starting_points_mode = starting_points_mode or cfg.starting_points_mode

    custom_tuple = None
    if starting_points_mode == "custom":
        if not custom_sp_raw:
            raise ValueError(
                "custom starting points selected but no values were provided"
            )
        custom_tuple = tuple(int(x.strip()) for x in custom_sp_raw.split(",") if x.strip())
    cfg = replace(cfg, starting_points_mode=starting_points_mode,
                  custom_starting_points=custom_tuple)

    # Run-level
    sims = ns.sims if ns.sims is not None else (interactive or {}).get("sims", 10000)
    seed = ns.seed if ns.seed is not None else (interactive or {}).get("seed", None)

    out_csv = ns.output_csv or (interactive or {}).get("output_csv",
                                                       str(DEFAULT_OUT_DIR / "summary.csv"))
    out_json = ns.output_json or (interactive or {}).get("output_json",
                                                         str(DEFAULT_OUT_DIR / "summary.json"))
    if ns.make_plot:
        out_plot = ns.output_plot or (interactive or {}).get("output_plot",
                                                             str(DEFAULT_OUT_DIR / "histogram.png"))
    else:
        out_plot = None

    return cfg, int(sims), seed, out_csv, out_json, out_plot, bool(ns.show_progress)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    argv = argv if argv is not None else sys.argv[1:]
    ns = parser.parse_args(argv)

    interactive = None
    if not argv:
        interactive = _interactive_inputs()

    cfg, sims, seed, out_csv, out_json, out_plot, show_progress = _build_config(
        ns, interactive
    )

    print(f"Running {sims} simulations (region={cfg.region_profile}, "
          f"starting_points={cfg.starting_points_mode}, seed={seed}) ...")
    results = run_simulations(cfg, n_sims=sims, seed=seed, show_progress=show_progress)
    summary = summarize(results, cfg)

    if ns.print_summary:
        print()
        print(format_summary_text(summary))
        print()

    if out_csv:
        to_csv(summary, out_csv)
        print(f"CSV written:  {out_csv}")
    if out_json:
        to_json(summary, out_json)
        print(f"JSON written: {out_json}")
    if out_plot:
        plot_ending_match_distribution(summary, out_plot)
        print(f"Plot written: {out_plot}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
