# パラメータ・定数リファレンス

JSON 設定ファイル (`--config PATH`) や CLI フラグから指定できる全パラメータと、コードに埋め込んである定数を一覧にまとめたもの。値はすべて CLI フラグまたは JSON キーで上書きできる（変更不可能なのはハードコード定数の節のみ）。

CLI > JSON > リージョンプロファイル > 既定値 の優先順で解決される。JSON のキー名は `SimulationConfig` の dataclass フィールド名 (snake_case) と一致する。CLI フラグは `--snake-case-with-hyphens` 形式。

---

## 1. 実行レベルキー（SimulationConfig のフィールドではないもの）

| キー名 (JSON) | CLI フラグ | 型 | 既定値 | 説明 |
|---|---|---|---|---|
| `sims` | `--sims` | int | 10000 | モンテカルロ試行回数（大会単位） |
| `seed` | `--seed` | int / null | null（毎回ランダム） | 乱数シード。同じ seed / sims / workers なら結果完全一致 |
| `workers` | `--workers` | int | 1 | 並列ワーカー数。`1`=直列、`0`=自動（おおよそ CPU 数 -1）、`>=2` で multiprocessing |
| `region_profile` | `--region-profile` | str | `"custom"` | `custom` / `americas` / `emea` / `apac_n` / `apac_s` |
| `starting_points` | `--starting-points` | str | `"none"` | `none` / `seeded` / `custom`。`starting_points_mode` でも可 |
| `custom_starting_points` | `--custom-starting-points` | 配列 or "x,x,..." | null | 20 個の整数。`starting_points=custom` のとき必須 |
| `output_csv` | `--output-csv` | str | `out/summary.csv` | 終了試合数分布の CSV 出力先 |
| `output_json` | `--output-json` | str | `out/summary.json` | サマリ全体の JSON 出力先 |
| `output_plot` | `--output-plot` | str | `out/histogram.png` | ヒストグラム PNG 出力先 |
| `make_plot` | `--no-plot` で false | bool | true | プロットを生成するか |
| `print_summary` | `--quiet` で false | bool | true | 標準出力にテキストサマリを出すか |
| `show_progress` | `--show-progress` | bool | false | tqdm が入っていれば進捗バー表示 |

---

## 2. SimulationConfig フィールド（モデルパラメータ）

CLI フラグは `--<field-name with hyphens>` で対応。JSON ではフィールド名そのまま (snake_case)。

### ルール

| フィールド | 型 | 既定値 | 説明 |
|---|---|---|---|
| `num_teams` | int | 20 | ロビーチーム数（ALGS は 20 固定） |
| `players_per_team` | int | 3 | 1 チームの人数 |
| `max_matches` | int | 30 | 大会の打ち切り試合数（Match Point 制では届かないことが多い） |
| `match_point_threshold` | int | 50 | Match Point 点灯閾値 |

### チーム強度

| フィールド | 型 | 既定値 | 説明 |
|---|---|---|---|
| `strength_sigma` | float | 0.45 | ロビー全体の戦力分散。大きいほど上下差が広がる（リージョンプリセットでは 0.27-0.43 の範囲） |
| `rank_beta` | float | 1.0 | placement_skill が順位重みに効く係数 |
| `kill_beta` | float | 0.8 | fight_skill がキル配分重みに効く係数 |
| `win_beta` | float | 0.8 | win_conversion が 1 位抽選に効く係数 |
| `consistency_beta` | float | 0.4 | macro_consistency が順位重みに効く係数（仕様書に値の指定なし、こちらで設定） |
| `placement_fight_correlation` | float | 0.6 | placement_skill と fight_skill の相関 |
| `placement_win_correlation` | float | 0.5 | placement_skill と win_conversion の相関 |
| `base_match_noise` | float | 0.8 | 順位重みに乗るマッチごとのノイズ大きさ |
| `volatility_mean` | float | 1.0 | チーム個別のばらつき係数の平均 |
| `volatility_sigma` | float | 0.25 | volatility 自体のばらつき |

### リスポーン

| フィールド | 型 | 既定値 | 説明 |
|---|---|---|---|
| `respawn_model` | str | `"negbin"` | `"poisson"` または `"negbin"` |
| `respawn_mean` | float | 6.0 | 1 試合あたり平均リスポーン数 |
| `respawn_dispersion` | float | 4.0 | NegBin の分散パラメータ（小さいほど過分散） |
| `max_respawned_players` | int | 30 | 安全上限 |

### チャンピオン生存者

| フィールド | 型 | 既定値 | 説明 |
|---|---|---|---|
| `champion_remaining_min` | int | 1 | 抽選レンジ下限 |
| `champion_remaining_max` | int | 3 | 抽選レンジ上限 |
| `champion_remaining_weights` | tuple/array | `(1.0, 4.0, 15.0)` | 各値の重み。既定で 1/2/3 を約 5%/20%/75% で抽選（平均 ≒ 2.7） |

### キルクレジット

