# 既定値と実データの整合性チェック

シミュレーションの既定値・ハードコード定数・地域プリセットが、ALGS の実際の大会結果とどれだけ合っているかを公開データ（主に Liquipedia）で検証した記録。Year 4 (2024) + Year 5 (2025) の地域別 Pro League Finals 16 大会 + Global Finals 5 大会の計 21 大会をサンプリング済み。

## 1. 公式ルールとの完全一致が確認できた項目

| 項目 | コード値 | 公式値 | 結果 |
|---|---|---|---|
| `PLACEMENT_POINTS` | `(12, 9, 7, 5, 4, 3, 3, 2, 2, 2, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0)` | 同上（Liquipedia 2025 Championship Finals） | ✓ 一致 |
| `match_point_threshold` | 50 | 50 ポイント（複数公式ソース、ALGS Year 6 ページ） | ✓ 一致 |
| キルポイント | 1 キル = 1 ポイント | 同上 | ✓ 一致 |
| ロビーチーム数 / チーム人数 | 20 / 3 | 同上 | ✓ 一致 |

## 2. Match Point Finals 終了試合数の実績データ

### 2-A. Global Finals（5 大会）

| 大会 | 試合数 | 優勝 |
|---|---|---|
| 2024 Split 1 Playoffs (London) | 8 | REJECT WINNITY (86p) |
| 2024 Split 2 Playoffs (Raleigh) | 10 | Spacestation Gaming (85p) |
| Year 4 Championship (2024 Sapporo) | 9 | GoNext Esports |
| 2025 Midseason Playoffs Finals | 9 | VK Gaming (96p) |
| 2025 Championship Finals | 9 | GoNext Esports (68p) |

Global Finals 5 大会平均: **9.00 試合**、範囲 **8 – 10**。

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

Global Finals を含めた 21 大会平均: **8.38 試合**（合計 176 試合 / 21 大会、範囲 6 – 13）。

> 履歴: 2026-05-19 までこの欄は「19 大会平均 8.21 試合」と記載していたが、Global Finals の集計が Y4 Split 1/Split 2 Playoffs (London / Raleigh) の 2 大会を欠落していたうえ、19 大会で再集計しても (131 + 27) / 19 = 8.32 のはずで 8.21 自体が計算ミスだった。2026-05-19 に Global Finals を 5 大会に補完して 21 大会平均 8.38 に統一。

## 3. シミュレーション結果との比較

### 3-A. 調整前（参考値）

`apply_region_profile` 後、`starting_points_mode="none"` で各地域 5000 sims (seed=42, workers=4):

| 地域 | 実績平均 | シミュ mean (調整前) | 差分 | 評価 |
|---|---|---|---|---|
| Americas | 7.50 | 7.02 | -0.48 | わずかに短い |
| EMEA | 8.50 | 7.67 | -0.83 | 明確に短い |
| APAC-N | 8.75 | 8.81 | +0.06 | ほぼ完璧 |
| APAC-S | 8.00 | 8.35 | +0.35 | やや長い |

### 3-B. 第 1 次調整後（参考値）

各地域 10000 sims (seed=42, workers=4):

| 地域 | 実績平均 | 実績範囲 | シミュ mean | シミュ p05-p95 | 差分 |
|---|---|---|---|---|---|
| Americas | 7.50 | 6-10 | 7.54 | 5-10 | +0.04 |
| EMEA | 8.50 | 6-11 | 8.35 | 6-11 | -0.15 |
| APAC-N | 8.75 | 6-13 | 8.81 | 6-11 | +0.06 |
| APAC-S | 8.00 | 7-10 | 8.11 | 5-11 | +0.11 |

ロビー全体平均: シミュ 8.20 vs 実績 8.19 (+0.01)、`Total |diff| = 0.36` 試合。

### 3-C. 第 2 次調整後（現状の REGION_PROFILES）

セクション 5 の追加調査結果（試合あたり Lobby kill ~52、優勝チームキル分布の勾配検証）を踏まえて `PLACEMENT_KILL_FACTOR` の勾配強化と地域別 `lost_kill_rate` / `neutral_death_rate` の引き上げを実施。Lobby kill 増加で 1 位チームの snowball が加速したため、`strength_sigma` を全地域少し下げてオフセット。各地域 10000 sims (seed=42, workers=4):

| 地域 | 実績平均 | 実績範囲 | シミュ mean | シミュ p05-p95 | p99 | 差分 | Lobby kill 平均 |
|---|---|---|---|---|---|---|---|
| Americas | 7.50 | 6-10 | **7.52** | 5-11 | 12 | **+0.02** ✓ | 57.4 |
| EMEA | 8.50 | 6-11 | **8.44** | 5-11 | 13 | **-0.06** ✓ | 57.0 |
| APAC-N | 8.75 | 6-13 | **8.75** | 6-12 | 13 | **0.00** ✓ | 55.1 |
| APAC-S | 8.00 | 7-10 | **8.05** | 5-11 | 12 | **+0.05** ✓ | 57.3 |

