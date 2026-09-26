# -*- coding: utf-8 -*-
"""
Weather & Power Data Analysis and Prediction Tool
Author: TAJ2HIG
Date: 2026-09-09

気象情報と電力供給データを分析・予測するツール

【セクション2-2の予測モデル仕様】
- 入力値：火力発電（合計）+ 太陽光発電 + 日時情報
- 出力：原子力・風力・水力の発電量を予測
- 気象情報（気温、降水量、風速等）は使用しない
- 火力は個別種類（LNG、石炭、石油）ではなく合計値から計算
"""

import streamlit as st
import pandas as pd
import numpy as np
import pickle
import joblib
import datetime
import plotly.graph_objects as go
from pathlib import Path
import hashlib
from datetime import datetime as dt
import warnings
import os

# ==================================================================================
# Suppress scikit-learn version warnings
# ==================================================================================
warnings.filterwarnings('ignore', category=Warning, module='sklearn')
warnings.filterwarnings('ignore', message='Trying to unpickle estimator')

# ==================================================================================
# Path Configuration for Streamlit Cloud Compatibility
# ==================================================================================
def get_base_dir():
    """
    Streamlit Cloud と ローカル環境の両方に対応したベースディレクトリを取得
    """
    try:
        # Streamlit Cloud環境での正確なパス処理
        script_dir = Path(__file__).resolve().parent
    except:
        # フォールバック: OSのカレントディレクトリを使用
        script_dir = Path(os.getcwd())
    return script_dir

BASE_DIR = get_base_dir()

# ==================================================================================
# Constants and Lists
# ==================================================================================

Weekday_List = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]

# モデル情報
MODELS = {
    "東京電力（Toden）": {
        "suffix": "toden",
        "location": "熊谷",
        "color": "rgb(220, 53, 69)",  # 赤系
        "csv_file": "all_data_Kumagaya.csv"
    },
    "東北電力（Tohoku）": {
        "suffix": "tohoku",
        "location": "仙台",
        "color": "rgb(0, 102, 204)",  # 青系
        "csv_file": "all_data_Sendai.csv"
    }
}

# ==================================================================================
# Functions
# ==================================================================================

@st.cache_resource
def load_models_and_data(model_suffix):
    """
    モデルとスケーラーをロード
    複数ユーザー間で安全に共用できる
    """
    work_dir = BASE_DIR
    
    model_file = work_dir / f"model_{model_suffix}_power_weather.pkl"
    scaler_file = work_dir / f"scaler_{model_suffix}_power_weather.pkl"
    feature_file = work_dir / f"feature_cols_{model_suffix}.pkl"
    
    with open(model_file, 'rb') as f:
        model = pickle.load(f)
    with open(scaler_file, 'rb') as f:
        scaler = pickle.load(f)
    with open(feature_file, 'rb') as f:
        feature_cols = pickle.load(f)
    
    return model, scaler, feature_cols


def load_power_prediction_models(location_name):
    """
    火力合計と太陽光から他の発電源を予測するモデルをロード
    
    【モデルの特徴】
    - 火力は個別データ（LNG、石炭、石油）ではなく合計値のみを使用
    - 気象情報・時系列情報（気温、降水量、風速等）は使用しない
    - 入力特徴量：火力合計、太陽光のみ（2次元）
    - 各モデルはRandomForestRegressorで訓練
    
    Parameters:
    -----------
    location_name : str
        地域名（kumagaya または sendai）
    
    Returns:
    --------
    models_dict : dict
        原子力、風力、水力のモデル辞書
    scaler : StandardScaler
        火力と太陽光の標準化用スケーラー（2次元）
    """
    work_dir = BASE_DIR / "models"
    
    models_dict = {}
    
    # 各発電源のモデルをロード
    model_types = ['原子力', '風力発電実績', '水力']
    for model_type in model_types:
        model_file = work_dir / f"model_{location_name}_{model_type}.pkl"
        try:
            # joblib でロード（picklefile）
            models_dict[model_type] = joblib.load(model_file)
        except FileNotFoundError:
            st.error(f"❌ モデルファイルが見つかりません: {model_file}")
            models_dict[model_type] = None
        except Exception as e:
            st.error(f"❌ モデルのロードに失敗しました（{model_type}）: {str(e)}")
            models_dict[model_type] = None
    
    # スケーラーをロード
    scaler_file = work_dir / f"scaler_{location_name}.pkl"
    try:
        scaler = joblib.load(scaler_file)
    except FileNotFoundError:
        st.error(f"❌ スケーラーファイルが見つかりません: {scaler_file}")
        scaler = None
    except Exception as e:
        st.error(f"❌ スケーラーのロードに失敗しました: {str(e)}")
        scaler = None
    
    return models_dict, scaler


@st.cache_data(ttl=3600)
def load_csv_data(csv_path):
    """
    CSVファイルをロード＆前処理
    ファイルパスで自動キャッシング（1時間）
    複数ユーザーで効率的に共有
    """
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    return _preprocess_dataframe(df)


def _preprocess_dataframe(df):
    """
    DataFrameを前処理（内部用）
    """
    df = df.copy()
    
    # DateTime列の処理
    if 'DateTime' in df.columns:
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        df['date'] = df['DateTime'].dt.date
        df['hour'] = df['DateTime'].dt.hour
        df['day_str'] = df['DateTime'].dt.strftime('%Y-%m-%d')
        df['month_str'] = df['DateTime'].dt.strftime('%y/%m')
    
    # 火力発電の合計を計算（LNG+石炭+石油+その他）
    thermal_cols = ['火力(LNG)', '火力(石炭)', '火力(石油)', '火力(その他)']
    available_thermal_cols = [col for col in thermal_cols if col in df.columns]
    if available_thermal_cols:
        df['火力_合計'] = df[available_thermal_cols].sum(axis=1)
    
    return df


def predict_power_generation(model, scaler, feature_cols, input_data):
    """
    モデルを使用して電力生成を予測
    
    Parameters:
    -----------
    model : trained model
        訓練済みモデル
    scaler : StandardScaler
        特徴量の標準化用スケーラー
    feature_cols : list
        特徴量の列名リスト
    input_data : dict
        入力データ（気象条件）
    
    Returns:
    --------
    predictions : ndarray
        3つの発電方式の予測値 [原子力, 火力, 太陽光]
    """
    # 入力データを特徴量の順序に合わせて配列に変換
    X = np.array([
        input_data['気温'],
        input_data['降水量'],
        input_data['風速'],
        input_data['相対湿度'],
        input_data['日射量'],
        input_data['天気_encoded'],
        input_data['月'],
        input_data['時間'],
        input_data['曜日'],
        input_data['日'],
        input_data['季節']
    ]).reshape(1, -1)
    
    # 標準化
    X_scaled = scaler.transform(X)
    
    # 予測
    predictions = model.predict(X_scaled)
    
    return predictions[0]


