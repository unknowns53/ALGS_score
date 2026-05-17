"""Render the 6 article-draft tables as PNG images for note upload.

note's editor does not parse Markdown pipe-tables; tables paste in as
broken text. So we render each table to a PNG with matplotlib and the
user uploads them as images.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams

# Exception to the project-wide Arial rule (CLAUDE.md): these tables are
# for a Japanese note article and contain Japanese parameter descriptions.
# matplotlib's font fallback for missing glyphs is unreliable, so we set
# Yu Gothic UI as primary (which carries both Japanese and Latin glyphs
# and is the recommended UI font on Windows 11 per CLAUDE.md WPF section).
rcParams["font.family"] = ["Noto Sans JP", "Yu Gothic", "Meiryo", "MS Gothic"]
rcParams["axes.unicode_minus"] = False

OUT_DIR = Path(__file__).resolve().parent.parent / "out" / "article_tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Color palette
HEADER_BG = "#E5E7EB"
HIGHLIGHT_BG = "#FEF3C7"
GRID = "#D1D5DB"


def render_table(
    headers: list[str],
    rows: list[list[str]],
    filename: str,
    col_widths: list[float] | None = None,
    highlight_rows: list[int] | None = None,
    bold_cols: list[int] | None = None,
    title: str | None = None,
    fontsize: int = 11,
) -> Path:
    n_cols = len(headers)
    n_rows = len(rows) + 1

    if col_widths is None:
        col_widths = [1.6] * n_cols
    fig_w = sum(col_widths)
    fig_h = 0.45 * n_rows + (0.5 if title else 0.2)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=160)
    ax.axis("off")

    if title:
        ax.set_title(title, fontsize=fontsize + 1, weight="bold",
                     loc="left", pad=8)

    table = ax.table(
        cellText=rows,
        colLabels=headers,
        cellLoc="center",
        loc="center",
        colWidths=[w / fig_w for w in col_widths],
    )

    table.auto_set_font_size(False)
    table.set_fontsize(fontsize)
    table.scale(1, 1.45)

    # Header styling
    for j in range(n_cols):
        cell = table[(0, j)]
        cell.set_facecolor(HEADER_BG)
        cell.set_text_props(weight="bold")
        cell.set_edgecolor(GRID)

    # Body cell edge color
    for i in range(1, n_rows):
        for j in range(n_cols):
            cell = table[(i, j)]
            cell.set_edgecolor(GRID)

    # Highlight rows
    if highlight_rows:
        for row_idx in highlight_rows:
            for j in range(n_cols):
                table[(row_idx + 1, j)].set_facecolor(HIGHLIGHT_BG)

    # Bold columns
    if bold_cols:
        for i in range(1, n_rows):
            for j in bold_cols:
                table[(i, j)].set_text_props(weight="bold")

    out_path = OUT_DIR / filename
    plt.savefig(out_path, bbox_inches="tight", dpi=160,
                facecolor="white")
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# Table 1: Baseline metrics (Section 1)
# ---------------------------------------------------------------------------
def table_base_metrics() -> Path:
    headers = ["Metric", "Value"]
    rows = [
        ["Mean ending match", "9.06"],
        ["Median", "9"],
        ["Mode", "9"],
        ["P(> 10 matches)", "21.6%"],
        ["P(> 12 matches)", "2.4%"],
        ["First MP-eligible match (avg)", "5.78"],
        ["MP-eligible at end (avg teams)", "8.01"],
        ["Scored kills per match (avg)", "57.27"],
    ]
    return render_table(
        headers, rows,
        filename="table_1_base_metrics.png",
        col_widths=[3.8, 1.8],
        bold_cols=[1],
    )


# ---------------------------------------------------------------------------
# Table 2: Main 4 factors (Section 2)
# ---------------------------------------------------------------------------
def table_main_4_factors() -> Path:
    headers = ["Parameter", "Range", "Mean shift", "Direction"]
    rows = [
        ["strength_sigma (戦力分散)",
         "0.05 → 0.45", "9.06 → 7.53 (Δ -1.53)", "格差拡大で短縮"],
        ["lost_kill_rate (失われるキル)",
         "0.00 → 0.12", "8.83 → 9.32 (Δ +0.49)", "キル価値低下で長尺化"],
        ["respawn_mean (1試合あたりの平均リスポーン数)",
         "2.0 → 10.0", "9.26 → 8.83 (Δ -0.43)", "復活増加で短縮"],
        ["mp_win_penalty (MP後勝利抑制)",
         "0.00 → 0.20", "8.93 → 9.20 (Δ +0.27)", "抑制強化で長尺化"],
    ]
    return render_table(
        headers, rows,
        filename="table_2_main_4_factors.png",
        col_widths=[4.5, 1.6, 2.6, 3.0],
        bold_cols=[2],
        fontsize=10,
    )


# ---------------------------------------------------------------------------
# Table 3: MP pressure 3 siblings (Section 3)
# ---------------------------------------------------------------------------
def table_mp_pressure_3() -> Path:
    headers = ["Parameter", "Range", "Mean shift"]
    rows = [
        ["mp_win_penalty",
         "0.00 → 0.20", "8.93 → 9.20 (Δ +0.27)"],
        ["mp_kill_penalty",
         "0.000 → 0.100", "9.06 → 9.08 (Δ +0.02)"],
        ["mp_pressure_lost_kill_multiplier",
         "0.75 → 1.75", "9.02 → 9.08 (Δ +0.06)"],
    ]
    return render_table(
        headers, rows,
        filename="table_3_mp_pressure_3.png",
        col_widths=[4.5, 1.8, 2.6],
        highlight_rows=[0],
        bold_cols=[2],
    )


# ---------------------------------------------------------------------------
# Table 4: placement_kill_sharpness (Section 5 — new)
# ---------------------------------------------------------------------------
def table_placement_kill_sharpness() -> Path:
    headers = ["placement_kill_sharpness", "Mean", "first MP",
               "elig@end", "Scored kills"]
    rows = [
        ["0.00 (全順位均等)", "9.70", "7.10", "9.41", "57.39"],
        ["0.50", "9.39", "6.44", "8.58", "57.32"],
        ["1.00 (base)", "9.06", "5.78", "8.01", "57.27"],
        ["1.50", "8.75", "5.21", "7.53", "57.22"],
        ["2.00 (上位独占)", "8.50", "4.78", "7.21", "57.19"],
    ]
    return render_table(
        headers, rows,
        filename="table_4_placement_kill_sharpness.png",
        col_widths=[3.2, 1.4, 1.6, 1.6, 2.0],
        highlight_rows=[2],
        bold_cols=[1],
        fontsize=10,
    )


# ---------------------------------------------------------------------------
# Table 5: transfer_kill_rate (Section 6)
# ---------------------------------------------------------------------------
def table_transfer_kill_rate() -> Path:
    headers = ["transfer_kill_rate", "Mean ending match", "Scored kills / match"]
    rows = [
        ["0.00", "9.04", "57.25"],
        ["0.05", "9.06", "57.27"],
        ["0.10 (base)", "9.11", "57.28"],
        ["0.15", "9.12", "57.30"],
        ["0.20", "9.12", "57.29"],
    ]
    return render_table(
        headers, rows,
        filename="table_5_transfer_kill_rate.png",
        col_widths=[2.4, 2.4, 2.6],
        highlight_rows=[2],
    )


# ---------------------------------------------------------------------------
# Table 6: Inert parameters (Section 7)
# ---------------------------------------------------------------------------
def table_inert_params() -> Path:
    headers = ["Parameter", "Meaning"]
    rows = [
        ["rank_beta",
         "順位 (placement) 決定で placement_skill をどれだけ重視するか"],
        ["kill_beta",
         "キル取得で fight_skill をどれだけ重視するか"],
        ["win_beta",
         "1位抽選で win_conversion (勝ち切り力) をどれだけ重視するか"],
        ["placement_win_correlation",
         "順位スキルと勝ち切り力の相関"],
        ["base_match_noise",
         "試合ごとに各チームの順位重みに乗るノイズの大きさ"],
        ["volatility_mean",
         "チーム個別のばらつき係数の平均"],
        ["respawn_dispersion",
         "リスポーン数の分散 (NegBin の dispersion 値、平均は変えず裾の厚さだけ動く)"],
    ]
    return render_table(
        headers, rows,
        filename="table_6_inert_params.png",
        col_widths=[2.8, 6.5],
        fontsize=10,
    )


# ---------------------------------------------------------------------------
# Table 7: Categorical conditions (Section 8)
# ---------------------------------------------------------------------------
def table_categorical_conditions() -> Path:
    headers = ["Condition", "Mean", "vs base", "Description"]
    rows = [
        ["base (現行 ALGS 相当)",
         "9.06", "—",
         "mp_pressure=on, starting_points=none, respawn=NegBin"],
        ["mp_pressure_enabled=false",
         "8.90", "-0.16",
         "MP 圧力 3 兄弟まとめてオフ"],
        ["starting_points_mode=seeded",
         "8.58", "-0.48",
         "レガシー seed bonus (上位シードに事前ポイント)"],
        ["respawn_model=poisson",
         "9.06", "-0.00",
         "復活分散だけ小さい Poisson"],
    ]
    return render_table(
        headers, rows,
        filename="table_7_categorical_conditions.png",
        col_widths=[3.6, 1.2, 1.4, 5.0],
        highlight_rows=[0],
        fontsize=10,
    )


def main() -> int:
    builders = [
        table_base_metrics,
        table_main_4_factors,
        table_mp_pressure_3,
        table_placement_kill_sharpness,
        table_transfer_kill_rate,
        table_inert_params,
        table_categorical_conditions,
    ]
    for build in builders:
        path = build()
        print(f"wrote: {path}")
    print(f"\n{len(builders)} table(s) written to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
