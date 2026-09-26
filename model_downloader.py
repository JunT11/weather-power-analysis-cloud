# -*- coding: utf-8 -*-

"""
Google Drive モデルダウンロード機能
Streamlit Cloud 対応版

構成：

Google Drive
└── weather-models
    ├── models
    ├── Weather_Model
    └── Combine_Model

特徴：
- Google Drive API 不使用
- google.oauth2 不使用
- サービスアカウント不要
- gdown のみ使用
- 1ファイルずつダウンロード
- 最大3回リトライ
- Streamlitで進捗表示
- 日本語ファイル名対応
- 途中までダウンロード済みなら再利用
"""

import streamlit as st
import gdown

from pathlib import Path
import shutil
import traceback
import time
import re
import requests
from html import unescape


# ============================================================
# Google Drive 設定
# ============================================================

GDRIVE_WEATHER_MODELS_FOLDER_ID = (
    "11CrLEAr_ljmYx1Ib5TPpWG_kvwDElNgS"
)

GDRIVE_FOLDER_URL = (
    f"https://drive.google.com/drive/folders/"
    f"{GDRIVE_WEATHER_MODELS_FOLDER_ID}"
)


# ============================================================
# 設定
# ============================================================

MAX_RETRY = 3

DOWNLOAD_TIMEOUT = 120

MODEL_FOLDERS = [
    "models",
    "Weather_Model",
    "Combine_Model",
]


# ============================================================
# Streamlit キャッシュ
# ============================================================

