# -*- coding: utf-8 -*-
"""
Weather & Power Data Analysis and Prediction Tool
Author: TAJ2HIG
Date: 2026-09-26

Google Driveからモデルを自動取得する完全版

【重要】
gdown 6.4.0 対応版

- download_folder() に remaining_ok を渡さない
- モデルが存在する場合は再ダウンロードしない
- Google Driveから .gdrive_temp にダウンロード
- ダウンロード完了後にBASE_DIRへ配置
- モデル不足時だけGoogle Driveへ接続
- ダウンロード処理のタイムアウトを設定
"""

import streamlit as st
import pandas as pd
import numpy as np
import pickle
import joblib
import datetime
import plotly.graph_objects as go

from pathlib import Path
from datetime import datetime as dt

import hashlib
import warnings
import os
import shutil
import time
import threading


# =============================================================================
# WARNING
# =============================================================================

warnings.filterwarnings("ignore", category=Warning, module="sklearn")
warnings.filterwarnings("ignore", message="Trying to unpickle estimator")


# =============================================================================
# BASE DIRECTORY
# =============================================================================

def get_base_dir():
    """アプリ本体が存在するディレクトリを取得"""

    try:
        return Path(__file__).resolve().parent
    except Exception:
        return Path(os.getcwd()).resolve()


BASE_DIR = get_base_dir()

# Google Driveから一時保存する場所
TEMP_DIR = BASE_DIR / ".gdrive_temp"

# Google Drive Folder ID
GOOGLE_DRIVE_FOLDER_ID = "11CrLEAr_ljmYx1Ib5TPpWG_kvwDElNgS"

GOOGLE_DRIVE_FOLDER_URL = (
    f"https://drive.google.com/drive/folders/{GOOGLE_DRIVE_FOLDER_ID}"
)


# =============================================================================
# MODELS
# =============================================================================

MODELS = {
    "東京電力（Toden）": {
        "suffix": "toden",
        "location": "熊谷",
        "location_name": "kumagaya",
        "color": "rgb(220, 53, 69)",
        "csv_file": "all_data_Kumagaya.csv",
    },
    "東北電力（Tohoku）": {
        "suffix": "tohoku",
        "location": "仙台",
        "location_name": "sendai",
        "color": "rgb(0, 102, 204)",
        "csv_file": "all_data_Sendai.csv",
    },
}


Weekday_List = [
    "月曜日",
    "火曜日",
    "水曜日",
    "木曜日",
    "金曜日",
    "土曜日",
    "日曜日",
]


# =============================================================================
# MODEL FILE DEFINITIONS
# =============================================================================

def get_required_model_files():
    """
    アプリで使用するモデルファイル一覧。

    「旧形式」
    model_toden_power_weather.pkl
    scaler_toden_power_weather.pkl
    feature_cols_toden.pkl

    「2-3」
    models/
    Weather_Model/
    Combine_Model/

    をまとめて対象にする。
    """

    files = []

    # -------------------------------------------------------------------------
    # 旧モデル
    # -------------------------------------------------------------------------

    for suffix in ["toden", "tohoku"]:
        files.extend([
            f"model_{suffix}_power_weather.pkl",
            f"scaler_{suffix}_power_weather.pkl",
            f"feature_cols_{suffix}.pkl",
        ])

    # -------------------------------------------------------------------------
    # 2-3 Power Model
    # -------------------------------------------------------------------------

    for location in ["kumagaya", "sendai"]:

        for model_type in [
            "原子力",
            "風力発電実績",
            "水力",
        ]:
            files.append(
                f"models/model_{location}_{model_type}.pkl"
            )

        files.append(
            f"models/scaler_{location}.pkl"
        )

    # -------------------------------------------------------------------------
    # Weather Model
    # -------------------------------------------------------------------------

    for location in ["kumagaya", "sendai"]:

        for element in [
            "気温",
            "相対湿度",
            "降水量",
            "風速",
            "日射量",
            "天気",
        ]:
            files.append(
                f"Weather_Model/model_{location}_{element}.pkl"
            )

        files.append(
            f"Weather_Model/scaler_{location}.pkl"
        )

    # -------------------------------------------------------------------------
    # Combine Model
    # -------------------------------------------------------------------------

    combinations = [
        ("01", "原子力"),
        ("02", "火力"),
        ("03", "水力"),
        ("04", "太陽光発電実績"),
        ("05", "風力発電実績"),
        ("06", "原子力_火力"),
        ("07", "原子力_水力"),
        ("08", "原子力_太陽光発電実績"),
        ("09", "原子力_風力発電実績"),
        ("10", "火力_水力"),
        ("11", "火力_太陽光発電実績"),
        ("12", "火力_風力発電実績"),
        ("13", "水力_太陽光発電実績"),
        ("14", "水力_風力発電実績"),
        ("15", "太陽光発電実績_風力発電実績"),
        ("16", "原子力_火力_水力"),
        ("17", "原子力_火力_太陽光発電実績"),
        ("18", "原子力_火力_風力発電実績"),
        ("19", "原子力_水力_太陽光発電実績"),
        ("20", "原子力_水力_風力発電実績"),
        ("21", "原子力_太陽光発電実績_風力発電実績"),
        ("22", "火力_水力_太陽光発電実績"),
        ("23", "火力_水力_風力発電実績"),
        ("24", "火力_太陽光発電実績_風力発電実績"),
        ("25", "水力_太陽光発電実績_風力発電実績"),
        ("26", "原子力_火力_水力_太陽光発電実績"),
        ("27", "原子力_火力_水力_風力発電実績"),
        ("28", "原子力_火力_太陽光発電実績_風力発電実績"),
        ("29", "原子力_水力_太陽光発電実績_風力発電実績"),
        ("30", "火力_水力_太陽光発電実績_風力発電実績"),
        ("31", "原子力_火力_水力_太陽光発電実績_風力発電実績"),
    ]

    for suffix in ["toden", "tohoku"]:

        for number, combination in combinations:

            files.append(
                f"Combine_Model/model_{suffix}_{number}_{combination}.pkl"
            )

            files.append(
                f"Combine_Model/scaler_{suffix}_{number}_{combination}.pkl"
            )

            files.append(
                f"Combine_Model/info_{suffix}_{number}_{combination}.json"
            )

    return files


