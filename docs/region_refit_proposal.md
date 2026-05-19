# 地域プリセット再フィッティング — ベイズ最適化提案

自動生成 (`tools/fit_region_presets.py --method bayesian`). dry_run=False, `gp_minimize` ベイズ最適化、n_calls=150 (initial=15), 2000 sims/eval.

## 探索範囲

| パラメータ | 下限 | 上限 |
|---|---|---|
| `strength_sigma` | 0.100 | 0.700 |
| `lost_kill_rate` | 0.020 | 0.200 |
| `placement_kill_sharpness` | 0.40 | 2.00 |
| `respawn_mean` | 1.0 | 12.0 |
| `mp_win_penalty` | 0.000 | 0.500 |

## ベスト解 (各地域)

| region | strength_sigma | lost_kill_rate | placement_kill_sharpness | respawn_mean | mp_win_penalty | obs mean_end | sim mean_end | obs p1_kills | sim p1_kills | obs p10_kills | sim p10_kills | obs p20_kills | sim p20_kills | obs total_kills | sim total_kills | err | n_obs_matches |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| americas | 0.288 | 0.020 | 0.71 | 12.0 | 0.000 | 7.50 | 7.85 | 9.03 | 7.97 | 2.37 | 2.84 | 1.60 | 1.31 | 61.90 | 65.61 | 0.0931 | 30 |
| emea | 0.509 | 0.030 | 1.10 | 3.3 | 0.500 | 8.50 | 7.96 | 9.44 | 9.70 | 2.53 | 2.03 | 0.56 | 0.60 | 56.50 | 56.79 | 0.0489 | 34 |
| apac_n | 0.445 | 0.020 | 1.00 | 8.5 | 0.500 | 8.75 | 8.29 | 9.97 | 9.56 | 3.51 | 2.39 | 0.80 | 0.85 | 55.40 | 62.30 | 0.1252 | 35 |
| apac_s | 0.610 | 0.091 | 1.05 | 9.6 | 0.500 | 8.00 | 7.41 | 9.22 | 9.67 | 2.69 | 2.12 | 0.59 | 0.64 | 57.91 | 58.04 | 0.0569 | 32 |
| global | 0.700 | 0.165 | 1.44 | 2.7 | 0.500 | 9.00 | 7.30 | 9.47 | 10.52 | 2.53 | 1.32 | 0.08 | 0.27 | 57.47 | 47.37 | 0.4419 | 36 |

## 上位 3 候補 (各地域、観測との正規化二乗誤差 — 5 成分)

err = (Δmean_end/obs)² + (Δp1/obs_p1)² + (Δp10/max(obs_p10,1.0))² + (Δp20/max(obs_p20,0.5))² + (Δtotal/obs_total)². 各成分は観測値で割って正規化した二乗差。

### americas

| rank | strength_sigma | lost_kill_rate | placement_kill_sharpness | respawn_mean | mp_win_penalty | sim mean_end | sim p1_kills | sim p10_kills | sim p20_kills | sim total_kills | err |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.288 | 0.020 | 0.71 | 12.0 | 0.000 | 7.85 | 7.97 | 2.84 | 1.31 | 65.61 | 0.0931 |
| 2 | 0.275 | 0.020 | 0.72 | 12.0 | 0.000 | 7.90 | 7.98 | 2.84 | 1.30 | 65.70 | 0.0945 |
| 3 | 0.232 | 0.033 | 0.73 | 12.0 | 0.000 | 8.15 | 7.84 | 2.80 | 1.31 | 64.75 | 0.0945 |

### emea

| rank | strength_sigma | lost_kill_rate | placement_kill_sharpness | respawn_mean | mp_win_penalty | sim mean_end | sim p1_kills | sim p10_kills | sim p20_kills | sim total_kills | err |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.509 | 0.030 | 1.10 | 3.3 | 0.500 | 7.96 | 9.70 | 2.03 | 0.60 | 56.79 | 0.0489 |
| 2 | 0.511 | 0.032 | 1.09 | 3.7 | 0.500 | 7.96 | 9.68 | 2.03 | 0.60 | 56.99 | 0.0495 |
| 3 | 0.511 | 0.033 | 1.09 | 3.8 | 0.500 | 7.96 | 9.81 | 2.02 | 0.60 | 57.08 | 0.0511 |

### apac_n

| rank | strength_sigma | lost_kill_rate | placement_kill_sharpness | respawn_mean | mp_win_penalty | sim mean_end | sim p1_kills | sim p10_kills | sim p20_kills | sim total_kills | err |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.445 | 0.020 | 1.00 | 8.5 | 0.500 | 8.29 | 9.56 | 2.39 | 0.85 | 62.30 | 0.1252 |
| 2 | 0.333 | 0.020 | 1.01 | 8.6 | 0.500 | 8.68 | 9.60 | 2.38 | 0.85 | 62.37 | 0.1255 |
| 3 | 0.362 | 0.036 | 1.01 | 10.2 | 0.500 | 8.57 | 9.64 | 2.40 | 0.86 | 62.60 | 0.1257 |

### apac_s

| rank | strength_sigma | lost_kill_rate | placement_kill_sharpness | respawn_mean | mp_win_penalty | sim mean_end | sim p1_kills | sim p10_kills | sim p20_kills | sim total_kills | err |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.610 | 0.091 | 1.05 | 9.6 | 0.500 | 7.41 | 9.67 | 2.12 | 0.64 | 58.04 | 0.0569 |
| 2 | 0.664 | 0.089 | 1.04 | 10.2 | 0.485 | 7.16 | 9.76 | 2.14 | 0.63 | 58.74 | 0.0594 |
| 3 | 0.584 | 0.097 | 1.05 | 9.4 | 0.486 | 7.52 | 9.54 | 2.09 | 0.64 | 57.43 | 0.0596 |

### global

| rank | strength_sigma | lost_kill_rate | placement_kill_sharpness | respawn_mean | mp_win_penalty | sim mean_end | sim p1_kills | sim p10_kills | sim p20_kills | sim total_kills | err |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.700 | 0.165 | 1.44 | 2.7 | 0.500 | 7.30 | 10.52 | 1.32 | 0.27 | 47.37 | 0.4419 |
| 2 | 0.700 | 0.171 | 1.44 | 3.5 | 0.500 | 7.27 | 10.52 | 1.32 | 0.27 | 47.62 | 0.4453 |
| 3 | 0.691 | 0.176 | 1.43 | 3.4 | 0.500 | 7.32 | 10.37 | 1.33 | 0.27 | 47.20 | 0.4464 |

## 採用手順 (人間判断)

ベスト解 (上の表) を `config.py:REGION_PROFILES` に反映する際は、各地域ブロックの該当 5 キー (`strength_sigma`, `lost_kill_rate`, `placement_kill_sharpness`, `respawn_mean`, `mp_win_penalty`) を書き換えた上で `pytest tests/` を実行し、regression テストが通ることを確認する。
