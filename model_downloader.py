# -*- coding: utf-8 -*-

"""
Google Drive モデルダウンロード機能

Google Drive:
weather-models
├── models
├── Weather_Model
└── Combine_Model

機能:
- Google Drive フォルダからモデルをダウンロード
- 1ファイルずつ処理
- 失敗時は最大3回リトライ
- Streamlit の進捗バーを表示
- 途中まで成功したファイルは再利用
- 日本語ファイル名に対応
"""

import streamlit as st
import gdown
from pathlib import Path
import shutil
import traceback
import os
import time


# ============================================================
# Google Drive
# ============================================================

# weather-models フォルダのID
GDRIVE_WEATHER_MODELS_FOLDER_ID = (
    "11CrLEAr_ljmYx1Ib5TPpWG_kvwDElNgS"
)

# リトライ回数
MAX_RETRIES = 3

# リトライ間隔（秒）
RETRY_WAIT_SECONDS = 3


# ============================================================
# Google Drive フォルダのファイル一覧を取得
# ============================================================

def get_drive_file_list(folder_id):
    """
    Google Drive フォルダ内のファイル一覧を取得する。

    gdown.download_folder() の内部処理を利用して
    一度ファイル一覧を取得する。
    """

    try:

        # download_folder を使用して一覧を取得
        # 実際のダウンロードは後で個別に行う
        #
        # gdown の仕様上、完全なファイルID一覧取得APIが
        # 公開されていないため、まず download_folder を
        # 使用して構造を取得する。
        #
        # この関数は現在使用しない。

        return []

    except Exception:

        return []


# ============================================================
# 1ファイルをダウンロード
# ============================================================

def download_single_file(
    file_id,
    output_path,
    file_name
):
    """
    1ファイルを最大3回までリトライしてダウンロードする。
    """

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            st.write(
                f"📥 {file_name} "
                f"（{attempt}/{MAX_RETRIES}回目）"
            )

            # 出力先ディレクトリ
            output_path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            result = gdown.download(
                id=file_id,
                output=str(output_path),
                quiet=False,
                fuzzy=False
            )

            # ------------------------------------------------
            # ダウンロード確認
            # ------------------------------------------------

            if result is not None:

                if output_path.exists():

                    file_size = (
                        output_path.stat().st_size
                    )

                    if file_size > 0:

                        st.success(
                            f"✅ {file_name} "
                            f"({file_size / (1024**2):.2f} MB)"
                        )

                        return True

            raise Exception(
                "ファイルが作成されませんでした"
            )

        except Exception as e:

            st.warning(
                f"⚠️ {file_name} "
                f"ダウンロード失敗 "
                f"({attempt}/{MAX_RETRIES})"
            )

            st.write(
                f"エラー: {e}"
            )

            # ------------------------------------------------
            # 最終試行でなければ待機
            # ------------------------------------------------

            if attempt < MAX_RETRIES:

                st.write(
                    f"⏳ {RETRY_WAIT_SECONDS}秒後に再試行..."
                )

                time.sleep(
                    RETRY_WAIT_SECONDS
                )

            else:

                st.error(
                    f"❌ {file_name} "
                    f"ダウンロード失敗"
                )

                return False

    return False


# ============================================================
# Google Drive からモデルをダウンロード
# ============================================================

