"""Command-line + interactive entry point."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import fields, replace
from pathlib import Path

from config import REGION_PROFILES, SimulationConfig, apply_region_profile
from plot import plot_ending_match_distribution
from stats import format_summary_text, summarize, to_csv, to_json
from tournament_sim import run_simulations


REGION_CHOICES = ["custom", "americas", "emea", "apac_n", "apac_s"]
STARTING_CHOICES = ["none", "seeded", "custom"]
DEFAULT_OUT_DIR = Path("out")

# Run-level keys that may appear in a JSON config file alongside
# SimulationConfig fields.
RUN_LEVEL_JSON_KEYS = {
    "sims", "seed", "workers",
    "starting_points",          # alias for starting_points_mode
    "output_csv", "output_json", "output_plot",
    "make_plot", "print_summary", "show_progress",
}

# Fields of SimulationConfig that may be set from JSON.
_CONFIG_FIELD_NAMES = {f.name for f in fields(SimulationConfig)}

# Union of accepted JSON keys.
ALLOWED_JSON_KEYS = _CONFIG_FIELD_NAMES | RUN_LEVEL_JSON_KEYS


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="algs_sim",
        description="ALGS Match Point Finals Monte Carlo simulator",
    )
    # JSON config file
    p.add_argument("--config", type=str, default=None,
                   help="path to a JSON config file (CLI flags still override)")

    # Top-level run config
    p.add_argument("--sims", type=int, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--workers", type=int, default=None,
                   help="parallel worker processes (0 = auto, 1 = serial)")
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
    p.add_argument("--placement-kill-sharpness", type=float, default=None,
                   help="log-space scaling around the geometric mean of the "
                        "per-placement kill factor tuple. 1.0 = base, "
                        "0.0 = uniform, >1.0 = sharper")
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


def _load_json_config(path: str | Path) -> dict:
    """Load a JSON config file and validate top-level keys."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"config file not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"config JSON must contain an object at the top level: {p}")

    unknown = set(data.keys()) - ALLOWED_JSON_KEYS
    if unknown:
        allowed_preview = sorted(ALLOWED_JSON_KEYS)
        print(
            f"warning: unknown keys in {p}: {sorted(unknown)}\n"
            f"         (valid keys include: "
            f"{', '.join(allowed_preview[:8])}, ...)",
            file=sys.stderr,
        )
    return data


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
    workers_raw = _prompt("並列ワーカー数 (1=直列, 0=自動)", "1")
    out["workers"] = int(workers_raw) if workers_raw else 1

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
    print("  （現行 ALGS は持ち越し点なし。明示的な理由が無ければ none 推奨）")
    sp = _prompt("選択", "none")
    out["starting_points"] = sp if sp in STARTING_CHOICES else "none"
    if out["starting_points"] == "custom":
        cs = _prompt("20個の整数をカンマ区切りで入力", "0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
        out["custom_starting_points"] = cs

    print()
    out["output_csv"] = _prompt("CSV 出力先", str(DEFAULT_OUT_DIR / "summary.csv"))
    out["output_json"] = _prompt("JSON 出力先", str(DEFAULT_OUT_DIR / "summary.json"))
    out["output_plot"] = _prompt("PNG 出力先", str(DEFAULT_OUT_DIR / "histogram.png"))
    print()
    return out


def _pick(*candidates):
    """Return the first candidate that is not None / empty marker."""
    for c in candidates:
        if c is not None:
            return c
    return None


def _build_config(
    ns: argparse.Namespace,
    interactive: dict | None,
    json_cfg: dict | None,
) -> tuple[SimulationConfig, int, int | None, str, str, str | None, bool, int]:
    """Compose SimulationConfig and run-level settings.

    Priority: CLI flag > JSON config > interactive prompt > built-in default.
    """
    base = SimulationConfig()
    json_cfg = json_cfg or {}
    interactive = interactive or {}

    # Region profile is special: applied first so per-field overrides win.
    region = _pick(
        ns.region_profile,
        json_cfg.get("region_profile"),
        interactive.get("region_profile"),
    ) or "custom"
    cfg = apply_region_profile(base, region)

    # Per-field overrides (SimulationConfig fields except region/starting points,
    # which need special handling).
    field_keys = [
        "max_matches", "match_point_threshold",
        "strength_sigma", "rank_beta", "kill_beta", "win_beta",
        "consistency_beta",
        "placement_fight_correlation", "placement_win_correlation",
        "base_match_noise", "volatility_mean", "volatility_sigma",
        "respawn_model", "respawn_mean", "respawn_dispersion",
        "max_respawned_players",
        "champion_remaining_min", "champion_remaining_max",
        "champion_remaining_weights",
        "neutral_death_rate", "lost_kill_rate", "transfer_kill_rate",
        "revive_knock_mean", "chaos_multiplier",
        "mp_pressure_lost_kill_multiplier",
        "placement_kill_sharpness",
        "mp_pressure_enabled", "mp_win_penalty", "mp_kill_penalty",
        "num_teams", "players_per_team",
    ]
    overrides: dict = {}
    for key in field_keys:
        cli_value = getattr(ns, key, None)
        chosen = _pick(cli_value, json_cfg.get(key))
        if chosen is None:
            continue
        # JSON arrays come back as lists; coerce to tuple for tuple-typed fields.
        if key == "champion_remaining_weights" and isinstance(chosen, list):
            chosen = tuple(float(x) for x in chosen)
        overrides[key] = chosen
    if overrides:
        cfg = replace(cfg, **overrides)

    # Starting points (accept both "starting_points" and "starting_points_mode" in JSON)
    starting_points_mode = _pick(
        ns.starting_points,
        json_cfg.get("starting_points"),
        json_cfg.get("starting_points_mode"),
        interactive.get("starting_points"),
        cfg.starting_points_mode,
    )

    custom_sp_raw = _pick(
        ns.custom_starting_points,
        json_cfg.get("custom_starting_points"),
        interactive.get("custom_starting_points"),
    )

    custom_tuple = None
    if starting_points_mode == "custom":
        if custom_sp_raw is None:
            raise ValueError(
                "custom starting points selected but no values were provided"
            )
        if isinstance(custom_sp_raw, (list, tuple)):
            custom_tuple = tuple(int(x) for x in custom_sp_raw)
        else:
            custom_tuple = tuple(
                int(x.strip()) for x in str(custom_sp_raw).split(",") if x.strip()
            )
    cfg = replace(
        cfg,
        starting_points_mode=starting_points_mode,
        custom_starting_points=custom_tuple,
    )

    # Run-level
    sims = _pick(ns.sims, json_cfg.get("sims"), interactive.get("sims"), 10000)
    seed = _pick(ns.seed, json_cfg.get("seed"), interactive.get("seed"))
    workers = _pick(
        ns.workers,
        json_cfg.get("workers"),
        interactive.get("workers"),
        1,
    )

    out_csv = _pick(
        ns.output_csv, json_cfg.get("output_csv"),
        interactive.get("output_csv"),
        str(DEFAULT_OUT_DIR / "summary.csv"),
    )
    out_json = _pick(
        ns.output_json, json_cfg.get("output_json"),
        interactive.get("output_json"),
        str(DEFAULT_OUT_DIR / "summary.json"),
    )

    # make_plot may be turned off via CLI (--no-plot) or JSON (make_plot=false).
    make_plot_flag = ns.make_plot
    if "make_plot" in json_cfg and ns.make_plot is True:
        # CLI default is True, so JSON wins unless user explicitly passed --no-plot
        # (which sets make_plot=False -- detected below).
        make_plot_flag = bool(json_cfg["make_plot"])
    if ns.make_plot is False:
        make_plot_flag = False

    if make_plot_flag:
        out_plot = _pick(
            ns.output_plot, json_cfg.get("output_plot"),
            interactive.get("output_plot"),
            str(DEFAULT_OUT_DIR / "histogram.png"),
        )
    else:
        out_plot = None

    # show_progress: CLI --show-progress (store_true) wins if set; otherwise honour JSON.
    if ns.show_progress:
        show_progress = True
    else:
        show_progress = bool(json_cfg.get("show_progress", False))

    return (
        cfg, int(sims), seed, out_csv, out_json, out_plot,
        show_progress, int(workers),
    )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    argv = argv if argv is not None else sys.argv[1:]
    ns = parser.parse_args(argv)

    json_cfg: dict | None = None
    if ns.config:
        json_cfg = _load_json_config(ns.config)

    interactive = None
    # Interactive prompt only when no args AND no config file given.
    if not argv:
        interactive = _interactive_inputs()

    cfg, sims, seed, out_csv, out_json, out_plot, show_progress, workers = (
        _build_config(ns, interactive, json_cfg)
    )

    # print_summary respects JSON too.
    print_summary = ns.print_summary
    if json_cfg is not None and "print_summary" in json_cfg and ns.print_summary is True:
        print_summary = bool(json_cfg["print_summary"])

    print(f"Running {sims} simulations (region={cfg.region_profile}, "
          f"starting_points={cfg.starting_points_mode}, seed={seed}, "
          f"workers={workers}) ...")
    results = run_simulations(
        cfg, n_sims=sims, seed=seed,
        show_progress=show_progress, workers=workers,
    )
    summary = summarize(results, cfg)

    if print_summary:
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