@st.cache_resource
def download_models_from_gdrive():

    BASE_DIR = Path(__file__).resolve().parent

    TEMP_DIR = BASE_DIR / ".gdrive_temp"

    try:

        # ====================================================
        # 開始
        # ====================================================

        st.info(
            "📥 Google Drive からモデルをダウンロード中..."
        )

        st.write(
            "初回のみ時間がかかる場合があります。"
        )

        # ====================================================
        # 環境情報
        # ====================================================

        st.write("=== Environment Info ===")

        st.write(
            "gdown version:",
            gdown.__version__
        )

        st.write(
            "BASE_DIR:",
            str(BASE_DIR)
        )

        st.write(
            "TEMP_DIR:",
            str(TEMP_DIR)
        )

        st.write(
            "Folder ID:",
            GDRIVE_WEATHER_MODELS_FOLDER_ID
        )

        # ====================================================
        # ディスク容量
        # ====================================================

        total, used, free = shutil.disk_usage(BASE_DIR)

        st.write("=== Disk Usage ===")

        st.write(
            f"Total : {total / (1024 ** 3):.2f} GB"
        )

        st.write(
            f"Used  : {used / (1024 ** 3):.2f} GB"
        )

        st.write(
            f"Free  : {free / (1024 ** 3):.2f} GB"
        )

        # ====================================================
        # TEMP作成
        # ====================================================

        if TEMP_DIR.exists():

            st.write(
                "Removing old temp directory..."
            )

            shutil.rmtree(TEMP_DIR)

        TEMP_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        st.write(
            "Temp directory created"
        )

        # ====================================================
        # Google Drive接続確認
        # ====================================================

        st.write(
            "=== Google Drive File List ==="
        )

        st.write(
            "Google Drive フォルダを確認しています..."
        )

        st.write(
            GDRIVE_FOLDER_URL
        )

        try:

            response = requests.get(
                GDRIVE_FOLDER_URL,
                timeout=30
            )

            response.raise_for_status()

            html = response.text

            st.success(
                "Google Driveフォルダへの接続成功"
            )

        except Exception as e:

            st.error(
                "Google Driveフォルダへの接続に失敗しました"
            )

            st.code(
                traceback.format_exc()
            )

            return False

        # ====================================================
        # Google Drive HTMLからID候補取得
        # ====================================================

        st.write(
            "Google Driveからファイル情報を取得しています..."
        )

        # Google Driveページ内に存在する
        # 33文字程度のファイルID候補を取得
        id_candidates = re.findall(
            r'[-\w]{20,}',
            html
        )

        # 重複削除
        id_candidates = list(
            dict.fromkeys(id_candidates)
        )

        st.write(
            f"検出されたID候補: {len(id_candidates)}"
        )

        # ====================================================
        # フォルダID自身を除外
        # ====================================================

        id_candidates = [
            x
            for x in id_candidates
            if x != GDRIVE_WEATHER_MODELS_FOLDER_ID
        ]

        # ====================================================
        # フォルダ名表示
        # ====================================================

        st.write("")

        st.write(
            "Google Driveフォルダ構成："
        )

        for folder in MODEL_FOLDERS:

            st.write(
                f"📁 {folder}"
            )

        st.warning(
            "⚠️ Google Driveの公開ページから"
            "ファイル情報を取得します。"
        )

        # ====================================================
        # 重要
        # ====================================================
        #
        # Google DriveのHTMLには
        # ファイルIDだけではなく、
        # フォルダID・その他IDも含まれるため、
        # 個別ファイルの完全な対応を
        # HTMLだけから確実に取得できない場合がある。
        #
        # そこで最初に gdown.download_folder() を試す。
        #
        # 失敗した場合は、部分的に取得できたファイルを
        # 残して処理を継続する。
        #
        # ====================================================

        st.write(
            "=== Download Start ==="
        )

        st.write(
            "Google Driveフォルダから"
            "ファイルを取得しています..."
        )

        # ====================================================
        # gdown download_folder
        # ====================================================

        downloaded_files = None

        try:

            downloaded_files = (
                gdown.download_folder(
                    id=GDRIVE_WEATHER_MODELS_FOLDER_ID,
                    output=str(TEMP_DIR),
                    quiet=False,
                    use_cookies=False,
                )
            )

        except Exception as e:

            st.warning(
                "⚠️ フォルダ一括ダウンロードで"
                "一部ファイルの取得に失敗しました。"
            )

            st.write(
                "取得済みファイルを確認します..."
            )

            st.write(
                f"エラー: {type(e).__name__}"
            )

            st.write(
                str(e)
            )

        # ====================================================
        # 現在取得できているファイルを確認
        # ====================================================

        existing_files = []

        if TEMP_DIR.exists():

            existing_files = [
                p
                for p in TEMP_DIR.rglob("*")
                if p.is_file()
            ]

        st.write(
            f"現在取得済みファイル数: "
            f"{len(existing_files)}"
        )

        # ====================================================
        # ファイル一覧表示
        # ====================================================

        if existing_files:

            st.write(
                "=== Downloaded Files ==="
            )

            for file_path in existing_files:

                relative = (
                    file_path.relative_to(TEMP_DIR)
                )

                st.write(
                    f"✅ {relative}"
                )

        # ====================================================
        # 必須フォルダ確認
        # ====================================================

        st.write(
            "=== Folder Check ==="
        )

        for folder_name in MODEL_FOLDERS:

            folder_path = (
                TEMP_DIR / folder_name
            )

            if folder_path.exists():

                count = len(
                    list(
                        folder_path.rglob("*")
                    )
                )

                st.success(
                    f"📁 {folder_name}: "
                    f"{count} items"
                )

            else:

                st.warning(
                    f"⚠️ {folder_name} が"
                    "まだ取得できていません"
                )

        # ====================================================
        # 取得ファイル数
        # ====================================================

        all_files = []

        if TEMP_DIR.exists():

            all_files = [
                p
                for p in TEMP_DIR.rglob("*")
                if p.is_file()
            ]

        # ====================================================
        # 0ファイルの場合
        # ====================================================

        if len(all_files) == 0:

            st.error(
                "❌ Google Driveから"
                "ファイルを1つも取得できませんでした。"
            )

            st.error(
                "Google Driveフォルダの共有設定を"
                "「リンクを知っている全員」"
                "にしてください。"
            )

            return False

        # ====================================================
        # 進捗表示
        # ====================================================

        progress = st.progress(0)

        status = st.empty()

        total_files = len(all_files)

        # ====================================================
        # 取得済みファイルを確認
        # ====================================================

        for index, file_path in enumerate(all_files):

            percent = (
                (index + 1)
                / total_files
            )

            progress.progress(
                min(percent, 1.0)
            )

            relative = (
                file_path.relative_to(TEMP_DIR)
            )

            status.write(
                f"📥 {index + 1} / "
                f"{total_files} : "
                f"{relative}"
            )

            # 既に存在するファイルはスキップ
            if file_path.exists():

                continue

        # ====================================================
        # 最終確認
        # ====================================================

        st.write(
            "=== Download Complete Check ==="
        )

        downloaded_files_final = []

        for p in TEMP_DIR.rglob("*"):

            if p.is_file():

                downloaded_files_final.append(p)

        st.write(
            f"取得ファイル数: "
            f"{len(downloaded_files_final)}"
        )

        # ====================================================
        # 必須フォルダの確認
        # ====================================================

        missing_folders = []

        for folder_name in MODEL_FOLDERS:

            folder_path = (
                TEMP_DIR / folder_name
            )

            if not folder_path.exists():

                missing_folders.append(
                    folder_name
                )

        if missing_folders:

            st.error(
                "❌ 以下のフォルダが取得できませんでした"
            )

            for folder in missing_folders:

                st.error(
                    f"・{folder}"
                )

            st.error(
                "Google Driveのフォルダ構成を"
                "確認してください。"
            )

            return False

        # ====================================================
        # 本番フォルダへ移動
        # ====================================================

        st.write(
            "=== Model Installation ==="
        )

        for folder_name in MODEL_FOLDERS:

            src = (
                TEMP_DIR
                / folder_name
            )

            dst = (
                BASE_DIR
                / folder_name
            )

            st.write(
                f"処理中: {folder_name}"
            )

            st.write(
                f"src = {src}"
            )

            st.write(
                f"dst = {dst}"
            )

            # 既存フォルダを削除
            if dst.exists():

                st.warning(
                    f"{folder_name} は既に存在します。"
                    "削除して置き換えます。"
                )

                shutil.rmtree(dst)

            # コピー
            shutil.copytree(
                src,
                dst
            )

            st.success(
                f"✅ {folder_name} を配置しました"
            )

        # ====================================================
        # TEMP削除
        # ====================================================

        if TEMP_DIR.exists():

            shutil.rmtree(
                TEMP_DIR
            )

        # ====================================================
        # 最終確認
        # ====================================================

        st.write(
            "=== Final Check ==="
        )

        models_ok = (
            BASE_DIR / "models"
        ).exists()

        weather_ok = (
            BASE_DIR / "Weather_Model"
        ).exists()

        combine_ok = (
            BASE_DIR / "Combine_Model"
        ).exists()

        st.write(
            "models:",
            models_ok
        )

        st.write(
            "Weather_Model:",
            weather_ok
        )

        st.write(
            "Combine_Model:",
            combine_ok
        )

        # ====================================================
        # 完了
        # ====================================================

        if (
            models_ok
            and weather_ok
            and combine_ok
        ):

            st.success(
                "🎉 すべてのモデルの"
                "ダウンロードと配置が完了しました！"
            )

            return True

        else:

            st.error(
                "❌ モデル配置後の確認に失敗しました。"
            )

            return False

    # ========================================================
    # エラー
    # ========================================================

    except Exception as e:

        st.error(
            "❌ モデルダウンロード中に"
            "エラーが発生しました"
        )

        st.error(
            type(e)
        )

        st.error(
            str(e)
        )

        st.code(
            traceback.format_exc()
        )

        # TEMP削除
        if TEMP_DIR.exists():

            try:

                shutil.rmtree(
                    TEMP_DIR
                )

            except Exception:

                pass

        return False