def predict_from_thermal_solar(models_dict, scaler, thermal_value, solar_value, input_data):
    """
    火力合計と太陽光から、原子力・風力・水力を予測
    
    【モデル仕様】
    - 入力特徴量：火力発電量（合計）、太陽光発電量のみ（2次元）
    - 気象情報・時系列情報は未使用
    - 火力は個別の種類（LNG、石炭、石油）ではなく合計値から予測
    
    Parameters:
    -----------
    models_dict : dict
        各発電源のモデル辞書（原子力、風力発電実績、水力）
    scaler : StandardScaler
        火力と太陽光の標準化用スケーラー（2次元）
    thermal_value : float
        火力発電量（合計） (MW)
    solar_value : float
        太陽光発電量 (MW)
    input_data : dict
        時系列データ（月、時間、曜日、日）
        ※ 気象情報は不要、ただし将来の拡張用に保持
    
    Returns:
    --------
    predictions : dict
        予測結果の辞書 {原子力: value, 風力発電実績: value, 水力: value}
    """
    predictions = {}
    
    # 入力特徴量：火力と太陽光のみ（2次元）
    X = np.array([
        thermal_value,
        solar_value
    ]).reshape(1, -1)
    
    # スケーラーで正規化
    if scaler is not None:
        try:
            # フィーチャー名の警告を抑制
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', message='X does not have valid feature names')
                X_scaled = scaler.transform(X)
        except Exception as e:
            st.warning(f"⚠️ スケーラー変換に失敗しました: {str(e)}")
            X_scaled = X
    else:
        X_scaled = X
    
    # 各モデルで予測
    for model_type, model in models_dict.items():
        if model is not None:
            try:
                pred = model.predict(X_scaled)
                predictions[model_type] = max(0, float(pred[0]))
            except Exception as e:
                st.warning(f"⚠️ {model_type}の予測に失敗しました: {str(e)}")
                predictions[model_type] = 0.0
        else:
            predictions[model_type] = 0.0
    
    return predictions


def get_season(month):
    """月から季節を取得"""
    if month in [12, 1, 2]:
        return 0  # 冬
    elif month in [3, 4, 5]:
        return 1  # 春
    elif month in [6, 7, 8]:
        return 2  # 夏
    else:
        return 3  # 秋


def load_weather_prediction_models(location_name):
    """
    日時から気象情報を予測するモデルをロード
    
    Parameters:
    -----------
    location_name : str
        地域名（kumagaya または sendai）
    
    Returns:
    --------
    models_dict : dict
        各気象要素のモデル辞書（気温、相対湿度、降水量、風速、日射量、天気）
    scaler : StandardScaler
        特徴量の標準化用スケーラー
    """
    work_dir = BASE_DIR / "Weather_Model"
    
    models_dict = {}
    
    # 各気象要素のモデルをロード
    weather_elements = ['気温', '相対湿度', '降水量', '風速', '日射量', '天気']
    for element in weather_elements:
        model_file = work_dir / f"model_{location_name}_{element}.pkl"
        try:
            models_dict[element] = joblib.load(model_file)
        except FileNotFoundError:
            st.error(f"❌ モデルファイルが見つかりません: {model_file}")
            models_dict[element] = None
        except Exception as e:
            st.error(f"❌ モデルのロードに失敗しました（{element}）: {str(e)}")
            models_dict[element] = None
    
    # スケーラーをロード
    scaler_file = work_dir / f"scaler_{location_name}.pkl"
    try:
        scaler = joblib.load(scaler_file)
    except FileNotFoundError:
        st.error(f"❌ スケーラーファイルが見つかりません: {scaler_file}")
        scaler = None
    except Exception as e:
        st.error(f"❌ スケーラーのロードに失敗しました: {str(e)}")
        scaler = None
    
    return models_dict, scaler


def predict_weather_from_datetime(models_dict, scaler, year, month, day, hour):
    """
    日時から気象情報を予測
    
    訓練時の特徴量（順序が重要）：
    0: hour, 1: day_of_week, 2: month, 3: day, 4: season,
    5: hour_sin, 6: hour_cos, 7: month_sin, 8: month_cos, 9: day_sin, 10: day_cos
    
    Parameters:
    -----------
    models_dict : dict
        各気象要素のモデル辞書
    scaler : StandardScaler
        特徴量の標準化用スケーラー
    year : int
        年
    month : int
        月（1-12）
    day : int
        日（1-31）
    hour : int
        時間（0-23）
    
    Returns:
    --------
    predictions : dict
        予測結果の辞書 {気温: value, 相対湿度: value, ...}
    """
    predictions = {}
    debug_info = {}
    
    # 曜日を計算
    date_obj = datetime.date(year, month, day)
    day_of_week = date_obj.weekday()
    season = get_season(month)
    
    # 三角関数特徴量を計算
    hour_sin = np.sin(2 * np.pi * hour / 24)
    hour_cos = np.cos(2 * np.pi * hour / 24)
    month_sin = np.sin(2 * np.pi * month / 12)
    month_cos = np.cos(2 * np.pi * month / 12)
    day_sin = np.sin(2 * np.pi * day_of_week / 7)
    day_cos = np.cos(2 * np.pi * day_of_week / 7)
    
    # 訓練時の特徴量順序に従ってX行列を構築
    # [hour, day_of_week, month, day, season, hour_sin, hour_cos, month_sin, month_cos, day_sin, day_cos]
    X = np.array([
        hour,
        day_of_week,
        month,
        day,
        season,
        hour_sin,
        hour_cos,
        month_sin,
        month_cos,
        day_sin,
        day_cos
    ]).reshape(1, -1)
    
    # デバッグ情報に入力値を保存
    debug_info['input_raw'] = X[0].tolist()
    
    # スケーラーで正規化
    if scaler is not None:
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', message='X does not have valid feature names')
                X_scaled = scaler.transform(X)
        except Exception as e:
            st.warning(f"⚠️ スケーラー変換に失敗しました: {str(e)}")
            X_scaled = X
    else:
        X_scaled = X
    
    debug_info['input_scaled'] = X_scaled[0].tolist()
    
    # セッション状態にデバッグ情報を保存
    st.session_state['weather_debug_info'] = debug_info
    
    # 各気象要素で予測
    weather_elements = ['気温', '相対湿度', '降水量', '風速', '日射量', '天気']
    
    # 予測実行
    for element in weather_elements:
        model = models_dict.get(element)
        if model is not None:
            try:
                pred = model.predict(X_scaled)
                value = float(pred[0])
                # 値の制限
                if element == '相対湿度':
                    value = max(0, min(100, value))
                elif element == '天気':
                    value = max(0, min(1, value))
                else:
                    value = max(0, value)
                predictions[element] = value
            except Exception as e:
                st.warning(f"⚠️ {element}の予測に失敗しました: {str(e)}")
                predictions[element] = 0.0
        else:
            predictions[element] = 0.0
    
    return predictions


