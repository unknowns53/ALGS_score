"""Fetch ALGS Pro League / Global Finals per-match standings from Liquipedia.

Uses the MediaWiki API to pull the raw wikitext of a Finals page, then
parses the `Bracket` template's `TeamOpponent` blocks for per-game
(placement, kills) values stored in `m1={{MS|placement|kills}}` slots.

The output is CSV rows in the format used by
`data/region_kill_breakdown.csv`:

    region,tournament,match_number,placement,team_kills

Usage:
    python -m tools.fetch_liquipedia_finals \
        --page Apex_Legends_Global_Series/2024/Split_1/Pro_League/APAC_South/Final \
        --region apac_s --tournament 2024-S1-Pro-League-Finals

The script never modifies the CSV itself. Splice the output into
`data/region_kill_breakdown.csv` manually (or via a one-off Python
helper) preserving the documented sort order
region -> tournament -> match -> placement.
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import re
import sys
import urllib.parse
import urllib.request


API_URL = "https://liquipedia.net/apexlegends/api.php"
UA = "algs-score-research/1.0 (https://github.com/unknowns53)"

OPP_RE = re.compile(
    r"opponent(\d+)=\{\{TeamOpponent\|([^|]+?)\s*\|(.*?\}\})\}\}",
    re.DOTALL,
)
MS_RE = re.compile(r"m(\d+)=\{\{MS\|(\d+)\|(\d+)\}\}")


def fetch_wikitext(page: str) -> str:
    params = {"action": "parse", "page": page, "prop": "wikitext", "format": "json"}
    req = urllib.request.Request(
        API_URL + "?" + urllib.parse.urlencode(params),
        headers={"User-Agent": UA, "Accept-Encoding": "gzip"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    payload = json.loads(raw.decode("utf-8"))
    if "parse" not in payload:
        raise RuntimeError(f"unexpected API response for {page}: {payload!r}")
    return payload["parse"]["wikitext"]["*"]


def parse_per_match(wikitext: str) -> dict[int, dict[int, int]]:
    """Return {match_number: {placement: kills}} for all m1..mN found."""
    per_match: dict[int, dict[int, int]] = {}
    for tm in OPP_RE.finditer(wikitext):
        body = tm.group(3)
        for mm in MS_RE.finditer(body):
            m = int(mm.group(1))
            p = int(mm.group(2))
            k = int(mm.group(3))
            per_match.setdefault(m, {})[p] = k
    return per_match


def emit_rows(region: str, tournament: str,
              per_match: dict[int, dict[int, int]]) -> list[str]:
    rows: list[str] = []
    for m in sorted(per_match):
        for p in sorted(per_match[m]):
            rows.append(f"{region},{tournament},{m},{p},{per_match[m][p]}")
    return rows


def main(argv: list[str] | None = None) -> int:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page", required=True,
                        help="Liquipedia page path, e.g. "
                             "'Apex_Legends_Global_Series/2024/Split_1/"
                             "Pro_League/APAC_South/Final'")
    parser.add_argument("--region", required=True,
                        help="CSV region tag (e.g. apac_s)")
    parser.add_argument("--tournament", required=True,
                        help="CSV tournament slug "
                             "(e.g. 2024-S1-Pro-League-Finals)")
    parser.add_argument("--save-wikitext", default=None,
                        help="Optional path to dump raw wikitext for "
                             "audit/debugging")
    args = parser.parse_args(argv)

    wikitext = fetch_wikitext(args.page)
    if args.save_wikitext:
        with open(args.save_wikitext, "w", encoding="utf-8") as f:
            f.write(wikitext)

    per_match = parse_per_match(wikitext)
    total = sum(len(v) for v in per_match.values())
    print(f"# {args.region} {args.tournament}: {total} cells across "
          f"{len(per_match)} matches", file=sys.stderr)
    for row in emit_rows(args.region, args.tournament, per_match):
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
