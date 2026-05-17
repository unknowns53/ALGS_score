# 大会形式の公平性比較

ALGS の Match Point 制シミュレータを土台に、同じ仮想チーム群を異なる大会形式で
回したときの公平性・ドラマ性・長さを定量比較するための拡張。`formats/` パッケージ
と `format_comparison.py`、CLI スクリプト `tools/run_format_comparison.py` から成る。

## 動機

ALGS Finals は 20 チーム単一ロビーの Match Point 制を採用しているが、Pro League
や Playoffs では別の形式（固定 6 試合、ダブルエリミ、スイス的なロビー再分割）が
使われている。「どの形式が、どれくらい強いチームを正しく勝たせるのか／番狂わせ
を起こすのか／試合数が長いのか」を Monte Carlo で並べて見るためのツール。

## 比較対象 6 形式

Apex は 20 チーム同時参加のバトロワなので、1v1 を前提とする「スイス」「ダブル
エリミ」「総当たり」はそのまま当てはまらない。Apex Playoffs の実運用に即して
再解釈したのが以下。

| 形式 | プール | ロビー構成 | 終了条件 | 実装ファイル |
| --- | --- | --- | --- | --- |
| MatchPoint | 20 | 単一 20 チーム | 累積 50 点リーチ後の 1 位 (max 12 試合) | `formats/match_point.py` |
| Fixed-6 | 20 | 単一 20 チーム | 6 試合固定 | `formats/fixed_matches.py` |
| Fixed-8 | 20 | 単一 20 チーム | 8 試合固定 | 同上 |
| Swiss | 30 | 10 チーム × 3 ロビー、毎ラウンド累積スコアで再分割 | 6 ラウンド固定 | `formats/swiss.py` |
| RoundRobin | 30 | 10 チーム × 3 ロビー、ペア対戦履歴を均す貪欲分割 | 6 ラウンド固定 | `formats/round_robin.py` |
| DoubleElim | 30 | WB(20) → LB(WB 下位 10+seed 21-30) → GF(20) | GF で短期 MP (threshold=30, max 8) | `formats/double_elim.py` |

20 チーム形式と 30 チーム形式が混在するため、後述の `upset_rate` はプールサイズに
応じて「下位 50% シードが優勝した確率」と動的定義している。

## 指標

`format_comparison.py:FormatMetrics` に集約。

| 指標 | 定義 |
| --- | --- |
| `seed1_win_rate` | 最強シード (seed 1) の優勝確率 |
| `top3_podium_rate` | seed 1〜3 のいずれかが表彰台 (1〜3 位) に入る確率 |
| `top5_win_rate` | seed 1〜5 のいずれかが優勝する確率 |
| `upset_rate` | 下位 50% シードが優勝する確率（20 チームなら seed ≥ 11、30 チームなら seed ≥ 16） |
| `mean_matches` / `median_matches` / `p95_matches` | 大会あたりの総試合数 |
| `mean_drama_score` | 最終試合開始時点で「上限 22 点（12 placement + ~10 kill）以内で 1 位を逆転可能」なチーム数の平均。1 以上（リーダー自身を含む） |
| `median_lead_changes` | 累積 1 位チームが試合間で変わった回数の中央値 |
| `mean_spearman` | composite_strength と最終順位の Spearman 順位相関、符号反転して「正＝強いチームが上に来る＝公平」 |
| `seed_win_rate` | 各シードの優勝確率（ヒートマップ用） |

drama_score の `MAX_SINGLE_MATCH_GAIN = 22` はチームが 1 試合で取り得る上限の経験
則値（12 + kill 上限）。残差シミュレーションでなく決定的閾値で代用しているのは、
50000 sim × 1000 残差 = 5×10⁷ 試行を避けるため。

## 実行方法

```powershell
python tools/run_format_comparison.py --sims 30000 --region apac_n --workers 0 --output-dir out/format_comparison
```

主なオプション：

- `--sims` ベース試行数。多ロビー形式（Swiss / RoundRobin / DE）は計算量が約 3 倍
  なので、デフォルトでは 60% にスケールダウンされる。`--no-scale` で全形式同数。
- `--region` `apac_n` `apac_s` `americas` `emea` `custom` から選択。
- `--workers` 0 で auto（CPU - 1）。1 で直列。
- `--formats match_point,fixed_8` のようにサブセット指定可。
- `--no-plot` で PNG 生成をスキップ。

形式は逐次実行され、各形式の内部で並列化される（`mp.Pool` の二重ネストを回避）。

## 生成物

`out/format_comparison/` に以下が出力される。

- `format_comparison.json` — 全指標の生データ
- `format_comparison.csv` — 1 行 = 1 形式の表形式
- `format_comparison_bars.png` — 6 指標 × 6 形式のグループ棒グラフ
- `seed_win_heatmap.png` — 形式 × シードの優勝率ヒートマップ
- `drama_and_length.png` — ドラマスコアと試合数（平均棒＋中央値ドット＋p95 ひげ）

