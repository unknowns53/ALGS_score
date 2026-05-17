# ALGS スコアシミュレーター

ALGS (Apex Legends Global Series) の Match Point 制 Finals と、他の代表的な大会形式を、モンテカルロで回して比較するための Python ツール。

「APAC-N の Finals は何試合で終わるか？」「Match Point 制と固定 8 試合制で、最強チームが勝つ確率はどれくらい変わるか？」みたいな問いに数値で答えるのが目的。

## クイックスタート

```powershell
pip install -r requirements.txt
python run_sim.py
```

`python run_sim.py` は対話モード。シミュレーション回数・地域・出力先を聞かれるので Enter 連打で全部デフォルト (APAC-N、10000 試行) でも動く。終わると `out\` に終了試合数分布のサマリ・CSV・JSON・ヒストグラム PNG が出る。

大会形式の比較を試したい場合は:

```powershell
python tools\run_format_comparison.py --sims 10000 --region apac_n --workers 0
```

`out\format_comparison\` に 6 形式 (MatchPoint / 6 試合制 / 8 試合制 / Swiss / RoundRobin / DoubleElim) を並べた指標 JSON・CSV と 3 枚の PNG が出る。

Python は 3.11 以上を想定。

## 何が分かるか

このツールで答えられる典型的な問い:

- **「この地域の Finals は何試合くらいで終わる？」** → Match Point シム (`run_sim.py`) の終了試合数分布
- **「APAC-N が長期化しがちなのは戦力均衡のせい？ それともキル消滅が多いせい？」** → 同シムのパラメータを切り替えて感度を見る (`--strength-sigma 0.20` 等)
- **「Match Point 制と固定 8 試合制、どちらが強豪に有利？」** → 大会形式比較 (`run_format_comparison.py`)
- **「ダブルエリミと Swiss、視聴者的に盛り上がるのはどっち？」** → 同上、`drama_score` 指標を比較
- **「持ち越し点ありルールに戻したら Finals は何試合短縮される？」** → `--starting-points seeded` で再計算

## 使い方

### ケース 1: Finals の試合数分布を見る

最短:

```powershell
python -m cli --sims 50000 --region-profile apac_n --seed 42
```

`out\histogram.png` に終了試合数のヒストグラム + 累積分布、`out\summary.csv` / `.json` に分布・チャンピオン seed 分布・MP テレメトリ・1 試合あたりの平均値などが入る。標準出力にも整形済みサマリが出る。

地域プロファイルは `americas` / `emea` / `apac_n` / `apac_s` / `custom`。それぞれ実 ALGS Pro League 4 大会の平均試合数に合わせてキャリブレートしてある (`docs\data_validation.md` 参照)。

引数なしで `python run_sim.py` を実行すると対話モードに入る (出力先を変えたい時とかに便利)。

### ケース 2: 自分でパラメータを振ってみる

引数で個別上書きできる:

```powershell
python -m cli --sims 50000 --region-profile apac_n `
    --strength-sigma 0.20 --lost-kill-rate 0.05 `
    --output-csv out\my_run.csv --output-plot out\my_run.png
