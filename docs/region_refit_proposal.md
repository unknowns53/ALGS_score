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
| americas | 0.307 | 0.031 | 0.85 | 11.6 | 0.000 | 7.50 | 7.74 | 9.03 | 8.99 | 2.37 | 2.62 | 1.60 | 1.04 | 61.90 | 64.52 | 0.0429 | 30 |
| emea | 0.349 | 0.035 | 1.02 | 7.2 | 0.468 | 8.50 | 8.46 | 9.44 | 9.44 | 2.53 | 2.28 | 0.56 | 0.78 | 56.50 | 60.11 | 0.0181 | 34 |
| apac_n | 0.268 | 0.020 | 0.98 | 12.0 | 0.277 | 8.75 | 8.40 | 9.97 | 9.80 | 3.51 | 2.56 | 0.80 | 0.96 | 55.40 | 65.47 | 0.1615 | 35 |
| apac_s | 0.402 | 0.054 | 0.95 | 9.8 | 0.359 | 8.00 | 7.96 | 9.22 | 9.14 | 2.69 | 2.40 | 0.59 | 0.87 | 57.91 | 61.06 | 0.0225 | 32 |
| global | 0.265 | 0.052 | 1.08 | 6.8 | 0.442 | 9.00 | 9.08 | 9.47 | 9.51 | 2.53 | 2.15 | 0.08 | 0.73 | 57.47 | 58.50 | 0.0681 | 36 |

## 上位 3 候補 (各地域、観測との正規化二乗誤差 — 5 成分)

err = (Δmean_end/obs)² + (Δp1/k_scale)² + (Δp10/k_scale)² + (Δp20/k_scale)² + (Δtotal/(k_scale*20))². ただし k_scale = obs_total/20 ≈ 2.8-3.1 (per-team mean kills)。Cycle 14 (2026-05): 全 kill metrics を共通スケール (1 kill = 1 unit、placement 非依存) で正規化。

### americas

| rank | strength_sigma | lost_kill_rate | placement_kill_sharpness | respawn_mean | mp_win_penalty | sim mean_end | sim p1_kills | sim p10_kills | sim p20_kills | sim total_kills | err |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.307 | 0.031 | 0.85 | 11.6 | 0.000 | 7.74 | 8.99 | 2.62 | 1.04 | 64.52 | 0.0429 |
| 2 | 0.318 | 0.027 | 0.85 | 11.7 | 0.000 | 7.80 | 8.99 | 2.64 | 1.05 | 64.82 | 0.0432 |
| 3 | 0.313 | 0.031 | 0.85 | 11.6 | 0.000 | 7.70 | 8.95 | 2.63 | 1.04 | 64.57 | 0.0433 |

### emea

| rank | strength_sigma | lost_kill_rate | placement_kill_sharpness | respawn_mean | mp_win_penalty | sim mean_end | sim p1_kills | sim p10_kills | sim p20_kills | sim total_kills | err |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.349 | 0.035 | 1.02 | 7.2 | 0.468 | 8.46 | 9.44 | 2.28 | 0.78 | 60.11 | 0.0181 |
| 2 | 0.272 | 0.082 | 1.01 | 11.2 | 0.278 | 8.53 | 9.43 | 2.30 | 0.80 | 60.25 | 0.0188 |
| 3 | 0.324 | 0.030 | 1.02 | 6.3 | 0.472 | 8.51 | 9.43 | 2.24 | 0.77 | 59.63 | 0.0191 |

### apac_n

| rank | strength_sigma | lost_kill_rate | placement_kill_sharpness | respawn_mean | mp_win_penalty | sim mean_end | sim p1_kills | sim p10_kills | sim p20_kills | sim total_kills | err |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.268 | 0.020 | 0.98 | 12.0 | 0.277 | 8.40 | 9.80 | 2.56 | 0.96 | 65.47 | 0.1615 |
| 2 | 0.266 | 0.020 | 0.99 | 11.9 | 0.487 | 8.65 | 9.88 | 2.54 | 0.95 | 65.50 | 0.1615 |
| 3 | 0.340 | 0.020 | 0.97 | 12.0 | 0.500 | 8.50 | 9.75 | 2.56 | 0.94 | 65.39 | 0.1618 |

### apac_s

| rank | strength_sigma | lost_kill_rate | placement_kill_sharpness | respawn_mean | mp_win_penalty | sim mean_end | sim p1_kills | sim p10_kills | sim p20_kills | sim total_kills | err |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.402 | 0.054 | 0.95 | 9.8 | 0.359 | 7.96 | 9.14 | 2.40 | 0.87 | 61.06 | 0.0225 |
| 2 | 0.455 | 0.069 | 0.96 | 10.8 | 0.363 | 7.78 | 9.20 | 2.36 | 0.83 | 60.62 | 0.0226 |
| 3 | 0.441 | 0.055 | 0.97 | 9.5 | 0.274 | 7.83 | 9.23 | 2.35 | 0.83 | 60.57 | 0.0227 |

### global

| rank | strength_sigma | lost_kill_rate | placement_kill_sharpness | respawn_mean | mp_win_penalty | sim mean_end | sim p1_kills | sim p10_kills | sim p20_kills | sim total_kills | err |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.265 | 0.052 | 1.08 | 6.8 | 0.442 | 9.08 | 9.51 | 2.15 | 0.73 | 58.50 | 0.0681 |
| 2 | 0.429 | 0.064 | 1.07 | 8.0 | 0.491 | 8.70 | 9.44 | 2.17 | 0.73 | 58.75 | 0.0684 |
| 3 | 0.283 | 0.020 | 1.07 | 4.6 | 0.500 | 9.16 | 9.43 | 2.19 | 0.75 | 58.72 | 0.0691 |

## 採用手順 (人間判断)

ベスト解 (上の表) を `config.py:REGION_PROFILES` に反映する際は、各地域ブロックの該当 5 キー (`strength_sigma`, `lost_kill_rate`, `placement_kill_sharpness`, `respawn_mean`, `mp_win_penalty`) を書き換えた上で `pytest tests/` を実行し、regression テストが通ることを確認する。
