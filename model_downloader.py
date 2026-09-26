# -*- coding: utf-8 -*-

"""
Google Drive モデルダウンロード機能
"""

import streamlit as st
import gdown
from pathlib import Path
import shutil
import traceback
import os
import logging

logging.basicConfig(level=logging.DEBUG)

# ============================================================
# Google Drive フォルダID
# ============================================================

GDRIVE_WEATHER_MODELS_FOLDER_ID = (
    "11CrLEAr_ljmYx1Ib5TPpWG_kvwDElNgS"
)


# ============================================================
# Google Driveからモデルをダウンロード
# ============================================================

@st.cache_resource
def download_models_from_gdrive():

    BASE_DIR = Path(__file__).resolve().parent
    temp_dir = BASE_DIR / ".gdrive_temp"

    try:

        st.info(
            "📥 Google Drive からモデルをダウンロード中...（初回のみ）"
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
            str(temp_dir)
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
            f"Total : {total / (1024**3):.2f} GB"
        )

        st.write(
            f"Used  : {used / (1024**3):.2f} GB"
        )

        st.write(
            f"Free  : {free / (1024**3):.2f} GB"
        )

        # ====================================================
        # 古い一時フォルダを削除
        # ====================================================

        if temp_dir.exists():

            st.write(
                "Removing old temp directory..."
            )

            shutil.rmtree(temp_dir)

        temp_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        st.write(
            "Temp directory created"
        )

        # ====================================================
        # Google Drive フォルダをダウンロード
        # ====================================================

        st.write(
            "Starting gdown.download_folder() ..."
        )

        downloaded_files = gdown.download_folder(
            id=GDRIVE_WEATHER_MODELS_FOLDER_ID,
            output=str(temp_dir),
            quiet=False,
            use_cookies=False
        )

        # ====================================================
        # ダウンロード結果
        # ====================================================

        st.write(
            "Download complete"
        )

        st.write(
            "downloaded_files:"
        )

        st.write(
            downloaded_files
        )

        if downloaded_files is None:

            raise Exception(
                "gdown.download_folder() returned None"
            )

        st.write(
            f"Downloaded file count: "
            f"{len(downloaded_files)}"
        )

        # ====================================================
        # ダウンロードしたファイル一覧
        # ====================================================

        st.write(
            "=== Downloaded Contents ==="
        )

        for root, dirs, files in os.walk(temp_dir):

            st.write(
                f"DIR: {root}"
            )

            for d in dirs:

                st.write(
                    f"   [DIR ] {d}"
                )

            for f in files:

                st.write(
                    f"   [FILE] {f}"
                )

        # ====================================================
        # weather-models フォルダを確認
        # ====================================================

        weather_models_dir = (
            temp_dir / "weather-models"
        )

        if weather_models_dir.exists():

            source_dir = weather_models_dir

            st.write(
                "Found weather-models folder"
            )

        else:

            source_dir = temp_dir

            st.write(
                "weather-models folder not found."
                " Using temp_dir"
            )

        # ====================================================
        # 必要なモデルフォルダ
        # ====================================================

        required_folders = [
            "models",
            "Weather_Model",
            "Combine_Model"
        ]

        # ====================================================
        # モデルフォルダを配置
        # ====================================================

        success_count = 0

        for folder_name in required_folders:

            src = source_dir / folder_name

            dst = BASE_DIR / folder_name

            st.write(
                f"Checking folder: {folder_name}"
            )

            st.write(
                f"src = {src}"
            )

            st.write(
                f"dst = {dst}"
            )

            # -----------------------------------------------
            # コピー元が存在するか
            # -----------------------------------------------

            if not src.exists():

                st.error(
                    f"❌ Source folder not found: {src}"
                )

                continue

            st.write(
                f"Source exists: {folder_name}"
            )

            # -----------------------------------------------
            # 既存フォルダがあれば削除
            # -----------------------------------------------

            if dst.exists():

                st.write(
                    f"Removing existing folder: {dst}"
                )

                if dst.is_dir():

                    shutil.rmtree(dst)

                else:

                    dst.unlink()

            # -----------------------------------------------
            # モデルフォルダをコピー
            # -----------------------------------------------

            shutil.copytree(
                src,
                dst
            )

            st.success(
                f"✅ {folder_name} を配置しました"
            )

            success_count += 1

        # ====================================================
        # モデル配置結果
        # ====================================================

        st.write(
            "=== Model Setup Result ==="
        )

        for folder_name in required_folders:

            folder_path = (
                BASE_DIR / folder_name
            )

            st.write(
                f"{folder_name}: "
                f"{folder_path.exists()}"
            )

        # ====================================================
        # 3フォルダすべて存在するか確認
        # ====================================================

        all_models_exist = all(
            (
                BASE_DIR / folder_name
            ).exists()
            for folder_name in required_folders
        )

        if not all_models_exist:

            st.error(
                "❌ 必要なモデルフォルダを"
                "すべて配置できませんでした"
            )

            st.error(
                "Google Driveのフォルダ構成を確認してください。"
            )

            return False

        # ====================================================
        # summary_all.csv の確認
        # ====================================================

        summary_files = list(
            source_dir.rglob(
                "summary_all.csv"
            )
        )

        if summary_files:

            st.success(
                "✅ summary_all.csv を確認しました"
            )

            st.write(
                "summary_all.csv:",
                str(summary_files[0])
            )

        else:

            st.warning(
                "⚠️ summary_all.csv が"
                "見つかりませんでした"
            )

        # ====================================================
        # 一時フォルダ削除
        # ====================================================

        if temp_dir.exists():

            st.write(
                "Removing temporary directory..."
            )

            shutil.rmtree(temp_dir)

        # ====================================================
        # 最終確認
        # ====================================================

        st.success(
            "🎉 モデルダウンロード完了"
        )

        return True

    # ========================================================
    # エラー処理
    # ========================================================

    except Exception as e:

        st.error(
            "❌ モデルダウンロード中にエラーが発生しました"
        )

        st.error(
            type(e)
        )

        st.error(
            str(e)
        )

        if hasattr(e, "__cause__"):

            st.write(
                "CAUSE =",
                repr(e.__cause__)
            )

        if hasattr(e, "__context__"):

            st.write(
                "CONTEXT =",
                repr(e.__context__)
            )

        st.code(
            traceback.format_exc()
        )

        # ====================================================
        # エラー時の一時ファイル削除
        # ====================================================

        if temp_dir.exists():

            try:

                shutil.rmtree(
                    temp_dir
                )

            except Exception:

                pass

        return False