# =============================================================================
# MODEL CHECK
# =============================================================================

def get_missing_model_files():
    """
    現在のBASE_DIRに存在しないモデルを取得。
    """

    missing = []

    for relative_path in get_required_model_files():

        path = BASE_DIR / relative_path

        if not path.exists():
            missing.append(relative_path)

    return missing


def get_existing_model_count():
    """
    存在するモデル数を取得。
    """

    all_files = get_required_model_files()

    existing = 0

    for relative_path in all_files:

        if (BASE_DIR / relative_path).exists():
            existing += 1

    return existing, len(all_files)


# =============================================================================
# GOOGLE DRIVE DOWNLOAD
# =============================================================================

def _run_gdrive_download(result_holder):
    """
    Google Driveダウンロードを別スレッドで実行。

    gdown 6.4.0対応版。
    - download_folder() に remaining_ok は指定しない
    - 通信タイムアウトを30秒に設定
    - 一時的な通信エラーは3回までリトライ
    - 途中まで取得したファイルは resume=True で再利用
    """
    try:
        import gdown

        result_holder["started"] = True
        result_holder["version"] = getattr(gdown, "__version__", "unknown")

        # gdown 6.3以降は download_folder() に timeout / retries / resume
        # を指定できる。5分間ずっと通信待ちになる問題を避けるため、
        # 「1回の通信待ち」を30秒に制限し、途中失敗は再試行する。
        downloaded = gdown.download_folder(
            id=GOOGLE_DRIVE_FOLDER_ID,
            output=str(TEMP_DIR),
            quiet=False,
            use_cookies=False,
            resume=True,
            timeout=30,
            retries=3,
        )

        result_holder["result"] = downloaded
        result_holder["finished"] = True

    except Exception as e:
        result_holder["error"] = f"{type(e).__name__}: {e}"
        result_holder["finished"] = True

