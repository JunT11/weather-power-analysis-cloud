import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import joblib
import matplotlib.pyplot as plt

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Yu Gothic', 'Hiragino Sans']
plt.rcParams['axes.unicode_minus'] = False

# フォルダパスを設定
output_folder = Path(__file__).parent / "Output"
output_folder.mkdir(exist_ok=True)
weather_model_folder = output_folder / "Weather_Model"
weather_model_folder.mkdir(exist_ok=True)

print("="*70)
print("気象予測モデル作成 (気温、降水量、風速、相対湿度、日射量、天気)")
print("="*70)

# 入力特徴量（DateTime から抽出）
def extract_datetime_features(df):
    """DateTimeカラムから時間的特徴量を抽出"""
    df['DateTime'] = pd.to_datetime(df['DateTime'])
    
    df['hour'] = df['DateTime'].dt.hour
    df['day_of_week'] = df['DateTime'].dt.dayofweek
    df['month'] = df['DateTime'].dt.month
    df['day'] = df['DateTime'].dt.day
    
    # 季節を追加 (0: 冬, 1: 春, 2: 夏, 3: 秋)
    def get_season(month):
        if month in [12, 1, 2]:
            return 0  # 冬
        elif month in [3, 4, 5]:
            return 1  # 春
        elif month in [6, 7, 8]:
            return 2  # 夏
        else:
            return 3  # 秋
    
    df['season'] = df['month'].apply(get_season)
    
    # 周期的特徴量（三角関数で日内周期と年周期を表現）
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    
    return df

feature_columns = [
    'hour', 'day_of_week', 'month', 'day', 'season',
    'hour_sin', 'hour_cos', 'month_sin', 'month_cos', 'day_sin', 'day_cos'
]

# 出力（目的変数）
target_columns = ['気温', '降水量', '風速', '相対湿度', '日射量', '天気']

# ==========================================
# 1. 熊谷気象データ
# ==========================================
print("\n【1】熊谷気象データでモデルを構築中...")
print("-"*70)

kumagaya_file = output_folder / "weather_Kumagaya.csv"

