# -*- coding: utf-8 -*-

"""
Google Drive モデルダウンロード機能
Streamlit Cloud対応版

特徴
------
・Google Driveフォルダ内のファイルを1個ずつダウンロード
・1ファイルにつき最大3回リトライ
・進捗表示
・日本語ファイル名対応
・models / Weather_Model / Combine_Model の構成を維持
・失敗したファイルを最後に一覧表示
"""

import streamlit as st
import gdown

from pathlib import Path
import shutil
import traceback
import os
import time


# ============================================================
# Google Drive フォルダID
# ============================================================

GDRIVE_WEATHER_MODELS_FOLDER_ID = (
    "11CrLEAr_ljmYx1Ib5TPpWG_kvwDElNgS"
)


# ============================================================
# 設定
# ============================================================

MAX_RETRY = 3

# Google Drive上のフォルダ構成
TARGET_FOLDERS = [
    "models",
    "Weather_Model",
    "Combine_Model",
]


# ============================================================
# Streamlit表示用
# ============================================================

def log(message):
    """
    Streamlit画面にメッセージを表示
    """
    st.write(message)


# ============================================================
# ファイルサイズ取得
# ============================================================

def get_file_size(path):
    """
    ファイルサイズをMBで返す
    """

    try:

        size = Path(path).stat().st_size

        return size / (1024 * 1024)

    except Exception:

        return 0


# ============================================================
# Google Drive ファイル一覧取得
# ============================================================

def get_google_drive_file_list(folder_id):
    """
    Google Driveフォルダ内のファイル一覧を取得

    gdownのfolder URLから一覧を取得する方式。
    """

    import requests
    import re

    log("Google Drive フォルダ内のファイル一覧を取得しています...")

    folder_url = (
        f"https://drive.google.com/drive/folders/{folder_id}"
    )

    try:

        response = requests.get(
            folder_url,
            timeout=30
        )

        response.raise_for_status()

        html = response.text

        log(
            f"Google Driveへの接続成功 "
            f"(HTTP {response.status_code})"
        )

        # ----------------------------------------------------
        # Google Drive HTMLからファイルIDを抽出
        # ----------------------------------------------------

        file_ids = re.findall(
            r'"([a-zA-Z0-9_-]{20,})"',
            html
        )

        # 重複削除
        file_ids = list(dict.fromkeys(file_ids))

        log(
            f"検出されたID候補数: {len(file_ids)}"
        )

        return file_ids

    except Exception as e:

        log(
            f"❌ Google Drive一覧取得エラー: {e}"
        )

        return []


# ============================================================
# gdownによるファイルダウンロード
# ============================================================

def download_single_file(
    file_id,
    output_path,
    display_name
):
    """
    1ファイルを最大3回ダウンロード
    """

    output_path = Path(output_path)

    for attempt in range(1, MAX_RETRY + 1):

        try:

            log(
                f"📥 {display_name}"
            )

            log(
                f"   試行 {attempt}/{MAX_RETRY}"
            )

            # ------------------------------------------------
            # 既存ファイルがあれば削除
            # ------------------------------------------------

            if output_path.exists():

                try:
                    output_path.unlink()

                except Exception:
                    pass

            # ------------------------------------------------
            # ダウンロード
            # ------------------------------------------------

            result = gdown.download(
                id=file_id,
                output=str(output_path),
                quiet=False,
                fuzzy=True
            )

            # ------------------------------------------------
            # 成功確認
            # ------------------------------------------------

            if result is not None and output_path.exists():

                size_mb = get_file_size(
                    output_path
                )

                log(
                    f"   ✅ ダウンロード成功 "
                    f"({size_mb:.2f} MB)"
                )

                return True

            else:

                log(
                    "   ⚠️ ダウンロード結果を確認できません"
                )

        except Exception as e:

            log(
                f"   ⚠️ エラー: {type(e).__name__}"
            )

            log(
                f"   {str(e)}"
            )

        # ----------------------------------------------------
        # リトライ
        # ----------------------------------------------------

        if attempt < MAX_RETRY:

            log(
                "   ⏳ 10秒後にリトライします..."
            )

            time.sleep(10)

    # --------------------------------------------------------
    # 3回失敗
    # --------------------------------------------------------

    log(
        f"   ❌ 3回とも失敗: {display_name}"
    )

    return False


