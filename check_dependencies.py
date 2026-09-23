# Streamlitアプリケーションテスト用スクリプト

import sys
from pathlib import Path

# 必要なモジュールの確認
required_modules = ['streamlit', 'pandas', 'numpy', 'plotly', 'sklearn', 'PIL', 'matplotlib']

print("必要なモジュールのチェック...")
print("-" * 50)

missing_modules = []
for module_name in required_modules:
    try:
        __import__(module_name)
        print(f"✓ {module_name} - インストール済み")
    except ImportError:
        print(f"✗ {module_name} - インストールが必要")
        missing_modules.append(module_name)

print("-" * 50)

# モデルファイルの確認
print("\nモデルファイルのチェック...")
print("-" * 50)

work_dir = Path(__file__).parent
model_files = [
    'model_toden_power_weather.pkl',
    'scaler_toden_power_weather.pkl',
    'feature_cols_toden.pkl',
    'model_stats_toden.pkl',
    'model_tohoku_power_weather.pkl',
    'scaler_tohoku_power_weather.pkl',
    'feature_cols_tohoku.pkl',
    'model_stats_tohoku.pkl',
]

for file in model_files:
    file_path = work_dir / file
    if file_path.exists():
        file_size = file_path.stat().st_size / (1024 * 1024)  # MB
        print(f"✓ {file} ({file_size:.2f} MB)")
    else:
        print(f"✗ {file} - ファイルが見つかりません")

print("-" * 50)

if missing_modules:
    print(f"\n⚠️  {len(missing_modules)}個のモジュールがインストールされていません:")
    for module in missing_modules:
        print(f"   pip install {module}")
    sys.exit(1)
else:
    print("\n✅ すべてのモジュールがインストールされています")
    print("✅ すべてのモデルファイルが配置されています")
    print("\nStreamlitアプリケーションを実行できます:")
    print("  streamlit run Weather_Analysis_Power_Prediction.py")
