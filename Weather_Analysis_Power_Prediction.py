# -*- coding: utf-8 -*-
"""
Weather & Power Data Analysis and Prediction Tool
Author: TAJ2HIG
Date: 2026-09-09

気象情報と電力供給データを分析・予測するツール

============================================================
重要
============================================================

Google Driveからモデルを自動ダウンロードします。

対応:
- Streamlit Cloud
- ローカル環境
- gdown 6.x
- Google Drive 公開フォルダ

Google Drive:
https://drive.google.com/drive/folders/11CrLEAr_ljmYx1Ib5TPpWG_kvwDElNgS

モデル構成:

model/
    model_toden_power_weather.pkl
    scaler_toden_power_weather.pkl
    feature_cols_toden.pkl

    model_tohoku_power_weather.pkl
    scaler_tohoku_power_weather.pkl
    feature_cols_tohoku.pkl

models/
    model_kumagaya_原子力.pkl
    model_kumagaya_風力発電実績.pkl
    model_kumagaya_水力.pkl
    scaler_kumagaya.pkl

    model_sendai_原子力.pkl
    model_sendai_風力発電実績.pkl
    model_sendai_水力.pkl
    scaler_sendai.pkl

Weather_Model/
    model_kumagaya_気温.pkl
    model_kumagaya_相対湿度.pkl
    model_kumagaya_降水量.pkl
    model_kumagaya_風速.pkl
    model_kumagaya_日射量.pkl
    model_kumagaya_天気.pkl
    scaler_kumagaya.pkl

    model_sendai_気温.pkl
    model_sendai_相対湿度.pkl
    model_sendai_降水量.pkl
    model_sendai_風速.pkl
    model_sendai_日射量.pkl
    model_sendai_天気.pkl
    scaler_sendai.pkl

Combine_Model/
    model_toden_01_原子力.pkl
    ...
    model_tohoku_31_原子力_火力_水力_太陽光発電実績_風力発電実績.pkl
"""

import streamlit as st
import pandas as pd
import numpy as np

import pickle
import joblib
import datetime
import hashlib
import warnings
import os
import shutil
import json
import traceback

from pathlib import Path
from datetime import datetime as dt

import plotly.graph_objects as go


# ============================================================
# Warning suppression
# ============================================================

warnings.filterwarnings(
    "ignore",
    category=Warning,
    module="sklearn"
)

warnings.filterwarnings(
    "ignore",
    message="Trying to unpickle estimator"
)

warnings.filterwarnings(
    "ignore",
    message="X does not have valid feature names"
)


# ============================================================
# Base directory
# ============================================================

def get_base_dir():
    """
    Streamlit Cloud / ローカル両対応
    """

    try:
        return Path(__file__).resolve().parent
    except Exception:
        return Path(os.getcwd()).resolve()


BASE_DIR = get_base_dir()

TEMP_DIR = BASE_DIR / ".gdrive_temp"


# ============================================================
# Google Drive settings
# ============================================================

GOOGLE_DRIVE_FOLDER_ID = "11CrLEAr_ljmYx1Ib5TPpWG_kvwDElNgS"

GOOGLE_DRIVE_FOLDER_URL = (
    f"https://drive.google.com/drive/folders/{GOOGLE_DRIVE_FOLDER_ID}"
)


# ============================================================
# Required files
# ============================================================

REQUIRED_FILES = [
    # 旧モデル
    "model_toden_power_weather.pkl",
    "scaler_toden_power_weather.pkl",
    "feature_cols_toden.pkl",

    "model_tohoku_power_weather.pkl",
    "scaler_tohoku_power_weather.pkl",
    "feature_cols_tohoku.pkl",

    # 2-3 Power models
    "model_kumagaya_原子力.pkl",
    "model_kumagaya_風力発電実績.pkl",
    "model_kumagaya_水力.pkl",
    "scaler_kumagaya.pkl",

    "model_sendai_原子力.pkl",
    "model_sendai_風力発電実績.pkl",
    "model_sendai_水力.pkl",
    "scaler_sendai.pkl",

    # Weather model
    "model_kumagaya_気温.pkl",
    "model_kumagaya_相対湿度.pkl",
    "model_kumagaya_降水量.pkl",
    "model_kumagaya_風速.pkl",
    "model_kumagaya_日射量.pkl",
    "model_kumagaya_天気.pkl",

    "model_sendai_気温.pkl",
    "model_sendai_相対湿度.pkl",
    "model_sendai_降水量.pkl",
    "model_sendai_風速.pkl",
    "model_sendai_日射量.pkl",
    "model_sendai_天気.pkl",
]


# ============================================================
# Display / labels
# ============================================================

Weekday_List = [
    "月曜日",
    "火曜日",
    "水曜日",
    "木曜日",
    "金曜日",
    "土曜日",
    "日曜日"
]


MODELS = {
    "東京電力（Toden）": {
        "suffix": "toden",
        "location": "熊谷",
        "location_name": "kumagaya",
        "color": "rgb(220, 53, 69)",
        "csv_file": "all_data_Kumagaya.csv"
    },

    "東北電力（Tohoku）": {
        "suffix": "tohoku",
        "location": "仙台",
        "location_name": "sendai",
        "color": "rgb(0, 102, 204)",
        "csv_file": "all_data_Sendai.csv"
    }
}


# ============================================================
# Utility
# ============================================================

def file_exists(path):
    """
    ファイル存在確認
    """

    try:
        return Path(path).is_file()
    except Exception:
        return False


def count_required_files():
    """
    現在存在している必要ファイル数を確認
    """

    count = 0

    for filename in REQUIRED_FILES:

        matches = list(BASE_DIR.rglob(filename))

        if matches:
            count += 1

    return count


def find_file(filename):
    """
    BASE_DIR以下からファイル名を検索

    優先順位:
    1. BASE_DIR直下
    2. 正しいモデルフォルダ
    3. その他サブフォルダ
    """

    direct = BASE_DIR / filename

    if direct.is_file():
        return direct

    matches = list(BASE_DIR.rglob(filename))

    if matches:
        return matches[0]

    return None


def safe_copy_file(src, dst):
    """
    ファイルを安全にコピー
    """

    src = Path(src)
    dst = Path(dst)

    if not src.is_file():
        return False

    dst.parent.mkdir(parents=True, exist_ok=True)

    try:

        if src.resolve() == dst.resolve():
            return True

    except Exception:
        pass

    try:
        shutil.copy2(src, dst)
        return True

    except Exception:
        return False


# ============================================================
# Google Drive download
# ============================================================