try:
    df_kumagaya = pd.read_csv(kumagaya_file, encoding='utf-8-sig')
    
    print(f"  データ読み込み完了: {len(df_kumagaya)} 行")
    
    # DateTime特徴量を抽出
    df_kumagaya = extract_datetime_features(df_kumagaya)
    
    # 欠損値を確認
    print(f"  欠損値数:")
    missing_cols = df_kumagaya[feature_columns + target_columns].isnull().sum()
    for col, missing_count in missing_cols[missing_cols > 0].items():
        print(f"    - {col}: {missing_count}")
    
    # 欠損値を削除
    df_kumagaya_clean = df_kumagaya[feature_columns + target_columns].dropna()
    print(f"  欠損値除去後: {len(df_kumagaya_clean)} 行 (削除数: {len(df_kumagaya) - len(df_kumagaya_clean)})")
    
    # データの統計量を表示
    print(f"\n  目的変数の統計量:")
    for target in target_columns:
        stats = df_kumagaya_clean[target].describe()
        print(f"    {target}: mean={stats['mean']:.2f}, std={stats['std']:.2f}, min={stats['min']:.2f}, max={stats['max']:.2f}")
    
    # 特徴量と目的変数を分割
    X_kumagaya = df_kumagaya_clean[feature_columns]
    y_kumagaya = df_kumagaya_clean[target_columns]
    
    # 訓練データとテストデータに分割
    X_train_k, X_test_k, y_train_k, y_test_k = train_test_split(
        X_kumagaya, y_kumagaya, test_size=0.2, random_state=42
    )
    
    print(f"\n  訓練データ: {len(X_train_k)} 行, テストデータ: {len(X_test_k)} 行")
    
    # スケーリング
    scaler_k = StandardScaler()
    X_train_k_scaled = scaler_k.fit_transform(X_train_k)
    X_test_k_scaled = scaler_k.transform(X_test_k)
    
    # 各目的変数ごとにモデルを構築
    models_kumagaya = {}
    results_kumagaya = {}
    
    for target in target_columns:
        print(f"\n  【{target}】のモデルを構築中...")
        
        # ランダムフォレストモデルの構築
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=20,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        # 訓練
        model.fit(X_train_k_scaled, y_train_k[target])
        
        # テスト予測
        y_pred_test = model.predict(X_test_k_scaled)
        
        # 評価指標
        mse = mean_squared_error(y_test_k[target], y_pred_test)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test_k[target], y_pred_test)
        r2 = r2_score(y_test_k[target], y_pred_test)
        
        print(f"    - RMSE: {rmse:.4f}")
        print(f"    - MAE: {mae:.4f}")
        print(f"    - R²: {r2:.4f}")
        
        # 交差検証
        cv_scores = cross_val_score(
            model, X_train_k_scaled, y_train_k[target],
            cv=5, scoring='r2'
        )
        print(f"    - 交差検証 R² (5-fold): {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
        
        # 特徴量重要度
        feature_importance = pd.DataFrame({
            'feature': feature_columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print(f"    - Top 5 重要な特徴量:")
        for idx, row in feature_importance.head(5).iterrows():
            print(f"      {row['feature']}: {row['importance']:.4f}")
        
        # モデルと評価結果を保存
        models_kumagaya[target] = model
        results_kumagaya[target] = {
            'RMSE': rmse,
            'MAE': mae,
            'R2': r2,
            'CV_R2_mean': cv_scores.mean(),
            'CV_R2_std': cv_scores.std(),
            'feature_importance': feature_importance
        }
    
    # モデルを保存
    for target, model in models_kumagaya.items():
        model_file = weather_model_folder / f"model_kumagaya_{target.replace(' ', '_').replace('/', '_')}.pkl"
        joblib.dump(model, model_file)
        print(f"\n  ✓ モデル保存: {model_file}")
    
    # スケーラーを保存
    scaler_file = weather_model_folder / "scaler_kumagaya.pkl"
    joblib.dump(scaler_k, scaler_file)
    print(f"  ✓ スケーラー保存: {scaler_file}")
    
    # 結果サマリーをCSVに保存
    summary_data = []
    for target, results in results_kumagaya.items():
        summary_data.append({
            'Region': '熊谷',
            'Target': target,
            'RMSE': results['RMSE'],
            'MAE': results['MAE'],
            'R2': results['R2'],
            'CV_R2_mean': results['CV_R2_mean'],
            'CV_R2_std': results['CV_R2_std']
        })
    
    summary_kumagaya = pd.DataFrame(summary_data)
    summary_file_k = weather_model_folder / "results_kumagaya.csv"
    summary_kumagaya.to_csv(summary_file_k, index=False, encoding='utf-8-sig')
    print(f"  ✓ 結果保存: {summary_file_k}")

except Exception as e:
    print(f"  ✗ エラー: {str(e)}")
    import traceback
    traceback.print_exc()

# ==========================================
# 2. 仙台気象データ
# ==========================================
print("\n【2】仙台気象データでモデルを構築中...")
print("-"*70)

sendai_file = output_folder / "weather_Sendai.csv"

try:
    df_sendai = pd.read_csv(sendai_file, encoding='utf-8-sig')
    
    print(f"  データ読み込み完了: {len(df_sendai)} 行")
    
    # DateTime特徴量を抽出
    df_sendai = extract_datetime_features(df_sendai)
    
    # 欠損値を確認
    print(f"  欠損値数:")
    missing_cols = df_sendai[feature_columns + target_columns].isnull().sum()
    for col, missing_count in missing_cols[missing_cols > 0].items():
        print(f"    - {col}: {missing_count}")
    
    # 欠損値を削除
    df_sendai_clean = df_sendai[feature_columns + target_columns].dropna()
    print(f"  欠損値除去後: {len(df_sendai_clean)} 行 (削除数: {len(df_sendai) - len(df_sendai_clean)})")
    
    # データの統計量を表示
    print(f"\n  目的変数の統計量:")
    for target in target_columns:
        stats = df_sendai_clean[target].describe()
        print(f"    {target}: mean={stats['mean']:.2f}, std={stats['std']:.2f}, min={stats['min']:.2f}, max={stats['max']:.2f}")
    
    # 特徴量と目的変数を分割
    X_sendai = df_sendai_clean[feature_columns]
    y_sendai = df_sendai_clean[target_columns]
    
    # 訓練データとテストデータに分割
    X_train_s, X_test_s, y_train_s, y_test_s = train_test_split(
        X_sendai, y_sendai, test_size=0.2, random_state=42
    )
    
    print(f"\n  訓練データ: {len(X_train_s)} 行, テストデータ: {len(X_test_s)} 行")
    
    # スケーリング
    scaler_s = StandardScaler()
    X_train_s_scaled = scaler_s.fit_transform(X_train_s)
    X_test_s_scaled = scaler_s.transform(X_test_s)
    
    # 各目的変数ごとにモデルを構築
    models_sendai = {}
    results_sendai = {}
    
    for target in target_columns:
        print(f"\n  【{target}】のモデルを構築中...")
        
        # ランダムフォレストモデルの構築
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=20,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        # 訓練
        model.fit(X_train_s_scaled, y_train_s[target])
        
        # テスト予測
        y_pred_test = model.predict(X_test_s_scaled)
        
        # 評価指標
        mse = mean_squared_error(y_test_s[target], y_pred_test)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test_s[target], y_pred_test)
        r2 = r2_score(y_test_s[target], y_pred_test)
        
        print(f"    - RMSE: {rmse:.4f}")
        print(f"    - MAE: {mae:.4f}")
        print(f"    - R²: {r2:.4f}")
        
        # 交差検証
        cv_scores = cross_val_score(
            model, X_train_s_scaled, y_train_s[target],
            cv=5, scoring='r2'
        )
        print(f"    - 交差検証 R² (5-fold): {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
        
        # 特徴量重要度
        feature_importance = pd.DataFrame({
            'feature': feature_columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print(f"    - Top 5 重要な特徴量:")
        for idx, row in feature_importance.head(5).iterrows():
            print(f"      {row['feature']}: {row['importance']:.4f}")
        
        # モデルと評価結果を保存
        models_sendai[target] = model
        results_sendai[target] = {
            'RMSE': rmse,
            'MAE': mae,
            'R2': r2,
            'CV_R2_mean': cv_scores.mean(),
            'CV_R2_std': cv_scores.std(),
            'feature_importance': feature_importance
        }
    
    # モデルを保存
    for target, model in models_sendai.items():
        model_file = weather_model_folder / f"model_sendai_{target.replace(' ', '_').replace('/', '_')}.pkl"
        joblib.dump(model, model_file)
        print(f"\n  ✓ モデル保存: {model_file}")
    
    # スケーラーを保存
    scaler_file = weather_model_folder / "scaler_sendai.pkl"
    joblib.dump(scaler_s, scaler_file)
    print(f"  ✓ スケーラー保存: {scaler_file}")
    
    # 結果サマリーをCSVに保存
    summary_data = []
    for target, results in results_sendai.items():
        summary_data.append({
            'Region': '仙台',
            'Target': target,
            'RMSE': results['RMSE'],
            'MAE': results['MAE'],
            'R2': results['R2'],
            'CV_R2_mean': results['CV_R2_mean'],
            'CV_R2_std': results['CV_R2_std']
        })
    
    summary_sendai = pd.DataFrame(summary_data)
    summary_file_s = weather_model_folder / "results_sendai.csv"
    summary_sendai.to_csv(summary_file_s, index=False, encoding='utf-8-sig')
    print(f"  ✓ 結果保存: {summary_file_s}")

except Exception as e:
    print(f"  ✗ エラー: {str(e)}")
    import traceback
    traceback.print_exc()

# ==========================================
# 3. 結果の比較
# ==========================================
print("\n【3】結果の比較")
print("-"*70)

try:
    # 両方の結果を結合して表示
    all_results = pd.concat([summary_kumagaya, summary_sendai], ignore_index=True)
    
    print("\n全体的な結果サマリー:")
    print(all_results.to_string(index=False))
    
    # 地域別・目的変数別の平均R²を表示
    print("\n【R² スコアの比較】")
    pivot_r2 = all_results.pivot_table(
        values='R2', index='Target', columns='Region', aggfunc='first'
    )
    print(pivot_r2)
    
    # 全体結果を保存
    all_results_file = weather_model_folder / "results_all.csv"
    all_results.to_csv(all_results_file, index=False, encoding='utf-8-sig')
    print(f"\n✓ 全体結果保存: {all_results_file}")

except Exception as e:
    print(f"✗ 結果比較エラー: {str(e)}")

print("\n" + "="*70)
print("気象モデル作成完了！")
print("="*70)
print(f"\n保存先:")
print(f"  - モデルファイル: {weather_model_folder}")
print(f"  - 結果ファイル: {weather_model_folder}")