def download_models_from_gdrive(force=False):
    """
    Google Driveからモデルをダウンロード。

    重要：
    モデルが全部存在する場合はGoogle Driveへ接続しない。

    Returns
    -------
    bool
        モデルが使用可能ならTrue
    """

    # =========================================================================
    # まずローカル確認
    # =========================================================================

    existing, total = get_existing_model_count()

    st.write(
        f"📦 モデルファイル確認: {existing}/{total}"
    )

    missing = get_missing_model_files()

    if len(missing) == 0 and not force:

        st.success(
            "✅ 必要なモデルファイルはすべて存在します。"
        )

        return True

    # =========================================================================
    # 不足モデル表示
    # =========================================================================

    st.warning(
        f"⚠️ モデルファイルが {len(missing)} 個不足しています。"
    )

    with st.expander("不足しているモデルファイル", expanded=False):

        for file in missing[:100]:
            st.write(f"- `{file}`")

        if len(missing) > 100:
            st.write(
                f"... その他 {len(missing) - 100} ファイル"
            )

    # =========================================================================
    # TEMP DIRECTORY
    # =========================================================================

    try:

        TEMP_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

    except Exception as e:

        st.error(
            f"❌ 一時フォルダを作成できません: {e}"
        )

        return False

    # =========================================================================
    # Google Drive接続
    # =========================================================================

    st.info(
        "📥 Google Driveからモデルを取得します。\n\n"
        "初回のみ時間がかかる場合があります。"
    )

    st.code(
        f"Google Drive Folder ID:\n{GOOGLE_DRIVE_FOLDER_ID}"
    )

    st.write(
        f"一時保存先: `{TEMP_DIR}`"
    )

    # =========================================================================
    # gdownバージョン
    # =========================================================================

    try:

        import gdown

        st.write(
            f"gdown version: `{getattr(gdown, '__version__', 'unknown')}`"
        )

    except Exception as e:

        st.error(
            f"❌ gdownを読み込めません: {e}"
        )

        return False

    # =========================================================================
    # ダウンロード開始
    # =========================================================================

    result_holder = {
        "started": False,
        "finished": False,
        "result": None,
        "error": None,
    }

    st.write("🔄 Google Driveフォルダ取得を開始します...")

    thread = threading.Thread(
        target=_run_gdrive_download,
        args=(result_holder,),
        daemon=True,
    )

    thread.start()

    # =========================================================================
    # タイムアウト監視
    # =========================================================================

    # 214ファイルを取得するため、全体の制限時間は30分にする。
    # 各通信そのものは gdown 側の timeout=30 で制御する。
    timeout_seconds = 1800

    start_time = time.time()

    progress = st.progress(0)

    status = st.empty()

    while thread.is_alive():

        elapsed = int(time.time() - start_time)

        percent = min(
            int(elapsed / timeout_seconds * 100),
            99
        )

        progress.progress(percent)

        status.info(
            f"📥 Google Driveからモデルを取得中... "
            f"{elapsed}秒経過"
        )

        # ---------------------------------------------------------------------
        # 5分経過
        # ---------------------------------------------------------------------

        if elapsed >= timeout_seconds:

            status.error(
                "❌ Google Driveからの取得が30分を超えたため停止しました。"
            )

            st.warning(
                "Google Driveフォルダへのアクセスに時間がかかりすぎています。\n\n"
                "gdownは1回の通信を30秒でタイムアウトし、最大3回リトライします。\n\n"
                "次を確認してください。\n"
                "1. Google Driveフォルダが「リンクを知っている全員」に公開されている\n"
                "2. 「リンクを知っている全員」が閲覧可能\n"
                "3. フォルダ内のモデル数が多すぎない\n"
                "4. Streamlit CloudからGoogle Driveへアクセスできる"
            )

            return False

        time.sleep(1)

    progress.progress(100)

    # =========================================================================
    # エラー確認
    # =========================================================================

    if result_holder.get("error"):

        st.error(
            "❌ Google Driveからのモデル取得に失敗しました。"
        )

        st.code(
            result_holder["error"]
        )

        return False

    # =========================================================================
    # TEMP → BASE_DIRへコピー
    # =========================================================================

    st.write(
        "📂 ダウンロードしたモデルを配置しています..."
    )

    copied = 0

    if TEMP_DIR.exists():

        for src in TEMP_DIR.rglob("*"):

            if not src.is_file():
                continue

            try:

                relative = src.relative_to(TEMP_DIR)

                dst = BASE_DIR / relative

                dst.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                shutil.copy2(
                    src,
                    dst
                )

                copied += 1

            except Exception as e:

                st.warning(
                    f"⚠️ ファイル配置失敗: {src.name} / {e}"
                )

    st.write(
        f"📦 {copied} ファイルを配置しました。"
    )

    # =========================================================================
    # 最終確認
    # =========================================================================

    missing_after = get_missing_model_files()

    if len(missing_after) == 0:

        st.success(
            "✅ モデルファイルの準備が完了しました。"
        )

        return True

    # =========================================================================
    # 一部不足
    # =========================================================================

    st.error(
        f"❌ モデルがまだ {len(missing_after)} 個不足しています。"
    )

    with st.expander("取得できなかったファイル"):

        for file in missing_after[:100]:
            st.write(f"- `{file}`")

    return False


# =============================================================================
# STARTUP MODEL INITIALIZATION
# =============================================================================

@st.cache_resource
def initialize_models_once():
    """
    Streamlit起動時のモデル準備。

    ここをcache_resourceにすることで、
    同一Streamlitプロセスで何度もGoogle Driveへ接続しない。
    """

    missing = get_missing_model_files()

    if not missing:

        return True

    return download_models_from_gdrive()


# =============================================================================
# WEATHER / POWER MODEL
# =============================================================================

@st.cache_resource
def load_models_and_data(model_suffix):

    work_dir = BASE_DIR

    model_file = (
        work_dir /
        f"model_{model_suffix}_power_weather.pkl"
    )

    scaler_file = (
        work_dir /
        f"scaler_{model_suffix}_power_weather.pkl"
    )

    feature_file = (
        work_dir /
        f"feature_cols_{model_suffix}.pkl"
    )

    missing = [
        p for p in [
            model_file,
            scaler_file,
            feature_file,
        ]
        if not p.exists()
    ]

    if missing:

        raise FileNotFoundError(
            "必要なモデルファイルがありません:\n"
            + "\n".join(str(x) for x in missing)
        )

    with open(model_file, "rb") as f:
        model = pickle.load(f)

    with open(scaler_file, "rb") as f:
        scaler = pickle.load(f)

    with open(feature_file, "rb") as f:
        feature_cols = pickle.load(f)

    return model, scaler, feature_cols


