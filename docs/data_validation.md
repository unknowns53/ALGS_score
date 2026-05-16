# 既定値と実データの整合性チェック

シミュレーションの既定値・ハードコード定数・地域プリセットが、ALGS の実際の大会結果とどれだけ合っているかを公開データ（主に Liquipedia）で検証した記録。Year 4 (2024) + Year 5 (2025) の地域別 Pro League Finals 16 大会 + Global Finals 3 大会の計 19 大会をサンプリング済み。

## 1. 公式ルールとの完全一致が確認できた項目

| 項目 | コード値 | 公式値 | 結果 |
|---|---|---|---|
| `PLACEMENT_POINTS` | `(12, 9, 7, 5, 4, 3, 3, 2, 2, 2, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0)` | 同上（Liquipedia 2025 Championship Finals） | ✓ 一致 |
| `match_point_threshold` | 50 | 50 ポイント（複数公式ソース、ALGS Year 6 ページ） | ✓ 一致 |
| キルポイント | 1 キル = 1 ポイント | 同上 | ✓ 一致 |
| ロビーチーム数 / チーム人数 | 20 / 3 | 同上 | ✓ 一致 |

## 2. Match Point Finals 終了試合数の実績データ

### 2-A. Global Finals（3 大会）

| 大会 | 試合数 | 優勝 |
|---|---|---|
| Year 4 Championship (2024-25 Sapporo) | 9 | GoNext Esports |
| 2025 Midseason Playoffs Finals | 9 | VK Gaming (96p) |
| 2025 Championship Finals | 9 | GoNext Esports (68p) |

### 2-B. 地域別 Pro League Finals（16 大会）

| 大会 | Americas | EMEA | APAC-N | APAC-S |
|---|---|---|---|---|
| 2024 Split 1 | 7 (DarkZero) | 8 (Aurora) | 6 (Fnatic) | 10 (Wonton Dumpling) |
| 2024 Split 2 | 6 (Team Falcons) | 9 (Alliance) | **13** (HAO 105p) | 7 (Mkers 77p) |
| 2025 Split 1 | 10 (Team Falcons) | 11 (GoNext 73p) | 8 (SBI 70p) | 7 (JDG 82p) |
| 2025 Split 2 | 7 (Shopify 81p) | 6 (Alliance 77p) | 8 (UNLIMIT 83p) | 8 (BGB 84p) |
| **地域平均** | **7.50** | **8.50** | **8.75** | **8.00** |

実績統計（地域別 16 大会全体）:
- 平均: **8.19 試合**
- 中央値: **8 試合**
- 範囲: **6 〜 13 試合**

Global Finals を含めた 19 大会平均: **8.21 試合**

## 3. シミュレーション結果との比較

`apply_region_profile` 後、`starting_points_mode="none"` で各地域 5000 sims (seed=42, workers=4) を回した結果:

| 地域 | 実績平均 | 実績範囲 | シミュ mean | シミュ p05-p95 | 差分 | 評価 |
|---|---|---|---|---|---|---|
| Americas | 7.50 | 6-10 | 7.02 | 5-10 | -0.48 | わずかに短い |
| EMEA | 8.50 | 6-11 | 7.67 | 5-10 | -0.83 | **明確に短い** |
| APAC-N | 8.75 | 6-13 | 8.81 | 6-11 | +0.06 | **ほぼ完璧** |
| APAC-S | 8.00 | 7-10 | 8.35 | 6-11 | +0.35 | やや長い |

ロビー全体平均:
- 実績平均: 8.19 試合
- シミュ平均: (7.02 + 7.67 + 8.81 + 8.35) / 4 = **7.96 試合**
- **差 -0.23**、おおむね一致 ✓

## 4. 読み取れる傾向（16 大会サンプルで更新）

1. **モデルの全体的な妥当性は OK**: ロビー全体の平均と中央値はシミュとほぼ一致（実績 8.19 / シミュ 7.96）。地域別範囲もシミュ p05-p95 にほぼ収まる。
2. **APAC-N プリセットは想定以上に正確**: 実績 8.75 試合とシミュ 8.81 試合の差はわずか 0.06。プリセットの「拮抗 + カオス高め」の方向は実データを再現できている。
3. **EMEA プリセットが明確に短期化させすぎ**: 実績 8.50 とシミュ 7.67 で 0.83 試合の乖離。実績の範囲 6-11 を見ると、EMEA はそこまで「structured & low chaos」ではない。
4. **Americas はわずかに短期化させすぎ**: 0.48 試合差。実績 2025 S1 の 10 試合のような長期化も普通にあるが、シミュ平均は 7.02 で実績 7.50 に届かない。
5. **APAC-S はやや長期化させすぎ**: 0.35 試合差。実績 4 大会で 7-10 のレンジに収まり、`volatility_mean=1.15` が高すぎる可能性。
6. **大会単位のばらつきは大きい**: APAC-N の 2024 S2 が 13 試合と飛び抜けて長く、シミュ p95=11 を超える外れ値だが、これは年間 4 大会のうち 1 つだけなので「モデルがおかしい」ではなく「現実が広く分布する」ことの反映。

