# 既定値と実データの整合性チェック

シミュレーションの既定値・ハードコード定数・地域プリセットが、ALGS の実際の大会結果とどれだけ合っているかを公開データ（主に Liquipedia）で検証した記録。サンプル数が地域あたり 1〜2 大会と少ないため、**結論を出すには追加サンプリングが必要** という立ち位置のメモ。

## 1. 公式ルールとの完全一致が確認できた項目

| 項目 | コード値 | 公式値 | 結果 |
|---|---|---|---|
| `PLACEMENT_POINTS` | `(12, 9, 7, 5, 4, 3, 3, 2, 2, 2, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0)` | 同上（Liquipedia 2025 Championship Finals） | ✓ 一致 |
| `match_point_threshold` | 50 | 50 ポイント（複数公式ソース、ALGS Year 6 ページ） | ✓ 一致 |
| キルポイント | 1 キル = 1 ポイント | 同上 | ✓ 一致 |
| ロビーチーム数 / チーム人数 | 20 / 3 | 同上 | ✓ 一致 |

## 2. Match Point Finals 終了試合数の実績データ

Liquipedia + Dexerto + Esportsinsider から集めた 8 大会:

| 大会 | 地域 | 試合数 | 優勝 |
|---|---|---|---|
| Year 4 Championship (2024-25 Sapporo) | Global | 9 | GoNext Esports |
| 2025 Midseason Playoffs Finals | Global | 9 | VK Gaming (96p) |
| 2025 Championship Finals | Global | 9 | GoNext Esports (68p) |
| 2025 Split 1 Pro League Final | Americas | **10** | Team Falcons |
| 2025 Split 2 Pro League Final | Americas | **7** | Shopify Rebellion (81p) |
| 2025 Split 1 Pro League Final | EMEA | **11** | GoNext Esports (73p) |
| 2025 Split 1 Pro League Final | APAC North | **8** | SBI e-Sports (70p) |
| 2025 Split 1 Pro League Final | APAC South | **7** | JD Gaming (82p) |

実績統計（8 大会）:
- 平均: **8.75 試合**
- 中央値: **9 試合**
- 範囲: **7 〜 11 試合**

## 3. シミュレーション結果との比較

`apply_region_profile` 後、`starting_points_mode="none"` で各地域 5000 sims (seed=42, workers=4) を回した結果:

| 地域 | 実績試合数 | シミュ mean | シミュ p25-p75 | シミュ p95 | 評価 |
|---|---|---|---|---|---|
| Americas | 10, 7 | 7.02 | 6-8 | 10 | やや短い |
| EMEA | 11 | 7.67 | 7-9 | 10 | **短すぎる**（実績 11 が p95 を超える） |
| APAC North | 8 | 8.81 | 8-10 | 11 | わずかに長い |
| APAC South | 7 | 8.35 | 7-9 | 11 | やや長い |

ロビー全体での平均比較:
- 実績平均: 8.75 試合
- シミュ平均: (7.02 + 7.67 + 8.81 + 8.35) / 4 = **7.96 試合**

## 4. 読み取れる傾向

1. **モデルの全体的な妥当性は OK**: 実績の範囲 (7-11) はシミュレーション分布の p05-p95 にほぼ収まる。「7 試合で終わる大会」も「11 試合まで伸びる大会」も、現状のモデルで再現可能。
2. **地域差を強調しすぎている疑い**: APAC-N を長く、Americas を短くというプリセット設計が、実データではそこまで明確に分かれていない。「APAC-N が長期化しやすい」はコミュニティの印象に近く、Pro League 1 大会のサンプルでは Americas / EMEA の方が長期化していた例もある。
3. **EMEA は明確に短く出すぎ**: 実績 11 試合がシミュレーション p95 を超える点は、`structured & low chaos` のプリセット設計に問題がありそう。EMEA は実は拮抗してるロビー。
4. **APAC-S は実績不足**: 1 サンプル (7 試合) では何とも言えない。

## 5. 結論と方針

サンプル数が地域あたり 1〜2 大会では統計的に強い結論は出せない。プリセットをいじるよりも、**追加のデータ収集を先にやってから判断する** のが安全。コード側は現状維持。

## 6. 今後追加で集めたいデータ

優先度順:

1. **Year 4 (2024) の地域別 Pro League Finals**（Split 1 / Split 2 × 4 地域 = 8 大会、特に APAC North と EMEA の試合数）
2. **Year 3 (2023) の地域別 Pro League Finals**
3. **2025 Split 2 の EMEA / APAC-N / APAC-S Pro League Final**（Americas は確認済み、他 3 地域を補完）
4. **過去 Champs の地域別 Group Stage 通過チームの優勝率と試合数**（地域差の検証）
5. **試合あたりの Lobby 合計キル数**（ApexLegendsStatus.com のスクレイピングなど）— `scored_kills` 既定 60-65 の検証用
6. **試合あたりの優勝チームキル数の分布**（`PLACEMENT_KILL_FACTOR` の傾斜が現実と合うか）

データソース候補:
- Liquipedia の各 Pro League / Finals ページ（試合数・スコアは取れる）
- ApexLegendsStatus.com（より細かい統計が見られる可能性）
- ALGS 公式 (algs.ea.com) のマッチリンク先（生の Lobby データに近い）

調整候補（追加データで確認されたら適用したい方向性のメモ）:

- Americas: `strength_sigma` 0.55 → 0.45、`win_beta` 0.95 → 0.80、`placement_win_correlation` 0.60 → 0.50
- EMEA: `volatility_mean` 0.90 → 1.00、`consistency_beta` 0.55 → 0.45、`base_match_noise` 0.70 → 0.85
- APAC-N: 現状維持（実績 8 に対しシミュ 8.81 で誤差小）
- APAC-S: `volatility_mean` を下げる / `lost_kill_rate` を下げて短期化させる方向

ただしこれらはあくまで仮説で、Year 3 / Year 4 のサンプルで再現性を見てから判断する。

## 7. 引用ソース

- [Apex Legends Global Series: 2025 Championship - Finals (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2025/Championship/Finals)
- [Apex Legends Global Series: 2025 Midseason Playoffs - Finals (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2025/Midseason_Playoffs/Finals)
- [Apex Legends Global Series 2025 Split 1 Pro League - Americas (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2025/Split_1/Pro_League/Americas)
- [Apex Legends Global Series 2025 Split 1 Pro League - EMEA Final (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2025/Split_1/Pro_League/EMEA/Final)
- [Apex Legends Global Series 2025 Split 1 Pro League - APAC North Final (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2025/Split_1/Pro_League/APAC_North/Final)
- [Apex Legends Global Series 2025 Split 1 Pro League - APAC South Final (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2025/Split_1/Pro_League/APAC_South/Final)
- [Apex Legends Global Series 2025 Split 2 Pro League - Americas Final (Liquipedia)](https://liquipedia.net/apexlegends/Apex_Legends_Global_Series/2025/Split_2/Pro_League/Americas/Final)
- [GoNext clinch victory in ALGS Championship Year 4 (Dexerto)](https://www.dexerto.com/apex-legends/how-to-watch-algs-championship-year-4-stream-schedule-and-results-3039736/)
- [ALGS Scoring System Guide (Au Pro Circuit)](https://auprocircuit.com/algs-scoring-system-guide-au/)
- [Championship Points - ALGS Year 6 (Official EA)](https://algs.ea.com/en/championship-points)