def get_model_combination_name(show_nuclear, show_thermal, show_hydro, show_solar, show_wind):
    """
    チェックボックスの状態から、対応するモデルの組み合わせ名を取得
    
    Parameters:
    -----------
    show_nuclear : bool
        原子力を選択
    show_thermal : bool
        火力を選択
    show_hydro : bool
        水力を選択
    show_solar : bool
        太陽光発電実績を選択
    show_wind : bool
        風力発電実績を選択
    
    Returns:
    --------
    combination_name : str
        モデルファイル名に使用される組み合わせ名（例：'原子力_火力'）
        または None（何も選択されていない場合）
    """
    # 選択された発電方式を順序を保ってリスト化
    # 順序：原子力 → 火力 → 水力 → 太陽光発電実績 → 風力発電実績
    selected = []
    
    if show_nuclear:
        selected.append('原子力')
    if show_thermal:
        selected.append('火力')
    if show_hydro:
        selected.append('水力')
    if show_solar:
        selected.append('太陽光発電実績')
    if show_wind:
        selected.append('風力発電実績')
    
    if not selected:
        return None
    
    return '_'.join(selected)


# Combine_Modelの組み合わせと番号のマッピング
COMBINATION_NUMBER_MAP = {
    "原子力": "01",
    "火力": "02",
    "水力": "03",
    "太陽光発電実績": "04",
    "風力発電実績": "05",
    "原子力_火力": "06",
    "原子力_水力": "07",
    "原子力_太陽光発電実績": "08",
    "原子力_風力発電実績": "09",
    "火力_水力": "10",
    "火力_太陽光発電実績": "11",
    "火力_風力発電実績": "12",
    "水力_太陽光発電実績": "13",
    "水力_風力発電実績": "14",
    "太陽光発電実績_風力発電実績": "15",
    "原子力_火力_水力": "16",
    "原子力_火力_太陽光発電実績": "17",
    "原子力_火力_風力発電実績": "18",
    "原子力_水力_太陽光発電実績": "19",
    "原子力_水力_風力発電実績": "20",
    "原子力_太陽光発電実績_風力発電実績": "21",
    "火力_水力_太陽光発電実績": "22",
    "火力_水力_風力発電実績": "23",
    "火力_太陽光発電実績_風力発電実績": "24",
    "水力_太陽光発電実績_風力発電実績": "25",
    "原子力_火力_水力_太陽光発電実績": "26",
    "原子力_火力_水力_風力発電実績": "27",
    "原子力_火力_太陽光発電実績_風力発電実績": "28",
    "原子力_水力_太陽光発電実績_風力発電実績": "29",
    "火力_水力_太陽光発電実績_風力発電実績": "30",
    "原子力_火力_水力_太陽光発電実績_風力発電実績": "31",
}


def load_combine_model(location_name, combination_name):
    """
    Combine_Modelフォルダからモデルをロード
    
    Parameters:
    -----------
    location_name : str
        地域名（kumagaya または sendai）
    combination_name : str
        組み合わせ名（例：'原子力_火力'）
    
    Returns:
    --------
    model : trained model
        訓練済みモデル
    scaler : StandardScaler
        特徴量の標準化用スケーラー
    feature_names : list
        出力特徴量の名前
    """
    work_dir = BASE_DIR / "Combine_Model"
    
    # モデルサフィックスを決定
    model_suffix = "toden" if location_name == "kumagaya" else "tohoku"
    
    # 組み合わせ名から番号を取得
    number = COMBINATION_NUMBER_MAP.get(combination_name)
    if number is None:
        st.error(f"❌ 不正な組み合わせです: {combination_name}")
        return None, None, None
    
    # モデルファイルをロード
    model_file = work_dir / f"model_{model_suffix}_{number}_{combination_name}.pkl"
    try:
        model = joblib.load(model_file)
    except FileNotFoundError:
        st.error(f"❌ モデルファイルが見つかりません: {model_file}")
        return None, None, None
    except Exception as e:
        st.error(f"❌ モデルのロードに失敗しました: {str(e)}")
        return None, None, None
    
    # スケーラーをロード
    scaler_file = work_dir / f"scaler_{model_suffix}_{number}_{combination_name}.pkl"
    try:
        scaler = joblib.load(scaler_file)
    except FileNotFoundError:
        st.warning(f"⚠️ スケーラーが見つかりません: {scaler_file}")
        scaler = None
    except Exception as e:
        st.warning(f"⚠️ スケーラーのロードに失敗しました: {str(e)}")
        scaler = None
    
    # 特徴量名をJSONから取得
    info_file = work_dir / f"info_{model_suffix}_{number}_{combination_name}.json"
    feature_names = None
    try:
        import json
        with open(info_file, 'r', encoding='utf-8') as f:
            info = json.load(f)
            # target_comboキーから出力特徴量を取得
            feature_names = info.get('target_combo', combination_name.split('_'))
    except Exception as e:
        # JSONが見つからない場合は、combination_nameから推測
        feature_names = combination_name.split('_')
    
    return model, scaler, feature_names