## 5. 推奨される調整方向（次のステップ）

サンプル 16 大会で傾向が見えてきたので、以下の方向で preset を調整するのが妥当。

| 地域 | 現状 mean | 目標 mean | 提案調整 |
|---|---|---|---|
| Americas | 7.02 | 7.5 (+0.5) | `strength_sigma` 0.55→0.45、`win_beta` 0.95→0.80、`placement_win_correlation` 0.60→0.50 |
| EMEA | 7.67 | 8.5 (+0.8) | `base_match_noise` 0.70→0.85、`volatility_mean` 0.90→1.00、`consistency_beta` 0.55→0.45 |
| APAC-N | 8.81 | 8.75 (~0) | **現状維持** |
| APAC-S | 8.35 | 8.00 (-0.35) | `volatility_mean` 1.15→1.05、`lost_kill_rate` 0.035→0.030 |

調整後の妥当性検証は、各地域 5000 sims を回して新 mean が目標±0.2 試合に入るかで判断する。サニティテストが破綻しないかも合わせて確認。

## 6. まだ集めていないデータ（さらに精度を上げたい場合）

1. **Year 3 (2023) の地域別 Pro League Finals**（4 地域 × 2 split = 8 大会）→ サンプル数を 24 大会に
2. **過去 Champs の Group Stage 結果**（地域差を別側面から検証）
3. **試合あたりの Lobby 合計キル数の実データ**（`scored_kills` 既定 60-65 の検証用）
4. **試合あたりの優勝チームキル数の分布**（`PLACEMENT_KILL_FACTOR` の傾斜が現実と合うか）
5. **APAC-N 2024 S2 の 13 試合に何が起きたか**（外れ値の原因解明、構造的なのか単発か）

## 7. 引用ソース

### Global Finals
- [Apex Legends Global Series: 2025 Championship - Finals (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2025/Championship/Finals)
- [Apex Legends Global Series: 2025 Midseason Playoffs - Finals (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2025/Midseason_Playoffs/Finals)
- [GoNext clinch victory in ALGS Championship Year 4 (Dexerto)](https://www.dexerto.com/apex-legends/how-to-watch-algs-championship-year-4-stream-schedule-and-results-3039736/)

### 2024 Split 1 Pro League Finals
- [North America (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2024/Split_1/Pro_League/North_America)
- [EMEA (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2024/Split_1/Pro_League/EMEA)
- [APAC North (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2024/Split_1/Pro_League/APAC_North)
- [APAC South (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2024/Split_1/Pro_League/APAC_South)

### 2024 Split 2 Pro League Finals
- [North America (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2024/Split_2/Pro_League/North_America)
- [EMEA (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2024/Split_2/Pro_League/EMEA)
- [APAC North Final (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2024/Split_2/Pro_League/APAC_North/Final)
- [APAC South Final (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2024/Split_2/Pro_League/APAC_South/Final)

### 2025 Split 1 Pro League Finals
- [Americas (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2025/Split_1/Pro_League/Americas)
- [EMEA Final (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2025/Split_1/Pro_League/EMEA/Final)
- [APAC North Final (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2025/Split_1/Pro_League/APAC_North/Final)
- [APAC South Final (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2025/Split_1/Pro_League/APAC_South/Final)

### 2025 Split 2 Pro League Finals
- [Americas Final (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2025/Split_2/Pro_League/Americas/Final)
- [EMEA Final (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2025/Split_2/Pro_League/EMEA/Final)
- [APAC North Final (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2025/Split_2/Pro_League/APAC_North/Final)
- [APAC South Final (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2025/Split_2/Pro_League/APAC_South/Final)

### 公式 / ルール
- [Championship Points - ALGS Year 6 (Official EA)](https://algs.ea.com/en/championship-points)
- [ALGS Scoring System Guide (Au Pro Circuit)](https://auprocircuit.com/algs-scoring-system-guide-au/)