## 結果の解釈ガイド（APAC-N、2000 sim スモーク値）

注：以下は精度の粗い予備値。本格運用は 30000 sim 以上を推奨。

```
format           sims  seed1%   top5%  upset%   avgM  drama   lc     rho
------------------------------------------------------------------------
match_point      2000  13.65%  49.65%  24.20%   8.75   5.26    4 +0.395
fixed_6          2000  17.65%  53.80%  20.70%   6.00   6.13    3 +0.346
fixed_8          2000  19.55%  58.60%  18.25%   8.00   4.97    4 +0.391
swiss            1200  14.67%  44.17%  21.00%  18.00   9.00    4 +0.337
round_robin      1200  16.17%  47.17%  16.42%  18.00   8.61    4 +0.375
double_elim      1200  10.83%  41.08%  19.08%  13.94   4.83    5 +0.487
```

定性的に見えてきた傾向：

- **最も公平 (rho 最大)** は DoubleElim (+0.487)。WB／LB の二段救済が「強いチームが
  事故っても拾われる」仕組みになって、最終順位と真の強さの相関を底上げしている。
- **最強チームを最も勝たせる (seed1%)** のは Fixed-8 (19.55%)。試合数を増やすほど
  分散が小さくなり、強豪が浮上しやすい。
- **MatchPoint は seed1% が低め (13.65%)** で意外に「最強が勝てない」。リーチ後の
  1 試合で 1 位を取らないと優勝できないという最終ハードルが、最強チームに対しても
  公平に不利に働いている。
- **最もドラマチック (drama 最大)** は Swiss (9.00)。30 チームのうち多数が最終試合
  まで優勝可能性を残す構造になる。逆に DE は GF が短期 MP なので drama が低い。
- **試合数は MatchPoint と Fixed-8 がほぼ同じ (≈8 試合)**。MP の不確定性は実は
  「8 試合制を行ったり来たり」している。
- **30 チーム形式 (Swiss / RR / DE) は upset% が変動する**が、これは pool サイズで
  分母が変わるため定量比較は注意。`upset_threshold` を JSON 出力で確認。

## アーキテクチャ

`formats.TournamentFormat` は ABC。各形式は `simulate(cfg, rng) -> FormatResult`
を実装。`FormatResult` は全形式共通のデータクラスで、形式固有情報は `extras: dict`
に入れる。共通の `leader_history` (各試合後の累積 1 位 team_id) は drama 指標で
活用。

ロビー分割が必要な多ロビー形式は `formats/lobby_assignment.py` の以下を共有：

- `split_by_score(...)` — 累積スコア降順分割（Swiss）
- `pair_balanced_split(...)` — ペア履歴貪欲最小化（RoundRobin）
- `run_lobby_match(...)` — 10 チームサブセットに対し team_id を 0..9 にリマップ
  して `simulate_match` を呼び、結果を 30 チームスペースに復元

このリマップが鍵で、`simulate_match` 内部の `PLACEMENT_KILL_FACTOR[placement_position[tid]]`
が連続 team_id を仮定しているため、ロビー内では必ず 0..lobby_size-1 を渡す。

## 既存挙動との互換性

`tournament_sim.simulate_tournament` と `tournament_sim.run_simulations` は
`MatchPointFormat` 経由で動く薄ラッパに置き換えてあり、戻り値 `TournamentResult`
の API は完全互換。既存テスト 19 件 + 新規 7 件の全パスで動作確認済み
（`tests/test_rules.py`, `tests/test_sanity.py`, `tests/test_parallel.py`,
`tests/test_formats.py`）。

## 制限事項

- 30 チーム形式の `PLACEMENT_POINTS` / `PLACEMENT_KILL_FACTOR` は既存の 20 位
  までのテーブルを `[:10]` でスライス利用。ALGS Pro League の実配点は 10 チーム
  ロビー用に別テーブルになっている場合があるため、現実値と若干ずれる可能性。
- DE の WB/LB 配分は seed 1-20 / 21-30 で固定。現実の ALGS Playoffs は事前
  Group Stage で再シャッフルする多段構造だが、本ツールでは簡素化。
- drama_score は決定的閾値による近似値。残差シミュレーションをやれば「実際の
  逆転確率」が出るが、計算量が 1000 倍になるため不採用。

## 関連ファイル一覧

実装：
- `formats/__init__.py`
- `formats/base.py`
- `formats/match_point.py`
- `formats/fixed_matches.py`
- `formats/lobby_assignment.py`
- `formats/swiss.py`
- `formats/round_robin.py`
- `formats/double_elim.py`
- `formats/runner.py`
- `format_comparison.py`
- `tools/run_format_comparison.py`
- `plot.py` (3 関数追加)

テスト：
- `tests/test_formats.py` (7 件)
