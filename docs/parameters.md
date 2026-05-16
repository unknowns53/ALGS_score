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
| `strength_sigma` | float | 0.45 | ロビー全体の戦力分散。大きいほど上下差が広がる |
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
| `neutral_death_rate` | float | 0.01 | 中立死（リング・地形死）の比率。ノック由来でない死亡 |
| `lost_kill_rate` | float | 0.03 | ノックしたがチームスコアに計上されなかった比率（自チーム全滅・第三者干渉等） |
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

つまり `1.35` と `0.45` は絶対値ではなく **softmax 後の確率比** に効く。値自体に意味があるのではなく、上位／下位の比 (約 3:1) に意味がある。

```
1st:        1.35
2nd:        1.25
3rd:        1.20
4th-5th:    1.10
6th-10th:   1.00
11th-15th:  0.75
16th-20th:  0.45
```

### Seeded 出発点テーブル `STARTING_POINTS_SEEDED`

`starting_points_mode="seeded"` を明示指定したときだけ使われるレガシー値。現行 ALGS の Match Point Finals は持ち越し点なしなので既定 (`none`) では呼ばれない。

```
シード:  1  2  3  4  5  6  7  8  9 10 11..20
得点:   10  9  8  7  6  5  4  3  2  1   0 (全部)
```

---

## 4. リージョンプロファイルの中身

`apply_region_profile()` で適用される値。CLI / JSON で個別に上書きできる。

| フィールド | americas | emea | apac_n | apac_s |
|---|---|---|---|---|
| `strength_sigma` | 0.55 | 0.45 | 0.30 | 0.40 |
| `rank_beta` | 1.05 | 1.00 | 0.85 | 0.95 |
| `kill_beta` | 0.85 | 0.80 | 0.75 | 0.70 |
| `win_beta` | 0.95 | 0.80 | 0.65 | 0.75 |
| `consistency_beta` | 0.45 | 0.55 | 0.40 | 0.35 |
| `placement_fight_correlation` | 0.65 | 0.60 | 0.45 | 0.50 |
| `placement_win_correlation` | 0.60 | 0.50 | 0.35 | 0.40 |
| `base_match_noise` | 0.70 | 0.70 | 1.00 | 0.95 |
| `volatility_mean` | 0.95 | 0.90 | 1.10 | 1.15 |
| `volatility_sigma` | 0.20 | 0.20 | 0.30 | 0.35 |
| `respawn_model` | negbin | negbin | negbin | negbin |
| `respawn_mean` | 6.0 | 6.0 | 7.0 | 6.5 |
| `respawn_dispersion` | 4.0 | 4.5 | 3.0 | 3.5 |
| `neutral_death_rate` | 0.01 | 0.01 | 0.01 | 0.01 |
| `lost_kill_rate` | 0.025 | 0.020 | 0.04 | 0.035 |
| `transfer_kill_rate` | 0.05 | 0.04 | 0.06 | 0.06 |
| `revive_knock_mean` | 9.0 | 9.0 | 12.0 | 11.0 |
| `mp_win_penalty` | 0.08 | 0.10 | 0.15 | 0.12 |
| `mp_kill_penalty` | 0.04 | 0.05 | 0.05 | 0.06 |
| `mp_pressure_lost_kill_multiplier` | 1.15 | 1.15 | 1.35 | 1.30 |
| `mp_pressure_enabled` | true | true | true | true |

意味合い:

- **americas**: 上位の戦力勾配が大きく win_conversion 高め、カオス低め。スコア力と優勝の相関が強く、短期決着になりやすい。
- **emea**: 中庸 strength_sigma、consistency 高め・volatility 低めで構造的な順位、カオスも低め。
- **apac_n**: 戦力が最も拮抗、カオス高め、得点と優勝変換のズレが大きい。MP 圧力ペナルティも厚い。長期戦になりやすい。
- **apac_s**: volatility が最大、キル side のランダム性高め、カオス中〜高め。

---

## 5. JSON フォーマット例

```json
{
  "sims": 50000,
  "seed": 42,
  "workers": 0,
  "region_profile": "apac_n",
  "starting_points": "none",
  "strength_sigma": 0.30,
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