# =============================================================================
# POWER MODEL
# =============================================================================

@st.cache_resource
def load_power_prediction_models(location_name):

    work_dir = BASE_DIR / "models"

    models_dict = {}

    model_types = [
        "原子力",
        "風力発電実績",
        "水力",
    ]

    for model_type in model_types:

        model_file = (
            work_dir /
            f"model_{location_name}_{model_type}.pkl"
        )

        if not model_file.exists():

            models_dict[model_type] = None

        else:

            try:

                models_dict[model_type] = joblib.load(
                    model_file
                )

            except Exception as e:

                st.error(
                    f"❌ {model_type}モデルの読み込み失敗: {e}"
                )

                models_dict[model_type] = None

    scaler_file = (
        work_dir /
        f"scaler_{location_name}.pkl"
    )

    if scaler_file.exists():

        try:
            scaler = joblib.load(scaler_file)

        except Exception as e:

            st.error(
                f"❌ スケーラー読み込み失敗: {e}"
            )

            scaler = None

    else:

        scaler = None

    return models_dict, scaler


def predict_from_thermal_solar(
    models_dict,
    scaler,
    thermal_value,
    solar_value,
    input_data=None
):

    X = np.array([
        thermal_value,
        solar_value,
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
                f"⚠️ スケーラー変換失敗: {e}"
            )

            X_scaled = X

    else:

        X_scaled = X

    predictions = {}

    for model_type, model in models_dict.items():

        if model is None:

            predictions[model_type] = 0.0
            continue

        try:

            pred = model.predict(X_scaled)

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


# =============================================================================
# DATA
# =============================================================================

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

        df["date"] = df["DateTime"].dt.date
        df["hour"] = df["DateTime"].dt.hour
        df["day_str"] = df["DateTime"].dt.strftime(
            "%Y-%m-%d"
        )
        df["month_str"] = df["DateTime"].dt.strftime(
            "%y/%m"
        )

    thermal_cols = [
        "火力(LNG)",
        "火力(石炭)",
        "火力(石油)",
        "火力(その他)",
    ]

    available = [
        col for col in thermal_cols
        if col in df.columns
    ]

    if available:

        df["火力_合計"] = df[available].sum(
            axis=1
        )

    return df


# =============================================================================
# SEASON
# =============================================================================

def get_season(month):

    if month in [12, 1, 2]:
        return 0

    if month in [3, 4, 5]:
        return 1

    if month in [6, 7, 8]:
        return 2

    return 3


# =============================================================================
# WEATHER MODEL
# =============================================================================

@st.cache_resource
def load_weather_prediction_models(location_name):

    work_dir = BASE_DIR / "Weather_Model"

    models_dict = {}

    weather_elements = [
        "気温",
        "相対湿度",
        "降水量",
        "風速",
        "日射量",
        "天気",
    ]

    for element in weather_elements:

        model_file = (
            work_dir /
            f"model_{location_name}_{element}.pkl"
        )

        if not model_file.exists():

            models_dict[element] = None

        else:

            try:

                models_dict[element] = joblib.load(
                    model_file
                )

            except Exception as e:

                st.error(
                    f"❌ {element}モデル読み込み失敗: {e}"
                )

                models_dict[element] = None

    scaler_file = (
        work_dir /
        f"scaler_{location_name}.pkl"
    )

    if scaler_file.exists():

        try:
            scaler = joblib.load(scaler_file)

        except Exception:

            scaler = None

    else:

        scaler = None

    return models_dict, scaler


def predict_weather_from_datetime(
    models_dict,
    scaler,
    year,
    month,
    day,
    hour
):

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
        day_cos,
    ]).reshape(1, -1)

    if scaler is not None:

        try:

            with warnings.catch_warnings():

                warnings.filterwarnings(
                    "ignore",
                    message="X does not have valid feature names"
                )

                X_scaled = scaler.transform(X)

        except Exception:

            X_scaled = X

    else:

        X_scaled = X

    predictions = {}

    for element, model in models_dict.items():

        if model is None:

            predictions[element] = 0.0
            continue

        try:

            pred = model.predict(
                X_scaled
            )

            value = float(pred[0])

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

        except Exception:

            predictions[element] = 0.0

    return predictions


# =============================================================================
# COMBINE MODEL
# =============================================================================

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