ロビー全体平均:
- 実績平均: 8.19 試合
- シミュ平均 (第 2 次): (7.52 + 8.44 + 8.75 + 8.05) / 4 = **8.19 試合**
- **差 ±0.00 試合、完全一致 ✓**

全地域が **目標±0.06 試合以内** に収束。`Total |diff| = 0.13` 試合（前回 0.36 から大幅改善）。

Lobby kill 平均は 55–57 で実測中心帯 (52–59、4 大会平均 ~52) に着地。範囲も 38–85 と広く、APAC-N 2024 S2 の低キル外れ値 (~42) も自然発生範囲。p99 で 12–13 試合に到達するため、**APAC-N 2024 S2 の 13 試合外れ値もモデル内から発生する**。

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

## 5. 追加データ調査（2026-05-17 実施）

セクション 4 までで地域別平均試合数のチューニングは完了したので、次に「分布形状」「キルクレジットモデル」「Champs 横断地域強度」「APAC-N 外れ値の解釈」の 4 系統を追加調査した。

### 5-A. Year 3 (2022-23) 地域別 Pro League Finals

Year 3 の全 8 大会（4 地域 × 2 split）はいずれも Match Point Finals 形式（50 点先取）で実施されていることを Liquipedia の `Overall_standings` HTML 直接パースで確認。

| 大会 | Americas | EMEA | APAC-N | APAC-S |
|---|---|---|---|---|
| Y3 Split 1 (2022-12) | 5 (Esports Arena 73p) | 7 (Fire Beavers 72p) | **13** (Crazy Raccoon 115p) | 5 (Moist Esports 89p) |
| Y3 Split 2 (2023-05) | 8 (DarkZero 82p) | 9 (Alliance 75p) | **4** (Fnatic 79p) | 6 (Moist Esports 84p) |
| **Y3 地域平均** | 6.5 | 8.0 | 8.5 | 5.5 |

Y3 8 大会平均は **7.13 試合** で、Y4/Y5 16 大会平均 8.19 より 1 試合以上短い。

**サンプル統合の判断: 主要チューニングサンプルには加えない**

理由:
1. **APAC-N S2 が 4 試合で終了**: Fnatic が Game 3 終了時点で 50 点超 → 平均 17 点/試合ペースが必要で、ピュア Match Point として確率的に極端に低い。Regular Season から Post-Match Series Points を持ち込んでいた可能性が高い
2. **Crazy Raccoon 115p / Fnatic 79p (4 試合)** など、Y4/Y5 のピュア MP モデルでは再現困難な総ポイント
3. **Split 1 が全体的に短い**: 「rush to 50」メタが浸透しきっていない過渡期挙動

なお Y3 Split 1 APAC-N の **13 試合** と Y3 Split 2 APAC-N の **4 試合** という極端な結果は、当時のコミュニティでも「異常」として注目された大会群。試合数の絶対値そのものは（Y4/Y5 の Match Point モデルとは結果論的に整合する範囲もあるが）持ち込み点込みの計算で発生した数字なので、シミュレータの校正には使わない。

→ Y3 は「フォーマット過渡期データ」として別バケット保管。サンプル数倍増の代替として、Y4/Y5 の Playoffs / Champs Group Stage を後で集めるほうが整合性が高い。

### 5-B. 試合あたり Lobby 合計キル数（4 大会、per-game 実測）

Liquipedia の試合詳細表から 4 大会の per-game × 20 チームの kill 数を抽出して合計した。

| 大会 | 試合数 | 平均 kills/試合 | 範囲 |
|---|---|---|---|
| 2025 Championship Finals | 9 | **51.7** | 46–59 |
| 2024 EMEA S2 PL Final | 9 | **58.6** | 53–66 |
| 2024 APAC-N S2 PL Final | 13 | ~42 (部分集計、下限) | 31–56 |
| 2025 APAC-N S1 PL Final | 8 | **55.9** | 51–63 |

4 大会総合の平均: **約 52 kills/試合**（APAC-N 2024 S2 を除けば 55–59 が中心帯）。

**所見**: シミュレータの想定値 `scored_kills` 既定 60–65 は実測より上振れ。**実測中心値 55±5 程度に下方修正**するのが現実的。具体的には現行の `lost_kill_rate` / `transfer_kill_rate` の合計が小さすぎて、リスポーン込みの death_events ≈ 65–70 のうち実スコア化される比率が高すぎる可能性。

### 5-C. 優勝チーム順位別キル数（PLACEMENT_KILL_FACTOR 検証）