def predict_combine_model(model, scaler, input_data):
    """
    Combine_Modelを使用して予測
    
    Parameters:
    -----------
    model : trained model
        訓練済みモデル
    scaler : StandardScaler
        特徴量の標準化用スケーラー
    input_data : dict
        入力データ（気象条件と日時情報）
        キー：気温、降水量、風速、相対湿度、日射量、天気_encoded、月、時間、曜日、日、季節
    
    Returns:
    --------
    predictions : ndarray
        予測値
    """
    # 三角関数特徴量を計算
    hour = input_data['時間']
    month = input_data['月']
    
    hour_sin = np.sin(2 * np.pi * hour / 24)
    hour_cos = np.cos(2 * np.pi * hour / 24)
    month_sin = np.sin(2 * np.pi * month / 12)
    month_cos = np.cos(2 * np.pi * month / 12)
    
    X = np.array([
        input_data['気温'],
        input_data['降水量'],
        input_data['風速'],
        input_data['相対湿度'],
        input_data['日射量'],
        input_data['月'],
        input_data['時間'],
        input_data['曜日'],
        input_data['日'],
        input_data['季節'],
        hour_sin,
        hour_cos,
        month_sin,
        month_cos
    ]).reshape(1, -1)
    
    # スケーラーで正規化
    if scaler is not None:
        try:
            X_scaled = scaler.transform(X)
        except Exception as e:
            X_scaled = X
    else:
        X_scaled = X
    
    # 予測実行
    predictions = model.predict(X_scaled)
    
    return predictions[0]


# ==================================================================================
# Session State Initialization
# ==================================================================================

def init_session_state():
    """
    セッション状態を初期化
    複数のユーザーを安全に処理
    """
    if "current_region" not in st.session_state:
        st.session_state.current_region = "東京電力（Toden）"
    if "df_cache" not in st.session_state:
        st.session_state.df_cache = {}
    if "session_id" not in st.session_state:
        # 各セッションに一意のIDを付与
        session_id = hashlib.md5(str(dt.now()).encode()).hexdigest()[:8]
        st.session_state.session_id = session_id


# ==================================================================================
# Main App
# ==================================================================================