@st.cache_resource
def load_combine_model(
    location_name,
    combination_name
):

    work_dir = BASE_DIR / "Combine_Model"

    model_suffix = (
        "toden"
        if location_name == "kumagaya"
        else "tohoku"
    )

    number = COMBINATION_NUMBER_MAP.get(
        combination_name
    )

    if number is None:

        return None, None, None

    model_file = (
        work_dir /
        f"model_{model_suffix}_{number}_{combination_name}.pkl"
    )

    if not model_file.exists():

        st.error(
            f"❌ モデルファイルがありません:\n{model_file}"
        )

        return None, None, None

    try:

        model = joblib.load(
            model_file
        )

    except Exception as e:

        st.error(
            f"❌ Combine Model読み込み失敗: {e}"
        )

        return None, None, None

    scaler_file = (
        work_dir /
        f"scaler_{model_suffix}_{number}_{combination_name}.pkl"
    )

    if scaler_file.exists():

        try:
            scaler = joblib.load(
                scaler_file
            )

        except Exception:

            scaler = None

    else:

        scaler = None

    info_file = (
        work_dir /
        f"info_{model_suffix}_{number}_{combination_name}.json"
    )

    feature_names = None

    if info_file.exists():

        try:

            import json

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

    if feature_names is None:

        feature_names = combination_name.split(
            "_"
        )

    return model, scaler, feature_names


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
        month_cos,
    ]).reshape(1, -1)

    if scaler is not None:

        try:
            X_scaled = scaler.transform(X)

        except Exception as e:

            st.warning(
                f"⚠️ スケーラー変換失敗: {e}"
            )

            X_scaled = X

    else:

        X_scaled = X

    return model.predict(
        X_scaled
    )[0]


# =============================================================================
# SESSION
# =============================================================================