# ============================================================
# モデルの存在確認
# ============================================================

def setup_models():

    BASE_DIR = Path(__file__).resolve().parent

    models_dir = (
        BASE_DIR / "models"
    )

    weather_model_dir = (
        BASE_DIR / "Weather_Model"
    )

    combine_model_dir = (
        BASE_DIR / "Combine_Model"
    )

    models_exist = (
        models_dir.exists()
        and
        weather_model_dir.exists()
        and
        combine_model_dir.exists()
    )

    # ========================================================
    # 現在の状態
    # ========================================================

    st.write(
        "=== Setup Models ==="
    )

    st.write(
        "models:",
        models_dir.exists()
    )

    st.write(
        "Weather_Model:",
        weather_model_dir.exists()
    )

    st.write(
        "Combine_Model:",
        combine_model_dir.exists()
    )

    # ========================================================
    # モデルが存在しない場合
    # ========================================================

    if not models_exist:

        st.warning(
            "⚠️ モデルが存在しません"
        )

        success = (
            download_models_from_gdrive()
        )

        if not success:

            st.error(
                "❌ モデルダウンロード失敗"
            )

            st.stop()

        # -----------------------------------------------
        # ダウンロード後に再確認
        # -----------------------------------------------

        models_exist_after_download = (
            models_dir.exists()
            and
            weather_model_dir.exists()
            and
            combine_model_dir.exists()
        )

        if not models_exist_after_download:

            st.error(
                "❌ モデルの配置後も"
                "必要なフォルダが見つかりません"
            )

            st.stop()

        st.success(
            "✅ モデルの準備が完了しました"
        )

    # ========================================================
    # モデルがすでに存在する場合
    # ========================================================

    else:

        st.success(
            "✅ モデルは既に存在します"
        )


# ============================================================
# 直接実行した場合
# ============================================================

if __name__ == "__main__":

    setup_models()

    print(
        "完了"
    )