def main():
    ### Page Configuration ###
    st.set_page_config(
        page_title="天気・電力データ分析ツール",
        page_icon="⚡",
        layout="wide",
    )
    
    # セッション状態の初期化
    init_session_state()
    
    st.title("⚡ 天気・電力データ分析ツール")
    st.markdown("気象情報から電力供給構成を予測します")
    
    # デフォルト設定（東京電力（Toden））
    selected_region = "東京電力（Toden）"
    model_config = MODELS[selected_region]
    model_suffix = model_config["suffix"]
    location = model_config["location"]
    
    # ==================================================================================
    # Load Models
    # ==================================================================================
    model, scaler, feature_cols = load_models_and_data(model_suffix)
    
    # ==================================================================================
    # Section 1: Graph Display
    # ==================================================================================
    st.header("📊 グラフで確認してみよう")
    
    with st.container(border=True):
        st.subheader("1-1. データを読み込む")
        
        uploaded_file = st.file_uploader(
            "CSVファイルをアップロードしてください",
            type="csv",
            help="dataフォルダ内のCSVファイルを選択してください"
        )
        
        df = None
        
        if uploaded_file is not None:
            try:
                df = _preprocess_dataframe(pd.read_csv(uploaded_file, encoding='utf-8-sig'))
                st.success(f"✓ {uploaded_file.name} が読み込まれました（{len(df)}件）")
                # ファイル名をsession_stateに保存（後続セクションで使用）
                st.session_state.uploaded_file_name = uploaded_file.name
            except Exception as e:
                st.error(f"❌ ファイルの読み込みに失敗しました: {str(e)}")
        
        if df is not None:
            
            st.subheader("1-2. 一年間のデータの変化")

            # 年を選択
            years = sorted(df['DateTime'].dt.year.unique())
            if len(years) > 0:
                # デフォルトを2024年にする
                default_year = 2024
                default_index = years.index(default_year) if default_year in years else 0

                selected_year = st.selectbox(
                    "確認したい年を選択",
                    years,
                    index=default_index
                )
                df_year = df[df['DateTime'].dt.year == selected_year]
            
                st.write(f"📅 {selected_year}年のデータを表示中（{len(df_year)}件）")
                
                # グラフ表示
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=df_year['DateTime'],
                    y=df_year['気温'],
                    line=dict(color='orange', width=2),
                    name='気温(℃)',
                    yaxis='y1'
                ))
                
                fig.add_trace(go.Scatter(
                    x=df_year['DateTime'],
                    y=df_year['降水量'],
                    line=dict(color='blue', width=2),
                    name='降水量(mm)',
                    yaxis='y2'
                ))
                
                fig.update_layout(
                    title=f'{selected_year}年の気象データ',
                    xaxis_title='日時',
                    yaxis1=dict(
                        title='気温(℃)',
                        side='left',
                        showgrid=True
                    ),
                    yaxis2=dict(
                        title='降水量(mm)',
                        side='right',
                        overlaying='y1'
                    ),
                    plot_bgcolor='white',
                    hovermode='x unified',
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 発電データがある場合は表示
                power_cols = ['原子力', '火力_合計', '太陽光発電実績']
                available_power_cols = [col for col in power_cols if col in df.columns]
            
            # 1日のデータを比較する
            st.subheader("1-3. 1日のデータを比較しよう")
            
            # 日付の範囲を取得
            min_date_data = df['DateTime'].min().date()
            max_date_data = df['DateTime'].max().date()
            
            col1, col2 = st.columns(2)
            with col1:
                date_1 = st.date_input(
                    '比較する1つ目の日付',
                    min_date_data,
                    min_value=min_date_data,
                    max_value=max_date_data,
                    key="date_1_comparison"
                )
            with col2:
                date_2 = st.date_input(
                    '比較する2つ目の日付',
                    min_date_data + datetime.timedelta(days=1),
                    min_value=min_date_data,
                    max_value=max_date_data,
                    key="date_2_comparison"
                )
            
            # データフィルタリング
            df_cut_1day_1 = df[df['day_str'] == str(date_1)]
            df_cut_1day_2 = df[df['day_str'] == str(date_2)]
            
            if date_1 == date_2:
                st.warning(f"⚠️ {date_1}と{date_2}を別日に設定してください。比較できません")
            else:
                st.info(f"📅 {date_1}と{date_2}を比較しています")
                
                # 2つの日付のグラフを横並びで表示
                col1, col2 = st.columns(2)
                
                with col1:
                    if len(df_cut_1day_1) > 0:
                        st.subheader(f"{date_1}の気象データ")
                        # 気温と降水量の折れ線グラフ
                        fig_weather_1 = go.Figure()
                        fig_weather_1.add_trace(go.Scatter(
                            x=df_cut_1day_1['hour'],
                            y=df_cut_1day_1['気温'],
                            name='気温(℃)',
                            line=dict(color='orange', width=2),
                            yaxis='y1'
                        ))
                        fig_weather_1.add_trace(go.Scatter(
                            x=df_cut_1day_1['hour'],
                            y=df_cut_1day_1['降水量'],
                            name='降水量(mm)',
                            line=dict(color='blue', width=2),
                            yaxis='y2'
                        ))
                        fig_weather_1.update_layout(
                            title=f'{date_1}の気象データ',
                            xaxis_title='時間',
                            yaxis1=dict(
                                title='気温(℃)',
                                side='left',
                                showgrid=True,
                                range=[-15, 40]
                            ),
                            yaxis2=dict(
                                title='降水量(mm)',
                                side='right',
                                overlaying='y1',
                                range=[0, 50]
                            ),
                            legend=dict(
                                x=0.02,
                                y=0.98,
                                xanchor='left',
                                yanchor='top',
                                bgcolor='rgba(255, 255, 255, 0.8)',
                                bordercolor='gray',
                                borderwidth=1
                            ),
                            plot_bgcolor='white',
                            hovermode='x unified',
                            height=400
                        )
                        st.plotly_chart(fig_weather_1, use_container_width=True)
                        
                        st.subheader(f"{date_1}の電力供給構成")
                        fig1 = go.Figure()
                        
                        for col in available_power_cols:
                            fig1.add_trace(go.Bar(
                                x=df_cut_1day_1['hour'],
                                y=df_cut_1day_1[col],
                                name=col,
                                text=df_cut_1day_1[col].round(0),
                                textposition='auto',
                            ))
                        
                        fig1.update_layout(
                            barmode='stack',
                            title=f'{date_1}の電力供給構成',
                            xaxis_title='時間',
                            yaxis_title='発電量',
                            yaxis=dict(range=[0, 50000]),
                            plot_bgcolor='white',
                            hovermode='x unified',
                            height=400
                        )
                        
                        st.plotly_chart(fig1, use_container_width=True)
                        
                        # データテーブル
                        st.write(f"**{date_1}のデータ**")
                        display_cols = ['hour'] + available_power_cols
                        display_df = df_cut_1day_1[display_cols].copy()
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                    else:
                        st.warning(f"⚠️ {date_1}のデータが見つかりません")
                
                with col2:
                    if len(df_cut_1day_2) > 0:
                        st.subheader(f"{date_2}の気象データ")
                        # 気温と降水量の折れ線グラフ
                        fig_weather_2 = go.Figure()
                        fig_weather_2.add_trace(go.Scatter(
                            x=df_cut_1day_2['hour'],
                            y=df_cut_1day_2['気温'],
                            name='気温(℃)',
                            line=dict(color='orange', width=2),
                            yaxis='y1'
                        ))
                        fig_weather_2.add_trace(go.Scatter(
                            x=df_cut_1day_2['hour'],
                            y=df_cut_1day_2['降水量'],
                            name='降水量(mm)',
                            line=dict(color='blue', width=2),
                            yaxis='y2'
                        ))
                        fig_weather_2.update_layout(
                            title=f'{date_2}の気象データ',
                            xaxis_title='時間',
                            yaxis1=dict(
                                title='気温(℃)',
                                side='left',
                                showgrid=True,
                                range=[-15, 40]
                            ),
                            yaxis2=dict(
                                title='降水量(mm)',
                                side='right',
                                overlaying='y1',
                                range=[0, 50]
                            ),
                            legend=dict(
                                x=0.02,
                                y=0.98,
                                xanchor='left',
                                yanchor='top',
                                bgcolor='rgba(255, 255, 255, 0.8)',
                                bordercolor='gray',
                                borderwidth=1
                            ),
                            plot_bgcolor='white',
                            hovermode='x unified',
                            height=400
                        )
                        st.plotly_chart(fig_weather_2, use_container_width=True)
                        
                        st.subheader(f"{date_2}の電力供給構成")
                        fig2 = go.Figure()
                        
                        for col in available_power_cols:
                            fig2.add_trace(go.Bar(
                                x=df_cut_1day_2['hour'],
                                y=df_cut_1day_2[col],
                                name=col,
                                text=df_cut_1day_2[col].round(0),
                                textposition='auto',
                            ))
                        
                        fig2.update_layout(
                            barmode='stack',
                            title=f'{date_2}の電力供給構成',
                            xaxis_title='時間',
                            yaxis_title='発電量',
                            yaxis=dict(range=[0, 50000]),
                            plot_bgcolor='white',
                            hovermode='x unified',
                            height=400
                        )
                        
                        st.plotly_chart(fig2, use_container_width=True)
                        
                        # データテーブル
                        st.write(f"**{date_2}のデータ**")
                        display_cols = ['hour'] + available_power_cols
                        display_df = df_cut_1day_2[display_cols].copy()
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                    else:
                        st.warning(f"⚠️ {date_2}のデータが見つかりません")
    
    # ==================================================================================
    # Section 2: AI Prediction
    # ==================================================================================
    st.header("🤖 AIでデータを予測してみよう")
    
    # ==================================================================================
    # Section 2-1: Predict Weather from DateTime
    # ==================================================================================
    if df is not None:
        with st.container(border=True):
            st.subheader("2-1. 日時から気象情報を予測")
            
            st.info(
                "**予測モデルの仕様**\n\n"
                "• 入力値：年、月、日、時間\n"
                "• 出力：気温、相対湿度、降水量、風速、日射量、天気を予測\n"
                "• 機械学習モデルによる時系列予測"
            )
            
            # アップロードされたファイル名からlocation_nameを決定
            location_mapping = {
                "all_data_Kumagaya.csv": "kumagaya",
                "all_data_Sendai.csv": "sendai"
            }
            
            location_name = None
            
            # session_stateからアップロードされたファイル名を取得
            if 'uploaded_file_name' in st.session_state:
                uploaded_file_name = st.session_state.uploaded_file_name
                for csv_name, loc_name in location_mapping.items():
                    if csv_name in uploaded_file_name:
                        location_name = loc_name
                        break
            
            # location_nameが決定されない場合はデフォルト
            if location_name is None:
                location_name = "kumagaya"
            
            location_display = "熊谷（東京電力）" if location_name == "kumagaya" else "仙台（東北電力）"
            st.info(f"📍 {location_display}のモデルを使用します")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**日時情報を入力**")
                
                pred_year = st.number_input(
                    '年',
                    min_value=2026,
                    max_value=2040,
                    value=2026,
                    step=1,
                    key="weather_pred_year"
                )
                
                pred_month = st.selectbox(
                    '月',
                    list(range(1, 13)),
                    index=9,  # デフォルト10月
                    key="weather_pred_month",
                    format_func=lambda x: f"{x:02d}月"
                )
                
                pred_day = st.number_input(
                    '日',
                    min_value=1,
                    max_value=31,
                    value=1,
                    step=1,
                    key="weather_pred_day"
                )
                
                pred_hour = st.selectbox(
                    '時間',
                    list(range(24)),
                    index=12,  # デフォルト12時
                    key="weather_pred_hour",
                    format_func=lambda x: f"{x:02d}:00"
                )
            
            with col2:
                st.write("**入力した日時**")
                try:
                    date_obj = datetime.date(int(pred_year), int(pred_month), int(pred_day))
                    weekday_jp = Weekday_List[date_obj.weekday()]
                    st.info(
                        f"🗓️ {date_obj.strftime('%Y年%m月%d日')} "
                        f"{int(pred_hour):02d}:00\n\n"
                        f"曜日：{weekday_jp}"
                    )
                except ValueError:
                    st.warning("⚠️ 無効な日付です（例：2月30日など）")
            
            # 予測ボタン
            if st.button("🔮 気象を予測", key=f"predict_weather_{location_name}", use_container_width=True):
                try:
                    # モデルをロード
                    models_dict, scaler = load_weather_prediction_models(location_name)
                    
                    if all(v is not None for v in models_dict.values()) and scaler is not None:
                        # 予測実行
                        weather_pred = predict_weather_from_datetime(
                            models_dict,
                            scaler,
                            int(pred_year),
                            int(pred_month),
                            int(pred_day),
                            int(pred_hour)
                        )
                        
                        st.success("✓ 気象予測が完了しました")
                        
                        # デバッグ情報：入力値を表示
                        with st.expander("📊 デバッグ情報（入力値と正規化値）"):
                            debug_input = pd.DataFrame({
                                "項目": ["年", "月", "日", "時間", "曜日"],
                                "値": [
                                    str(pred_year),
                                    f"{pred_month:02d}",
                                    f"{pred_day:02d}",
                                    f"{pred_hour:02d}:00",
                                    Weekday_List[datetime.date(int(pred_year), int(pred_month), int(pred_day)).weekday()]
                                ]
                            })
                            st.dataframe(debug_input, use_container_width=True, hide_index=True)
                            
                            # スケーラー適用前後の特徴量を表示
                            if 'weather_debug_info' in st.session_state:
                                debug_info = st.session_state['weather_debug_info']
                                st.write("**入力特徴量（正規化前）：**")
                                feature_names = ['hour', 'day_of_week', 'month', 'day', 'season', 'hour_sin', 'hour_cos', 'month_sin', 'month_cos', 'day_sin', 'day_cos']
                                for i, (name, value) in enumerate(zip(feature_names, debug_info.get('input_raw', []))):
                                    st.write(f"  {i}: {name:12} = {value:.4f}")
                                
                                st.write("**入力特徴量（正規化後）：**")
                                for i, (name, value) in enumerate(zip(feature_names, debug_info.get('input_scaled', []))):
                                    st.write(f"  {i}: {name:12} = {value:.4f}")
                                
                                # スケーラーの統計情報を表示
                                st.write("**スケーラー統計情報（訓練時）：**")
                                st.write("平均値（mean）：")
                                for i, (name, value) in enumerate(zip(feature_names, scaler.mean_)):
                                    st.write(f"  {i}: {name:12} = {value:.4f}")
                                
                                st.write("標準偏差（scale）：")
                                for i, (name, value) in enumerate(zip(feature_names, scaler.scale_)):
                                    st.write(f"  {i}: {name:12} = {value:.4f}")
                        
                        # 結果を表示
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric(
                                "気温",
                                f"{weather_pred.get('気温', 0):.1f}°C"
                            )
                            st.metric(
                                "相対湿度",
                                f"{weather_pred.get('相対湿度', 0):.1f}%"
                            )
                        
                        with col2:
                            st.metric(
                                "降水量",
                                f"{weather_pred.get('降水量', 0):.1f}mm"
                            )
                            st.metric(
                                "風速",
                                f"{weather_pred.get('風速', 0):.1f}m/s"
                            )
                        
                        with col3:
                            st.metric(
                                "日射量",
                                f"{weather_pred.get('日射量', 0):.1f}W/m²"
                            )
                            st.metric(
                                "天気",
                                f"{weather_pred.get('天気', 0):.2f}"
                            )
                        
                        # 詳細テーブル
                        st.subheader("📊 予測結果の詳細")
                        
                        result_df = pd.DataFrame({
                            "気象要素": ["気温", "相対湿度", "降水量", "風速", "日射量", "天気"],
                            "予測値": [
                                f"{weather_pred.get('気温', 0):.2f}°C",
                                f"{weather_pred.get('相対湿度', 0):.2f}%",
                                f"{weather_pred.get('降水量', 0):.2f}mm",
                                f"{weather_pred.get('風速', 0):.2f}m/s",
                                f"{weather_pred.get('日射量', 0):.2f}W/m²",
                                f"{weather_pred.get('天気', 0):.4f}"
                            ]
                        })
                        
                        st.dataframe(result_df, use_container_width=True, hide_index=True)
                    else:
                        st.error("❌ モデルの読み込みに失敗しました。")
                
                except Exception as e:
                    st.error(f"❌ 予測中にエラーが発生しました: {str(e)}")
    
    # ==================================================================================
    # Section 2-2: Predict Power from Weather
    # ==================================================================================
    with st.container(border=True):
        st.subheader("2-2. 予測条件を入力")

        # ==========================================
        # 表示する発電方式
        # ==========================================
        st.write("**表示する発電方式**")
        col_chk1, col_chk2, col_chk3, col_chk4, col_chk5 = st.columns(5)

        with col_chk1:
            show_thermal = st.checkbox("🔥火力", value=True)
        with col_chk2:
            show_solar_power = st.checkbox("☀️太陽光", value=False)
        with col_chk3:
            show_wind = st.checkbox("🌬️風力", value=False)
        with col_chk4:
            show_hydro = st.checkbox("💧水力", value=False)
        with col_chk5:
            show_nuclear = st.checkbox("☢️原子力", value=False)  
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**日時情報**")
            min_date = datetime.date(2026, 10, 1)
            max_date = datetime.date(2040, 12, 31)
            pred_date = st.date_input(
                '予測したい日',
                datetime.date(2026, 10, 1),
                min_value=min_date,
                max_value=max_date,
                key=f"date_{model_suffix}"
            )
            
            select_hour = st.selectbox(
                '時間を選択',
                list(range(24)),
                index=12,
                key=f"hour_{model_suffix}"
            )
            
            # 日付情報を取得
            select_month = pred_date.month
            select_day = pred_date.day
            select_weekday = pred_date.weekday()
            
            st.info(
                f"🗓️ {pred_date.strftime('%Y年%m月%d日')} "
                f"{select_hour}時 ({Weekday_List[select_weekday]})"
            )
        
        with col2:
            st.write("**気象条件**")
            
            temp_options = list(np.arange(0, 41, 1))
            select_temp = st.selectbox(
                '気温(℃)',
                temp_options,
                index=20,
                key=f"temp_{model_suffix}"
            )
            
            rain_options = [0, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
            select_rain = st.selectbox(
                '降水量(mm)',
                rain_options,
                index=0,
                key=f"rain_{model_suffix}"
            )
            
            wind_options = list(np.arange(0, 21, 1))
            select_wind = st.selectbox(
                '風速(m/s)',
                wind_options,
                index=3,
                key=f"wind_{model_suffix}"
            )
        
        with col3:
            st.write("**その他**")
            
            humidity_options = list(range(0, 101, 10))
            select_humidity = st.selectbox(
                '相対湿度(%)',
                humidity_options,
                index=6,
                key=f"humidity_{model_suffix}"
            )

            solar_options = list(np.arange(0, 1001, 50))
            select_solar = st.selectbox(
                '日射量(W/m²)',
                solar_options,
                index=3,
                key=f"solar_{model_suffix}"
            )
            
            # 天気をエンコード（シンプルな分類）
            weather_types = ["晴れ", "曇り", "雨", "雪"]
            select_weather = st.selectbox(
                '天気',
                weather_types,
                index=0,
                key=f"weather_{model_suffix}"
            )
            weather_encoded = weather_types.index(select_weather)
        
        # ==================================================================================
        # Section 2-2: Prediction Button & Results
        # ==================================================================================
        if st.button("🔮 AI予測スタート", key=f"predict_{model_suffix}", use_container_width=True):
            # チェックボックスの状態から、対応するモデルの組み合わせ名を取得
            combination_name = get_model_combination_name(
                show_nuclear,
                show_thermal,
                show_hydro,
                show_solar_power,
                show_wind
            )
            
            # チェックボックスが何も選ばれていない場合はエラーを表示
            if combination_name is None:
                st.error("❌ 予測する発電方式を最低1つ選択してください")
            else:
                try:
                    # location_nameをsession_stateから取得
                    location_name = None
                    if 'uploaded_file_name' in st.session_state:
                        uploaded_file_name = st.session_state.uploaded_file_name
                        if "Kumagaya" in uploaded_file_name:
                            location_name = "kumagaya"
                        elif "Sendai" in uploaded_file_name:
                            location_name = "sendai"
                    
                    if location_name is None:
                        location_name = "kumagaya"  # デフォルト
                    
                    # Combine_Modelからモデルをロード
                    combine_model, combine_scaler, feature_names = load_combine_model(location_name, combination_name)
                    
                    if combine_model is not None:
                        # 入力データを準備
                        input_data = {
                            '気温': select_temp,
                            '降水量': select_rain,
                            '風速': select_wind,
                            '相対湿度': select_humidity,
                            '日射量': select_solar,
                            '月': select_month,
                            '時間': select_hour,
                            '曜日': select_weekday,
                            '日': select_day,
                            '季節': get_season(select_month)
                        }
                        
                        # 予測実行
                        predictions = predict_combine_model(combine_model, combine_scaler, input_data)
                        
                        st.success("✓ 予測が完了しました")
                        
                        # 結果を表示
                        result_data = {}
                        for i, name in enumerate(feature_names):
                            result_data[name] = max(0, round(float(predictions[i]), 1))
                        
                        total = sum(result_data.values())
                        
                        # メトリクスで表示
                        cols = st.columns(len(result_data))
                        for idx, (name, value) in enumerate(result_data.items()):
                            with cols[idx]:
                                st.metric(
                                    f"{name}",
                                    f"{value:,.0f}MW",
                                    delta=f"{(value/total*100):.1f}%" if total > 0 else "0%",
                                    delta_color="off"
                                )
                        
                        # 棒グラフで表示
                        fig_result = go.Figure(data=[
                            go.Bar(
                                x=list(result_data.keys()),
                                y=list(result_data.values()),
                                marker=dict(color=['#FFD700', '#FF6B6B', '#4ECDC4', '#95E1D3', '#4A90E2'][:len(result_data)]),
                                text=[f'{v:,.0f}MW' for v in result_data.values()],
                                textposition='auto',
                            )
                        ])
                        
                        fig_result.update_layout(
                            title='電力供給構成の予測（棒グラフ）',
                            yaxis_title='発電量(MW)',
                            plot_bgcolor='white',
                            height=400,
                            showlegend=False
                        )
                        
                        # 円グラフで表示
                        fig_pie = go.Figure(data=[
                            go.Pie(
                                labels=list(result_data.keys()),
                                values=list(result_data.values()),
                                marker=dict(colors=['#FFD700', '#FF6B6B', '#4ECDC4', '#95E1D3', '#4A90E2'][:len(result_data)]),
                                textposition='inside',
                                textinfo='label+percent'
                            )
                        ])
                        
                        fig_pie.update_layout(
                            title='電力供給構成の予測（円グラフ）',
                            height=400,
                        )
                        
                        # 2列に配置
                        col_chart1, col_chart2 = st.columns(2)
                        
                        with col_chart1:
                            st.plotly_chart(fig_result, use_container_width=True)
                        
                        with col_chart2:
                            st.plotly_chart(fig_pie, use_container_width=True)
                        
                        # 詳細情報
                        st.subheader("詳細情報")
                        
                        info_col1, info_col2 = st.columns(2)
                        
                        with info_col1:
                            st.write("**入力条件**")
                            info_df = pd.DataFrame({
                                "項目": ["日時", "気温", "降水量", "風速", "相対湿度", "日射量", "天気"],
                                "値": [
                                    f"{pred_date.strftime('%Y/%m/%d %H:00')}",
                                    f"{select_temp}℃",
                                    f"{select_rain}mm",
                                    f"{select_wind}m/s",
                                    f"{select_humidity}%",
                                    f"{select_solar}W/m²",
                                    select_weather
                                ]
                            })
                            st.dataframe(info_df, use_container_width=True, hide_index=True)
                        
                        with info_col2:
                            st.write("**予測結果**")
                            result_display = list(result_data.items()) + [("合計", total)]
                            result_df = pd.DataFrame(result_display, columns=["発電方式", "発電量(MW)"])
                            result_df["構成比"] = result_df["発電量(MW)"].apply(
                                lambda x: f"{(x/total*100):.1f}%" if total > 0 else "0%"
                            )
                            st.dataframe(result_df, use_container_width=True, hide_index=True)
                    else:
                        st.error("❌ モデルの読み込みに失敗しました")
                
                except Exception as e:
                    st.error(f"❌ 予測中にエラーが発生しました: {str(e)}")
    
    # ==================================================================================
    # Section 2-3: Predict Other Power Sources from Thermal & Solar
    # ==================================================================================
    st.header("🔌 火力と太陽光から発電源を予測")
    
    with st.container(border=True):
        st.subheader("2-3. 火力と太陽光から他の発電源を予測")
        
        st.info(
            "**予測モデルの仕様**\n\n"
            "• 入力値：火力発電（合計）+ 太陽光発電のみ\n"
            "• 出力：原子力・風力・水力の発電量を予測\n"
            "• 気象情報・時系列情報は使用しません\n"
            "• 火力は個別種類（LNG・石炭・石油）ではなく合計値から計算します"
        )
        
        # 位置情報を取得（熊谷 or 仙台）
        location_mapping = {
            "東京電力（Toden）": "kumagaya",
            "東北電力（Tohoku）": "sendai"
        }
        location_name = location_mapping[selected_region]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**発電量の入力**")
            thermal_input = st.number_input(
                '火力発電合計(MW)',
                min_value=0.0,
                max_value=50000.0,
                value=10000.0,
                step=500.0,
                key=f"thermal_input_{model_suffix}",
                help="火力発電の合計値（LNG、石炭、石油の合計）"
            )
            
            solar_input = st.number_input(
                '太陽光発電(MW)',
                min_value=0.0,
                max_value=10000.0,
                value=2000.0,
                step=100.0,
                key=f"solar_input_{model_suffix}",
                help="太陽光発電の実績値"
            )
        
        # 予測実行ボタン
        if st.button("🔮 発電源を予測", key=f"predict_2_2_{model_suffix}", use_container_width=True):
            # モデルをロード
            models_dict, scaler_2_2 = load_power_prediction_models(location_name)
            
            # 予測実行
            predictions_2_2 = predict_from_thermal_solar(
                models_dict,
                scaler_2_2,
                thermal_input,
                solar_input,
                {}  # 入力データは不使用（火力と太陽光のみで予測）
            )
            
            # 結果を整理
            result_nuclear = max(0, round(predictions_2_2.get('原子力', 0), 1))
            result_wind = max(0, round(predictions_2_2.get('風力発電実績', 0), 1))
            result_hydro = max(0, round(predictions_2_2.get('水力', 0), 1))
            
            # 火力と太陽光を含めた合計
            total_all = thermal_input + solar_input + result_nuclear + result_wind + result_hydro
            
            st.success("✓ 予測が完了しました")
            
            # 予測結果をメトリクスで表示（予測した発電源のみ）
            st.subheader("📊 予測結果")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "原子力発電（予測）",
                    f"{result_nuclear:,.0f}MW",
                    delta=f"{(result_nuclear/total_all*100):.1f}%" if total_all > 0 else "0%",
                    delta_color="off"
                )
            
            with col2:
                st.metric(
                    "風力発電（予測）",
                    f"{result_wind:,.0f}MW",
                    delta=f"{(result_wind/total_all*100):.1f}%" if total_all > 0 else "0%",
                    delta_color="off"
                )
            
            with col3:
                st.metric(
                    "水力発電（予測）",
                    f"{result_hydro:,.0f}MW",
                    delta=f"{(result_hydro/total_all*100):.1f}%" if total_all > 0 else "0%",
                    delta_color="off"
                )
            
            # 全発電源を含む円グラフ
            st.subheader("⚡ 電力供給構成（全体）")
            
            all_sources = {
                '原子力': result_nuclear,
                '火力': thermal_input,
                '太陽光': solar_input,
                '風力': result_wind,
                '水力': result_hydro
            }
            
            # 円グラフの作成
            fig_pie = go.Figure(data=[
                go.Pie(
                    labels=list(all_sources.keys()),
                    values=list(all_sources.values()),
                    marker=dict(
                        colors=['#FFD700', '#FF6B6B', '#4ECDC4', '#95E1D3', '#4A90E2']
                    ),
                    textposition='inside',
                    textinfo='label+percent',
                    hovertemplate='<b>%{label}</b><br>発電量: %{value:.0f}MW<br>構成比: %{percent}<extra></extra>'
                )
            ])
            
            fig_pie.update_layout(
                title='火力と太陽光から予測した電力供給構成',
                height=500,
                font=dict(size=12)
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # 詳細テーブル表示
            st.subheader("📈 詳細結果")
            
            result_df = pd.DataFrame({
                "発電方式": ["原子力", "火力", "太陽光", "風力", "水力", "合計"],
                "発電量(MW)": [
                    f"{result_nuclear:,.1f}",
                    f"{thermal_input:,.1f}",
                    f"{solar_input:,.1f}",
                    f"{result_wind:,.1f}",
                    f"{result_hydro:,.1f}",
                    f"{total_all:,.1f}"
                ],
                "構成比": [
                    f"{(result_nuclear/total_all*100):.1f}%" if total_all > 0 else "0%",
                    f"{(thermal_input/total_all*100):.1f}%" if total_all > 0 else "0%",
                    f"{(solar_input/total_all*100):.1f}%" if total_all > 0 else "0%",
                    f"{(result_wind/total_all*100):.1f}%" if total_all > 0 else "0%",
                    f"{(result_hydro/total_all*100):.1f}%" if total_all > 0 else "0%",
                    "100%"
                ]
            })
            
            st.dataframe(result_df, use_container_width=True, hide_index=True)
            
            # 入力条件の表示
            st.subheader("📋 入力条件")
            
            info_df = pd.DataFrame({
                "項目": ["火力発電（合計）", "太陽光発電"],
                "値": [
                    f"{thermal_input:,.0f}MW",
                    f"{solar_input:,.0f}MW"
                ]
            })
            
            st.dataframe(info_df, use_container_width=True, hide_index=True)
    
    # ==================================================================================
    # Footer
    # ==================================================================================
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #888; font-size: 12px;'>
        <p>⚡ 天気・電力データ分析ツール v1.0</p>
        <p>機械学習モデルによる予測ツール | 気象条件から電力供給構成を推定します</p>
        </div>
        """,
        unsafe_allow_html=True
    )



if __name__ == "__main__":
    main()