def download_models_from_gdrive():
    """
    Google Driveからモデルをダウンロード

    gdown 6.x対応版

    注意:
    gdown 6.xでは remaining_ok は使用しない。
    """

    st.info("📥 Google Drive からモデルをダウンロード中...")
    st.caption("初回のみ時間がかかる場合があります。")

    st.write("### Environment Info")

    try:

        import gdown

        try:
            gdown_version = gdown.__version__
        except Exception:
            gdown_version = "unknown"

        st.code(
            f"gdown version: {gdown_version}\n"
            f"BASE_DIR: {BASE_DIR}\n"
            f"TEMP_DIR: {TEMP_DIR}\n"
            f"Folder ID: {GOOGLE_DRIVE_FOLDER_ID}"
        )

    except ImportError:

        st.error(
            "❌ gdown がインストールされていません。\n\n"
            "requirements.txt に gdown>=6.0.0 を追加してください。"
        )

        return False


    # --------------------------------------------------------
    # 既存ファイル確認
    # --------------------------------------------------------

    existing_count = count_required_files()

    st.write(
        f"現在取得済みの必要モデル: "
        f"{existing_count}/{len(REQUIRED_FILES)}"
    )

    if existing_count == len(REQUIRED_FILES):

        st.success("✓ 必要なモデルファイルはすべて存在します。")

        return True


    # --------------------------------------------------------
    # Temp directory
    # --------------------------------------------------------

    try:

        TEMP_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        st.write(
            f"Temp directory: {TEMP_DIR}"
        )

    except Exception as e:

        st.error(
            f"❌ 一時ディレクトリを作成できません: {e}"
        )

        return False


    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------

    st.write("### Google Drive File List")

    st.write(
        "Google Driveフォルダを確認しています..."
    )

    st.code(GOOGLE_DRIVE_FOLDER_URL)

    st.write("Starting Google Drive download...")

    try:

        # ----------------------------------------------------
        # gdown 6.x
        #
        # remaining_ok は絶対に指定しない
        # ----------------------------------------------------

        downloaded = gdown.download_folder(
            url=GOOGLE_DRIVE_FOLDER_URL,
            output=str(TEMP_DIR),
            quiet=False,
            resume=True,
            retries=3,
            timeout=60
        )

        st.success("✓ Google Driveからの取得処理が完了しました。")

        if downloaded is not None:

            try:
                st.write(
                    f"取得対象ファイル数: {len(downloaded)}"
                )
            except Exception:
                pass

    except TypeError as e:

        st.error(
            "❌ gdownのAPIエラーが発生しました。"
        )

        st.code(
            str(e)
        )

        st.info(
            "gdown 6.xでは remaining_ok を使用できません。"
        )

        return False

    except Exception as e:

        st.error(
            "⚠️ Google Driveフォルダ取得中にエラーが発生しました"
        )

        st.code(
            f"{type(e).__name__}: {e}"
        )

        st.write("詳細:")

        st.code(
            traceback.format_exc()
        )

        return False


    # --------------------------------------------------------
    # Downloaded files
    # --------------------------------------------------------

    downloaded_files = list(
        TEMP_DIR.rglob("*")
    )

    file_list = [
        p for p in downloaded_files
        if p.is_file()
    ]

    st.write(
        f"取得済みファイル数: {len(file_list)}"
    )


    if file_list:

        with st.expander("📁 取得したファイル一覧"):

            for path in sorted(file_list):

                try:
                    relative = path.relative_to(TEMP_DIR)
                except Exception:
                    relative = path.name

                st.write(str(relative))


    # --------------------------------------------------------
    # Copy files
    # --------------------------------------------------------

    st.write("### モデルファイルを配置しています...")

    copied_count = 0

    # Drive側にあるファイルを名前で検索
    for filename in REQUIRED_FILES:

        source = None

        # Tempから検索
        candidates = list(
            TEMP_DIR.rglob(filename)
        )

        if candidates:
            source = candidates[0]

        # 見つかったら適切な場所へコピー
        if source is not None:

            # ファイル種別によって配置場所を決定

            if filename.startswith("model_kumagaya_"):
                destination = BASE_DIR / "models" / filename

                # Weather_Modelのファイルならこちら
                weather_elements = [
                    "気温",
                    "相対湿度",
                    "降水量",
                    "風速",
                    "日射量",
                    "天気"
                ]

                if any(
                    f"_{element}.pkl" in filename
                    for element in weather_elements
                ):
                    destination = (
                        BASE_DIR
                        / "Weather_Model"
                        / filename
                    )

            elif filename.startswith("model_sendai_"):
                destination = BASE_DIR / "models" / filename

                weather_elements = [
                    "気温",
                    "相対湿度",
                    "降水量",
                    "風速",
                    "日射量",
                    "天気"
                ]

                if any(
                    f"_{element}.pkl" in filename
                    for element in weather_elements
                ):
                    destination = (
                        BASE_DIR
                        / "Weather_Model"
                        / filename
                    )

            else:
                destination = BASE_DIR / filename

            if safe_copy_file(
                source,
                destination
            ):

                copied_count += 1

        else:

            # すでにBASE_DIR以下に存在する場合は何もしない
            if find_file(filename) is not None:
                continue


    # --------------------------------------------------------
    # Combine_Model
    # --------------------------------------------------------

    combine_files = []

    for path in TEMP_DIR.rglob("*.pkl"):

        name = path.name

        if (
            name.startswith("model_toden_")
            or name.startswith("scaler_toden_")
            or name.startswith("model_tohoku_")
            or name.startswith("scaler_tohoku_")
        ):

            # power_weather系は除外
            if "power_weather" not in name:

                combine_files.append(path)


    for source in combine_files:

        destination = (
            BASE_DIR
            / "Combine_Model"
            / source.name
        )

        safe_copy_file(
            source,
            destination
        )


    # --------------------------------------------------------
    # JSON files
    # --------------------------------------------------------

    for source in TEMP_DIR.rglob("*.json"):

        destination = (
            BASE_DIR
            / "Combine_Model"
            / source.name
        )

        safe_copy_file(
            source,
            destination
        )


    # --------------------------------------------------------
    # 最終確認
    # --------------------------------------------------------

    final_count = count_required_files()

    st.write(
        f"必要モデル確認: "
        f"{final_count}/{len(REQUIRED_FILES)}"
    )

    if final_count > 0:

        st.success(
            f"✓ {final_count}個のモデルファイルを確認しました。"
        )


    # Combine Modelなどを含めた全体チェック
    important_dirs = [
        BASE_DIR / "models",
        BASE_DIR / "Weather_Model",
        BASE_DIR / "Combine_Model"
    ]

    found_any = False

    for directory in important_dirs:

        if directory.exists():

            files = [
                p for p in directory.rglob("*")
                if p.is_file()
            ]

            if files:
                found_any = True

    if found_any:

        st.success(
            "✓ モデルディレクトリを確認しました。"
        )

        return True

    st.error(
        "❌ Google Driveからモデルファイルを取得できませんでした。\n\n"
        "Google Driveフォルダが「リンクを知っている全員」に"
        "閲覧可能になっているか確認してください。"
    )

    return False


# ============================================================
# Model preparation
# ============================================================

@st.cache_resource
def ensure_models_available():
    """
    モデルが存在することを保証する。

    重要:
    main()より先に実行する。
    """

    # まず既存ファイルを確認
    if count_required_files() > 0:

        return True

    # Driveから取得
    return download_models_from_gdrive()


# ============================================================
# Legacy model loader
# ============================================================

