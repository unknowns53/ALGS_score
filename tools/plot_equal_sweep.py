"""Generate one overlay PNG per swept parameter (5 series each).

`--mode equal`  : reads SWEEP_DEFINITIONS, writes plot_equal_sweep_*.png
`--mode tilt30` : reads SWEEP_DEFINITIONS_TILT30, writes plot_tilt30_sweep_*.png
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams

# Reuse the same definitions as the table builder.
from build_sweep_table import (  # type: ignore
    SWEEP_DEFINITIONS,
    SWEEP_DEFINITIONS_TILT30,
    OUT_DIR,
    format_param_value,
)

rcParams["font.family"] = "Arial"
rcParams["axes.unicode_minus"] = False

# A color ramp from cool -> warm so the eye can read low -> high level order.
COLORS = ["#1D4ED8", "#0891B2", "#059669", "#D97706", "#DC2626"]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def plot_param(param: str, base_value: float,
               rows: list[tuple[float, str, bool]],
               mode: str = "equal") -> Path | None:
    fig, ax = plt.subplots(figsize=(9.0, 5.4), dpi=140)

    plotted = 0
    for (value, filename, is_base), color in zip(rows, COLORS):
        path = OUT_DIR / filename
        if not path.exists():
            print(f"  warning: missing {path.name}, skipping series")
            continue
        data = load_json(path)
        dist = data.get("ending_match_distribution", {})
        if not dist:
            continue
        matches = sorted(int(k) for k in dist.keys())
        probs = [dist[str(m)] for m in matches]
        mean = data.get("mean", float("nan"))
        label = (f"{param}={format_param_value(param, value)} "
                 f"(mean {mean:.2f})")
        if is_base:
            label += " [base]"
            linewidth = 2.4
            linestyle = "-"
            marker = "o"
            markersize = 6.0
        else:
            linewidth = 1.5
            linestyle = "-"
            marker = "o"
            markersize = 4.0
        ax.plot(matches, probs, marker=marker, markersize=markersize,
                linewidth=linewidth, linestyle=linestyle, color=color,
                label=label, alpha=0.95)
        plotted += 1

    if plotted == 0:
        plt.close(fig)
        return None

    ax.set_xlabel("Ending match")
    ax.set_ylabel("Probability")
    title_prefix = ("Equal-baseline sweep" if mode == "equal"
                    else "Tilted-baseline (ss=0.30) sweep")
    ax.set_title(
        f"{title_prefix}: {param} "
        f"(baseline {format_param_value(param, base_value)})"
    )
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_ylim(bottom=0)
    fig.tight_layout()

    out_prefix = "plot_equal_sweep" if mode == "equal" else "plot_tilt30_sweep"
    out_path = OUT_DIR / f"{out_prefix}_{param}.png"
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["equal", "tilt30"], default="equal",
                        help="どのスイープ集合を描くか (default: equal)")
    args = parser.parse_args(argv)

    definitions = (SWEEP_DEFINITIONS if args.mode == "equal"
                   else SWEEP_DEFINITIONS_TILT30)

    written = []
    for param, (base_value, rows) in definitions.items():
        path = plot_param(param, base_value, rows, mode=args.mode)
        if path is not None:
            print(f"wrote: {path}")
            written.append(path)
    print(f"\n{len(written)} plot(s) written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
