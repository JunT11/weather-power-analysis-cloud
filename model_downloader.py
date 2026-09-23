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

# Google Drive フォルダID
GDRIVE_WEATHER_MODELS_FOLDER_ID = "11CrLEAr_ljmYx1Ib5TPpWG_kvwDElNgS"


@st.cache_resource
def download_models_from_gdrive():

    BASE_DIR = Path(__file__).resolve().parent
    temp_dir = BASE_DIR / ".gdrive_temp"

    try:

        st.info(
            "📥 Google Drive からモデルをダウンロード中...（初回のみ）"
        )

        # ===== 環境情報 =====

        st.write("=== Environment Info ===")
        st.write("gdown version:", gdown.__version__)
        st.write("BASE_DIR:", str(BASE_DIR))
        st.write("TEMP_DIR:", str(temp_dir))
        st.write("Folder ID:", GDRIVE_WEATHER_MODELS_FOLDER_ID)

        # ===== ディスク容量 =====

        total, used, free = shutil.disk_usage(BASE_DIR)

        st.write("=== Disk Usage ===")
        st.write(f"Total : {total / (1024**3):.2f} GB")
        st.write(f"Used  : {used / (1024**3):.2f} GB")
        st.write(f"Free  : {free / (1024**3):.2f} GB")

        # ===== temp削除 =====

        if temp_dir.exists():
            st.write("Removing old temp directory...")
            shutil.rmtree(temp_dir)

        temp_dir.mkdir(parents=True, exist_ok=True)

        st.write("Temp directory created")

        # ===== ダウンロード開始 =====

        st.write("Starting gdown.download_folder() ...")

        #downloaded_files = gdown.download_folder(
        #    id=GDRIVE_WEATHER_MODELS_FOLDER_ID,
        #    output=str(temp_dir),
        #    quiet=False,
        #    use_cookies=False
        #)
        st.write("Single file download test start")

        test_file = gdown.download(
            id="ここにsummary_all.csvのファイルID",
            output="summary_all.csv",
            quiet=False
        )

        st.write("Result =", test_file)

        if Path("summary_all.csv").exists():
            st.success("download success")
        else:
            st.error("download failed")

        st.write("Download complete")
        st.write("downloaded_files:")
        st.write(downloaded_files)

        if downloaded_files is None:
            raise Exception(
                "gdown.download_folder() returned None"
            )

        st.write(
            f"Downloaded file count: {len(downloaded_files)}"
        )

        # ===== temp_dir確認 =====

        st.write("=== Downloaded Contents ===")

        for root, dirs, files in os.walk(temp_dir):

            st.write(f"DIR: {root}")

            for d in dirs:
                st.write(f"   [DIR ] {d}")

            for f in files:
                st.write(f"   [FILE] {f}")

        # ===== フォルダ位置特定 =====

        weather_models_dir = temp_dir / "weather-models"

        if weather_models_dir.exists():
            source_dir = weather_models_dir
            st.write(
                "Found weather-models folder"
            )
        else:
            source_dir = temp_dir
            st.write(
                "weather-models folder not found. Using temp_dir"
            )

        # ===== コピー =====

        for folder_name in [
            "models",
            "Weather_Model",
            "Combine_Model"
        ]:

            src = source_dir / folder_name
            dst = BASE_DIR / folder_name

            st.write(
                f"Checking folder: {folder_name}"
            )

            st.write(f"src = {src}")
            st.write(f"dst = {dst}")

            if src.exists():

                st.write(
                    f"Source exists: {folder_name}"
                )

                if not dst.exists():

                    shutil.move(
                        str(src),
                        str(dst)
                    )

                    st.success(
                        f"✅ {folder_name} を配置"
                    )
                else:
                    st.warning(
                        f"{folder_name} already exists"
                    )

            else:

                st.error(
                    f"Source folder not found: {src}"
                )

        # ===== temp削除 =====

        if temp_dir.exists():
            shutil.rmtree(temp_dir)

        st.success(
            "🎉 モデルダウンロード完了"
        )

        return True

    except Exception as e:

        st.error(type(e))
        st.error(str(e))

        if hasattr(e, "__cause__"):
            st.write("CAUSE =", repr(e.__cause__))

        if hasattr(e, "__context__"):
            st.write("CONTEXT =", repr(e.__context__))

        st.code(traceback.format_exc())

        #st.error("❌ ダウンロード失敗")

        #st.error(f"Exception Type: {type(e)}")
        #st.error(f"Exception Message: {str(e)}")

        #st.code(traceback.format_exc())

        if temp_dir.exists():

            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

        return False


def setup_models():

    BASE_DIR = Path(__file__).resolve().parent

    models_exist = (
        (BASE_DIR / "models").exists()
        and
        (BASE_DIR / "Weather_Model").exists()
        and
        (BASE_DIR / "Combine_Model").exists()
    )

    st.write("=== Setup Models ===")

    st.write(
        "models:",
        (BASE_DIR / "models").exists()
    )

    st.write(
        "Weather_Model:",
        (BASE_DIR / "Weather_Model").exists()
    )

    st.write(
        "Combine_Model:",
        (BASE_DIR / "Combine_Model").exists()
    )

    if not models_exist:

        st.warning(
            "⚠️ モデルが存在しません"
        )

        success = download_models_from_gdrive()

        if not success:

            st.error(
                "❌ モデルダウンロード失敗"
            )

            st.stop()

    else:

        st.success(
            "✅ モデルは既に存在します"
        )


if __name__ == "__main__":
    setup_models()
    print("完了")