```

毎回打つのが面倒なら JSON にまとめて `--config` で渡す:

```powershell
python -m cli --config examples\apac_n_preset.json
# 一部だけ CLI で上書きも可:
python -m cli --config examples\apac_n_preset.json --sims 5000 --seed 99
```

優先順位は **CLI > JSON > リージョンプロファイル > 既定値**。JSON のキーは `SimulationConfig` のフィールド名 (snake_case) と、`sims` / `seed` / `workers` / `output_csv` / `output_json` / `output_plot` / `starting_points` などの実行レベルキー。知らないキーが入っていたら標準エラーに警告を出す。

`examples\apac_n_preset.json` がフル定義、`examples\custom_minimal.json` が部分上書きの最小例。

全パラメータ・既定値・ハードコード定数の完全リファレンスは [`docs/parameters.md`](docs/parameters.md)。

### ケース 3: 大会形式を比較する

```powershell
python tools\run_format_comparison.py --sims 30000 --region apac_n --workers 0
```

実行が終わると標準出力に比較表が出る:

```
format           sims  seed1%   top5%  upset%   avgM  drama   lc     rho
------------------------------------------------------------------------
match_point     30000  13.6%   49.7%   24.2%    8.75   5.26    4  +0.395
fixed_6         30000  17.7%   53.8%   20.7%    6.00   6.13    3  +0.346
fixed_8         30000  19.5%   58.6%   18.3%    8.00   4.97    4  +0.391
swiss           18000  14.7%   44.2%   21.0%   18.00   9.00    4  +0.337
round_robin     18000  16.2%   47.2%   16.4%   18.00   8.61    4  +0.375
double_elim     18000  10.8%   41.1%   19.1%   13.94   4.83    5  +0.487
```

(値は 2000 sim スモークの参考値)

指標の意味:

- `seed1%` — 最強シード (seed 1) が優勝する確率
- `top5%` — seed 1〜5 のいずれかが優勝する確率
- `upset%` — 下位半分のシード (20 チーム形式なら seed ≥ 11、30 チーム形式なら seed ≥ 16) が優勝する確率
- `avgM` — 平均総試合数
- `drama` — 最終試合開始時点で逆転可能なチーム数の平均 (大きいほど「最後まで分からない」)
- `lc` — 累積 1 位チームが入れ替わる回数の中央値
- `rho` — 真の強さと最終順位の Spearman 相関 (高いほど公平)

同じディレクトリに以下のファイルが出る:

- `format_comparison.json` / `.csv` — 全指標の生データ
- `format_comparison_bars.png` — 6 指標 × 6 形式の棒グラフ
- `seed_win_heatmap.png` — 形式 × シードの優勝率ヒートマップ
- `drama_and_length.png` — ドラマスコアと試合数分布

主な CLI オプション:

- `--sims N` ベース試行数。Swiss / RoundRobin / DoubleElim は計算量が約 3 倍なのでデフォルトでは 60% に自動スケールダウン (`--no-scale` で全形式同数)
- `--region {americas, emea, apac_n, apac_s, custom}`
- `--workers 0` で auto (CPU - 1)、`1` で直列
- `--formats match_point,fixed_8` で形式をサブセット指定
- `--output-dir PATH` で出力先変更
- `--no-plot` で PNG スキップ

形式の定義 (特に Swiss / RoundRobin / DoubleElim を Apex バトロワにどう移植したか) と指標の細かい定義は [`docs/format_comparison.md`](docs/format_comparison.md) に書いてある。

### ケース 4: 大量試行を高速に回す

`--workers` で `multiprocessing` の並列分割が効く:

```powershell
python -m cli --sims 100000 --region-profile apac_n --workers 0   # CPU 数 -1 で auto
python -m cli --sims 100000 --region-profile apac_n --workers 4   # 4 プロセス固定
```

性質:

- **同じ `(seed, sims, workers)` の組み合わせなら結果は完全に決定的** (`numpy.random.SeedSequence.spawn` で子シード生成)
- `workers` を変えるとチャンク分割が変わるため、`seed` 同じでも結果列は変わる。再現性が必要なら `workers` も固定
- `sims < 1000` は並列オーバーヘッドの方が大きいので自動的に直列に切り替わる
- Windows / Linux 共通で `spawn` コンテキストを使うため `if __name__ == "__main__":` ガードが必須 (`cli.py` / `run_sim.py` / `tools\run_format_comparison.py` には入れてある)

形式比較ツールも同じ仕組み (`--workers 0` 推奨)。各形式は逐次実行され、形式内で並列化される。

## モデルの要点

1. 死亡イベント母数 = `総人数 + リスポーン数 - 優勝チーム生存者数` で動的に決まる
2. そのうち一部は中立死・キルポイント消滅でスコア化しない
3. 一部は他チームへ移転する (漁夫モデル: 漁夫先は順位非依存・`fight_skill` のみの重みで抽選)
4. 残ったぶんが `scored_kills` になり、`fight_skill` と順位重みで多項配分
5. 総ノック数 `total_knocks = (death_events - neutral_deaths) + revived_knocks` を陽に集計

総キル数を直接いじらず上記の流れで自然に決まる設計にしてあるのがポイント。詳しくは `仕様書.md` 本文と [`docs/parameters.md`](docs/parameters.md) のキルクレジット節。

Match Point ルールで気を付けている点:

- **eligibility は試合開始時点で評価**: 49 点で 1 位を取って同試合中に 61 点に到達しても大会は終わらない (仕様書テスト 4)
- 開始時点で 50 点以上のチームが 1 位を取った試合のみ大会終了 (仕様書テスト 5)

## 出発点 (starting points)

現行 ALGS の Match Point Finals は **持ち越し点なし** (全チームが 0 点開始)。なので既定値は `--starting-points none`。

レガシー互換用に 2 つの選択肢がある:

- `--starting-points seeded` — `config.py` の `STARTING_POINTS_SEEDED` テーブル (シード 1〜20 順に `10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0, ...`) を適用。過去フォーマットの Winners Bracket 持ち越し点を模倣したい時
- `--starting-points custom --custom-starting-points "5,4,3,..."` — 20 個のカンマ区切り整数を直接指定。JSON では `"custom_starting_points": [5, 4, ...]` の配列でも可

`seeded` テーブルを書き換えたければ `config.py` の `STARTING_POINTS_SEEDED` を直接編集。

## 仕様書に明示が無くこちら側で決めた値

| パラメータ | 既定値 | 出典 |
|---|---|---|
| `consistency_beta` | 0.4 | 仕様書 Recommended default config に値が無いため |
| `chaos_multiplier` | 1.0 | 仕様書 Parameters 一覧には在るが値の指定が無い |
| `champion_remaining` | 1〜3 の重み付き抽選 (約 5% / 20% / 75%、平均 ≒ 2.7) | 仕様書「Usually 1 to 3」を満たしつつ現実の優勝チームはほぼ全員生存で締めるため 3 寄せ。`champion_remaining_weights` で調整可 |
| `mp_pressure_lost_kill_multiplier` の適用条件 | eligible team が 1 つでも存在する試合に乗算 | 仕様書記述の素直な解釈 |
| Americas / EMEA / APAC-S プリセット数値 | 仕様書「特徴」記述から推測 + 実大会データでキャリブレート | 仕様書には APAC-N preset のみ数値記載。`docs/data_validation.md` で検証 |

数値はすべて `--*` フラグで上書き可能。

## テスト

```powershell
pytest tests
```

合計 26 件:

- `test_rules.py` (10 件) — 仕様書 Rule tests + 復活ノック / 移転キル invariant
- `test_sanity.py` (5 件) — 仕様書 Sanity tests
- `test_parallel.py` (4 件) — 並列ドライバの再現性
- `test_formats.py` (7 件) — ロビー分割保存則 / RoundRobin ペアバランス / DE ブラケット整合性 / Spearman サニティ / 形式間再現性

サニティと並列再現性は確率的だが、サンプル数とシードを固定しているので決定的に通る。

## ファイル構成

```
config.py                  SimulationConfig + リージョンプリセット + 固定テーブル
teams.py                   Team dataclass + 多変量正規でチーム強度生成
match_sim.py               1 試合分のシミュレート (Plackett-Luce 順位 / リスポーン / キル配分)
tournament_sim.py          1 大会のシミュレート (MatchPointFormat の薄ラッパ + 並列実行ドライバ)
stats.py                   SummaryResult 集計、CSV/JSON 出力、テキスト整形
plot.py                    matplotlib ヒストグラム + 大会形式比較プロット
cli.py                     argparse + 対話プロンプト (Match Point シミュ用)
run_sim.py                 対話モード起動ラッパー

formats\                   大会形式 Strategy パッケージ
  base.py                  TournamentFormat ABC + FormatResult
  match_point.py           ALGS Finals (50 点リーチ後 1 位優勝)
  fixed_matches.py         6 試合制 / 8 試合制
  swiss.py                 30 チーム / 累積スコアでロビー再分割
  round_robin.py           30 チーム / ペア対戦履歴を均す貪欲分割
  double_elim.py           30 チーム / WB → LB → GF (短期 MP)
  lobby_assignment.py      ロビー分割 + ロビー内試合実行ユーティリティ
  runner.py                format 用並列実行ドライバ
format_comparison.py       FormatMetrics 集計 + 出力

tools\run_format_comparison.py  大会形式比較の CLI
docs\parameters.md              全パラメータ・定数の完全リファレンス
docs\data_validation.md         既定値と実 ALGS 大会データの照合
docs\format_comparison.md       大会形式比較の仕様 / 指標定義 / 結果解釈ガイド
examples\                       JSON 設定サンプル
tests\                          pytest 一式
```
