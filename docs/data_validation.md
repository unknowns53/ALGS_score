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

### 3-A. 調整前（参考値）

`apply_region_profile` 後、`starting_points_mode="none"` で各地域 5000 sims (seed=42, workers=4):

| 地域 | 実績平均 | シミュ mean (調整前) | 差分 | 評価 |
|---|---|---|---|---|
| Americas | 7.50 | 7.02 | -0.48 | わずかに短い |
| EMEA | 8.50 | 7.67 | -0.83 | 明確に短い |
| APAC-N | 8.75 | 8.81 | +0.06 | ほぼ完璧 |
| APAC-S | 8.00 | 8.35 | +0.35 | やや長い |

### 3-B. 調整後（現状の REGION_PROFILES）

各地域 10000 sims (seed=42, workers=4):

| 地域 | 実績平均 | 実績範囲 | シミュ mean | シミュ p05-p95 | 差分 | 評価 |
|---|---|---|---|---|---|---|
| Americas | 7.50 | 6-10 | **7.54** | 5-10 | **+0.04** | ✓ |
| EMEA | 8.50 | 6-11 | **8.35** | 6-11 | **-0.15** | ✓ |
| APAC-N | 8.75 | 6-13 | **8.81** | 6-11 | **+0.06** | ✓ |
| APAC-S | 8.00 | 7-10 | **8.11** | 5-11 | **+0.11** | ✓ |

ロビー全体平均:
- 実績平均: 8.19 試合
- シミュ平均 (調整後): (7.54 + 8.35 + 8.81 + 8.11) / 4 = **8.20 試合**
- **差 +0.01 試合、ほぼ完全一致 ✓**

全地域が **目標±0.2 試合以内** に収束。`Total |diff| = 0.36` 試合（4 地域合計）。

## 4. 読み取れた傾向と調整内容

調整前（8 大会サンプル時点）で見えた傾向:

1. **APAC-N プリセットは想定以上に正確**: 実績 8.75 試合とシミュ 8.81 試合の差はわずか 0.06。「拮抗 + カオス高め」の方向は実データを再現できていた。**調整なし**。
2. **EMEA プリセットが明確に短期化させすぎ**: 実績 8.50 とシミュ 7.67 で 0.83 試合の乖離。実績の範囲 6-11 を見ると、EMEA はそこまで「structured & low chaos」ではなく、むしろ APAC-N に近い拮抗ロビー。
3. **Americas はわずかに短期化させすぎ**: 0.48 試合差。`win_beta=0.95` が高すぎて短期決着を促していた。
4. **APAC-S はやや長期化させすぎ**: 0.35 試合差。`volatility_mean=1.15` が過剰だった。
5. **大会単位のばらつきは大きい**: APAC-N の 2024 S2 が 13 試合と飛び抜けて長く、シミュ p95=11 を超える外れ値だが、これは年間 4 大会のうち 1 つだけなので「モデルがおかしい」ではなく「現実が広く分布する」ことの反映。

実施した preset 調整:

| 地域 | 主な変更 |
|---|---|
| Americas | `strength_sigma` 0.55→0.48、`win_beta` 0.95→0.85、`placement_win_correlation` 0.60→0.50、`base_match_noise` 0.70→0.75 |
| EMEA | `strength_sigma` 0.45→0.38、`base_match_noise` 0.70→0.95、`volatility_mean` 0.90→1.05、`consistency_beta` 0.55→0.40、`lost_kill_rate` 0.020→0.035、`mp_win_penalty` 0.10→0.13、`mp_pressure_lost_kill_multiplier` 1.15→1.25 |
| APAC-N | **変更なし** |
| APAC-S | `strength_sigma` 0.40→0.42、`volatility_mean` 1.15→0.98、`volatility_sigma` 0.35→0.25、`base_match_noise` 0.95→0.82、`lost_kill_rate` 0.035→0.030 |

## 5. まだ集めていないデータ（さらに精度を上げたい場合）

地域別平均はチューニング完了したが、以下を集めれば「分布形状」や「キル credit モデル」も検証可能:

1. **Year 3 (2023) の地域別 Pro League Finals**（4 地域 × 2 split = 8 大会）→ サンプル 24 大会に拡張、地域別の std もチューニングできる
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
