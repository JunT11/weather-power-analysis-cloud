from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Optional

import gdown
import streamlit as st


# ============================================================
# 基本設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODELS_DIR = BASE_DIR / "models"
WEATHER_MODEL_DIR = BASE_DIR / "Weather_Model"
COMBINE_MODEL_DIR = BASE_DIR / "Combine_Model"

TEMP_DIR = BASE_DIR / ".gdrive_temp"

# Streamlit Secrets または環境変数から取得
GDRIVE_FOLDER_ID = (
    st.secrets.get("GDRIVE_FOLDER_ID", None)
    if hasattr(st, "secrets")
    else None
)

if not GDRIVE_FOLDER_ID:
    GDRIVE_FOLDER_ID = os.environ.get(
        "GDRIVE_FOLDER_ID",
        "11CrLEAr_ljmYx1Ib5TPpWG_kvwDElNgS",
    )


# ============================================================
# 必須ディレクトリ
# ============================================================

REQUIRED_DIRS = (
    MODELS_DIR,
    WEATHER_MODEL_DIR,
    COMBINE_MODEL_DIR,
)


def log(message: str) -> None:
    """Streamlit画面と標準出力の両方に表示"""
    print(message)

    try:
        st.write(message)
    except Exception:
        pass


def ensure_directories() -> None:
    for directory in REQUIRED_DIRS:
        directory.mkdir(parents=True, exist_ok=True)


# ============================================================
# モデル存在確認
# ============================================================

def count_files(directory: Path) -> int:
    if not directory.exists():
        return 0

    return sum(
        1
        for path in directory.rglob("*")
        if path.is_file()
    )


def models_are_available() -> bool:
    """
    3フォルダが存在し、最低限のモデルファイルがあるか確認。
    """

    if not all(directory.exists() for directory in REQUIRED_DIRS):
        return False

    models_count = count_files(MODELS_DIR)
    weather_count = count_files(WEATHER_MODEL_DIR)
    combine_count = count_files(COMBINE_MODEL_DIR)

    return (
        models_count > 0
        and weather_count > 0
        and combine_count > 0
    )


def show_model_status() -> None:
    st.write("=== Setup Models ===")
    st.write(f"models: {MODELS_DIR.exists()}")
    st.write(f"Weather_Model: {WEATHER_MODEL_DIR.exists()}")
    st.write(f"Combine_Model: {COMBINE_MODEL_DIR.exists()}")

    if models_are_available():
        st.success("モデルは配置済みです")
    else:
        st.warning("モデルが存在しません")


# ============================================================
# Google Drive URL
# ============================================================

def get_drive_folder_url() -> str:
    return (
        f"https://drive.google.com/drive/folders/"
        f"{GDRIVE_FOLDER_ID}"
    )


# ============================================================
# 1ファイルダウンロード
# ============================================================

def download_file(
    file_id: str,
    destination: Path,
    retries: int = 3,
) -> bool:
    """
    Google Driveの1ファイルを最大3回リトライして取得する。

    既に完全に存在するファイルは再ダウンロードしない。
    """

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if destination.exists() and destination.stat().st_size > 0:
        log(f"⏭️ スキップ: {destination.relative_to(BASE_DIR)}")
        return True

    url = f"https://drive.google.com/uc?id={file_id}"

    for attempt in range(1, retries + 1):
        try:
            log(
                f"📥 ダウンロード "
                f"{attempt}/{retries}: "
                f"{destination.name}"
            )

            result = gdown.download(
                url,
                str(destination),
                quiet=False,
                fuzzy=False,
            )

            if result and destination.exists():
                if destination.stat().st_size > 0:
                    log(
                        f"✅ 完了: "
                        f"{destination.relative_to(BASE_DIR)}"
                    )
                    return True

        except Exception as exc:
            log(
                f"⚠️ ダウンロード失敗 "
                f"{attempt}/{retries}: {exc}"
            )

        if destination.exists():
            try:
                destination.unlink()
            except Exception:
                pass

        if attempt < retries:
            wait_seconds = attempt * 2

            log(
                f"⏳ {wait_seconds}秒後に再試行します..."
            )

            time.sleep(wait_seconds)

    log(
        f"❌ 取得失敗: "
        f"{destination.relative_to(BASE_DIR)}"
    )

    return False


# ============================================================
# Google Driveフォルダ一括取得
# ============================================================

