"""Aggregate out/sweep_eq_*.json or sweep_tilt30_*.json into docs.

Modes (selected via `--mode`):
  - equal  : reads sweep_equal_base.json + sweep_eq_*.json (legacy default).
             Writes docs/sweep_equal_baseline.md. 16 parameters.
  - tilt30 : reads sweep_tilt30_base.json + sweep_tilt30_*.json. Writes
             docs/sweep_tilt30_baseline.md. 12 parameters (main 5 + the
             "no-effect at equal" 7), pinned to strength_sigma=0.30.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "out"
DOCS_DIR = REPO / "docs"

BASE_PATH = OUT_DIR / "sweep_equal_base.json"
TARGET_MD = DOCS_DIR / "sweep_equal_baseline.md"

TILT30_BASE_PATH = OUT_DIR / "sweep_tilt30_base.json"
TILT30_TARGET_MD = DOCS_DIR / "sweep_tilt30_baseline.md"

# param_name -> (base_value, [(value, filename, is_base), ...])
#
# Each sweep is "5 levels, base at level3 (center), evenly spaced".
# strength_sigma is the sole exception: base is at level1, swept only upward,
# because baseline strength_sigma=0.05 is too small to allow a symmetric
# negative-side sweep (would produce negative sigma).
SWEEP_DEFINITIONS: dict[str, tuple[float, list[tuple[float, str, bool]]]] = {
    # --- "main 4" used as the article's primary 4 drivers ---
    "strength_sigma": (0.05, [
        # EXCEPTION: base at level1, 4 levels upward, delta = 0.10
        (0.05, "sweep_equal_base.json", True),
        (0.15, "sweep_eq_strength_sigma_lvl2.json", False),
        (0.25, "sweep_eq_strength_sigma_lvl3.json", False),
        (0.35, "sweep_eq_strength_sigma_lvl4.json", False),
        (0.45, "sweep_eq_strength_sigma_lvl5.json", False),
    ]),
    "lost_kill_rate": (0.06, [  # delta = 0.03
        (0.00, "sweep_eq_lost_kill_rate_lvl1.json", False),
        (0.03, "sweep_eq_lost_kill_rate_lvl2.json", False),
        (0.06, "sweep_equal_base.json", True),
        (0.09, "sweep_eq_lost_kill_rate_lvl4.json", False),
        (0.12, "sweep_eq_lost_kill_rate_lvl5.json", False),
    ]),
    "respawn_mean": (6.0, [  # delta = 2.0
        (2.0, "sweep_eq_respawn_mean_lvl1.json", False),
        (4.0, "sweep_eq_respawn_mean_lvl2.json", False),
        (6.0, "sweep_equal_base.json", True),
        (8.0, "sweep_eq_respawn_mean_lvl4.json", False),
        (10.0, "sweep_eq_respawn_mean_lvl5.json", False),
    ]),
    "mp_win_penalty": (0.10, [  # delta = 0.05
        (0.00, "sweep_eq_mp_win_penalty_lvl1.json", False),
        (0.05, "sweep_eq_mp_win_penalty_lvl2.json", False),
        (0.10, "sweep_equal_base.json", True),
        (0.15, "sweep_eq_mp_win_penalty_lvl4.json", False),
        (0.20, "sweep_eq_mp_win_penalty_lvl5.json", False),
    ]),

    # --- MP pressure brothers + chaos ---
    "mp_kill_penalty": (0.05, [  # delta = 0.025
        (0.00, "sweep_eq_mp_kill_penalty_lvl1.json", False),
        (0.025, "sweep_eq_mp_kill_penalty_lvl2.json", False),
        (0.05, "sweep_equal_base.json", True),
        (0.075, "sweep_eq_mp_kill_penalty_lvl4.json", False),
        (0.10, "sweep_eq_mp_kill_penalty_lvl5.json", False),
    ]),
    "mp_pressure_lost_kill_multiplier": (1.25, [  # delta = 0.25
        (0.75, "sweep_eq_mp_pressure_lost_kill_mult_lvl1.json", False),
        (1.00, "sweep_eq_mp_pressure_lost_kill_mult_lvl2.json", False),
        (1.25, "sweep_equal_base.json", True),
        (1.50, "sweep_eq_mp_pressure_lost_kill_mult_lvl4.json", False),
        (1.75, "sweep_eq_mp_pressure_lost_kill_mult_lvl5.json", False),
    ]),
    "chaos_multiplier": (1.00, [  # delta = 0.25
        (0.50, "sweep_eq_chaos_mult_lvl1.json", False),
        (0.75, "sweep_eq_chaos_mult_lvl2.json", False),
        (1.00, "sweep_equal_base.json", True),
        (1.25, "sweep_eq_chaos_mult_lvl4.json", False),
        (1.50, "sweep_eq_chaos_mult_lvl5.json", False),
    ]),

    # --- strength model details + dispersion ---
    "win_beta": (0.80, [  # delta = 0.25
        (0.30, "sweep_eq_win_beta_lvl1.json", False),
        (0.55, "sweep_eq_win_beta_lvl2.json", False),
        (0.80, "sweep_equal_base.json", True),
        (1.05, "sweep_eq_win_beta_lvl4.json", False),
        (1.30, "sweep_eq_win_beta_lvl5.json", False),
    ]),
    "placement_win_correlation": (0.50, [  # delta = 0.20
        (0.10, "sweep_eq_place_win_corr_lvl1.json", False),
        (0.30, "sweep_eq_place_win_corr_lvl2.json", False),
        (0.50, "sweep_equal_base.json", True),
        (0.70, "sweep_eq_place_win_corr_lvl4.json", False),
        (0.90, "sweep_eq_place_win_corr_lvl5.json", False),
    ]),
    "base_match_noise": (0.80, [  # delta = 0.20
        (0.40, "sweep_eq_base_noise_lvl1.json", False),
        (0.60, "sweep_eq_base_noise_lvl2.json", False),
        (0.80, "sweep_equal_base.json", True),
        (1.00, "sweep_eq_base_noise_lvl4.json", False),
        (1.20, "sweep_eq_base_noise_lvl5.json", False),
    ]),
    "volatility_mean": (1.0, [  # delta = 0.2
        (0.6, "sweep_eq_volatility_mean_lvl1.json", False),
        (0.8, "sweep_eq_volatility_mean_lvl2.json", False),
        (1.0, "sweep_equal_base.json", True),
        (1.2, "sweep_eq_volatility_mean_lvl4.json", False),
        (1.4, "sweep_eq_volatility_mean_lvl5.json", False),
    ]),
    "rank_beta": (1.0, [  # delta = 0.3
        (0.4, "sweep_eq_rank_beta_lvl1.json", False),
        (0.7, "sweep_eq_rank_beta_lvl2.json", False),
        (1.0, "sweep_equal_base.json", True),
        (1.3, "sweep_eq_rank_beta_lvl4.json", False),
        (1.6, "sweep_eq_rank_beta_lvl5.json", False),
    ]),
    "kill_beta": (0.8, [  # delta = 0.2
        (0.4, "sweep_eq_kill_beta_lvl1.json", False),
        (0.6, "sweep_eq_kill_beta_lvl2.json", False),
        (0.8, "sweep_equal_base.json", True),
        (1.0, "sweep_eq_kill_beta_lvl4.json", False),
        (1.2, "sweep_eq_kill_beta_lvl5.json", False),
    ]),
    "respawn_dispersion": (4.0, [  # delta = 1.0
        (2.0, "sweep_eq_respawn_disp_lvl1.json", False),
        (3.0, "sweep_eq_respawn_disp_lvl2.json", False),
        (4.0, "sweep_equal_base.json", True),
        (5.0, "sweep_eq_respawn_disp_lvl4.json", False),
        (6.0, "sweep_eq_respawn_disp_lvl5.json", False),
    ]),

    # --- predicted weak / no effect ---
    # EXCEPTION: transfer_kill_rate is centered at 0.10 (not the config default
    # 0.05) so the symmetric sweep can reach 0.20 — "high-third-party" lobbies
    # are explicitly of interest. All 5 levels are new runs; level3 does NOT
    # reference sweep_equal_base.json.
    "transfer_kill_rate": (0.10, [  # delta = 0.05
        (0.00, "sweep_eq_transfer_kill_lvl1.json", False),
        (0.05, "sweep_eq_transfer_kill_lvl2.json", False),
        (0.10, "sweep_eq_transfer_kill_lvl3.json", True),
        (0.15, "sweep_eq_transfer_kill_lvl4.json", False),
        (0.20, "sweep_eq_transfer_kill_lvl5.json", False),
    ]),
    "neutral_death_rate": (0.03, [  # delta = 0.015
        (0.00, "sweep_eq_neutral_death_lvl1.json", False),
        (0.015, "sweep_eq_neutral_death_lvl2.json", False),
        (0.03, "sweep_equal_base.json", True),
        (0.045, "sweep_eq_neutral_death_lvl4.json", False),
        (0.06, "sweep_eq_neutral_death_lvl5.json", False),
    ]),

    # --- placement structure intervention ---
    # log-space sharpness around the geometric mean of PLACEMENT_KILL_FACTOR.
    # 1.0 = current tuple (1st:20th ~ 12:1); 0.0 = flat (kills proportional to
    # fight skill alone); 2.0 ~ 144:1 ratio. base=level3.
    "placement_kill_sharpness": (1.0, [  # delta = 0.5
        (0.00, "sweep_eq_placement_kill_sharpness_lvl1.json", False),
        (0.50, "sweep_eq_placement_kill_sharpness_lvl2.json", False),
        (1.00, "sweep_equal_base.json", True),
        (1.50, "sweep_eq_placement_kill_sharpness_lvl4.json", False),
        (2.00, "sweep_eq_placement_kill_sharpness_lvl5.json", False),
    ]),

    # --- telemetry-only verification ---
    # revive_knock_mean is recorded into MatchResult but does NOT feed into
    # allocate_kills() or scored_kills. We expect mean ending match to be
    # invariant across the sweep — measuring it just confirms code reading.
    "revive_knock_mean": (10.0, [  # delta = 3.0
        (4.0, "sweep_eq_revive_knock_mean_lvl1.json", False),
        (7.0, "sweep_eq_revive_knock_mean_lvl2.json", False),
        (10.0, "sweep_equal_base.json", True),
        (13.0, "sweep_eq_revive_knock_mean_lvl4.json", False),
        (16.0, "sweep_eq_revive_knock_mean_lvl5.json", False),
    ]),
}

# Tilted-baseline definitions: same level values where applicable so the
# tilt-mode tables sit beside the equal-mode tables apples-to-apples. The
# strength_sigma sweep becomes symmetric around 0.30 (instead of the equal-
# mode one-sided sweep from 0.05). MP-brother / chaos / transfer_kill /
# neutral_death / revive_knock are intentionally omitted — section 5/6 of the
# article doesn't need them re-evaluated under tilt.
SWEEP_DEFINITIONS_TILT30: dict[str, tuple[float, list[tuple[float, str, bool]]]] = {
    # --- main 5 ---
    "strength_sigma": (0.30, [
        (0.10, "sweep_tilt30_strength_sigma_lvl1.json", False),
        (0.20, "sweep_tilt30_strength_sigma_lvl2.json", False),
        (0.30, "sweep_tilt30_base.json", True),
        (0.40, "sweep_tilt30_strength_sigma_lvl4.json", False),
        (0.50, "sweep_tilt30_strength_sigma_lvl5.json", False),
    ]),
    "lost_kill_rate": (0.06, [  # delta = 0.03
        (0.00, "sweep_tilt30_lost_kill_rate_lvl1.json", False),
        (0.03, "sweep_tilt30_lost_kill_rate_lvl2.json", False),
        (0.06, "sweep_tilt30_base.json", True),
        (0.09, "sweep_tilt30_lost_kill_rate_lvl4.json", False),
        (0.12, "sweep_tilt30_lost_kill_rate_lvl5.json", False),
    ]),
    "respawn_mean": (6.0, [  # delta = 2.0
        (2.0, "sweep_tilt30_respawn_mean_lvl1.json", False),
        (4.0, "sweep_tilt30_respawn_mean_lvl2.json", False),
        (6.0, "sweep_tilt30_base.json", True),
        (8.0, "sweep_tilt30_respawn_mean_lvl4.json", False),
        (10.0, "sweep_tilt30_respawn_mean_lvl5.json", False),
    ]),
    "mp_win_penalty": (0.10, [  # delta = 0.05
        (0.00, "sweep_tilt30_mp_win_penalty_lvl1.json", False),
        (0.05, "sweep_tilt30_mp_win_penalty_lvl2.json", False),
        (0.10, "sweep_tilt30_base.json", True),
        (0.15, "sweep_tilt30_mp_win_penalty_lvl4.json", False),
        (0.20, "sweep_tilt30_mp_win_penalty_lvl5.json", False),
    ]),
    "placement_kill_sharpness": (1.0, [  # delta = 0.5
        (0.00, "sweep_tilt30_placement_kill_sharpness_lvl1.json", False),
        (0.50, "sweep_tilt30_placement_kill_sharpness_lvl2.json", False),
        (1.00, "sweep_tilt30_base.json", True),
        (1.50, "sweep_tilt30_placement_kill_sharpness_lvl4.json", False),
        (2.00, "sweep_tilt30_placement_kill_sharpness_lvl5.json", False),
    ]),

    # --- "no-effect at equal" 7 ---
    "win_beta": (0.80, [  # delta = 0.25
        (0.30, "sweep_tilt30_win_beta_lvl1.json", False),
        (0.55, "sweep_tilt30_win_beta_lvl2.json", False),
        (0.80, "sweep_tilt30_base.json", True),
        (1.05, "sweep_tilt30_win_beta_lvl4.json", False),
        (1.30, "sweep_tilt30_win_beta_lvl5.json", False),
    ]),
    "placement_win_correlation": (0.50, [  # delta = 0.20
        (0.10, "sweep_tilt30_place_win_corr_lvl1.json", False),
        (0.30, "sweep_tilt30_place_win_corr_lvl2.json", False),
        (0.50, "sweep_tilt30_base.json", True),
        (0.70, "sweep_tilt30_place_win_corr_lvl4.json", False),
        (0.90, "sweep_tilt30_place_win_corr_lvl5.json", False),
    ]),
    "base_match_noise": (0.80, [  # delta = 0.20
        (0.40, "sweep_tilt30_base_noise_lvl1.json", False),
        (0.60, "sweep_tilt30_base_noise_lvl2.json", False),
        (0.80, "sweep_tilt30_base.json", True),
        (1.00, "sweep_tilt30_base_noise_lvl4.json", False),
        (1.20, "sweep_tilt30_base_noise_lvl5.json", False),
    ]),
    "volatility_mean": (1.0, [  # delta = 0.2
        (0.6, "sweep_tilt30_volatility_mean_lvl1.json", False),
        (0.8, "sweep_tilt30_volatility_mean_lvl2.json", False),
        (1.0, "sweep_tilt30_base.json", True),
        (1.2, "sweep_tilt30_volatility_mean_lvl4.json", False),
        (1.4, "sweep_tilt30_volatility_mean_lvl5.json", False),
    ]),
    "rank_beta": (1.0, [  # delta = 0.3
        (0.4, "sweep_tilt30_rank_beta_lvl1.json", False),
        (0.7, "sweep_tilt30_rank_beta_lvl2.json", False),
        (1.0, "sweep_tilt30_base.json", True),
        (1.3, "sweep_tilt30_rank_beta_lvl4.json", False),
        (1.6, "sweep_tilt30_rank_beta_lvl5.json", False),
    ]),
    "kill_beta": (0.8, [  # delta = 0.2
        (0.4, "sweep_tilt30_kill_beta_lvl1.json", False),
        (0.6, "sweep_tilt30_kill_beta_lvl2.json", False),
        (0.8, "sweep_tilt30_base.json", True),
        (1.0, "sweep_tilt30_kill_beta_lvl4.json", False),
        (1.2, "sweep_tilt30_kill_beta_lvl5.json", False),
    ]),
    "respawn_dispersion": (4.0, [  # delta = 1.0
        (2.0, "sweep_tilt30_respawn_disp_lvl1.json", False),
        (3.0, "sweep_tilt30_respawn_disp_lvl2.json", False),
        (4.0, "sweep_tilt30_base.json", True),
        (5.0, "sweep_tilt30_respawn_disp_lvl4.json", False),
        (6.0, "sweep_tilt30_respawn_disp_lvl5.json", False),
    ]),
}

# (section_id, title, [param_name]).
# mp_win_penalty intentionally appears in both "main4" and "mp_brothers".
SECTIONS: list[tuple[str, str, list[str]]] = [
    ("main4", "記事採用候補 (1): 主要 4 要因",
     ["strength_sigma", "lost_kill_rate", "respawn_mean", "mp_win_penalty"]),
    ("mp_brothers", "記事採用候補 (2): MP 圧力 3 兄弟 + 全試合 lost_kill 倍率",
     ["mp_win_penalty", "mp_kill_penalty",
      "mp_pressure_lost_kill_multiplier", "chaos_multiplier"]),
    ("strength_model",
     "参考資料 (1): 戦力モデル感度 (等戦力ベースでは影響が薄いと予想)",
     ["win_beta", "placement_win_correlation", "base_match_noise",
      "volatility_mean", "rank_beta", "kill_beta", "respawn_dispersion"]),
    ("no_effect", "参考資料 (2): ほぼ効かない検証 (記事では「動かない」の根拠に使う)",
     ["transfer_kill_rate", "neutral_death_rate"]),
    ("placement_structure",
     "記事採用候補 (3): 順位構造への介入 (PLACEMENT_KILL_FACTOR を外出し)",
     ["placement_kill_sharpness"]),
    ("telemetry_only",
     "参考資料 (3): テレメトリのみ (スコア計算には渡らないので不動の予想)",
     ["revive_knock_mean"]),
]

# Section layout for the tilt30 table. The "no-effect at equal" 7 are kept as
# a single bucket here — the article rewrite will split them into "revived"
# vs "still quiet" based on the actual tilt30 numbers, but the table builder
# stays neutral.
SECTIONS_TILT30: list[tuple[str, str, list[str]]] = [
    ("main5", "主要 5 要因 (tilted-strength でも一次効果が支配的)",
     ["strength_sigma", "lost_kill_rate", "respawn_mean", "mp_win_penalty",
      "placement_kill_sharpness"]),
    ("equal_no_effect_7",
     "等戦力では不動だった 7 (tilt で活性化する/しないを判定)",
     ["rank_beta", "kill_beta", "win_beta", "placement_win_correlation",
      "base_match_noise", "volatility_mean", "respawn_dispersion"]),
]

# (display_label, filename, short_description)
CATEGORICAL_CONDITIONS: list[tuple[str, str, str]] = [
    ("mp_pressure_enabled=false", "sweep_equal_no_mp_pressure.json",
     "MP 圧力 3 兄弟 (win_penalty, kill_penalty, lost_kill_multiplier) まとめてオフ"),
    ("starting_points_mode=seeded", "sweep_equal_seeded.json",
     "レガシー seed bonus を有効化 (現行 ALGS には無し)"),
    ("respawn_model=poisson", "sweep_equal_respawn_poisson.json",
     "Poisson 分布 (mean 6.0 固定, NegBin より分散小)"),
]

METRIC_COLUMNS: list[tuple[str, str, str]] = [
    ("mean", "mean", "{:.2f}"),
    ("median", "median", "{:.1f}"),
    ("mode", "mode", "{:d}"),
    ("prob_exceeds_10", "P(>10)", "{:.3f}"),
    ("prob_exceeds_12", "P(>12)", "{:.3f}"),
    ("avg_first_mp_match", "first MP", "{:.2f}"),
    ("avg_eligible_at_ending_match_start", "elig@end", "{:.2f}"),
    ("avg_scored_kills", "scored kills", "{:.2f}"),
]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def fmt(value, spec: str) -> str:
    if value is None:
        return "-"
    try:
        return spec.format(value)
    except (ValueError, TypeError):
        return str(value)


def format_param_value(param: str, value: float) -> str:
    # respawn_mean / respawn_dispersion / revive_knock_mean: 1 decimal looks
    # more natural for >1 ranges.
    if param in ("respawn_mean", "respawn_dispersion", "revive_knock_mean"):
        return f"{value:.1f}"
    # mp_kill_penalty / neutral_death_rate need 3 decimals for the 0.025 /
    # 0.015 step values. transfer_kill_rate now uses 0.05-step (2 decimals).
    if param in ("mp_kill_penalty", "neutral_death_rate"):
        return f"{value:.3f}"
    return f"{value:.2f}"


def build_param_table(param: str, definitions=None) -> str:
    if definitions is None:
        definitions = SWEEP_DEFINITIONS
    base_value, rows = definitions[param]
    header = "| value | " + " | ".join(name for _, name, _ in METRIC_COLUMNS) + " |"
    sep = "|---" + "|---" * len(METRIC_COLUMNS) + "|"
    lines = [f"#### `{param}` (baseline = {format_param_value(param, base_value)})",
             "",
             header,
             sep]
    for value, filename, is_base in rows:
        path = OUT_DIR / filename
        if not path.exists():
            print(f"  warning: missing {path.name}, skipping row")
            continue
        data = load_json(path)
        label = format_param_value(param, value)
        if is_base:
            label = f"**{label} [base]**"
        cells = [label]
        for key, _, spec in METRIC_COLUMNS:
            cells.append(fmt(data.get(key), spec))
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def build_baseline_section(base_path: Path | None = None) -> str:
    if base_path is None:
        base_path = BASE_PATH
    if not base_path.exists():
        return f"_(baseline file missing: out/{base_path.name})_\n"
    data = load_json(base_path)
    rows = [
        f"- n_sims: **{data.get('n_sims')}**",
        f"- region_profile: `{data.get('region_profile')}`",
        f"- starting_points_mode: `{data.get('starting_points_mode')}`",
        f"- match_point_threshold: {data.get('match_point_threshold')}",
        "",
        "| metric | value |",
        "|---|---|",
    ]
    for key, name, spec in METRIC_COLUMNS:
        rows.append(f"| {name} | {fmt(data.get(key), spec)} |")
    return "\n".join(rows) + "\n"


def build_overview_table(definitions=None) -> str:
    """Compact overview: each sweep's mean across levels side by side."""
    if definitions is None:
        definitions = SWEEP_DEFINITIONS
    header = "| param | levels (low -> high) | mean range |"
    sep = "|---|---|---|"
    lines = [header, sep]
    for param, (base_value, rows) in definitions.items():
        means = []
        for value, filename, _ in rows:
            path = OUT_DIR / filename
            if not path.exists():
                means.append("-")
                continue
            d = load_json(path)
            means.append(f"{d.get('mean', float('nan')):.2f}")
        levels = " -> ".join(format_param_value(param, v) for v, _, _ in rows)
        lines.append(f"| `{param}` | {levels} | {' -> '.join(means)} |")
    return "\n".join(lines) + "\n"


