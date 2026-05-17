# 地域プリセット再校正 — grid search 提案

自動生成 (`tools/fit_region_presets.py`). dry_run=False, sims/condition=2000.

## グリッド範囲

| パラメータ | 候補値 |
|---|---|
| `strength_sigma` | 0.2, 0.27, 0.35, 0.43, 0.5 |
| `lost_kill_rate` | 0.04, 0.06, 0.08, 0.1, 0.12 |
| `revive_knock_mean` | 7.0, 9.0, 11.0, 13.0 |
| `placement_kill_sharpness` | 0.6, 0.8, 1.0, 1.2, 1.5 |

## ベスト解 (各地域)

| region | strength_sigma | lost_kill_rate | revive_knock_mean | placement_kill_sharpness | obs mean_end | sim mean_end | obs p1_kills | sim p1_kills | obs p20_kills | sim p20_kills | n_obs_matches |
|---|---|---|---|---|---|---|---|---|---|---|---|
| americas | 0.350 | 0.040 | 13.0 | 0.60 | 7.50 | 8.14 | 9.03 | 6.44 | 1.60 | 1.31 | 30 |
| emea | 0.270 | 0.120 | 7.0 | 1.20 | 8.50 | 8.61 | 9.44 | 9.64 | 0.56 | 0.56 | 34 |
| apac_n | 0.350 | 0.040 | 9.0 | 1.00 | 8.75 | 8.39 | 9.97 | 9.07 | 0.80 | 0.84 | 35 |
| apac_s | 0.270 | 0.040 | 7.0 | 0.60 | 8.00 | 8.65 | 8.44 | 6.27 | 1.70 | 1.44 | 27 |

## 上位 3 候補 (各地域、観測との正規化二乗誤差)

### americas

| rank | strength_sigma | lost_kill_rate | revive_knock_mean | placement_kill_sharpness | sim mean_end | sim p1_kills | sim p20_kills | err |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.350 | 0.040 | 13.0 | 0.60 | 8.14 | 6.44 | 1.31 | 0.1239 |
| 2 | 0.430 | 0.040 | 11.0 | 0.60 | 7.79 | 6.59 | 1.24 | 0.1254 |
| 3 | 0.430 | 0.040 | 13.0 | 0.60 | 7.75 | 6.56 | 1.24 | 0.1259 |

### emea

| rank | strength_sigma | lost_kill_rate | revive_knock_mean | placement_kill_sharpness | sim mean_end | sim p1_kills | sim p20_kills | err |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.270 | 0.120 | 7.0 | 1.20 | 8.61 | 9.64 | 0.56 | 0.0006 |
| 2 | 0.270 | 0.120 | 13.0 | 1.20 | 8.61 | 9.65 | 0.56 | 0.0006 |
| 3 | 0.270 | 0.120 | 9.0 | 1.20 | 8.63 | 9.69 | 0.56 | 0.0010 |

### apac_n

| rank | strength_sigma | lost_kill_rate | revive_knock_mean | placement_kill_sharpness | sim mean_end | sim p1_kills | sim p20_kills | err |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.350 | 0.040 | 9.0 | 1.00 | 8.39 | 9.07 | 0.84 | 0.0118 |
| 2 | 0.270 | 0.040 | 9.0 | 1.00 | 8.57 | 9.12 | 0.85 | 0.0122 |
| 3 | 0.270 | 0.040 | 7.0 | 1.00 | 8.55 | 9.01 | 0.84 | 0.0122 |

### apac_s

| rank | strength_sigma | lost_kill_rate | revive_knock_mean | placement_kill_sharpness | sim mean_end | sim p1_kills | sim p20_kills | err |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.270 | 0.040 | 7.0 | 0.60 | 8.65 | 6.27 | 1.44 | 0.0965 |
| 2 | 0.350 | 0.040 | 13.0 | 0.60 | 8.34 | 6.34 | 1.38 | 0.0993 |
| 3 | 0.350 | 0.040 | 7.0 | 0.60 | 8.34 | 6.36 | 1.37 | 0.1008 |

## 採用手順 (人間判断)

ベスト解 (上の表) を `config.py:REGION_PROFILES` に反映する際は、各地域ブロックの該当 4 キーを書き換えた上で `pytest tests/` を実行し、regression テストが通ることを確認する。`placement_kill_sharpness` は 現状 REGION_PROFILES に未含有なので、新規キーとして追加する形になる。