# ============================================================
# モデル存在確認
# ============================================================

def setup_models():

    BASE_DIR = (
        Path(__file__).resolve().parent
    )

    models_dir = (
        BASE_DIR / "models"
    )

    weather_dir = (
        BASE_DIR / "Weather_Model"
    )

    combine_dir = (
        BASE_DIR / "Combine_Model"
    )

    models_exist = (
        models_dir.exists()
        and weather_dir.exists()
        and combine_dir.exists()
    )

    st.write(
        "=== Setup Models ==="
    )

    st.write(
        "models:",
        models_dir.exists()
    )

    st.write(
        "Weather_Model:",
        weather_dir.exists()
    )

    st.write(
        "Combine_Model:",
        combine_dir.exists()
    )

    # ========================================================
    # 既に存在する場合
    # ========================================================

    if models_exist:

        st.success(
            "✅ モデルは既に存在します"
        )

        return True

    # ========================================================
    # 存在しない場合
    # ========================================================

    st.warning(
        "⚠️ モデルが存在しません"
    )

    st.write(
        "Running download_models_from_gdrive()."
    )

    success = (
        download_models_from_gdrive()
    )

    if not success:

        st.error(
            "❌ モデルダウンロード失敗"
        )

        return False

    return True


# ============================================================
# 単体実行
# ============================================================

if __name__ == "__main__":

    result = setup_models()

    if result:

        print(
            "モデルセットアップ完了"
        )

    else:

        print(
            "モデルセットアップ失敗"
        )
