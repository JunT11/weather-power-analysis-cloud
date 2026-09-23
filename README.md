# 天気・電力データ分析ツール

気象情報から電力供給構成を予測するStreamlitアプリケーション

## 🌟 機能

### 1. グラフで確認してみよう
- CSVファイルのアップロード機能
- 気象データ（気温、降水量）の時系列グラフ表示
- 電力供給構成の可視化
- 年単位でのデータ分析

### 2. AIでデータを予測してみよう
- 予測対象日時の選択
- 気象条件（気温、降水量、風速、相対湿度、日射量、天気）の入力
- 機械学習モデルを使用した電力供給構成の予測
- 3つの発電方式の予測結果表示
  - 原子力発電
  - 火力発電
  - 太陽光発電

## 📍 対応地域

- **東京電力（Toden）**: 熊谷市の気象データを使用
- **東北電力（Tohoku）**: 仙台市の気象データを使用

各地域に最適化されたモデルで予測を行います。

## 📋 必要ファイル

### モデルファイル
- `model_toden_power_weather.pkl` - 東京電力用モデル
- `scaler_toden_power_weather.pkl` - 東京電力用スケーラー
- `feature_cols_toden.pkl` - 東京電力用特徴量情報
- `model_stats_toden.pkl` - 東京電力用統計情報

- `model_tohoku_power_weather.pkl` - 東北電力用モデル
- `scaler_tohoku_power_weather.pkl` - 東北電力用スケーラー
- `feature_cols_tohoku.pkl` - 東北電力用特徴量情報
- `model_stats_tohoku.pkl` - 東北電力用統計情報

## 🚀 実行方法

### 1. 必要なパッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. アプリの起動

```bash
streamlit run Weather_Analysis_Power_Prediction.py
```

ブラウザが自動的に開きます（http://localhost:8501）

### 3. 使用方法

#### グラフ表示
1. サイドバーで分析対象地域を選択（東京電力 or 東北電力）
2. CSVファイルをアップロード
3. グラフの年を選択して気象・電力データを確認

#### AI予測
1. 左側のパネルで予測日時を選択
2. 気象条件を入力
3. 「AI予測スタート」ボタンをクリック
4. 予測結果を確認

## 📊 入力パラメータ

### 日時情報
- 日付：2024年1月1日～2030年12月31日
- 時間：0～23時

### 気象条件
- 気温：0～40℃
- 降水量：0～50mm
- 風速：0～20m/s
- 相対湿度：0～100%
- 日射量：0～1000W/m²
- 天気：晴れ、曇り、雨、雪

## 📈 モデル性能

### 東京電力（Toden）
- テストデータ R²: 0.717
- 火力発電 R²: 0.864（高精度）
- 太陽光発電 R²: 0.842（高精度）

### 東北電力（Tohoku）
- テストデータ R²: 0.672
- 火力発電 R²: 0.839（高精度）
- 太陽光発電 R²: 0.819（高精度）

## 🔍 特徴量（重要度順）

1. **時間**（25～36%）
   - 需要パターンに最も大きく影響

2. **月**（20～23%）
   - 季節性による変動

3. **天気**（10～11%）
   - 気象条件の影響

4. **日射量**（9～10%）
   - 太陽光発電の直接的な要因

5. その他（気温、湿度、風速、降水量など）

## 📝 注意事項

- 予測は機械学習モデルの出力であり、実際の発電量と異なる場合があります
- 負の予測値が表示される場合は、実際には0MWとして解釈してください
- データクリーニングのため、欠損値を含むレコードは使用されません

## 📦 ファイル構成

```
Weather_Analysis_New/
├── Weather_Analysis_Power_Prediction.py
├── requirements.txt
├── README.md
├── model_toden_power_weather.pkl
├── scaler_toden_power_weather.pkl
├── feature_cols_toden.pkl
├── model_stats_toden.pkl
├── model_tohoku_power_weather.pkl
├── scaler_tohoku_power_weather.pkl
├── feature_cols_tohoku.pkl
└── model_stats_tohoku.pkl
```

## 🛠️ トラブルシューティング

### エラー: "No module named 'streamlit'"
```bash
pip install streamlit
```

### エラー: "モデルファイルが見つかりません"
- モデルファイル（.pkl）が正しく配置されているか確認
- ファイルはアプリと同じディレクトリにあるか確認

### エラー: "IndexError: string index out of range"
- CSVファイルの形式が正しいか確認
- 必須列（DateTime、気温、降水量など）が含まれているか確認

## 📧 問い合わせ

問題が発生した場合は、以下を確認してください：
- Python バージョン：3.8以上推奨
- 必要なパッケージがインストールされているか
- モデルファイルが正しくコピーされているか

## 📜 ライセンス

このツールはTAJ2HIGにより作成されました。

---

**最終更新**: 2026年9月9日