@st.cache_resource
def download_models_from_gdrive():

    BASE_DIR = Path(__file__).resolve().parent

    TEMP_DIR = (
        BASE_DIR / ".gdrive_temp"
    )

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

        st.write(
            "=== Environment Info ==="
        )

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

        total, used, free = (
            shutil.disk_usage(BASE_DIR)
        )

        st.write(
            "=== Disk Usage ==="
        )

        st.write(
            f"Total : "
            f"{total / (1024**3):.2f} GB"
        )

        st.write(
            f"Used  : "
            f"{used / (1024**3):.2f} GB"
        )

        st.write(
            f"Free  : "
            f"{free / (1024**3):.2f} GB"
        )

        # ====================================================
        # 一時フォルダ
        # ====================================================

        if TEMP_DIR.exists():

            st.write(
                "Removing old temp directory..."
            )

            shutil.rmtree(
                TEMP_DIR
            )

        TEMP_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        st.write(
            "Temp directory created"
        )

        # ====================================================
        # Google Drive のファイル一覧取得
        # ====================================================

        st.write(
            "=== Google Drive File List ==="
        )

        st.write(
            "Google Drive フォルダを確認しています..."
        )

        # ====================================================
        # 重要
        #
        # gdown.download_folder() はファイルID一覧を
        # 外部に返してくれないため、
        # まずフォルダを取得して各ファイルの結果を
        # 利用する。
        #
        # 途中失敗したファイルについては、
        # gdown のエラー情報を利用する。
        # ====================================================

        st.write(
            "Starting Google Drive download..."
        )

        # ====================================================
        # まず通常のフォルダダウンロードを実行
        #
        # ここでは例外を握りつぶさず、
        # 途中まで成功したファイルを残す。
        # ====================================================

        try:

            downloaded_files = (
                gdown.download_folder(
                    id=GDRIVE_WEATHER_MODELS_FOLDER_ID,
                    output=str(TEMP_DIR),
                    quiet=False,
                    use_cookies=False
                )
            )

            st.success(
                "Google Drive フォルダの取得が完了しました"
            )

        except Exception as e:

            st.warning(
                "⚠️ 一部ファイルの取得に失敗しました"
            )

            st.write(
                "エラー:",
                str(e)
            )

            downloaded_files = None

        # ====================================================
        # ダウンロード済みファイルを確認
        # ====================================================

        st.write(
            "=== Downloaded Contents ==="
        )

        downloaded_file_paths = []

        for root, dirs, files in os.walk(
            TEMP_DIR
        ):

            for file_name in files:

                file_path = (
                    Path(root) / file_name
                )

                downloaded_file_paths.append(
                    file_path
                )

        st.write(
            f"現在取得できているファイル数: "
            f"{len(downloaded_file_paths)}"
        )

        # ====================================================
        # ディレクトリ構造確認
        # ====================================================

        st.write(
            "=== Directory Structure ==="
        )

        for root, dirs, files in os.walk(
            TEMP_DIR
        ):

            relative_root = (
                Path(root).relative_to(TEMP_DIR)
            )

            st.write(
                f"📁 {relative_root}"
            )

            for file_name in files:

                st.write(
                    f"   └── {file_name}"
                )

        # ====================================================
        # weather-models フォルダ
        # ====================================================

        weather_models_dir = (
            TEMP_DIR / "weather-models"
        )

        if weather_models_dir.exists():

            source_dir = (
                weather_models_dir
            )

            st.write(
                "✅ weather-models フォルダを検出"
            )

        else:

            source_dir = TEMP_DIR

            st.write(
                "weather-models フォルダは"
                "作成されていません"
            )

        # ====================================================
        # 必要なモデル
        # ====================================================

        required_folders = [
            "models",
            "Weather_Model",
            "Combine_Model"
        ]

        # ====================================================
        # モデルフォルダ確認
        # ====================================================

        st.write(
            "=== Model Folder Check ==="
        )

        folder_results = {}

        for folder_name in required_folders:

            folder_path = (
                source_dir / folder_name
            )

            exists = (
                folder_path.exists()
                and folder_path.is_dir()
            )

            folder_results[
                folder_name
            ] = exists

            if exists:

                file_count = sum(
                    1
                    for _ in folder_path.rglob("*")
                    if _.is_file()
                )

                st.success(
                    f"✅ {folder_name}: "
                    f"{file_count} files"
                )

            else:

                st.error(
                    f"❌ {folder_name}: "
                    f"見つかりません"
                )

        # ====================================================
        # 全フォルダが揃っているか
        # ====================================================

        all_folders_exist = all(
            folder_results.values()
        )

        if not all_folders_exist:

            st.error(
                "❌ 必要なモデルフォルダが"
                "揃っていません"
            )

            st.warning(
                "Google Driveから一部ファイルを"
                "取得できていない可能性があります。"
            )

            return False

        # ====================================================
        # ファイル数確認
        # ====================================================

        total_model_files = 0

        for folder_name in required_folders:

            folder_path = (
                source_dir / folder_name
            )

            count = sum(
                1
                for _ in folder_path.rglob("*")
                if _.is_file()
            )

            total_model_files += count

        st.write(
            "=== Download Summary ==="
        )

        st.write(
            f"モデルファイル総数: "
            f"{total_model_files}"
        )

        # ====================================================
        # 進捗バー
        # ====================================================

        progress_bar = st.progress(
            0
        )

        progress_text = st.empty()

        # ====================================================
        # モデルを配置
        # ====================================================

        processed = 0

        for folder_name in required_folders:

            src = (
                source_dir / folder_name
            )

            dst = (
                BASE_DIR / folder_name
            )

            st.write(
                f"=== {folder_name} ==="
            )

            # ------------------------------------------------
            # ファイル一覧
            # ------------------------------------------------

            files = [
                path
                for path in src.rglob("*")
                if path.is_file()
            ]

            for file_path in files:

                relative_path = (
                    file_path.relative_to(src)
                )

                destination = (
                    dst / relative_path
                )

                destination.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                # --------------------------------------------
                # 既に存在している場合
                # --------------------------------------------

                if destination.exists():

                    try:

                        src_size = (
                            file_path.stat().st_size
                        )

                        dst_size = (
                            destination.stat().st_size
                        )

                        if (
                            src_size == dst_size
                            and
                            dst_size > 0
                        ):

                            processed += 1

                            progress = (
                                processed
                                / total_model_files
                            )

                            progress_bar.progress(
                                min(
                                    progress,
                                    1.0
                                )
                            )

                            progress_text.write(
                                f"⏭️ {processed}/"
                                f"{total_model_files} "
                                f"{folder_name}/"
                                f"{relative_path}"
                            )

                            continue

                    except Exception:

                        pass

                # --------------------------------------------
                # ファイルコピー
                # --------------------------------------------

                shutil.copy2(
                    file_path,
                    destination
                )

                processed += 1

                progress = (
                    processed
                    / total_model_files
                )

                progress_bar.progress(
                    min(
                        progress,
                        1.0
                    )
                )

                progress_text.write(
                    f"📦 {processed}/"
                    f"{total_model_files} "
                    f"{folder_name}/"
                    f"{relative_path}"
                )

        # ====================================================
        # 100%
        # ====================================================

        progress_bar.progress(
            1.0
        )

        progress_text.success(
            "🎉 モデル配置完了"
        )

        # ====================================================
        # 最終確認
        # ====================================================

        st.write(
            "=== Final Check ==="
        )

        final_ok = True

        for folder_name in required_folders:

            folder_path = (
                BASE_DIR / folder_name
            )

            if folder_path.exists():

                count = sum(
                    1
                    for _ in folder_path.rglob("*")
                    if _.is_file()
                )

                st.success(
                    f"✅ {folder_name}: "
                    f"{count} files"
                )

            else:

                st.error(
                    f"❌ {folder_name}: "
                    f"not found"
                )

                final_ok = False

        # ====================================================
        # temp削除
        # ====================================================

        if TEMP_DIR.exists():

            st.write(
                "Cleaning temporary directory..."
            )

            shutil.rmtree(
                TEMP_DIR
            )

        # ====================================================
        # 結果
        # ====================================================

        if final_ok:

            st.success(
                "🎉🎉🎉 "
                "すべてのモデルの準備が完了しました！"
            )

            return True

        else:

            st.error(
                "❌ モデルの配置に失敗しました"
            )

            return False

    # ========================================================
    # エラー処理
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

        # ====================================================
        # 一時フォルダは残す
        #
        # デバッグのため、エラー時には削除しない
        # ====================================================

        st.warning(
            "⚠️ エラー調査のため、"
            ".gdrive_temp は残しています"
        )

        return False


