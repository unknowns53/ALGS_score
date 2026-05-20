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
| `placement_kill_mid_boost` | 0.000 | 1.500 |

## ベスト解 (各地域)

| region | strength_sigma | lost_kill_rate | placement_kill_sharpness | respawn_mean | mp_win_penalty | placement_kill_mid_boost | obs mean_end | sim mean_end | obs p1_kills | sim p1_kills | obs p10_kills | sim p10_kills | obs p20_kills | sim p20_kills | obs total_kills | sim total_kills | err | n_obs_matches |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| americas | 0.285 | 0.020 | 0.86 | 11.4 | 0.006 | 0.000 | 7.50 | 7.85 | 9.03 | 9.07 | 2.37 | 2.65 | 1.60 | 1.06 | 61.90 | 65.21 | 0.0445 | 30 |
| emea | 0.351 | 0.068 | 1.19 | 6.2 | 0.390 | 0.372 | 8.50 | 8.50 | 9.44 | 9.41 | 2.53 | 2.52 | 0.56 | 0.55 | 56.50 | 56.86 | 0.0002 | 34 |
| apac_n | 0.123 | 0.050 | 1.41 | 9.2 | 0.102 | 0.916 | 8.75 | 8.74 | 9.97 | 9.93 | 3.51 | 3.44 | 0.80 | 0.46 | 55.40 | 60.65 | 0.0251 | 35 |
| apac_s | 0.403 | 0.045 | 1.14 | 6.3 | 0.271 | 0.415 | 8.00 | 8.00 | 9.22 | 9.20 | 2.69 | 2.72 | 0.59 | 0.60 | 57.91 | 58.46 | 0.0003 | 32 |
| global | 0.319 | 0.054 | 1.39 | 1.5 | 0.268 | 0.644 | 9.00 | 8.98 | 9.47 | 9.44 | 2.53 | 2.53 | 0.08 | 0.40 | 57.47 | 53.55 | 0.0168 | 36 |

## 上位 3 候補 (各地域、観測との正規化二乗誤差 — 5 成分)

err = (Δmean_end/obs)² + (Δp1/k_scale)² + (Δp10/k_scale)² + (Δp20/k_scale)² + (Δtotal/(k_scale*20))². ただし k_scale = obs_total/20 ≈ 2.8-3.1 (per-team mean kills)。Cycle 14 (2026-05): 全 kill metrics を共通スケール (1 kill = 1 unit、placement 非依存) で正規化。

### americas

| rank | strength_sigma | lost_kill_rate | placement_kill_sharpness | respawn_mean | mp_win_penalty | placement_kill_mid_boost | sim mean_end | sim p1_kills | sim p10_kills | sim p20_kills | sim total_kills | err |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.285 | 0.020 | 0.86 | 11.4 | 0.006 | 0.000 | 7.85 | 9.07 | 2.65 | 1.06 | 65.21 | 0.0445 |
| 2 | 0.360 | 0.027 | 0.87 | 10.3 | 0.080 | 0.000 | 7.64 | 8.99 | 2.56 | 0.97 | 63.68 | 0.0465 |
| 3 | 0.290 | 0.020 | 0.88 | 9.3 | 0.038 | 0.000 | 7.91 | 8.95 | 2.55 | 0.99 | 63.23 | 0.0472 |

### emea

| rank | strength_sigma | lost_kill_rate | placement_kill_sharpness | respawn_mean | mp_win_penalty | placement_kill_mid_boost | sim mean_end | sim p1_kills | sim p10_kills | sim p20_kills | sim total_kills | err |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.351 | 0.068 | 1.19 | 6.2 | 0.390 | 0.372 | 8.50 | 9.41 | 2.52 | 0.55 | 56.86 | 0.0002 |
| 2 | 0.268 | 0.148 | 1.24 | 11.9 | 0.191 | 0.435 | 8.58 | 9.38 | 2.51 | 0.51 | 55.92 | 0.0010 |
| 3 | 0.413 | 0.083 | 1.18 | 7.8 | 0.492 | 0.368 | 8.28 | 9.48 | 2.52 | 0.53 | 57.20 | 0.0011 |

### apac_n

| rank | strength_sigma | lost_kill_rate | placement_kill_sharpness | respawn_mean | mp_win_penalty | placement_kill_mid_boost | sim mean_end | sim p1_kills | sim p10_kills | sim p20_kills | sim total_kills | err |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.123 | 0.050 | 1.41 | 9.2 | 0.102 | 0.916 | 8.74 | 9.93 | 3.44 | 0.46 | 60.65 | 0.0251 |
| 2 | 0.142 | 0.058 | 1.40 | 10.0 | 0.126 | 0.907 | 8.70 | 9.94 | 3.43 | 0.46 | 60.85 | 0.0257 |
| 3 | 0.109 | 0.037 | 1.41 | 7.4 | 0.183 | 0.913 | 8.83 | 9.89 | 3.39 | 0.45 | 60.05 | 0.0259 |

### apac_s

| rank | strength_sigma | lost_kill_rate | placement_kill_sharpness | respawn_mean | mp_win_penalty | placement_kill_mid_boost | sim mean_end | sim p1_kills | sim p10_kills | sim p20_kills | sim total_kills | err |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.403 | 0.045 | 1.14 | 6.3 | 0.271 | 0.415 | 8.00 | 9.20 | 2.72 | 0.60 | 58.46 | 0.0003 |
| 2 | 0.371 | 0.022 | 1.12 | 4.7 | 0.162 | 0.368 | 7.98 | 9.20 | 2.70 | 0.62 | 58.65 | 0.0003 |
| 3 | 0.451 | 0.095 | 1.13 | 10.6 | 0.383 | 0.415 | 7.94 | 9.24 | 2.72 | 0.60 | 58.62 | 0.0004 |

### global

| rank | strength_sigma | lost_kill_rate | placement_kill_sharpness | respawn_mean | mp_win_penalty | placement_kill_mid_boost | sim mean_end | sim p1_kills | sim p10_kills | sim p20_kills | sim total_kills | err |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.319 | 0.054 | 1.39 | 1.5 | 0.268 | 0.644 | 8.98 | 9.44 | 2.53 | 0.40 | 53.55 | 0.0168 |
| 2 | 0.157 | 0.069 | 1.42 | 2.0 | 0.051 | 0.671 | 9.05 | 9.50 | 2.55 | 0.38 | 53.07 | 0.0168 |
| 3 | 0.280 | 0.051 | 1.42 | 1.2 | 0.361 | 0.703 | 9.21 | 9.42 | 2.59 | 0.38 | 53.47 | 0.0168 |

## 採用手順 (人間判断)

ベスト解 (上の表) を `config.py:REGION_PROFILES` に反映する際は、各地域ブロックの該当 6 キー (`strength_sigma`, `lost_kill_rate`, `placement_kill_sharpness`, `respawn_mean`, `mp_win_penalty`, `placement_kill_mid_boost`) を書き換えた上で `pytest tests/` を実行し、regression テストが通ることを確認する。