| フィールド | 型 | 既定値 | 説明 |
|---|---|---|---|
| `neutral_death_rate` | float | 0.03 | 中立死（リング・地形死）の比率。ノック由来でない死亡。実 Lobby kill ~52/試合に合わせて 0.01 → 0.03 に引き上げ済み |
| `lost_kill_rate` | float | 0.06 | ノックしたがチームスコアに計上されなかった比率（自チーム全滅・第三者干渉等）。地域別では 0.06-0.10 |
| `transfer_kill_rate` | float | 0.05 | scored_kills のうち漁夫で別チームに渡る比率。実配分にも反映され、漁夫先は順位非依存・fight_skill のみの重みで抽選される |
| `revive_knock_mean` | float | 10.0 | 復活ノックの平均（死亡イベント・scored_kills と独立） |
| `chaos_multiplier` | float | 1.0 | lost_kill_rate に掛かる全体カオス係数（仕様書に値の指定なし、こちらで設定） |
| `mp_pressure_lost_kill_multiplier` | float | 1.25 | eligible team が 1 つでも居る試合に lost_kill_rate へ乗算 |

ノック関連は陽に変数化してある:

```
total_knocks = (death_events - neutral_deaths) + revived_knocks
             = scored_kills + lost_kill_points + revived_knocks
```

- `death_events`: 確定死亡数（中立死含む）
- `neutral_deaths`: そのうち地形・リング死（ノック由来でない）
- `death_events - neutral_deaths`: ノック由来の確定死亡
- `lost_kill_points`: ノックしたが確定キル化に失敗した数
- `scored_kills`: チームスコアに計上された確定キル数
- `transferred_kills`: scored_kills のうち漁夫で別チームに渡った数
- `revived_knocks`: ノックされたが復活して死亡にならなかった数
- `total_knocks`: その試合の総ノック数（テレメトリで `avg total knocks per match` として出力される）

キル配分は 2 段階で行われる:
1. `scored_kills - transferred_kills` 個 → 順位＋fight_skill の重みで多項配分（`PLACEMENT_KILL_FACTOR` が効く）
2. `transferred_kills` 個 → fight_skill のみの重みで多項配分（順位は無視）

両者の合算がチームの最終キル数。総量は scored_kills で保存される。

### Match Point 圧力

| フィールド | 型 | 既定値 | 説明 |
|---|---|---|---|
| `mp_pressure_enabled` | bool | true | MP 圧力モデル全体の ON/OFF |
| `mp_win_penalty` | float | 0.10 | eligible team の 1 位抽選 log-weight に `-mp_win_penalty` を加算 |
| `mp_kill_penalty` | float | 0.05 | eligible team のキル配分 log-weight に `-mp_kill_penalty` を加算 |

---

## 3. ハードコード定数（コード変更が必要）

`config.py` のモジュールトップレベルにある定数。変えたいときはコード直接編集する。

### 配点テーブル `PLACEMENT_POINTS`

順位 1〜20 の配点。ALGS 公式と一致。

```
(12, 9, 7, 5, 4, 3, 3, 2, 2, 2, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0)
```

### 順位別キル配分倍率 `PLACEMENT_KILL_FACTOR`

順位 1〜20 のキル配分重みに乗る倍率。「均等 3 ポイント配分に傾斜」ではなく、各チームの **相対的な配分重み** を表す。実際の配分は次の流れ:

```
log_weight_i = kill_beta * fight_skill_i + log(PLACEMENT_KILL_FACTOR[placement_i])
probs        = softmax(log_weight)
team_kills   = multinomial(scored_kills - transferred_kills, probs)
            + multinomial(transferred_kills, fight_skill のみの重み)
```

つまり `2.50` と `0.20` は絶対値ではなく **softmax 後の確率比** に効く。値自体に意味があるのではなく、上位／下位の比 (約 12:1) に意味がある。実 ALGS の Pro League / Champs Finals 4 大会で「優勝チームの 1 位試合平均 7.4 kills、16-20 位試合平均 0.7 kills」を観測しており、これを再現する勾配に校正済み。

```
1st:        2.50
2nd:        2.00
3rd:        1.70
4th:        1.40
5th:        1.20
6th:        1.00
7th:        0.90
8th:        0.80
9th:        0.70
10th:       0.60
11th:       0.50
12th:       0.45
13th:       0.40
14th:       0.35
15th:       0.30
16th-17th:  0.25
18th-20th:  0.20
```

### Seeded 出発点テーブル `STARTING_POINTS_SEEDED`

`starting_points_mode="seeded"` を明示指定したときだけ使われるレガシー値。現行 ALGS の Match Point Finals は持ち越し点なしなので既定 (`none`) では呼ばれない。

```
シード:  1  2  3  4  5  6  7  8  9 10 11..20
得点:   10  9  8  7  6  5  4  3  2  1   0 (全部)
```

---

## 4. リージョンプロファイルの中身

