# ALGS Match Point スコアシミュレーター

ALGS (Apex Legends Global Series) の Match Point 制 Finals をモンテカルロでシミュレートして、終了試合数の分布や内部テレメトリを推定するためのツール。仕様の詳細は `仕様書.md` を参照。

狙いは「終了試合数分布」を、地域内拮抗・ロビーカオス度・Match Point 点灯後の勝ち切り難度・得点力と優勝変換力のズレ、として分解的に表現できるようにしてあること。APAC-N っぽい長期化を「弱いから」ではなく構造として再現できるようにしてある。

## セットアップ

```powershell
pip install -r requirements.txt
```

Python 3.11 以上を想定。

## 使い方

### 対話モード

引数なしで実行すると、対話プロンプトでパラメータを聞いてくる:

```powershell
python run_sim.py
```

シミュレーション回数・乱数シード・リージョンプロファイル・出発点・出力先を順番に答えると、終了試合数分布のサマリ・CSV・JSON・ヒストグラム PNG が `out\` 配下に生成される。

### CLI モード

引数を 1 つでも与えると対話モードはスキップされ、argparse で全部上書きできる:

```powershell
python -m cli --sims 50000 --region-profile apac_n --seed 42 `
    --output-csv out\apac_n.csv --output-json out\apac_n.json --output-plot out\apac_n.png
```

主要オプション（全部 `python -m cli --help` で確認できる）:

- `--sims` シミュレーション回数
- `--seed` 乱数シード
- `--region-profile {custom, americas, emea, apac_n, apac_s}`
- `--starting-points {none, seeded, custom}` （`custom` のときは `--custom-starting-points "3,3,2,2,2,2,1,1,1,1,0,..."` で 20 個指定）
- `--max-matches` 大会の打ち切り試合数（デフォルト 30）
- `--match-point-threshold` Match Point 点灯閾値（デフォルト 50）
- 強度・キル・順位の β / 相関、リスポーンモデル、キル消滅・移転率、Match Point 圧力など、仕様書記載の全パラメータに対応する `--*` フラグ
- `--config PATH` で JSON 設定ファイルを読み込み
- `--no-plot` で PNG 生成スキップ

### JSON 設定ファイル

毎回大量の引数を打つのが面倒なので、`--config` で JSON にまとめて渡せる。CLI 引数を併用したときは **CLI > JSON > リージョンプロファイル > 既定値** の優先順位で解決される。

```powershell
python -m cli --config examples\apac_n_preset.json
# CLI で部分上書きもできる:
python -m cli --config examples\apac_n_preset.json --sims 5000 --seed 99
```

JSON のキーは `SimulationConfig` のフィールド名（snake_case）と一致するものが全部使える。加えて以下の実行レベルキーも受け付ける:

- `sims`, `seed`
- `starting_points`（`starting_points_mode` でも可）, `custom_starting_points`（配列 or カンマ区切り文字列）
- `region_profile`
- `output_csv`, `output_json`, `output_plot`
- `make_plot`, `print_summary`, `show_progress`

`examples\apac_n_preset.json` に APAC-N プリセットのフル定義、`examples\custom_minimal.json` に一部だけ上書きする最小例がある。知らないキーが入っていたら標準エラーに警告を出すから、typo はそこで気付ける。

## ファイル構成

```
config.py            SimulationConfig + リージョンプリセット + 固定テーブル
teams.py             Team dataclass + 多変量正規でチーム強度生成
match_sim.py         1 試合分のシミュレート（Plackett-Luce 順位 / リスポーン / キル配分）
tournament_sim.py    1 大会のシミュレート（Match Point 判定・打ち切り）
stats.py             SummaryResult 集計、CSV/JSON 出力、テキスト整形
plot.py              matplotlib ヒストグラム
cli.py               argparse + 対話プロンプト
run_sim.py           対話起動ラッパー
tests\               pytest 一式
```

## 主要モデルの要点

1. リスポーンで死亡イベント母数が増える
2. 一部は中立死・キルポイント消滅でスコア化しない
3. 一部は他チームへ移転する（v1 ではテレメトリのみで再分配は省略）
4. 残ったぶんが `scored_kills` になり、`fight_skill` と順位重みで多項配分

総キル数を直接いじらず、上の流れで自然に決まるようにしてあるのがポイント。詳しくは仕様書本文を参照。

## Match Point ルールで気を付けている点

- **eligibility は試合開始時点で評価**: 大会終了の判定は `eligible_before[winner_idx]` を見ているため、49 点で 1 位を取ってその試合で 61 点に到達しても大会は終わらない（仕様書テスト 4）
- 開始時点で 50 点以上のチームが 1 位を取った試合のみ大会終了（仕様書テスト 5）

## 出発点プリセット

`--starting-points seeded` のときの加算値（シード 1〜20 順）:

```
3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
```

これは ALGS Year 4 Champs の Match Point Finals 加算ベース。値は `config.py` の `STARTING_POINTS_SEEDED` で定義してあるので、変えたいときはここを書き換えるか `--starting-points custom --custom-starting-points "..."` で上書き。

## 仕様書に明示が無くこちら側で決めた値

| パラメータ | 既定値 | 出典 |
|---|---|---|
| `consistency_beta` | 0.4 | 仕様書 Recommended default config に値が無いため |
| `chaos_multiplier` | 1.0 | 仕様書 Parameters 一覧には在るが値の指定が無い |
| `champion_remaining` | 1〜3 一様抽出 | 仕様書「Usually 1 to 3」の素直な解釈 |
| `mp_pressure_lost_kill_multiplier` の適用条件 | eligible team が 1 つでも存在する試合に乗算 | 仕様書記述の素直な解釈 |
| Americas / EMEA / APAC-S プリセット数値 | 仕様書「特徴」記述から推測 | 仕様書には APAC-N preset のみ数値が記載 |

数値はすべて `--*` フラグで上書き可能。

## テスト

```powershell
pytest tests
```

ルール 8 件（仕様書 Rule tests）+ サニティ 5 件（仕様書 Sanity tests）。サニティは確率的だが、サンプル数とシードを固定してあるので決定的に通る。