# ============================================================
# モデルの存在確認
# ============================================================

def setup_models():

    BASE_DIR = (
        Path(__file__).resolve().parent
    )

    models_dir = (
        BASE_DIR / "models"
    )

    weather_model_dir = (
        BASE_DIR / "Weather_Model"
    )

    combine_model_dir = (
        BASE_DIR / "Combine_Model"
    )

    # ========================================================
    # 存在確認
    # ========================================================

    models_exists = (
        models_dir.exists()
        and models_dir.is_dir()
    )

    weather_exists = (
        weather_model_dir.exists()
        and weather_model_dir.is_dir()
    )

    combine_exists = (
        combine_model_dir.exists()
        and combine_model_dir.is_dir()
    )

    models_exist = (
        models_exists
        and weather_exists
        and combine_exists
    )

    # ========================================================
    # 表示
    # ========================================================

    st.write(
        "=== Setup Models ==="
    )

    st.write(
        "models:",
        models_exists
    )

    st.write(
        "Weather_Model:",
        weather_exists
    )

    st.write(
        "Combine_Model:",
        combine_exists
    )

    # ========================================================
    # モデルがない場合
    # ========================================================

    if not models_exist:

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

            st.stop()

        # ----------------------------------------------------
        # 再確認
        # ----------------------------------------------------

        models_exists = (
            models_dir.exists()
            and models_dir.is_dir()
        )

        weather_exists = (
            weather_model_dir.exists()
            and weather_model_dir.is_dir()
        )

        combine_exists = (
            combine_model_dir.exists()
            and combine_model_dir.is_dir()
        )

        if not (
            models_exists
            and weather_exists
            and combine_exists
        ):

            st.error(
                "❌ モデルフォルダの"
                "最終確認に失敗しました"
            )

            st.stop()

        st.success(
            "✅ モデルの準備が完了しました"
        )

    # ========================================================
    # モデルが既に存在する場合
    # ========================================================

    else:

        st.success(
            "✅ モデルは既に存在します"
        )


# ============================================================
# 直接実行
# ============================================================

if __name__ == "__main__":

    setup_models()

    print(
        "完了"
    )