`apply_region_profile()` で適用される値。CLI / JSON で個別に上書きできる。Year 4-5 の各地域 4 大会（計 16 大会）の実績平均 + per-match Lobby kill 実測 4 大会で第 2 次校正済み。詳細は `docs/data_validation.md` を参照。

| フィールド | americas | emea | apac_n | apac_s |
|---|---|---|---|---|
| **目標 mean (実績)** | **7.50** | **8.50** | **8.75** | **8.00** |
| **シミュ mean** | **7.52** | **8.44** | **8.75** | **8.05** |
| **シミュ Lobby kill 平均** | 57.4 | 57.0 | 55.1 | 57.3 |
| `strength_sigma` | 0.43 | 0.30 | 0.27 | 0.38 |
| `rank_beta` | 1.00 | 0.95 | 0.85 | 0.95 |
| `kill_beta` | 0.85 | 0.80 | 0.75 | 0.72 |
| `win_beta` | 0.85 | 0.75 | 0.55 | 0.85 |
| `consistency_beta` | 0.45 | 0.40 | 0.40 | 0.45 |
| `placement_fight_correlation` | 0.60 | 0.55 | 0.45 | 0.52 |
| `placement_win_correlation` | 0.50 | 0.45 | 0.35 | 0.42 |
| `base_match_noise` | 0.75 | 0.95 | 1.00 | 0.82 |
| `volatility_mean` | 0.95 | 1.05 | 1.10 | 0.98 |
| `volatility_sigma` | 0.20 | 0.28 | 0.30 | 0.25 |
| `respawn_model` | negbin | negbin | negbin | negbin |
| `respawn_mean` | 6.0 | 6.5 | 7.0 | 6.5 |
| `respawn_dispersion` | 4.0 | 3.5 | 3.0 | 3.5 |
| `neutral_death_rate` | 0.03 | 0.03 | 0.03 | 0.03 |
| `lost_kill_rate` | 0.06 | 0.07 | 0.10 | 0.065 |
| `transfer_kill_rate` | 0.05 | 0.05 | 0.06 | 0.06 |
| `revive_knock_mean` | 9.0 | 10.0 | 12.0 | 11.0 |
| `mp_win_penalty` | 0.11 | 0.17 | 0.15 | 0.14 |
| `mp_kill_penalty` | 0.04 | 0.05 | 0.05 | 0.06 |
| `mp_pressure_lost_kill_multiplier` | 1.15 | 1.25 | 1.35 | 1.30 |
| `mp_pressure_enabled` | true | true | true | true |

意味合い（第 2 次校正後）:

- **americas**: 上位の戦力勾配は地域内で最も大きい (strength_sigma 0.43)。実績平均 7.5 試合で、地域内で最も短期決着しやすい。
- **emea**: 戦力拮抗が APAC-N と同等まで縮んだ (strength_sigma 0.30)。「structured & low chaos」のイメージは Y4/Y5 実データには合わず、特に Y5 で EMEA が大幅後退したことを反映。実績平均 8.5 試合、`mp_win_penalty` も全地域中最も厚い 0.17。
- **apac_n**: 戦力拮抗が最も強い (strength_sigma 0.27) + 低キル傾向 (lost_kill_rate 0.10) + 勝ち切り難度高い (win_beta 0.55)。実績平均 8.75 試合で 4 地域中最長、2024 S2 の 13 試合外れ値も p99 で自然発生する。
- **apac_s**: 戦力差は中位、カオス中程度。実績平均 8.0 試合で Americas と APAC-N の中間。

---

## 5. JSON フォーマット例

```json
{
  "sims": 50000,
  "seed": 42,
  "workers": 0,
  "region_profile": "apac_n",
  "starting_points": "none",
  "strength_sigma": 0.27,
  "respawn_mean": 7.0,
  "champion_remaining_weights": [1.0, 4.0, 15.0],
  "mp_win_penalty": 0.15,
  "output_csv": "out/apac_n.csv",
  "output_json": "out/apac_n.json",
  "output_plot": "out/apac_n.png"
}
```

`examples/apac_n_preset.json` と `examples/custom_minimal.json` も参照。知らないキーが入っていたら標準エラーに警告が出るので、typo はそこで気付ける。

---

## 6. 並列処理の注意

`workers >= 2` のとき:

- `numpy.random.SeedSequence(seed).spawn(workers)` で各ワーカーに独立な子シードを配るので、同じ `(seed, sims, workers)` の組み合わせなら結果は完全に決定的。
- `(seed, sims)` を固定しても `workers` を変えると結果列は変わる（チャンク分割の都合）。再現性が必要なら `workers` も含めて固定すること。
- `sims < 1000` のときは並列のオーバーヘッドが上回るので自動的に直列実行に切り替わる。
- Windows / Linux 共通で `multiprocessing` の `spawn` コンテキストを使う。なので CLI 経由で起動するときは `if __name__ == "__main__":` ガード（`cli.py` と `run_sim.py` に既に入っている）が効いている。