@st.cache_resource
def load_models_and_data(model_suffix):
    """
    旧Power Weatherモデルをロード
    """

    model_file = find_file(
        f"model_{model_suffix}_power_weather.pkl"
    )

    scaler_file = find_file(
        f"scaler_{model_suffix}_power_weather.pkl"
    )

    feature_file = find_file(
        f"feature_cols_{model_suffix}.pkl"
    )


    if model_file is None:
        raise FileNotFoundError(
            f"モデルファイルが見つかりません: "
            f"model_{model_suffix}_power_weather.pkl"
        )

    if scaler_file is None:
        raise FileNotFoundError(
            f"スケーラーファイルが見つかりません: "
            f"scaler_{model_suffix}_power_weather.pkl"
        )

    if feature_file is None:
        raise FileNotFoundError(
            f"特徴量ファイルが見つかりません: "
            f"feature_cols_{model_suffix}.pkl"
        )


    with open(
        model_file,
        "rb"
    ) as f:
        model = pickle.load(f)


    with open(
        scaler_file,
        "rb"
    ) as f:
        scaler = pickle.load(f)


    with open(
        feature_file,
        "rb"
    ) as f:
        feature_cols = pickle.load(f)


    return model, scaler, feature_cols


# ============================================================
# Power prediction models
# ============================================================

@st.cache_resource
def load_power_prediction_models(location_name):
    """
    火力合計 + 太陽光
    →
    原子力・風力・水力
    """

    work_dir = BASE_DIR / "models"

    models_dict = {}

    model_types = [
        "原子力",
        "風力発電実績",
        "水力"
    ]


    for model_type in model_types:

        model_file = (
            work_dir
            / f"model_{location_name}_{model_type}.pkl"
        )

        if not model_file.is_file():

            # サブフォルダも検索
            found = find_file(model_file.name)

            if found is not None:
                model_file = found


        try:

            if not model_file.is_file():
                raise FileNotFoundError(
                    str(model_file)
                )

            models_dict[model_type] = joblib.load(
                model_file
            )

        except Exception as e:

            st.error(
                f"❌ {model_type}モデルのロードに失敗しました\n"
                f"{model_file}\n"
                f"{e}"
            )

            models_dict[model_type] = None


    # scaler
    scaler_file = (
        work_dir
        / f"scaler_{location_name}.pkl"
    )

    if not scaler_file.is_file():

        found = find_file(
            scaler_file.name
        )

        if found is not None:
            scaler_file = found


    try:

        if not scaler_file.is_file():
            raise FileNotFoundError(
                str(scaler_file)
            )

        scaler = joblib.load(
            scaler_file
        )

    except Exception as e:

        st.error(
            f"❌ スケーラーのロードに失敗しました\n"
            f"{scaler_file}\n"
            f"{e}"
        )

        scaler = None


    return models_dict, scaler


# ============================================================
# CSV
# ============================================================

@st.cache_data(ttl=3600)
def load_csv_data(csv_path):

    df = pd.read_csv(
        csv_path,
        encoding="utf-8-sig"
    )

    return _preprocess_dataframe(df)


def _preprocess_dataframe(df):

    df = df.copy()

    if "DateTime" in df.columns:

        df["DateTime"] = pd.to_datetime(
            df["DateTime"],
            errors="coerce"
        )

        df = df.dropna(
            subset=["DateTime"]
        )

        df["date"] = df["DateTime"].dt.date

        df["hour"] = (
            df["DateTime"]
            .dt.hour
        )

        df["day_str"] = (
            df["DateTime"]
            .dt.strftime("%Y-%m-%d")
        )

        df["month_str"] = (
            df["DateTime"]
            .dt.strftime("%y/%m")
        )


    # 火力合計
    thermal_cols = [
        "火力(LNG)",
        "火力(石炭)",
        "火力(石油)",
        "火力(その他)"
    ]

    available_thermal_cols = [
        col
        for col in thermal_cols
        if col in df.columns
    ]

    if available_thermal_cols:

        df["火力_合計"] = (
            df[available_thermal_cols]
            .fillna(0)
            .sum(axis=1)
        )


    return df


# ============================================================
# Weather model
# ============================================================

@st.cache_resource
def load_weather_prediction_models(location_name):

    work_dir = (
        BASE_DIR
        / "Weather_Model"
    )

    models_dict = {}

    weather_elements = [
        "気温",
        "相対湿度",
        "降水量",
        "風速",
        "日射量",
        "天気"
    ]


    for element in weather_elements:

        filename = (
            f"model_{location_name}_{element}.pkl"
        )

        model_file = (
            work_dir
            / filename
        )

        if not model_file.is_file():

            found = find_file(filename)

            if found is not None:
                model_file = found


        try:

            if not model_file.is_file():
                raise FileNotFoundError(
                    str(model_file)
                )

            models_dict[element] = joblib.load(
                model_file
            )

        except Exception as e:

            st.error(
                f"❌ 気象モデルロード失敗: "
                f"{element}\n{e}"
            )

            models_dict[element] = None


    scaler_filename = (
        f"scaler_{location_name}.pkl"
    )

    scaler_file = (
        work_dir
        / scaler_filename
    )

    if not scaler_file.is_file():

        found = find_file(
            scaler_filename
        )

        if found is not None:
            scaler_file = found


    try:

        if not scaler_file.is_file():
            raise FileNotFoundError(
                str(scaler_file)
            )

        scaler = joblib.load(
            scaler_file
        )

    except Exception as e:

        st.error(
            f"❌ 気象スケーラーのロード失敗\n{e}"
        )

        scaler = None


    return models_dict, scaler


# ============================================================
# Season
# ============================================================

def get_season(month):

    if month in [12, 1, 2]:
        return 0

    elif month in [3, 4, 5]:
        return 1

    elif month in [6, 7, 8]:
        return 2

    return 3


# ============================================================
# Weather prediction
# ============================================================

def predict_weather_from_datetime(
    models_dict,
    scaler,
    year,
    month,
    day,
    hour
):

    predictions = {}

    debug_info = {}


    date_obj = datetime.date(
        year,
        month,
        day
    )

    day_of_week = date_obj.weekday()

    season = get_season(month)


    hour_sin = np.sin(
        2 * np.pi * hour / 24
    )

    hour_cos = np.cos(
        2 * np.pi * hour / 24
    )

    month_sin = np.sin(
        2 * np.pi * month / 12
    )

    month_cos = np.cos(
        2 * np.pi * month / 12
    )

    day_sin = np.sin(
        2 * np.pi * day_of_week / 7
    )

    day_cos = np.cos(
        2 * np.pi * day_of_week / 7
    )


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


    debug_info["input_raw"] = (
        X[0].tolist()
    )


    if scaler is not None:

        try:

            with warnings.catch_warnings():

                warnings.filterwarnings(
                    "ignore",
                    message="X does not have valid feature names"
                )

                X_scaled = scaler.transform(X)

        except Exception as e:

            st.warning(
                f"⚠️ スケーラー変換に失敗: {e}"
            )

            X_scaled = X

    else:

        X_scaled = X


    debug_info["input_scaled"] = (
        X_scaled[0].tolist()
    )


    st.session_state[
        "weather_debug_info"
    ] = debug_info


    for element in [
        "気温",
        "相対湿度",
        "降水量",
        "風速",
        "日射量",
        "天気"
    ]:

        model = models_dict.get(element)

        if model is None:

            predictions[element] = 0.0
            continue


        try:

            pred = model.predict(
                X_scaled
            )

            value = float(
                pred[0]
            )


            if element == "相対湿度":

                value = max(
                    0,
                    min(100, value)
                )

            elif element == "天気":

                value = max(
                    0,
                    min(1, value)
                )

            else:

                value = max(
                    0,
                    value
                )


            predictions[element] = value


        except Exception as e:

            st.warning(
                f"⚠️ {element}予測失敗: {e}"
            )

            predictions[element] = 0.0


    return predictions