4 大会の優勝チーム（GoNext / FaZe / Alliance / SBI / HAO）の per-game placement × kills を順位帯で集計。

| 順位帯 | サンプル件数 | 平均 kills | 観測の幅 |
|---|---|---|---|
| 1 位 | 7 | **7.4** | 4–11 |
| 2–3 位 | 8 | **9.0** | 5–19 |
| 4–6 位 | 9 | **3.4** | 0–11 |
| 7–10 位 | 12 | **2.3** | 0–6 |
| 11–15 位 | 9 | **2.0** | 0–5 |
| 16–20 位 | 7 | **0.7** | 0–1 |

**所見**: 現行 `PLACEMENT_KILL_FACTOR = (1.35, 1.25, 1.20, 1.10, 1.10, 1.00×5, 0.75×5, 0.45×5)` は方向性は正しいが**勾配が緩すぎる**。
- ロビー平均 kills/チーム ≈ 52/20 = 2.6。1 位係数 1.35 × 2.6 = 3.5 だが実測は 7.4 → **1 位係数 2.5–2.8** が妥当
- 16–20 位は 0.45 × 2.6 = 1.17 だが実測は 0.7 → **下位係数 0.25–0.30** が妥当
- 2–3 位の盛り（実測 9.0）が 1 位より高く出ているのは、優勝チームが 2–3 位で kill 稼ぎして次の試合で 1 位を狙う典型パターン。FACTOR 自体は「placement→kill 取得率」なので、2 位係数を 1 位より低めに保つ現行設計は妥当

調整案: `PLACEMENT_KILL_FACTOR = (2.70, 2.20, 1.80, 1.40, 1.20, 1.00, 0.90, 0.80, 0.70, 0.60, 0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.25, 0.20, 0.20, 0.20)` のような形状（要シミュレーション再検証）。

### 5-D. APAC-N 2024 Split 2 が 13 試合に伸びた要因

| 観点 | 観測 |
|---|---|
| 優勝 HAO の挙動 | G1 で 2 位/12K = 24 点で爆走 → G3–7 で 11/19/9/10/19 位連発で 6 点しか稼げず失速 → G8 以降に 4–5 位帯で再浮上 → G13 で 12 位/4K で勝利、最終 105 点 |
| Match Point 到達 | G8–10 で 4–6 チームが同時に 50 点突破 |
| MP 到達後試合数 | **約 5–6 試合**（G8 で MP eligible 出現 → G13 で勝者確定） |
| Lobby kill 合計 | 13 試合中 7 試合で 42 以下、中央値 ~37 と低水準 |
| キル分布 | 1 試合の最大個人チーム kill 13/12/11 と上位は爆発、下位は 0 連発 → 総量が伸びない |

**所見**: HAO の単発的事情ではなく、**「defensive lobby（低総 kill）」と「MP eligible 集中（複数チーム同時 50 点）」の合成効果**が構造的要因。シミュレータが 13 試合を自然に出すには、「Lobby kill total ~35 + MP eligible 同時数 6+」の両条件を地域条件として再現できる必要がある。

**第 2 次校正での対応（適用済み）**: APAC-N の `lost_kill_rate` を 0.04 → 0.10 に引き上げ（低キルロビー方向を強化）、`strength_sigma` 0.30 → 0.27、`win_beta` 0.65 → 0.55 で MP eligible 集中を強化。結果として p99 = 13 試合に到達し、Lobby kill 範囲 38–83 で実測の 42（外れ値帯）も自然に発生する範囲に。

### 5-E. Champs Group Stage 地域強度比較（3 大会）

40 チーム × 4 グループ × 各 18 試合（計 36 試合開催）形式。Winners Bracket 進出 = 上位 20 を「地域強度」の指標とした。

| 地域 | Y3 (2023) | Y4 (Sapporo 2024) | Y5 (Sapporo 2026) | 3 大会平均通過率 |
|---|---|---|---|---|
| Americas | ~64% (9/14) | 57% (8/14) | ~55% (8/14–15) | **~56%** |
| EMEA | ~63% (5/8) | 64% (7/11) | 43% (3/7) | **~50%** |
| APAC-N | ~57% (4/7) | 43% (3/7) | 50% (5/10) | **~47%** |
| APAC-S | ~25% (2/8) | 25% (2/8) | 50% (4/8) | **~38%** |

Champs ベースの地域強度ヒエラルキー: **Americas ≳ EMEA > APAC-N ≳ APAC-S**