def init_session_state():

    if "current_region" not in st.session_state:

        st.session_state.current_region = (
            "東京電力（Toden）"
        )

    if "df_cache" not in st.session_state:

        st.session_state.df_cache = {}

    if "session_id" not in st.session_state:

        st.session_state.session_id = (
            hashlib.md5(
                str(dt.now()).encode()
            ).hexdigest()[:8]
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    st.set_page_config(
        page_title="天気・電力データ分析ツール",
        page_icon="⚡",
        layout="wide",
    )

    init_session_state()

    st.title(
        "⚡ 天気・電力データ分析ツール"
    )

    st.markdown(
        "気象情報から電力供給構成を予測します"
    )

    # =========================================================================
    # MODEL INITIALIZATION
    # =========================================================================

    with st.container(border=True):

        st.subheader(
            "🔧 モデル準備"
        )

        existing, total = get_existing_model_count()

        st.write(
            f"モデルファイル: **{existing}/{total}**"
        )

        if existing < total:

            with st.spinner(
                "Google Driveからモデルを確認・取得しています..."
            ):

                model_ready = (
                    initialize_models_once()
                )

        else:

            model_ready = True

            st.success(
                "✅ ローカルにモデルが存在します。"
                "Google Driveへの接続は行いません。"
            )

    # =========================================================================
    # 最低限の旧モデル確認
    # =========================================================================

    selected_region = (
        "東京電力（Toden）"
    )

    model_config = MODELS[
        selected_region
    ]

    model_suffix = model_config[
        "suffix"
    ]

    location_name = model_config[
        "location_name"
    ]

    # =========================================================================
    # CSV
    # =========================================================================

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
            help="dataフォルダ内のCSVファイルを選択してください",
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
                    f"が読み込まれました（{len(df)}件）"
                )

                st.session_state[
                    "uploaded_file_name"
                ] = uploaded_file.name

            except Exception as e:

                st.error(
                    f"❌ CSV読み込み失敗: {e}"
                )

        # =====================================================================
        # YEAR GRAPH
        # =====================================================================

        if df is not None:

            st.subheader(
                "1-2. 一年間のデータの変化"
            )

            if "DateTime" in df.columns:

                years = sorted(
                    df["DateTime"]
                    .dt.year
                    .dropna()
                    .unique()
                )

                if len(years) > 0:

                    default_year = 2024

                    default_index = (
                        years.index(default_year)
                        if default_year in years
                        else 0
                    )

                    selected_year = st.selectbox(
                        "確認したい年を選択",
                        years,
                        index=default_index,
                    )

                    df_year = df[
                        df["DateTime"].dt.year
                        == selected_year
                    ]

                    fig = go.Figure()

                    if "気温" in df_year.columns:

                        fig.add_trace(
                            go.Scatter(
                                x=df_year["DateTime"],
                                y=df_year["気温"],
                                name="気温(℃)",
                                line=dict(
                                    color="orange"
                                ),
                            )
                        )

                    if "降水量" in df_year.columns:

                        fig.add_trace(
                            go.Scatter(
                                x=df_year["DateTime"],
                                y=df_year["降水量"],
                                name="降水量(mm)",
                                line=dict(
                                    color="blue"
                                ),
                                    yaxis="y2",
                            )
                        )

                    fig.update_layout(
                        title=f"{selected_year}年の気象データ",
                        xaxis_title="日時",
                        yaxis=dict(
                            title="気温(℃)"
                        ),
                        yaxis2=dict(
                            title="降水量(mm)",
                            overlaying="y",
                            side="right",
                        ),
                        height=500,
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )

                    available_power_cols = [
                        c for c in [
                            "原子力",
                            "火力_合計",
                            "太陽光発電実績",
                        ]
                        if c in df.columns
                    ]

            # =================================================================
            # ONE DAY
            # =================================================================

            st.subheader(
                "1-3. 1日のデータを比較しよう"
            )

            min_date_data = (
                df["DateTime"].min().date()
            )

            max_date_data = (
                df["DateTime"].max().date()
            )

            col1, col2 = st.columns(2)

            with col1:

                date_1 = st.date_input(
                    "比較する1つ目の日付",
                    min_date_data,
                    min_value=min_date_data,
                    max_value=max_date_data,
                    key="date_1_comparison",
                )

            with col2:

                default_date_2 = min(
                    min_date_data
                    + datetime.timedelta(days=1),
                    max_date_data,
                )

                date_2 = st.date_input(
                    "比較する2つ目の日付",
                    default_date_2,
                    min_value=min_date_data,
                    max_value=max_date_data,
                    key="date_2_comparison",
                )

            df1 = df[
                df["day_str"] == str(date_1)
            ]

            df2 = df[
                df["day_str"] == str(date_2)
            ]

            if date_1 != date_2:

                c1, c2 = st.columns(2)

                for col_container, current_df, current_date in [
                    (c1, df1, date_1),
                    (c2, df2, date_2),
                ]:

                    with col_container:

                        if len(current_df) == 0:

                            st.warning(
                                f"{current_date}のデータがありません"
                            )

                            continue

                        fig = go.Figure()

                        if "気温" in current_df.columns:

                            fig.add_trace(
                                go.Scatter(
                                    x=current_df["hour"],
                                    y=current_df["気温"],
                                    name="気温",
                                )
                            )

                        if "降水量" in current_df.columns:

                            fig.add_trace(
                                go.Scatter(
                                    x=current_df["hour"],
                                    y=current_df["降水量"],
                                    name="降水量",
                                    yaxis="y2",
                                )
                            )

                        fig.update_layout(
                            title=str(current_date),
                            xaxis_title="時間",
                            yaxis=dict(
                                title="気温"
                            ),
                            yaxis2=dict(
                                title="降水量",
                                overlaying="y",
                                side="right",
                            ),
                            height=350,
                        )

                        st.plotly_chart(
                            fig,
                            use_container_width=True
                        )

                        if available_power_cols:

                            fig_power = go.Figure()

                            for power_col in available_power_cols:

                                fig_power.add_trace(
                                    go.Bar(
                                        x=current_df["hour"],
                                        y=current_df[
                                            power_col
                                        ],
                                        name=power_col,
                                    )
                                )

                            fig_power.update_layout(
                                barmode="stack",
                                title=f"{current_date} 電力供給構成",
                                height=350,
                            )

                            st.plotly_chart(
                                fig_power,
                                use_container_width=True
                            )

            else:

                st.warning(
                    "⚠️ 2つの日付を別日にしてください。"
                )

    # =========================================================================
    # SECTION 2
    # =========================================================================

    st.header(
        "🤖 AIでデータを予測してみよう"
    )

    # =========================================================================
    # 2-1 WEATHER
    # =========================================================================

    if df is not None:

        with st.container(border=True):

            st.subheader(
                "2-1. 日時から気象情報を予測"
            )

            uploaded_name = st.session_state.get(
                "uploaded_file_name",
                ""
            )

            if "Sendai" in uploaded_name:

                weather_location = "sendai"

            else:

                weather_location = "kumagaya"

            location_display = (
                "仙台（東北電力）"
                if weather_location == "sendai"
                else "熊谷（東京電力）"
            )

            st.info(
                f"📍 {location_display}のモデルを使用"
            )

            col1, col2 = st.columns(2)

            with col1:

                pred_year = st.number_input(
                    "年",
                    min_value=2026,
                    max_value=2040,
                    value=2026,
                    step=1,
                    key="weather_pred_year",
                )

                pred_month = st.selectbox(
                    "月",
                    list(range(1, 13)),
                    index=9,
                    key="weather_pred_month",
                )

                pred_day = st.number_input(
                    "日",
                    min_value=1,
                    max_value=31,
                    value=1,
                    key="weather_pred_day",
                )

                pred_hour = st.selectbox(
                    "時間",
                    list(range(24)),
                    index=12,
                    key="weather_pred_hour",
                )

            with col2:

                try:

                    date_obj = datetime.date(
                        int(pred_year),
                        int(pred_month),
                        int(pred_day),
                    )

                    st.info(
                        f"{date_obj.strftime('%Y年%m月%d日')} "
                        f"{int(pred_hour):02d}:00\n\n"
                        f"{Weekday_List[date_obj.weekday()]}"
                    )

                except ValueError:

                    st.warning(
                        "⚠️ 無効な日付です"
                    )

            if st.button(
                "🔮 気象を予測",
                key=f"predict_weather_{weather_location}",
                use_container_width=True,
            ):

                try:

                    models_dict, weather_scaler = (
                        load_weather_prediction_models(
                            weather_location
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
                                int(pred_hour),
                            )
                        )

                        st.success(
                            "✓ 気象予測が完了しました"
                        )

                        cols = st.columns(3)

                        with cols[0]:

                            st.metric(
                                "気温",
                                f"{weather_pred['気温']:.1f}°C"
                            )

                            st.metric(
                                "相対湿度",
                                f"{weather_pred['相対湿度']:.1f}%"
                            )

                        with cols[1]:

                            st.metric(
                                "降水量",
                                f"{weather_pred['降水量']:.1f}mm"
                            )

                            st.metric(
                                "風速",
                                f"{weather_pred['風速']:.1f}m/s"
                            )

                        with cols[2]:

                            st.metric(
                                "日射量",
                                f"{weather_pred['日射量']:.1f}W/m²"
                            )

                            st.metric(
                                "天気",
                                f"{weather_pred['天気']:.2f}"
                            )

                    else:

                        st.error(
                            "❌ 気象モデルが不足しています。"
                        )

                except Exception as e:

                    st.error(
                        f"❌ 気象予測中にエラー: {e}"
                    )

    # =========================================================================
    # 2-2 COMBINE MODEL
    # =========================================================================

    with st.container(border=True):

        st.subheader(
            "2-2. 予測条件を入力"
        )

        st.write(
            "**表示する発電方式**"
        )

        c1, c2, c3, c4, c5 = st.columns(5)

        with c1:
            show_thermal = st.checkbox(
                "🔥火力",
                value=True
            )

        with c2:
            show_solar_power = st.checkbox(
                "☀️太陽光",
                value=False
            )

        with c3:
            show_wind = st.checkbox(
                "🌬️風力",
                value=False
            )

        with c4:
            show_hydro = st.checkbox(
                "💧水力",
                value=False
            )

        with c5:
            show_nuclear = st.checkbox(
                "☢️原子力",
                value=False
            )

        c1, c2, c3 = st.columns(3)

        with c1:

            pred_date = st.date_input(
                "予測したい日",
                datetime.date(2026, 10, 1),
                min_value=datetime.date(2026, 10, 1),
                max_value=datetime.date(2040, 12, 31),
                key=f"date_{model_suffix}",
            )

            select_hour = st.selectbox(
                "時間を選択",
                list(range(24)),
                index=12,
                key=f"hour_{model_suffix}",
            )

        with c2:

            select_temp = st.selectbox(
                "気温(℃)",
                list(range(0, 41)),
                index=20,
                key=f"temp_{model_suffix}",
            )

            select_rain = st.selectbox(
                "降水量(mm)",
                [0, 0.5, 1, 2, 5, 10, 20, 50],
                key=f"rain_{model_suffix}",
            )

            select_wind = st.selectbox(
                "風速(m/s)",
                list(range(21)),
                index=3,
                key=f"wind_{model_suffix}",
            )

        with c3:

            select_humidity = st.selectbox(
                "相対湿度(%)",
                list(range(0, 101, 10)),
                index=6,
                key=f"humidity_{model_suffix}",
            )

            select_solar = st.selectbox(
                "日射量(W/m²)",
                list(range(0, 1001, 50)),
                index=3,
                key=f"solar_{model_suffix}",
            )

            weather_types = [
                "晴れ",
                "曇り",
                "雨",
                "雪",
            ]

            select_weather = st.selectbox(
                "天気",
                weather_types,
                key=f"weather_{model_suffix}",
            )

        if st.button(
            "🔮 AI予測スタート",
            key=f"predict_{model_suffix}",
            use_container_width=True,
        ):

            combination_name = (
                get_model_combination_name(
                    show_nuclear,
                    show_thermal,
                    show_hydro,
                    show_solar_power,
                    show_wind,
                )
            )

            if combination_name is None:

                st.error(
                    "❌ 発電方式を最低1つ選択してください"
                )

            else:

                uploaded_name = (
                    st.session_state.get(
                        "uploaded_file_name",
                        ""
                    )
                )

                combine_location = (
                    "sendai"
                    if "Sendai" in uploaded_name
                    else "kumagaya"
                )

                model, combine_scaler, feature_names = (
                    load_combine_model(
                        combine_location,
                        combination_name,
                    )
                )

                if model is None:

                    st.error(
                        "❌ Combine Modelが見つかりません。"
                    )

                else:

                    input_data = {
                        "気温": select_temp,
                        "降水量": select_rain,
                        "風速": select_wind,
                        "相対湿度": select_humidity,
                        "日射量": select_solar,
                        "月": pred_date.month,
                        "時間": select_hour,
                        "曜日": pred_date.weekday(),
                        "日": pred_date.day,
                        "季節": get_season(
                            pred_date.month
                        ),
                    }

                    try:

                        predictions = (
                            predict_combine_model(
                                model,
                                combine_scaler,
                                input_data,
                            )
                        )

                        result_data = {}

                        for i, name in enumerate(
                            feature_names
                        ):

                            if i < len(predictions):

                                result_data[name] = max(
                                    0,
                                    round(
                                        float(
                                            predictions[i]
                                        ),
                                        1,
                                    ),
                                )

                        total = sum(
                            result_data.values()
                        )

                        st.success(
                            "✓ 予測が完了しました"
                        )

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

                                st.metric(
                                    name,
                                    f"{value:,.0f}MW",
                                    delta=(
                                        f"{value / total * 100:.1f}%"
                                        if total > 0
                                        else "0%"
                                    ),
                                    delta_color="off",
                                )

                        fig = go.Figure(
                            data=[
                                go.Bar(
                                    x=list(
                                        result_data.keys()
                                    ),
                                    y=list(
                                        result_data.values()
                                    ),
                                    text=[
                                        f"{v:,.0f}MW"
                                        for v in result_data.values()
                                    ],
                                    textposition="auto",
                                )
                            ]
                        )

                        fig.update_layout(
                            title="電力供給構成の予測",
                            yaxis_title="発電量(MW)",
                            height=400,
                        )

                        st.plotly_chart(
                            fig,
                            use_container_width=True
                        )

                    except Exception as e:

                        st.error(
                            f"❌ 予測エラー: {e}"
                        )

    # =========================================================================
    # 2-3 THERMAL + SOLAR
    # =========================================================================

    st.header(
        "🔌 火力と太陽光から発電源を予測"
    )

    with st.container(border=True):

        st.subheader(
            "2-3. 火力と太陽光から他の発電源を予測"
        )

        st.info(
            "入力：火力発電合計 + 太陽光発電\n\n"
            "出力：原子力・風力・水力"
        )

        col1, col2 = st.columns(2)

        with col1:

            thermal_input = st.number_input(
                "火力発電合計(MW)",
                min_value=0.0,
                max_value=50000.0,
                value=10000.0,
                step=500.0,
                key=f"thermal_input_{model_suffix}",
            )

            solar_input = st.number_input(
                "太陽光発電(MW)",
                min_value=0.0,
                max_value=10000.0,
                value=2000.0,
                step=100.0,
                key=f"solar_input_{model_suffix}",
            )

        if st.button(
            "🔮 発電源を予測",
            key=f"predict_2_3_{model_suffix}",
            use_container_width=True,
        ):

            models_dict, power_scaler = (
                load_power_prediction_models(
                    location_name
                )
            )

            predictions = (
                predict_from_thermal_solar(
                    models_dict,
                    power_scaler,
                    thermal_input,
                    solar_input,
                )
            )

            nuclear = round(
                predictions.get(
                    "原子力",
                    0
                ),
                1
            )

            wind = round(
                predictions.get(
                    "風力発電実績",
                    0
                ),
                1
            )

            hydro = round(
                predictions.get(
                    "水力",
                    0
                ),
                1
            )

            total = (
                thermal_input
                + solar_input
                + nuclear
                + wind
                + hydro
            )

            st.success(
                "✓ 予測が完了しました"
            )

            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric(
                    "原子力",
                    f"{nuclear:,.0f}MW"
                )

            with c2:
                st.metric(
                    "風力",
                    f"{wind:,.0f}MW"
                )

            with c3:
                st.metric(
                    "水力",
                    f"{hydro:,.0f}MW"
                )

            all_sources = {
                "原子力": nuclear,
                "火力": thermal_input,
                "太陽光": solar_input,
                "風力": wind,
                "水力": hydro,
            }

            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=list(
                            all_sources.keys()
                        ),
                        values=list(
                            all_sources.values()
                        ),
                        textinfo="label+percent",
                        hovertemplate=(
                            "<b>%{label}</b><br>"
                            "発電量: %{value:.0f}MW<br>"
                            "構成比: %{percent}"
                            "<extra></extra>"
                        ),
                    )
                ]
            )

            fig.update_layout(
                title="電力供給構成",
                height=500,
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            result_df = pd.DataFrame({
                "発電方式": [
                    "原子力",
                    "火力",
                    "太陽光",
                    "風力",
                    "水力",
                    "合計",
                ],
                "発電量(MW)": [
                    nuclear,
                    thermal_input,
                    solar_input,
                    wind,
                    hydro,
                    total,
                ],
            })

            result_df["構成比"] = (
                result_df["発電量(MW)"]
                / total
                * 100
                if total > 0
                else 0
            )

            result_df["構成比"] = (
                result_df["構成比"]
                .apply(
                    lambda x: f"{x:.1f}%"
                )
                if total > 0
                else "0%"
            )

            st.dataframe(
                result_df,
                use_container_width=True,
                hide_index=True,
            )

    # =========================================================================
    # FOOTER
    # =========================================================================

    st.markdown("---")

    st.markdown(
        """
        <div style='text-align:center;color:#888;font-size:12px;'>
        <p>⚡ 天気・電力データ分析ツール v1.0</p>
        <p>機械学習モデルによる予測ツール</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# START
# =============================================================================

if __name__ == "__main__":
    main()