# ============================================================
# 2-3 prediction
# ============================================================

def predict_from_thermal_solar(
    models_dict,
    scaler,
    thermal_value,
    solar_value,
    input_data
):

    predictions = {}


    X = np.array([
        thermal_value,
        solar_value
    ]).reshape(1, -1)


    if scaler is not None:

        try:

            with warnings.catch_warnings():

                warnings.filterwarnings(
                    "ignore",
                    message="X does not have valid feature names"
                )

                X_scaled = scaler.transform(X)

        except Exception as e:

            st.warning(
                f"⚠️ スケーラー変換に失敗: {e}"
            )

            X_scaled = X

    else:

        X_scaled = X


    for model_type, model in models_dict.items():

        if model is None:

            predictions[model_type] = 0.0
            continue


        try:

            pred = model.predict(
                X_scaled
            )

            predictions[model_type] = max(
                0,
                float(pred[0])
            )

        except Exception as e:

            st.warning(
                f"⚠️ {model_type}予測失敗: {e}"
            )

            predictions[model_type] = 0.0


    return predictions


# ============================================================
# Combine model map
# ============================================================

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


# ============================================================
# Combine model
# ============================================================

@st.cache_resource
def load_combine_model(
    location_name,
    combination_name
):

    work_dir = (
        BASE_DIR
        / "Combine_Model"
    )


    model_suffix = (
        "toden"
        if location_name == "kumagaya"
        else "tohoku"
    )


    number = COMBINATION_NUMBER_MAP.get(
        combination_name
    )


    if number is None:

        st.error(
            f"❌ 不正な組み合わせ: "
            f"{combination_name}"
        )

        return None, None, None


    model_filename = (
        f"model_{model_suffix}_"
        f"{number}_{combination_name}.pkl"
    )

    scaler_filename = (
        f"scaler_{model_suffix}_"
        f"{number}_{combination_name}.pkl"
    )

    info_filename = (
        f"info_{model_suffix}_"
        f"{number}_{combination_name}.json"
    )


    model_file = (
        work_dir
        / model_filename
    )

    if not model_file.is_file():

        found = find_file(
            model_filename
        )

        if found is not None:
            model_file = found


    if not model_file.is_file():

        st.error(
            f"❌ Combine_Modelが見つかりません\n"
            f"{model_file}"
        )

        return None, None, None


    try:

        model = joblib.load(
            model_file
        )

    except Exception as e:

        st.error(
            f"❌ Combine_Modelロード失敗\n{e}"
        )

        return None, None, None


    # scaler
    scaler_file = (
        work_dir
        / scaler_filename
    )

    if not scaler_file.is_file():

        found = find_file(
            scaler_filename
        )

        if found is not None:
            scaler_file = found


    scaler = None

    if scaler_file.is_file():

        try:

            scaler = joblib.load(
                scaler_file
            )

        except Exception as e:

            st.warning(
                f"⚠️ scalerロード失敗: {e}"
            )


    # feature names
    info_file = (
        work_dir
        / info_filename
    )

    feature_names = None


    if not info_file.is_file():

        found = find_file(
            info_filename
        )

        if found is not None:
            info_file = found


    if info_file.is_file():

        try:

            with open(
                info_file,
                "r",
                encoding="utf-8"
            ) as f:

                info = json.load(f)

            feature_names = info.get(
                "target_combo"
            )

        except Exception:
            feature_names = None


    if not feature_names:

        feature_names = (
            combination_name.split("_")
        )


    return (
        model,
        scaler,
        feature_names
    )


# ============================================================
# Combination name
# ============================================================

def get_model_combination_name(
    show_nuclear,
    show_thermal,
    show_hydro,
    show_solar,
    show_wind
):

    selected = []

    if show_nuclear:
        selected.append("原子力")

    if show_thermal:
        selected.append("火力")

    if show_hydro:
        selected.append("水力")

    if show_solar:
        selected.append("太陽光発電実績")

    if show_wind:
        selected.append("風力発電実績")


    if not selected:
        return None


    return "_".join(selected)


# ============================================================
# Combine prediction
# ============================================================

def predict_combine_model(
    model,
    scaler,
    input_data
):

    hour = input_data["時間"]
    month = input_data["月"]


    hour_sin = np.sin(
        2 * np.pi * hour / 24
    )

    hour_cos = np.cos(
        2 * np.pi * hour / 24
    )

    month_sin = np.sin(
        2 * np.pi * month / 12
    )

    month_cos = np.cos(
        2 * np.pi * month / 12
    )


    X = np.array([
        input_data["気温"],
        input_data["降水量"],
        input_data["風速"],
        input_data["相対湿度"],
        input_data["日射量"],
        input_data["月"],
        input_data["時間"],
        input_data["曜日"],
        input_data["日"],
        input_data["季節"],
        hour_sin,
        hour_cos,
        month_sin,
        month_cos
    ]).reshape(1, -1)


    if scaler is not None:

        try:

            with warnings.catch_warnings():

                warnings.filterwarnings(
                    "ignore",
                    message="X does not have valid feature names"
                )

                X_scaled = scaler.transform(X)

        except Exception as e:

            st.warning(
                f"⚠️ Combine scaler変換失敗: {e}"
            )

            X_scaled = X

    else:

        X_scaled = X


    predictions = model.predict(
        X_scaled
    )


    return predictions[0]


# ============================================================
# Session state
# ============================================================

def init_session_state():

    if "current_region" not in st.session_state:

        st.session_state.current_region = (
            "東京電力（Toden）"
        )


    if "df_cache" not in st.session_state:

        st.session_state.df_cache = {}


    if "session_id" not in st.session_state:

        session_id = hashlib.md5(
            str(dt.now()).encode()
        ).hexdigest()[:8]

        st.session_state.session_id = session_id


# ============================================================
# Main
# ============================================================