def build_categorical_section(base_path: Path | None = None) -> str:
    if base_path is None:
        base_path = BASE_PATH
    if not base_path.exists():
        return ""
    base_data = load_json(base_path)
    header = ("| condition | mean | median | P(>10) | first MP | elig@end "
              "| scored kills | description |")
    sep = "|---|---|---|---|---|---|---|---|"
    lines = [header, sep]
    cells = [
        "**base (all defaults)**",
        fmt(base_data.get("mean"), "{:.2f}"),
        fmt(base_data.get("median"), "{:.1f}"),
        fmt(base_data.get("prob_exceeds_10"), "{:.3f}"),
        fmt(base_data.get("avg_first_mp_match"), "{:.2f}"),
        fmt(base_data.get("avg_eligible_at_ending_match_start"), "{:.2f}"),
        fmt(base_data.get("avg_scored_kills"), "{:.2f}"),
        "mp_pressure=true, starting_points=none, respawn_model=negbin",
    ]
    lines.append("| " + " | ".join(cells) + " |")
    for label, filename, desc in CATEGORICAL_CONDITIONS:
        path = OUT_DIR / filename
        if not path.exists():
            print(f"  warning: missing {path.name}, skipping categorical row")
            continue
        d = load_json(path)
        cells = [
            f"`{label}`",
            fmt(d.get("mean"), "{:.2f}"),
            fmt(d.get("median"), "{:.1f}"),
            fmt(d.get("prob_exceeds_10"), "{:.3f}"),
            fmt(d.get("avg_first_mp_match"), "{:.2f}"),
            fmt(d.get("avg_eligible_at_ending_match_start"), "{:.2f}"),
            fmt(d.get("avg_scored_kills"), "{:.2f}"),
            desc,
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["equal", "tilt30"], default="equal",
                        help="どのスイープ集合を集計するか (default: equal)")
    args = parser.parse_args(argv)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    if args.mode == "equal":
        definitions = SWEEP_DEFINITIONS
        sections = SECTIONS
        base_path = BASE_PATH
        target_md = TARGET_MD
        include_categorical = True
        header_title = ("# 等戦力ベースラインからのパラメータ感度スイープ "
                        "(V2: 等間隔)\n")
        header_blurb = (
            "ALGS Match Point Finals シミュレータを `strength_sigma=0.05` の"
            "「ほぼ拮抗」ベースラインで固定し、16 個の連続値パラメータについて "
            "5 段階を **ベース値を中央 (level3) に置き等間隔** で振った結果 "
            "(strength_sigma のみベース値が小さく対称な負側を取れないため、"
            "ベースを level1 とした片側等間隔スイープ)。3 個の対照条件 "
            "(categorical) も並記。全条件 10000 sims, seed=42, workers=auto。"
            "生成: `tools/build_sweep_table.py --mode equal`。\n"
        )
        baseline_section_title = "## ベースライン (sweep_equal_base.json)\n"
    else:
        definitions = SWEEP_DEFINITIONS_TILT30
        sections = SECTIONS_TILT30
        base_path = TILT30_BASE_PATH
        target_md = TILT30_TARGET_MD
        include_categorical = False
        header_title = ("# Tilted ベースライン (strength_sigma=0.30) からの "
                        "パラメータ感度スイープ\n")
        header_blurb = (
            "等戦力ベース (strength_sigma=0.05) の評価では一次効果が見えにくい"
            "戦力モデル直接の係数群を、現実的な戦力傾斜 strength_sigma=0.30 "
            "(cycle 13 で pin した article 第 2-6 節の改稿基準) の下で再評価"
            "した結果。12 パラメータ = 主要 5 (strength_sigma / lost_kill_rate"
            " / respawn_mean / mp_win_penalty / placement_kill_sharpness) + "
            "「等戦力では不動」7 (rank_beta / kill_beta / win_beta / "
            "placement_win_correlation / base_match_noise / volatility_mean "
            "/ respawn_dispersion) を各 5 段階 (ベース level3 を中央に等間隔)。"
            "全条件 10000 sims, seed=42, workers=0。生成: "
            "`tools/build_sweep_table.py --mode tilt30`。\n"
        )
        baseline_section_title = "## ベースライン (sweep_tilt30_base.json)\n"

    parts: list[str] = []
    parts.append(header_title)
    parts.append(header_blurb)

    parts.append(baseline_section_title)
    parts.append(build_baseline_section(base_path))

    parts.append("\n## 全パラメータ概観 (mean of ending match across levels)\n")
    parts.append(build_overview_table(definitions))

    for section_id, title, params in sections:
        parts.append(f"\n## {title}\n")
        for param in params:
            if param not in definitions:
                continue
            parts.append(build_param_table(param, definitions))

    if include_categorical:
        parts.append("\n## 対照条件 (categorical, single-row)\n")
        parts.append(build_categorical_section(base_path))

    parts.append(
        "\n## 列定義\n"
        "- `mean` / `median` / `mode`: 終了試合数 (ending match) の代表値\n"
        "- `P(>10)` / `P(>12)`: 終了試合数が 10 / 12 を超える確率\n"
        "- `first MP`: 初めて MP-eligible (>=50点) チームが出る試合の平均\n"
        "- `elig@end`: 最終試合開始時点での eligible チーム数の平均\n"
        "- `scored kills`: 1 試合あたりスコアに計上されたキル数の平均\n"
    )

    text = "\n".join(parts)
    target_md.write_text(text, encoding="utf-8")
    print(f"wrote: {target_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