def download_models_from_gdrive() -> bool:
    """
    Google Drive公開フォルダからモデルを取得。

    gdownのフォルダ一括ダウンロードに依存せず、
    可能な限り個別ファイルとして処理する。
    """

    ensure_directories()

    st.write("=== Environment Info ===")
    st.write(f"gdown version: {getattr(gdown, '__version__', 'unknown')}")
    st.write(f"BASE_DIR: {BASE_DIR}")
    st.write(f"TEMP_DIR: {TEMP_DIR}")
    st.write(f"Folder ID: {GDRIVE_FOLDER_ID}")

    st.write("")

    st.write("=== Google Drive File List ===")

    drive_url = get_drive_folder_url()

    st.write(
        "Google Driveフォルダを確認しています..."
    )

    st.write(drive_url)

    # --------------------------------------------------------
    # 一時ディレクトリ
    # --------------------------------------------------------

    if TEMP_DIR.exists():
        try:
            shutil.rmtree(TEMP_DIR)
        except Exception as exc:
            log(f"⚠️ 一時フォルダ削除失敗: {exc}")

    TEMP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    log("Temp directory created")

    # --------------------------------------------------------
    # Google Driveフォルダ接続確認
    # --------------------------------------------------------

    st.write("Starting Google Drive download...")

    try:
        log("Google Driveフォルダへの接続を確認しています...")

        # gdownによる公開フォルダ取得
        downloaded_path = gdown.download_folder(
            drive_url,
            output=str(TEMP_DIR),
            quiet=False,
            use_cookies=False,
            remaining_ok=True,
        )

        if downloaded_path:
            log("Google Driveフォルダへの接続成功")
        else:
            log("⚠️ Google Driveフォルダからデータを取得できませんでした")

    except Exception as exc:
        log(
            "⚠️ Google Driveフォルダ取得中にエラーが発生しました"
        )
        log(f"エラー: {type(exc).__name__}: {exc}")

    # --------------------------------------------------------
    # 取得ファイル確認
    # --------------------------------------------------------

    files = [
        path
        for path in TEMP_DIR.rglob("*")
        if path.is_file()
    ]

    log(
        f"取得済みファイル数: {len(files)}"
    )

    if not files:
        st.error(
            "Google Driveからモデルファイルを取得できませんでした。"
        )

        st.info(
            "Google Driveフォルダが「リンクを知っている全員」に"
            "閲覧可能になっているか確認してください。"
        )

        return False

    # --------------------------------------------------------
    # フォルダ構成確認
    # --------------------------------------------------------

    st.write("=== Folder Check ===")

    for directory_name in (
        "models",
        "Weather_Model",
        "Combine_Model",
    ):
        directory = TEMP_DIR / directory_name

        count = count_files(directory)

        st.write(
            f"📁 {directory_name}: {count} items"
        )

    # --------------------------------------------------------
    # 配置
    # --------------------------------------------------------

    st.write("=== Model Installation ===")

    source_destinations = (
        (TEMP_DIR / "models", MODELS_DIR),
        (TEMP_DIR / "Weather_Model", WEATHER_MODEL_DIR),
        (TEMP_DIR / "Combine_Model", COMBINE_MODEL_DIR),
    )

    for source, destination in source_destinations:
        st.write(f"処理中: {destination.name}")
        st.write(f"src = {source}")
        st.write(f"dst = {destination}")

        if not source.exists():
            st.warning(
                f"{source.name} フォルダが取得されていません"
            )
            continue

        destination.mkdir(
            parents=True,
            exist_ok=True,
        )

        copied = 0

        for source_file in source.rglob("*"):
            if not source_file.is_file():
                continue

            relative_path = source_file.relative_to(source)
            destination_file = destination / relative_path

            destination_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            try:
                shutil.copy2(
                    source_file,
                    destination_file,
                )
                copied += 1

            except Exception as exc:
                st.warning(
                    f"コピー失敗: "
                    f"{source_file.name}: {exc}"
                )

        if copied > 0:
            st.success(
                f"{destination.name} を配置しました "
                f"({copied} files)"
            )
        else:
            st.warning(
                f"{destination.name} にファイルがありません"
            )

    # --------------------------------------------------------
    # 最終確認
    # --------------------------------------------------------

    st.write("=== Final Check ===")

    models_count = count_files(MODELS_DIR)
    weather_count = count_files(WEATHER_MODEL_DIR)
    combine_count = count_files(COMBINE_MODEL_DIR)

    st.write(f"models: {models_count > 0}")
    st.write(
        f"Weather_Model: {weather_count > 0}"
    )
    st.write(
        f"Combine_Model: {combine_count > 0}"
    )

    if (
        models_count > 0
        and weather_count > 0
        and combine_count > 0
    ):
        st.success(
            "🎉 すべてのモデルのダウンロードと配置が完了しました！"
        )

        return True

    st.error(
        "モデルの配置が不完全です。"
    )

    return False


# ============================================================
# 起動時モデルセットアップ
# ============================================================

def setup_models() -> bool:
    """
    アプリ起動時にモデルを確認。

    既に存在する場合はGoogle Driveへアクセスしない。
    """

    ensure_directories()

    if models_are_available():
        show_model_status()
        return True

    show_model_status()

    st.write(
        "Running download_models_from_gdrive()."
    )

    st.info(
        "📥 Google Drive からモデルをダウンロード中..."
    )

    st.caption(
        "初回のみ時間がかかる場合があります。"
    )

    return download_models_from_gdrive()


if __name__ == "__main__":
    setup_models()