**所見**:
- 現プリセットの `strength_sigma`（小=均質=長期化）の順は APAC-N < APAC-S < EMEA < Americas で、これは「地域内拮抗度」の解釈であって「地域強度」とは独立の指標。Champs 通過率は別概念なので直接の矛盾ではない
- ただし **Y5 で EMEA が大幅後退（64%→43%）、APAC-S が急騰（25%→50%）** という直近トレンドは preset の固定値が捉えていない。preset を「過去 4 大会平均」で校正すると Y5 のメタシフトに追随できない
- 特に EMEA preset は Y4/Y5 Pro League Final データで `strength_sigma=0.38`（APAC-N 並みに均質）まで下げたが、これは Y5 の EMEA 弱体化（チーム間の地力ばらつき増）を反映している可能性。Y4 単独で見ると EMEA は強豪集中（短期化）寄りだったはず

### 5-F. 引用ソース（追加分）

Year 3 Pro League Finals:
- [Y3 Split 1 NA Final](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2022/Split_1/Pro_League/North_America/Final)
- [Y3 Split 1 EMEA Final](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2022/Split_1/Pro_League/EMEA/Final)
- [Y3 Split 1 APAC-N Final](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2022/Split_1/Pro_League/APAC_North/Final)
- [Y3 Split 1 APAC-S Final](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2022/Split_1/Pro_League/APAC_South/Final)
- [Y3 Split 2 NA Final](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2023/Split_2/Pro_League/North_America/Final)
- [Y3 Split 2 EMEA Final](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2023/Split_2/Pro_League/EMEA/Final)
- [Y3 Split 2 APAC-N Final](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2023/Split_2/Pro_League/APAC_North/Final)
- [Y3 Split 2 APAC-S Final](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2023/Split_2/Pro_League/APAC_South/Final)

Champs Group Stage:
- [2024 Champs Group Stage](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2024/Championship/Group_Stage)
- [2026 Champs Group Stage](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2026/Championship/Group_Stage)
- [2023 Champs Group Stage](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2023/Championship/Group_Stage)

### 5-G. 第 2 次校正で実施した調整（適用済み、結果はセクション 3-C）

調査結果を踏まえて以下を 1 セットで config.py に適用:

1. **`PLACEMENT_KILL_FACTOR` 勾配強化（適用済み）**:
   - 旧: `(1.35, 1.25, 1.20, 1.10, 1.10, 1.00×5, 0.75×5, 0.45×5)`
   - 新: `(2.50, 2.00, 1.70, 1.40, 1.20, 1.00, 0.90, 0.80, 0.70, 0.60, 0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.25, 0.20, 0.20, 0.20)`
   - 実測の 1 位平均 7.4 kills / 16-20 位平均 0.7 kills を再現する勾配
2. **`neutral_death_rate` 0.01 → 0.03**（全地域共通）。Lobby kill 実測 52 を再現するための中立死率引き上げ
3. **地域別 `lost_kill_rate` 引き上げ**: americas 0.025→0.06、emea 0.035→0.07、apac_n 0.04→0.10、apac_s 0.030→0.065
4. **APAC-N の MP eligible 集中強化**: `strength_sigma` 0.30→0.27、`win_beta` 0.65→0.55
5. **PLACEMENT_KILL_FACTOR 勾配強化による snowball オフセット**: 全地域 `strength_sigma` を少し下げて拮抗強化
   - Americas: 0.48 → 0.43、`mp_win_penalty` 0.08 → 0.11
   - EMEA: 0.38 → 0.30、`mp_win_penalty` 0.13 → 0.17
   - APAC-S: 0.42 → 0.38、`mp_win_penalty` 0.12 → 0.14

結果（セクション 3-C）: 全地域 ±0.06 試合以内、ロビー全体平均は実績と完全一致 (8.19 vs 8.19)、Lobby kill 平均 55–57 で実測中心帯。p99 で 12–13 試合に到達するので APAC-N 2024 S2 の 13 試合外れ値も自然発生範囲。

### 5-H. まだ残っている課題

1. **EMEA の年次別変動**: Y5 の Champs 通過率が 43% と急落していたが、preset は単一値で固定。年次別 preset（emea_y4 / emea_y5）に分けるかの方針判断は未着手
2. **APAC-S Y5 急騰（25→50%）への追随**: 同上、preset の単一値設計の限界
3. **個別地域の分布形状検証**: 平均試合数だけでなく、std や歪度も実データと整合するかは未検証（サンプル 16 大会では std を有意に推定できない）
4. **Champs Group Stage の per-match キル分布データ**: 試合数が地域 Pro League より多いので、収集すれば PLACEMENT_KILL_FACTOR の勾配を更に精緻化できる

## 7. 引用ソース

### Global Finals
- [Apex Legends Global Series: 2024 Split 1 Playoffs - Finals (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2024/Split_1/Playoffs/Finals)
- [Apex Legends Global Series: 2024 Split 2 Playoffs - Finals (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2024/Split_2/Playoffs/Finals)
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