# ============================================================
# Google Driveからモデルをダウンロード
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

        st.info(
            "初回のみ時間がかかる場合があります。"
        )

        # ====================================================
        # Environment Info
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
        # Disk Usage
        # ====================================================

        total, used, free = shutil.disk_usage(
            BASE_DIR
        )

        st.write(
            "=== Disk Usage ==="
        )

        st.write(
            f"Total : "
            f"{total / (1024**3):.2f} GB"
        )

        st.write(
            f"Used : "
            f"{used / (1024**3):.2f} GB"
        )

        st.write(
            f"Free : "
            f"{free / (1024**3):.2f} GB"
        )

        # ====================================================
        # 空き容量チェック
        # ====================================================

        free_gb = free / (1024**3)

        if free_gb < 5:

            st.error(
                "❌ ディスク空き容量が5GB未満です。"
            )

            return False

        # ====================================================
        # TEMP削除
        # ====================================================

        if TEMP_DIR.exists():

            st.write(
                "Removing old temp directory..."
            )

            shutil.rmtree(
                TEMP_DIR,
                ignore_errors=True
            )

        TEMP_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        st.write(
            "Temp directory created"
        )

        # ====================================================
        # Google DriveフォルダURL
        # ====================================================

        folder_url = (
            "https://drive.google.com/drive/folders/"
            f"{GDRIVE_WEATHER_MODELS_FOLDER_ID}"
        )

        st.write(
            "=== Google Drive File List ==="
        )

        st.write(
            "Google Drive フォルダを確認しています..."
        )

        st.write(
            folder_url
        )

        # ====================================================
        # 重要
        #
        # gdown.download_folder() は使わない
        # ====================================================

        st.write(
            "Starting Google Drive download..."
        )

        # ====================================================
        # Google DriveフォルダのHTML取得
        # ====================================================

        import requests
        import re

        try:

            response = requests.get(
                folder_url,
                timeout=30
            )

            response.raise_for_status()

        except Exception as e:

            st.error(
                "❌ Google Driveフォルダへの接続に失敗しました"
            )

            st.error(
                str(e)
            )

            return False

        html = response.text

        st.success(
            "Google Driveフォルダへの接続成功"
        )

        # ====================================================
        # ファイル情報抽出
        # ====================================================

        st.write(
            "Google Driveからファイル情報を取得しています..."
        )

        # ----------------------------------------------------
        # Google DriveのHTMLからID候補を取得
        # ----------------------------------------------------

        file_ids = re.findall(
            r'"([a-zA-Z0-9_-]{20,})"',
            html
        )

        file_ids = list(
            dict.fromkeys(file_ids)
        )

        # フォルダID自身を除外
        file_ids = [
            x
            for x in file_ids
            if x != GDRIVE_WEATHER_MODELS_FOLDER_ID
        ]

        st.write(
            f"検出されたID候補: {len(file_ids)}"
        )

        # ====================================================
        # 注意
        # ====================================================

        if not file_ids:

            st.error(
                "❌ Google DriveからファイルIDを取得できませんでした。"
            )

            st.warning(
                "Google Driveフォルダが「リンクを知っている全員」に"
                "公開されているか確認してください。"
            )

            return False

        # ====================================================
        # ここから実際のダウンロード
        # ====================================================

        st.write(
            "=== Download Start ==="
        )

        st.write(
            f"ファイルID候補数: {len(file_ids)}"
        )

        # ====================================================
        # 重要
        #
        # Google Drive HTMLからファイル名とIDを
        # 完全に対応させるのは難しいため、
        # 今回はgdown.download_folder()の問題を
        # 回避するための方式として、
        # まずフォルダ単位の取得を試す。
        #
        # ただしdownload_folder()は使わない。
        # ====================================================

        # ====================================================
        # 実際にはGoogle Drive APIなしでは
        # フォルダ内の「名前→ID」を完全取得できない場合がある
        # ====================================================

        st.warning(
            "⚠️ Google Driveの公開フォルダから"
            "ファイル名とIDの完全な対応取得を行います。"
        )

        # ====================================================
        # gdown.download_folder()を使わずに
        # Google Driveのファイル一覧を取得する
        # ====================================================

        # Google Driveのページに埋め込まれている
        # ファイルIDとファイル名を検索
        #
        # ファイル名がHTMLに存在する場合の処理
        # ====================================================

        downloaded = 0
        failed = []

        # ----------------------------------------------------
        # 対象フォルダ
        # ----------------------------------------------------

        for target_folder in TARGET_FOLDERS:

            st.write(
                f"## {target_folder}"
            )

            target_dir = (
                TEMP_DIR / target_folder
            )

            target_dir.mkdir(
                parents=True,
                exist_ok=True
            )

        # ====================================================
        # ここでGoogle Drive API方式を使用
        # ====================================================

        try:

            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            st.write(
                "Google Drive APIを確認しています..."
            )

            # ------------------------------------------------
            # Streamlit Secretsからサービスアカウント取得
            # ------------------------------------------------

            if "gdrive" not in st.secrets:

                raise Exception(
                    "Streamlit Secretsに [gdrive] "
                    "設定がありません"
                )

            credentials_info = dict(
                st.secrets["gdrive"]
            )

            credentials = (
                service_account
                .Credentials
                .from_service_account_info(
                    credentials_info,
                    scopes=[
                        "https://www.googleapis.com/auth/drive.readonly"
                    ]
                )
            )

            service = build(
                "drive",
                "v3",
                credentials=credentials
            )

            st.success(
                "Google Drive API接続成功"
            )

        except Exception as e:

            st.error(
                "❌ Google Drive API接続に失敗しました"
            )

            st.error(
                str(e)
            )

            st.info(
                "Streamlit SecretsにGoogle Drive APIの"
                "サービスアカウント設定が必要です。"
            )

            return False

        # ====================================================
        # フォルダ階層を取得
        # ====================================================

        def get_children(parent_id):

            query = (
                f"'{parent_id}' in parents "
                "and trashed = false"
            )

            results = []

            page_token = None

            while True:

                response = service.files().list(

                    q=query,

                    fields=(
                        "nextPageToken,"
                        "files(id,name,mimeType,size)"
                    ),

                    pageSize=1000,

                    pageToken=page_token

                ).execute()

                results.extend(
                    response.get(
                        "files",
                        []
                    )
                )

                page_token = (
                    response.get(
                        "nextPageToken"
                    )
                )

                if not page_token:
                    break

            return results

        # ====================================================
        # weather-models フォルダ内取得
        # ====================================================

        st.write(
            "weather-models フォルダを検索しています..."
        )

        root_items = get_children(
            GDRIVE_WEATHER_MODELS_FOLDER_ID
        )

        st.write(
            f"weather-models直下: "
            f"{len(root_items)} 件"
        )

        # ====================================================
        # 各フォルダを取得
        # ====================================================

        all_files = []

        for item in root_items:

            if (
                item["mimeType"]
                == "application/vnd.google-apps.folder"
            ):

                folder_name = item["name"]

                if folder_name in TARGET_FOLDERS:

                    st.write(
                        f"📁 {folder_name}"
                    )

                    children = get_children(
                        item["id"]
                    )

                    st.write(
                        f"   {len(children)} ファイル"
                    )

                    for child in children:

                        if (
                            child["mimeType"]
                            != "application/vnd.google-apps.folder"
                        ):

                            all_files.append({

                                "id": child["id"],

                                "name": child["name"],

                                "folder": folder_name,

                                "size": child.get(
                                    "size",
                                    0
                                )

                            })

        # ====================================================
        # ファイル数
        # ====================================================

        total_files = len(
            all_files
        )

        st.write(
            f"=== ダウンロード対象 ==="
        )

        st.write(
            f"合計 {total_files} ファイル"
        )

        if total_files == 0:

            st.error(
                "❌ ダウンロード対象ファイルがありません。"
            )

            return False

        # ====================================================
        # 進捗バー
        # ====================================================

        progress = st.progress(
            0
        )

        status = st.empty()

        # ====================================================
        # 1ファイルずつダウンロード
        # ====================================================

        for index, file_info in enumerate(
            all_files,
            start=1
        ):

            file_id = file_info["id"]

            file_name = file_info["name"]

            folder_name = file_info["folder"]

            output_dir = (
                TEMP_DIR / folder_name
            )

            output_path = (
                output_dir / file_name
            )

            # ------------------------------------------------
            # 進捗表示
            # ------------------------------------------------

            percent = (
                (index - 1)
                / total_files
            )

            progress.progress(
                percent
            )

            status.write(
                f"### "
                f"[{index}/{total_files}] "
                f"{folder_name}/{file_name}"
            )

            # ------------------------------------------------
            # サイズ
            # ------------------------------------------------

            size = file_info.get(
                "size",
                0
            )

            try:

                size_mb = (
                    int(size)
                    / (1024 * 1024)
                )

            except Exception:

                size_mb = 0

            st.write(
                f"📦 {folder_name}/"
                f"{file_name} "
                f"({size_mb:.2f} MB)"
            )

            # ------------------------------------------------
            # ダウンロード
            # ------------------------------------------------

            success = download_single_file(

                file_id=file_id,

                output_path=output_path,

                display_name=(
                    f"{folder_name}/"
                    f"{file_name}"
                )

            )

            if success:

                downloaded += 1

            else:

                failed.append(
                    {
                        "folder":
                            folder_name,

                        "name":
                            file_name,

                        "id":
                            file_id
                    }
                )

        # ====================================================
        # 100%
        # ====================================================

        progress.progress(
            1.0
        )

        status.write(
            "ダウンロード処理完了"
        )

        # ====================================================
        # 結果
        # ====================================================

        st.write(
            "=== Download Result ==="
        )

        st.write(
            f"成功: {downloaded}"
        )

        st.write(
            f"失敗: {len(failed)}"
        )

        # ====================================================
        # 失敗ファイル
        # ====================================================

        if failed:

            st.error(
                "❌ 一部ファイルのダウンロードに失敗しました"
            )

            st.write(
                "=== Failed Files ==="
            )

            for item in failed:

                st.write(
                    f"- "
                    f"{item['folder']}/"
                    f"{item['name']}"
                )

            st.warning(
                "失敗したファイルがあるため、"
                "モデル配置は実行しません。"
            )

            return False

        # ====================================================
        # すべて成功
        # ====================================================

        st.success(
            "🎉 すべてのファイルの"
            "ダウンロードに成功しました"
        )

        # ====================================================
        # ファイル確認
        # ====================================================

        st.write(
            "=== Downloaded Contents ==="
        )

        for target_folder in TARGET_FOLDERS:

            folder_path = (
                TEMP_DIR / target_folder
            )

            files = list(
                folder_path.rglob("*")
            )

            file_count = sum(
                1
                for f in files
                if f.is_file()
            )

            st.write(
                f"{target_folder}: "
                f"{file_count} files"
            )

        # ====================================================
        # モデル配置
        # ====================================================

        st.write(
            "=== Model Installation ==="
        )

        for folder_name in TARGET_FOLDERS:

            src = (
                TEMP_DIR / folder_name
            )

            dst = (
                BASE_DIR / folder_name
            )

            st.write(
                f"Installing: "
                f"{folder_name}"
            )

            # ------------------------------------------------
            # 既存フォルダ削除
            # ------------------------------------------------

            if dst.exists():

                st.write(
                    f"Removing existing: "
                    f"{dst}"
                )

                shutil.rmtree(
                    dst,
                    ignore_errors=True
                )

            # ------------------------------------------------
            # 移動
            # ------------------------------------------------

            shutil.move(
                str(src),
                str(dst)
            )

            st.success(
                f"✅ {folder_name} を配置しました"
            )

        # ====================================================
        # TEMP削除
        # ====================================================

        if TEMP_DIR.exists():

            shutil.rmtree(
                TEMP_DIR,
                ignore_errors=True
            )

        # ====================================================
        # 最終確認
        # ====================================================

        st.write(
            "=== Final Check ==="
        )

        all_exist = True

        for folder_name in TARGET_FOLDERS:

            folder_path = (
                BASE_DIR / folder_name
            )

            exists = (
                folder_path.exists()
            )

            st.write(
                f"{folder_name}: "
                f"{exists}"
            )

            if not exists:

                all_exist = False

        if not all_exist:

            st.error(
                "❌ モデルフォルダの配置確認に失敗しました"
            )

            return False

        st.success(
            "🎉 モデルセットアップ完了"
        )

        return True

    except Exception as e:

        # ====================================================
        # エラー処理
        # ====================================================

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

        # ----------------------------------------------------
        # TEMP削除
        # ----------------------------------------------------

        if TEMP_DIR.exists():

            try:

                shutil.rmtree(
                    TEMP_DIR,
                    ignore_errors=True
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

    models_path = (
        BASE_DIR / "models"
    )

    weather_path = (
        BASE_DIR / "Weather_Model"
    )

    combine_path = (
        BASE_DIR / "Combine_Model"
    )

    # ========================================================
    # 存在確認
    # ========================================================

    models_exist = (
        models_path.exists()
        and
        weather_path.exists()
        and
        combine_path.exists()
    )

    st.write(
        "=== Setup Models ==="
    )

    st.write(
        "models:",
        models_path.exists()
    )

    st.write(
        "Weather_Model:",
        weather_path.exists()
    )

    st.write(
        "Combine_Model:",
        combine_path.exists()
    )

    # ========================================================
    # 既に存在
    # ========================================================

    if models_exist:

        st.success(
            "✅ モデルは既に存在します"
        )

        return True

    # ========================================================
    # 存在しない
    # ========================================================

    st.warning(
        "⚠️ モデルが存在しません"
    )

    st.write(
        "Running download_models_from_gdrive()."
    )

    # ========================================================
    # ダウンロード
    # ========================================================

    success = (
        download_models_from_gdrive()
    )

    # ========================================================
    # 失敗
    # ========================================================

    if not success:

        st.error(
            "❌ モデルダウンロード失敗"
        )

        st.stop()

    # ========================================================
    # 成功
    # ========================================================

    st.success(
        "🎉 モデルセットアップ成功"
    )

    return True


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    setup_models()

    print(
        "完了"
    )