def main():

    st.set_page_config(
        page_title="天気・電力データ分析ツール",
        page_icon="⚡",
        layout="wide"
    )


    init_session_state()


    # ========================================================
    # Model preparation
    # ========================================================

    if "models_checked" not in st.session_state:

        st.session_state.models_checked = False


    if not st.session_state.models_checked:

        st.info(
            "🔧 モデルファイルを確認しています..."
        )

        success = ensure_models_available()

        st.session_state.models_checked = True

        if not success:

            st.error(
                "❌ モデルを準備できませんでした。"
            )

            st.stop()


    # ========================================================
    # Title
    # ========================================================

    st.title(
        "⚡ 天気・電力データ分析ツール"
    )

    st.markdown(
        "気象情報から電力供給構成を予測します"
    )


    # ========================================================
    # Region
    # ========================================================

    selected_region = st.selectbox(
        "電力エリア",
        list(MODELS.keys()),
        index=0
    )


    model_config = MODELS[
        selected_region
    ]

    model_suffix = model_config[
        "suffix"
    ]

    location = model_config[
        "location"
    ]

    location_name = model_config[
        "location_name"
    ]


    # ========================================================
    # Section 1
    # ========================================================

    st.header(
        "📊 グラフで確認してみよう"
    )


    with st.container(border=True):

        st.subheader(
            "1-1. データを読み込む"
        )


        uploaded_file = st.file_uploader(
            "CSVファイルをアップロードしてください",
            type="csv",
            help="dataフォルダ内のCSVファイルを選択してください"
        )


        df = None


        if uploaded_file is not None:

            try:

                df = _preprocess_dataframe(
                    pd.read_csv(
                        uploaded_file,
                        encoding="utf-8-sig"
                    )
                )


                st.success(
                    f"✓ {uploaded_file.name} "
                    f"が読み込まれました "
                    f"（{len(df)}件）"
                )


                st.session_state[
                    "uploaded_file_name"
                ] = uploaded_file.name


            except Exception as e:

                st.error(
                    f"❌ ファイル読み込み失敗: {e}"
                )


        # ====================================================
        # 1-2
        # ====================================================

        if df is not None:

            st.subheader(
                "1-2. 一年間のデータの変化"
            )


            years = sorted(
                df["DateTime"]
                .dt.year
                .unique()
            )


            if len(years) > 0:

                default_year = 2024

                if default_year in years:

                    default_index = years.index(
                        default_year
                    )

                else:

                    default_index = 0


                selected_year = st.selectbox(
                    "確認したい年を選択",
                    years,
                    index=default_index
                )


                df_year = df[
                    df["DateTime"]
                    .dt.year == selected_year
                ]


                st.write(
                    f"📅 {selected_year}年のデータを表示中 "
                    f"（{len(df_year)}件）"
                )


                fig = go.Figure()


                if "気温" in df_year.columns:

                    fig.add_trace(
                        go.Scatter(
                            x=df_year["DateTime"],
                            y=df_year["気温"],
                            line=dict(
                                color="orange",
                                width=2
                            ),
                            name="気温(℃)",
                            yaxis="y1"
                        )
                    )


                if "降水量" in df_year.columns:

                    fig.add_trace(
                        go.Scatter(
                            x=df_year["DateTime"],
                            y=df_year["降水量"],
                            line=dict(
                                color="blue",
                                width=2
                            ),
                            name="降水量(mm)",
                            yaxis="y2"
                        )
                    )


                fig.update_layout(
                    title=f"{selected_year}年の気象データ",
                    xaxis_title="日時",
                    yaxis1=dict(
                        title="気温(℃)",
                        side="left",
                        showgrid=True
                    ),
                    yaxis2=dict(
                        title="降水量(mm)",
                        side="right",
                        overlaying="y1"
                    ),
                    plot_bgcolor="white",
                    hovermode="x unified",
                    height=500
                )


                st.plotly_chart(
                    fig,
                    use_container_width=True
                )


                power_cols = [
                    "原子力",
                    "火力_合計",
                    "太陽光発電実績"
                ]


                available_power_cols = [
                    col
                    for col in power_cols
                    if col in df.columns
                ]


            # =================================================
            # 1-3
            # =================================================

            st.subheader(
                "1-3. 1日のデータを比較しよう"
            )


            min_date_data = (
                df["DateTime"]
                .min()
                .date()
            )

            max_date_data = (
                df["DateTime"]
                .max()
                .date()
            )


            col1, col2 = st.columns(2)


            with col1:

                date_1 = st.date_input(
                    "比較する1つ目の日付",
                    min_date_data,
                    min_value=min_date_data,
                    max_value=max_date_data,
                    key="date_1_comparison"
                )


            with col2:

                second_default = (
                    min_date_data
                    + datetime.timedelta(days=1)
                )

                if second_default > max_date_data:
                    second_default = min_date_data


                date_2 = st.date_input(
                    "比較する2つ目の日付",
                    second_default,
                    min_value=min_date_data,
                    max_value=max_date_data,
                    key="date_2_comparison"
                )


            df_cut_1day_1 = df[
                df["day_str"] == str(date_1)
            ]

            df_cut_1day_2 = df[
                df["day_str"] == str(date_2)
            ]


            if date_1 == date_2:

                st.warning(
                    f"⚠️ {date_1}と{date_2}を"
                    "別日に設定してください。"
                )

            else:

                col1, col2 = st.columns(2)


                for col_container, day_df, day_value in [
                    (col1, df_cut_1day_1, date_1),
                    (col2, df_cut_1day_2, date_2)
                ]:

                    with col_container:

                        if len(day_df) == 0:

                            st.warning(
                                f"⚠️ {day_value}のデータがありません"
                            )

                            continue


                        st.subheader(
                            f"{day_value}の気象データ"
                        )


                        fig_weather = go.Figure()


                        if "気温" in day_df.columns:

                            fig_weather.add_trace(
                                go.Scatter(
                                    x=day_df["hour"],
                                    y=day_df["気温"],
                                    name="気温(℃)",
                                    line=dict(
                                        color="orange",
                                        width=2
                                    ),
                                    yaxis="y1"
                                )
                            )


                        if "降水量" in day_df.columns:

                            fig_weather.add_trace(
                                go.Scatter(
                                    x=day_df["hour"],
                                    y=day_df["降水量"],
                                    name="降水量(mm)",
                                    line=dict(
                                        color="blue",
                                        width=2
                                    ),
                                    yaxis="y2"
                                )
                            )


                        fig_weather.update_layout(
                            title=f"{day_value}の気象データ",
                            xaxis_title="時間",
                            yaxis1=dict(
                                title="気温(℃)",
                                side="left",
                                range=[-15, 40]
                            ),
                            yaxis2=dict(
                                title="降水量(mm)",
                                side="right",
                                overlaying="y1",
                                range=[0, 50]
                            ),
                            plot_bgcolor="white",
                            hovermode="x unified",
                            height=400
                        )


                        st.plotly_chart(
                            fig_weather,
                            use_container_width=True
                        )


                        st.subheader(
                            f"{day_value}の電力供給構成"
                        )


                        fig_power = go.Figure()


                        for power_col in available_power_cols:

                            fig_power.add_trace(
                                go.Bar(
                                    x=day_df["hour"],
                                    y=day_df[power_col],
                                    name=power_col
                                )
                            )


                        fig_power.update_layout(
                            barmode="stack",
                            title=f"{day_value}の電力供給構成",
                            xaxis_title="時間",
                            yaxis_title="発電量",
                            plot_bgcolor="white",
                            hovermode="x unified",
                            height=400
                        )


                        st.plotly_chart(
                            fig_power,
                            use_container_width=True
                        )


                        display_cols = (
                            ["hour"]
                            + available_power_cols
                        )


                        if display_cols:

                            st.dataframe(
                                day_df[display_cols],
                                use_container_width=True,
                                hide_index=True
                            )


    # ========================================================
    # Section 2
    # ========================================================

    st.header(
        "🤖 AIでデータを予測してみよう"
    )


    # ========================================================
    # 2-1 Weather
    # ========================================================

    if df is not None:

        with st.container(border=True):

            st.subheader(
                "2-1. 日時から気象情報を予測"
            )


            st.info(
                "**予測モデルの仕様**\n\n"
                "• 入力値：年、月、日、時間\n"
                "• 出力：気温、相対湿度、降水量、風速、日射量、天気\n"
                "• 機械学習モデルによる予測"
            )


            detected_location = location_name


            uploaded_name = st.session_state.get(
                "uploaded_file_name",
                ""
            )


            if "Kumagaya" in uploaded_name:
                detected_location = "kumagaya"

            elif "Sendai" in uploaded_name:
                detected_location = "sendai"


            location_display = (
                "熊谷（東京電力）"
                if detected_location == "kumagaya"
                else "仙台（東北電力）"
            )


            st.info(
                f"📍 {location_display}のモデルを使用します"
            )


            col1, col2 = st.columns(2)


            with col1:

                pred_year = st.number_input(
                    "年",
                    min_value=2026,
                    max_value=2040,
                    value=2026,
                    step=1,
                    key="weather_pred_year"
                )


                pred_month = st.selectbox(
                    "月",
                    list(range(1, 13)),
                    index=9,
                    format_func=lambda x: f"{x:02d}月",
                    key="weather_pred_month"
                )


                pred_day = st.number_input(
                    "日",
                    min_value=1,
                    max_value=31,
                    value=1,
                    step=1,
                    key="weather_pred_day"
                )


                pred_hour = st.selectbox(
                    "時間",
                    list(range(24)),
                    index=12,
                    format_func=lambda x: f"{x:02d}:00",
                    key="weather_pred_hour"
                )


            with col2:

                try:

                    date_obj = datetime.date(
                        int(pred_year),
                        int(pred_month),
                        int(pred_day)
                    )


                    weekday_jp = Weekday_List[
                        date_obj.weekday()
                    ]


                    st.info(
                        f"🗓️ "
                        f"{date_obj.strftime('%Y年%m月%d日')} "
                        f"{int(pred_hour):02d}:00\n\n"
                        f"曜日：{weekday_jp}"
                    )


                except ValueError:

                    st.warning(
                        "⚠️ 無効な日付です"
                    )


            if st.button(
                "🔮 気象を予測",
                key=f"predict_weather_{detected_location}",
                use_container_width=True
            ):

                try:

                    models_dict, weather_scaler = (
                        load_weather_prediction_models(
                            detected_location
                        )
                    )


                    if (
                        all(
                            v is not None
                            for v in models_dict.values()
                        )
                        and weather_scaler is not None
                    ):

                        weather_pred = (
                            predict_weather_from_datetime(
                                models_dict,
                                weather_scaler,
                                int(pred_year),
                                int(pred_month),
                                int(pred_day),
                                int(pred_hour)
                            )
                        )


                        st.success(
                            "✓ 気象予測が完了しました"
                        )


                        col1, col2, col3 = (
                            st.columns(3)
                        )


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


                        result_df = pd.DataFrame({
                            "気象要素": [
                                "気温",
                                "相対湿度",
                                "降水量",
                                "風速",
                                "日射量",
                                "天気"
                            ],

                            "予測値": [
                                f"{weather_pred.get('気温', 0):.2f}°C",
                                f"{weather_pred.get('相対湿度', 0):.2f}%",
                                f"{weather_pred.get('降水量', 0):.2f}mm",
                                f"{weather_pred.get('風速', 0):.2f}m/s",
                                f"{weather_pred.get('日射量', 0):.2f}W/m²",
                                f"{weather_pred.get('天気', 0):.4f}"
                            ]
                        })


                        st.dataframe(
                            result_df,
                            use_container_width=True,
                            hide_index=True
                        )


                    else:

                        st.error(
                            "❌ 気象モデルの読み込みに失敗しました。"
                        )


                except Exception as e:

                    st.error(
                        f"❌ 気象予測中にエラーが発生しました: {e}"
                    )

                    with st.expander(
                        "詳細エラー"
                    ):

                        st.code(
                            traceback.format_exc()
                        )


    # ========================================================
    # 2-2 Combine
    # ========================================================

    with st.container(border=True):

        st.subheader(
            "2-2. 予測条件を入力"
        )


        st.write(
            "**表示する発電方式**"
        )


        col_chk1, col_chk2, col_chk3, col_chk4, col_chk5 = (
            st.columns(5)
        )


        with col_chk1:
            show_thermal = st.checkbox(
                "🔥火力",
                value=True,
                key=f"show_thermal_{model_suffix}"
            )


        with col_chk2:
            show_solar_power = st.checkbox(
                "☀️太陽光",
                value=False,
                key=f"show_solar_{model_suffix}"
            )


        with col_chk3:
            show_wind = st.checkbox(
                "🌬️風力",
                value=False,
                key=f"show_wind_{model_suffix}"
            )


        with col_chk4:
            show_hydro = st.checkbox(
                "💧水力",
                value=False,
                key=f"show_hydro_{model_suffix}"
            )


        with col_chk5:
            show_nuclear = st.checkbox(
                "☢️原子力",
                value=False,
                key=f"show_nuclear_{model_suffix}"
            )


        col1, col2, col3 = st.columns(3)


        with col1:

            st.write(
                "**日時情報**"
            )


            min_date = datetime.date(
                2026,
                10,
                1
            )


            max_date = datetime.date(
                2040,
                12,
                31
            )


            pred_date = st.date_input(
                "予測したい日",
                min_date,
                min_value=min_date,
                max_value=max_date,
                key=f"date_{model_suffix}"
            )


            select_hour = st.selectbox(
                "時間を選択",
                list(range(24)),
                index=12,
                key=f"hour_{model_suffix}"
            )


            select_month = pred_date.month
            select_day = pred_date.day
            select_weekday = pred_date.weekday()


            st.info(
                f"🗓️ "
                f"{pred_date.strftime('%Y年%m月%d日')} "
                f"{select_hour}時 "
                f"({Weekday_List[select_weekday]})"
            )


        with col2:

            st.write(
                "**気象条件**"
            )


            temp_options = list(
                np.arange(0, 41, 1)
            )


            select_temp = st.selectbox(
                "気温(℃)",
                temp_options,
                index=20,
                key=f"temp_{model_suffix}"
            )


            rain_options = [
                0,
                0.5,
                1.0,
                2.0,
                5.0,
                10.0,
                20.0,
                50.0
            ]


            select_rain = st.selectbox(
                "降水量(mm)",
                rain_options,
                index=0,
                key=f"rain_{model_suffix}"
            )


            wind_options = list(
                np.arange(0, 21, 1)
            )


            select_wind = st.selectbox(
                "風速(m/s)",
                wind_options,
                index=3,
                key=f"wind_{model_suffix}"
            )


        with col3:

            st.write(
                "**その他**"
            )


            humidity_options = list(
                range(0, 101, 10)
            )


            select_humidity = st.selectbox(
                "相対湿度(%)",
                humidity_options,
                index=6,
                key=f"humidity_{model_suffix}"
            )


            solar_options = list(
                np.arange(0, 1001, 50)
            )


            select_solar = st.selectbox(
                "日射量(W/m²)",
                solar_options,
                index=3,
                key=f"solar_{model_suffix}"
            )


            weather_types = [
                "晴れ",
                "曇り",
                "雨",
                "雪"
            ]


            select_weather = st.selectbox(
                "天気",
                weather_types,
                index=0,
                key=f"weather_{model_suffix}"
            )


        # ====================================================
        # Prediction
        # ====================================================

        if st.button(
            "🔮 AI予測スタート",
            key=f"predict_{model_suffix}",
            use_container_width=True
        ):

            combination_name = (
                get_model_combination_name(
                    show_nuclear,
                    show_thermal,
                    show_hydro,
                    show_solar_power,
                    show_wind
                )
            )


            if combination_name is None:

                st.error(
                    "❌ 予測する発電方式を"
                    "最低1つ選択してください"
                )

            else:

                try:

                    combine_model, combine_scaler, feature_names = (
                        load_combine_model(
                            location_name,
                            combination_name
                        )
                    )


                    if combine_model is None:

                        st.error(
                            "❌ Combine_Modelを読み込めませんでした。"
                        )

                    else:

                        input_data = {

                            "気温": select_temp,

                            "降水量": select_rain,

                            "風速": select_wind,

                            "相対湿度": select_humidity,

                            "日射量": select_solar,

                            "月": select_month,

                            "時間": select_hour,

                            "曜日": select_weekday,

                            "日": select_day,

                            "季節": get_season(
                                select_month
                            )
                        }


                        predictions = (
                            predict_combine_model(
                                combine_model,
                                combine_scaler,
                                input_data
                            )
                        )


                        st.success(
                            "✓ 予測が完了しました"
                        )


                        result_data = {}


                        for i, name in enumerate(
                            feature_names
                        ):

                            if i >= len(predictions):
                                break

                            result_data[name] = max(
                                0,
                                round(
                                    float(
                                        predictions[i]
                                    ),
                                    1
                                )
                            )


                        total = sum(
                            result_data.values()
                        )


                        if result_data:

                            cols = st.columns(
                                len(result_data)
                            )


                            for idx, (
                                name,
                                value
                            ) in enumerate(
                                result_data.items()
                            ):

                                with cols[idx]:

                                    percentage = (
                                        value / total * 100
                                        if total > 0
                                        else 0
                                    )


                                    st.metric(
                                        name,
                                        f"{value:,.0f}MW",
                                        delta=(
                                            f"{percentage:.1f}%"
                                        ),
                                        delta_color="off"
                                    )


                        colors = [
                            "#FFD700",
                            "#FF6B6B",
                            "#4ECDC4",
                            "#95E1D3",
                            "#4A90E2"
                        ]


                        fig_result = go.Figure(
                            data=[
                                go.Bar(
                                    x=list(
                                        result_data.keys()
                                    ),
                                    y=list(
                                        result_data.values()
                                    ),
                                    marker=dict(
                                        color=colors[
                                            :len(result_data)
                                        ]
                                    ),
                                    text=[
                                        f"{v:,.0f}MW"
                                        for v
                                        in result_data.values()
                                    ],
                                    textposition="auto"
                                )
                            ]
                        )


                        fig_result.update_layout(
                            title="電力供給構成の予測",
                            yaxis_title="発電量(MW)",
                            plot_bgcolor="white",
                            height=400,
                            showlegend=False
                        )


                        fig_pie = go.Figure(
                            data=[
                                go.Pie(
                                    labels=list(
                                        result_data.keys()
                                    ),
                                    values=list(
                                        result_data.values()
                                    ),
                                    marker=dict(
                                        colors=colors[
                                            :len(result_data)
                                        ]
                                    ),
                                    textposition="inside",
                                    textinfo="label+percent"
                                )
                            ]
                        )


                        fig_pie.update_layout(
                            title="電力供給構成",
                            height=400
                        )


                        col_chart1, col_chart2 = (
                            st.columns(2)
                        )


                        with col_chart1:

                            st.plotly_chart(
                                fig_result,
                                use_container_width=True
                            )


                        with col_chart2:

                            st.plotly_chart(
                                fig_pie,
                                use_container_width=True
                            )


                        st.subheader(
                            "詳細情報"
                        )


                        info_col1, info_col2 = (
                            st.columns(2)
                        )


                        with info_col1:

                            info_df = pd.DataFrame({

                                "項目": [
                                    "日時",
                                    "気温",
                                    "降水量",
                                    "風速",
                                    "相対湿度",
                                    "日射量",
                                    "天気"
                                ],

                                "値": [

                                    pred_date.strftime(
                                        "%Y/%m/%d"
                                    )
                                    + f" {select_hour:02d}:00",

                                    f"{select_temp}℃",

                                    f"{select_rain}mm",

                                    f"{select_wind}m/s",

                                    f"{select_humidity}%",

                                    f"{select_solar}W/m²",

                                    select_weather
                                ]
                            })


                            st.dataframe(
                                info_df,
                                use_container_width=True,
                                hide_index=True
                            )


                        with info_col2:

                            result_display = (
                                list(
                                    result_data.items()
                                )
                                + [
                                    ("合計", total)
                                ]
                            )


                            result_df = pd.DataFrame(
                                result_display,
                                columns=[
                                    "発電方式",
                                    "発電量(MW)"
                                ]
                            )


                            result_df[
                                "構成比"
                            ] = result_df[
                                "発電量(MW)"
                            ].apply(
                                lambda x:
                                f"{x / total * 100:.1f}%"
                                if total > 0
                                else "0%"
                            )


                            st.dataframe(
                                result_df,
                                use_container_width=True,
                                hide_index=True
                            )


                except Exception as e:

                    st.error(
                        f"❌ 予測中にエラーが発生しました: {e}"
                    )

                    with st.expander(
                        "詳細エラー"
                    ):

                        st.code(
                            traceback.format_exc()
                        )


    # ========================================================
    # Section 2-3
    # ========================================================

    st.header(
        "🔌 火力と太陽光から発電源を予測"
    )


    with st.container(border=True):

        st.subheader(
            "2-3. 火力と太陽光から他の発電源を予測"
        )


        st.info(
            "**予測モデルの仕様**\n\n"
            "• 入力値：火力発電（合計）+ 太陽光発電のみ\n"
            "• 出力：原子力・風力・水力の発電量を予測\n"
            "• 気象情報・時系列情報は使用しません\n"
            "• 火力は個別種類ではなく合計値を使用します"
        )


        col1, col2 = st.columns(2)


        with col1:

            st.write(
                "**発電量の入力**"
            )


            thermal_input = st.number_input(
                "火力発電合計(MW)",
                min_value=0.0,
                max_value=50000.0,
                value=10000.0,
                step=500.0,
                key=f"thermal_input_{model_suffix}"
            )


            solar_input = st.number_input(
                "太陽光発電(MW)",
                min_value=0.0,
                max_value=10000.0,
                value=2000.0,
                step=100.0,
                key=f"solar_input_{model_suffix}"
            )


        if st.button(
            "🔮 発電源を予測",
            key=f"predict_2_3_{model_suffix}",
            use_container_width=True
        ):

            try:

                models_dict, scaler_2_3 = (
                    load_power_prediction_models(
                        location_name
                    )
                )


                if (
                    not any(
                        model is not None
                        for model
                        in models_dict.values()
                    )
                ):

                    st.error(
                        "❌ 発電モデルが見つかりません。"
                    )

                    st.stop()


                predictions_2_3 = (
                    predict_from_thermal_solar(
                        models_dict,
                        scaler_2_3,
                        thermal_input,
                        solar_input,
                        {}
                    )
                )


                result_nuclear = max(
                    0,
                    round(
                        predictions_2_3.get(
                            "原子力",
                            0
                        ),
                        1
                    )
                )


                result_wind = max(
                    0,
                    round(
                        predictions_2_3.get(
                            "風力発電実績",
                            0
                        ),
                        1
                    )
                )


                result_hydro = max(
                    0,
                    round(
                        predictions_2_3.get(
                            "水力",
                            0
                        ),
                        1
                    )
                )


                total_all = (
                    thermal_input
                    + solar_input
                    + result_nuclear
                    + result_wind
                    + result_hydro
                )


                st.success(
                    "✓ 予測が完了しました"
                )


                st.subheader(
                    "📊 予測結果"
                )


                col1, col2, col3 = (
                    st.columns(3)
                )


                for container, label, value in [
                    (
                        col1,
                        "原子力発電（予測）",
                        result_nuclear
                    ),
                    (
                        col2,
                        "風力発電（予測）",
                        result_wind
                    ),
                    (
                        col3,
                        "水力発電（予測）",
                        result_hydro
                    )
                ]:

                    with container:

                        percentage = (
                            value / total_all * 100
                            if total_all > 0
                            else 0
                        )


                        st.metric(
                            label,
                            f"{value:,.0f}MW",
                            delta=f"{percentage:.1f}%",
                            delta_color="off"
                        )


                all_sources = {

                    "原子力":
                        result_nuclear,

                    "火力":
                        thermal_input,

                    "太陽光":
                        solar_input,

                    "風力":
                        result_wind,

                    "水力":
                        result_hydro
                }


                fig_pie = go.Figure(
                    data=[
                        go.Pie(
                            labels=list(
                                all_sources.keys()
                            ),
                            values=list(
                                all_sources.values()
                            ),
                            marker=dict(
                                colors=[
                                    "#FFD700",
                                    "#FF6B6B",
                                    "#4ECDC4",
                                    "#95E1D3",
                                    "#4A90E2"
                                ]
                            ),
                            textposition="inside",
                            textinfo="label+percent",
                            hovertemplate=(
                                "<b>%{label}</b><br>"
                                "発電量: %{value:.0f}MW<br>"
                                "構成比: %{percent}"
                                "<extra></extra>"
                            )
                        )
                    ]
                )


                fig_pie.update_layout(
                    title=(
                        "火力と太陽光から予測した"
                        "電力供給構成"
                    ),
                    height=500
                )


                st.plotly_chart(
                    fig_pie,
                    use_container_width=True
                )


                result_df = pd.DataFrame({

                    "発電方式": [
                        "原子力",
                        "火力",
                        "太陽光",
                        "風力",
                        "水力",
                        "合計"
                    ],

                    "発電量(MW)": [
                        f"{result_nuclear:,.1f}",
                        f"{thermal_input:,.1f}",
                        f"{solar_input:,.1f}",
                        f"{result_wind:,.1f}",
                        f"{result_hydro:,.1f}",
                        f"{total_all:,.1f}"
                    ],

                    "構成比": [

                        (
                            f"{result_nuclear / total_all * 100:.1f}%"
                            if total_all > 0
                            else "0%"
                        ),

                        (
                            f"{thermal_input / total_all * 100:.1f}%"
                            if total_all > 0
                            else "0%"
                        ),

                        (
                            f"{solar_input / total_all * 100:.1f}%"
                            if total_all > 0
                            else "0%"
                        ),

                        (
                            f"{result_wind / total_all * 100:.1f}%"
                            if total_all > 0
                            else "0%"
                        ),

                        (
                            f"{result_hydro / total_all * 100:.1f}%"
                            if total_all > 0
                            else "0%"
                        ),

                        "100%"
                    ]
                })


                st.dataframe(
                    result_df,
                    use_container_width=True,
                    hide_index=True
                )


                st.subheader(
                    "📋 入力条件"
                )


                input_df = pd.DataFrame({

                    "項目": [
                        "火力発電（合計）",
                        "太陽光発電"
                    ],

                    "値": [
                        f"{thermal_input:,.0f}MW",
                        f"{solar_input:,.0f}MW"
                    ]
                })


                st.dataframe(
                    input_df,
                    use_container_width=True,
                    hide_index=True
                )


            except Exception as e:

                st.error(
                    f"❌ 発電予測中にエラーが発生しました: {e}"
                )

                with st.expander(
                    "詳細エラー"
                ):

                    st.code(
                        traceback.format_exc()
                    )


    # ========================================================
    # Model status
    # ========================================================

    with st.expander(
        "🔧 モデルファイルの状態"
    ):

        st.write(
            f"BASE_DIR: `{BASE_DIR}`"
        )

        st.write(
            f"Temp: `{TEMP_DIR}`"
        )

        st.write(
            f"Google Drive: `{GOOGLE_DRIVE_FOLDER_URL}`"
        )


        current_count = count_required_files()


        st.write(
            f"確認済み必要モデル: "
            f"{current_count}/{len(REQUIRED_FILES)}"
        )


        if current_count < len(REQUIRED_FILES):

            st.warning(
                "一部のモデルファイルが見つかりません。"
            )


        for directory_name in [
            "models",
            "Weather_Model",
            "Combine_Model"
        ]:

            directory = (
                BASE_DIR
                / directory_name
            )


            if directory.exists():

                files = [
                    p
                    for p in directory.rglob("*")
                    if p.is_file()
                ]


                st.write(
                    f"**{directory_name}**: "
                    f"{len(files)} files"
                )

            else:

                st.write(
                    f"**{directory_name}**: "
                    "❌ directory not found"
                )


    # ========================================================
    # Footer
    # ========================================================

    st.markdown("---")


    st.markdown(
        """
        <div style='text-align: center; color: #888; font-size: 12px;'>
        <p>⚡ 天気・電力データ分析ツール v1.0</p>
        <p>機械学習モデルによる予測ツール</p>
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":

    main()
