# model_downloader.py
# -*- coding: utf-8 -*-

"""
Streamlit Cloud 用モデルダウンローダー

Google Drive:
    weather-models/
    ├── models/
    ├── Weather_Model/
    └── Combine_Model/

を対象に、

- 1ファイルずつダウンロード
- 最大3回リトライ
- Streamlit進捗表示
- 途中まで成功したファイルは再利用
- gdown.download_folder() は使用しない
- Google Drive API / google.oauth2 は使用しない
- 日本語ファイル名対応
- ダウンロード後に正しいフォルダへ配置
"""

from __future__ import annotations

import os
import re
import shutil
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import gdown


# ============================================================
# 基本設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TEMP_DIR = BASE_DIR / ".gdrive_temp"

MODEL_DIRS = [
    "models",
    "Weather_Model",
    "Combine_Model",
]

# Google Drive フォルダID
GDRIVE_FOLDER_ID = "11CrLEAr_ljmYx1Ib5TPpWG_kvwDElNgS"

MAX_RETRIES = 3

# リトライ間隔
RETRY_WAIT_SECONDS = 3

# 大きなファイルを扱うための最小サイズ判定
MIN_VALID_FILE_SIZE = 1


# ============================================================
# Streamlit は必須にしない
# ============================================================

try:
    import streamlit as st
except ImportError:
    st = None


# ============================================================
# 表示ヘルパー
# ============================================================

def _write(message: str) -> None:
    """Streamlit があれば画面へ、なければ print。"""
    if st is not None:
        st.write(message)
    else:
        print(message)


def _info(message: str) -> None:
    if st is not None:
        st.info(message)
    else:
        print(message)


def _warning(message: str) -> None:
    if st is not None:
        st.warning(message)
    else:
        print(f"WARNING: {message}")


def _error(message: str) -> None:
    if st is not None:
        st.error(message)
    else:
        print(f"ERROR: {message}")


def _success(message: str) -> None:
    if st is not None:
        st.success(message)
    else:
        print(message)


# ============================================================
# パス関連
# ============================================================

def get_model_root() -> Path:
    """
    モデルのルートディレクトリ。

    weather-models/
    ├── models/
    ├── Weather_Model/
    └── Combine_Model/
    """
    return BASE_DIR


def get_model_dir(name: str) -> Path:
    return BASE_DIR / name


# ============================================================
# フォルダ存在確認
# ============================================================

def check_model_directories() -> bool:
    """
    3フォルダが存在し、1ファイル以上入っているか確認。
    """

    all_ok = True

    _write("=== Setup Models ===")

    for directory_name in MODEL_DIRS:
        directory = BASE_DIR / directory_name

        exists = directory.exists() and directory.is_dir()

        file_count = 0

        if exists:
            try:
                file_count = sum(
                    1
                    for p in directory.rglob("*")
                    if p.is_file()
                )
            except Exception:
                file_count = 0

        _write(
            f"{directory_name}: "
            f"{exists and file_count > 0}"
        )

        if not exists or file_count == 0:
            all_ok = False

    return all_ok


# ============================================================
# 一時ディレクトリ
# ============================================================

def prepare_temp_directory() -> Path:
    """
    一時ディレクトリを準備する。

    既存ファイルを完全削除すると、
    途中まで成功していたダウンロードまで消えるため、
    基本的には既存ファイルを再利用する。
    """

    TEMP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    _write("Temp directory ready")

    return TEMP_DIR


# ============================================================
# Google Drive URL
# ============================================================

def get_folder_url() -> str:
    return (
        f"https://drive.google.com/drive/folders/"
        f"{GDRIVE_FOLDER_ID}"
    )


# ============================================================
# Google Drive ページからファイル情報を取得
# ============================================================

def get_drive_file_list() -> list[dict]:
    """
    公開Google DriveフォルダのHTMLから、

        id
        name
        relative path

    を可能な範囲で取得する。

    Google Drive API は使用しない。
    """

    import requests

    folder_url = get_folder_url()

    _write("Google Driveフォルダへの接続を確認しています...")
    _write(folder_url)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/131.0 Safari/537.36"
        )
    }

    response = requests.get(
        folder_url,
        headers=headers,
        timeout=60,
    )

    response.raise_for_status()

    html = response.text

    if not html:
        raise RuntimeError(
            "Google Driveからページを取得できませんでした。"
        )

    _success("Google Driveフォルダへの接続成功")

    # --------------------------------------------------------
    # Google Drive のHTML / JSONには、
    # ファイルIDが大量に登場する。
    # まずID候補を取得する。
    # --------------------------------------------------------

    id_pattern = re.compile(
        r'"([a-zA-Z0-9_-]{20,})"'
    )

    ids = list(dict.fromkeys(
        id_pattern.findall(html)
    ))

    _write(
        f"検出されたID候補: {len(ids)}"
    )

    # --------------------------------------------------------
    # HTML中のファイル名候補
    # --------------------------------------------------------

    file_extensions = (
        ".pkl",
        ".pickle",
        ".json",
        ".csv",
        ".joblib",
        ".npz",
        ".npy",
        ".pt",
        ".pth",
        ".bin",
    )

    # Unicode文字を含むファイル名にも対応
    filename_pattern = re.compile(
        r'([^"<>\\/:*?]+'
        r'(?:'
        + "|".join(
            re.escape(ext)
            for ext in file_extensions
        )
        + r'))',
        re.IGNORECASE,
    )

    filenames = list(dict.fromkeys(
        filename_pattern.findall(html)
    ))

    # --------------------------------------------------------
    # Google DriveのHTMLに現れるファイル情報を
    # 周辺文字列からできるだけ対応させる。
    # --------------------------------------------------------

    results: list[dict] = []

    for filename in filenames:

        filename = filename.strip()

        if not filename:
            continue

        if len(filename) > 300:
            continue

        # ファイル名が含まれる周辺HTMLを探す
        pos = html.find(filename)

        if pos < 0:
            continue

        start = max(0, pos - 3000)
        end = min(
            len(html),
            pos + len(filename) + 3000,
        )

        area = html[start:end]

        nearby_ids = id_pattern.findall(area)

        for file_id in nearby_ids:

            if file_id == GDRIVE_FOLDER_ID:
                continue

            results.append(
                {
                    "id": file_id,
                    "name": filename,
                }
            )

            break

    # 重複削除
    unique = {}

    for item in results:

        key = (
            item["id"],
            item["name"],
        )

        unique[key] = item

    results = list(unique.values())

    # --------------------------------------------------------
    # Google Drive上の既知のフォルダ構造から
    # 3フォルダに振り分ける。
    # --------------------------------------------------------

    categorized = []

    for item in results:

        name = item["name"]

        if name.startswith("model_") or name.startswith("scaler_"):

            # Combine_Model にあるもの
            if (
                "toden" in name
                or "tohoku" in name
                or name.startswith("summary_")
                or name.startswith("info_")
            ):
                category = "Combine_Model"

            # models にあるもの
            elif (
                "kumagaya" in name
                or "sendai" in name
            ):
                category = "models"

            else:
                category = None

        elif name.startswith("info_"):
            category = "Combine_Model"

        elif name.startswith("results_"):
            category = "Weather_Model"

        else:
            category = None

        # Weather_Modelのファイル
        if (
            name.startswith("model_kumagaya_")
            or name.startswith("model_sendai_")
        ):

            weather_keywords = (
                "天気",
                "日射量",
                "気温",
                "相対湿度",
                "降水量",
                "風速",
            )

            if any(
                keyword in name
                for keyword in weather_keywords
            ):
                category = "Weather_Model"

        if category:
            item["category"] = category
            categorized.append(item)

    # --------------------------------------------------------
    # 同じ名前で複数IDがある場合は重複排除
    # --------------------------------------------------------

    unique_by_path = {}

    for item in categorized:

        key = (
            item["category"],
            item["name"],
        )

        unique_by_path[key] = item

    categorized = list(
        unique_by_path.values()
    )

    # --------------------------------------------------------
    # フォルダ名自体の検出
    # --------------------------------------------------------

    folder_names = []

    for folder_name in MODEL_DIRS:

        if folder_name in html:
            folder_names.append(folder_name)

    if folder_names:

        _write("Google Driveフォルダ構成：")

        for folder_name in MODEL_DIRS:

            if folder_name in folder_names:
                _write(f"📁 {folder_name}")

    return categorized


# ============================================================
# gdownで1ファイルダウンロード
# ============================================================

def download_single_file(
    file_id: str,
    destination: Path,
) -> bool:
    """
    Google Driveの1ファイルをダウンロード。

    最大3回。
    """

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # 既に存在する場合は再利用
    if (
        destination.exists()
        and destination.is_file()
        and destination.stat().st_size >= MIN_VALID_FILE_SIZE
    ):
        return True

    url = (
        f"https://drive.google.com/uc?id="
        f"{quote(file_id)}"
    )

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            _write(
                f"  ダウンロード試行 "
                f"{attempt}/{MAX_RETRIES}"
            )

            # 壊れた途中ファイルがあれば削除
            if destination.exists():
                try:
                    destination.unlink()
                except Exception:
                    pass

            result = gdown.download(
                url=url,
                output=str(destination),
                quiet=False,
                fuzzy=True,
            )

            if result is None:
                raise RuntimeError(
                    "gdown.download() が None を返しました"
                )

            if (
                not destination.exists()
                or destination.stat().st_size < MIN_VALID_FILE_SIZE
            ):
                raise RuntimeError(
                    "ダウンロード後のファイルが存在しないか空です"
                )

            return True

        except Exception as e:

            _warning(
                f"  ⚠️ ダウンロード失敗 "
                f"({attempt}/{MAX_RETRIES}): {e}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT_SECONDS)

    return False


# ============================================================
# ダウンロード処理
# ============================================================

def download_files(
    file_list: list[dict],
) -> tuple[int, int]:
    """
    1ファイルずつダウンロード。

    Returns:
        (成功数, 失敗数)
    """

    if not file_list:
        _warning(
            "Google Driveからダウンロード対象のファイルを"
            "検出できませんでした。"
        )
        return 0, 0

    total = len(file_list)

    _write("=== Download Start ===")
    _write(
        f"ダウンロード対象ファイル数: {total}"
    )

    progress = None

    if st is not None:
        progress = st.progress(0)

    success_count = 0
    failed_count = 0

    for index, item in enumerate(file_list, start=1):

        category = item["category"]
        filename = item["name"]
        file_id = item["id"]

        relative_path = (
            Path(category)
            / filename
        )

        destination = (
            TEMP_DIR
            / relative_path
        )

        _write(
            f"📥 {index}/{total} "
            f"{relative_path.as_posix()}"
        )

        ok = download_single_file(
            file_id=file_id,
            destination=destination,
        )

        if ok:
            success_count += 1

            _success(
                f"✅ {relative_path.as_posix()}"
            )

        else:
            failed_count += 1

            _error(
                f"❌ {relative_path.as_posix()}"
            )

        if progress is not None:
            progress.progress(
                index / total
            )

    _write(
        f"=== Download Result ===\n"
        f"成功: {success_count}\n"
        f"失敗: {failed_count}\n"
        f"合計: {total}"
    )

    return success_count, failed_count


# ============================================================
# 既存ファイル一覧
# ============================================================

def count_files(directory: Path) -> int:
    if not directory.exists():
        return 0

    try:
        return sum(
            1
            for p in directory.rglob("*")
            if p.is_file()
        )
    except Exception:
        return 0


def list_downloaded_files() -> None:

    _write("=== Folder Check ===")

    for directory_name in MODEL_DIRS:

        directory = TEMP_DIR / directory_name

        count = count_files(directory)

        _write(
            f"📁 {directory_name}: "
            f"{count} items"
        )


# ============================================================
# インストール
# ============================================================

def install_models() -> bool:
    """
    .gdrive_temp 以下の3フォルダを
    BASE_DIR直下へコピーする。

    コピー先:
        models/
        Weather_Model/
        Combine_Model/
    """

    _write("=== Model Installation ===")

    all_ok = True

    for directory_name in MODEL_DIRS:

        src = TEMP_DIR / directory_name
        dst = BASE_DIR / directory_name

        _write(
            f"処理中: {directory_name}"
        )

        _write(f"src = {src}")
        _write(f"dst = {dst}")

        if not src.exists():

            _warning(
                f"{directory_name} のダウンロード先がありません"
            )

            all_ok = False
            continue

        source_count = count_files(src)

        if source_count == 0:

            _warning(
                f"{directory_name} にファイルがありません"
            )

            all_ok = False
            continue

        dst.mkdir(
            parents=True,
            exist_ok=True,
        )

        copied = 0

        for source_file in src.rglob("*"):

            if not source_file.is_file():
                continue

            relative = source_file.relative_to(src)

            destination_file = (
                dst / relative
            )

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

            except Exception as e:

                _warning(
                    f"コピー失敗: "
                    f"{source_file}: {e}"
                )

        destination_count = count_files(dst)

        if destination_count > 0:

            _success(
                f"✅ {directory_name} を配置しました "
                f"({destination_count} files)"
            )

        else:

            _error(
                f"❌ {directory_name} の配置に失敗しました"
            )

            all_ok = False

    return all_ok


# ============================================================
# 必要モデル検索
# ============================================================

def find_model_file(
    filename: str,
) -> Optional[Path]:
    """
    モデルファイルを以下から検索。

    1. BASE_DIR
    2. models
    3. Weather_Model
    4. Combine_Model
    """

    candidates = [
        BASE_DIR / filename,
        BASE_DIR / "models" / filename,
        BASE_DIR / "Weather_Model" / filename,
        BASE_DIR / "Combine_Model" / filename,
    ]

    for path in candidates:

        if path.exists() and path.is_file():
            return path

    # 最終手段として再帰検索
    for directory_name in MODEL_DIRS:

        directory = (
            BASE_DIR / directory_name
        )

        if not directory.exists():
            continue

        matches = list(
            directory.rglob(filename)
        )

        if matches:
            return matches[0]

    return None


# ============================================================
# モデル構成確認
# ============================================================

def print_model_tree() -> None:

    _write("=== Installed Model Files ===")

    for directory_name in MODEL_DIRS:

        directory = (
            BASE_DIR / directory_name
        )

        if not directory.exists():

            _write(
                f"❌ {directory_name}: not found"
            )

            continue

        files = [
            p
            for p in directory.rglob("*")
            if p.is_file()
        ]

        _write(
            f"📁 {directory_name}: "
            f"{len(files)} files"
        )


# ============================================================
# メインダウンロード関数
# ============================================================

def download_models_from_gdrive(
    force: bool = False,
) -> bool:
    """
    Streamlit Cloud起動時に呼び出すメイン関数。

    成功:
        True

    失敗:
        False
    """

    # --------------------------------------------------------
    # 既にモデルが存在するなら何もしない
    # --------------------------------------------------------

    if not force:

        if check_model_directories():

            _success(
                "✅ 必要なモデルは既に存在します。"
            )

            return True

    _write("⚠️ モデルが存在しません")

    _write(
        "Running download_models_from_gdrive()."
    )

    _info(
        "📥 Google Drive からモデルをダウンロード中..."
    )

    _write(
        "初回のみ時間がかかる場合があります。"
    )

    # --------------------------------------------------------
    # 環境情報
    # --------------------------------------------------------

    _write("=== Environment Info ===")

    _write(
        f"gdown version: "
        f"{getattr(gdown, '__version__', 'unknown')}"
    )

    _write(
        f"BASE_DIR: {BASE_DIR}"
    )

    _write(
        f"TEMP_DIR: {TEMP_DIR}"
    )

    _write(
        f"Folder ID: {GDRIVE_FOLDER_ID}"
    )

    # --------------------------------------------------------
    # TEMP
    # --------------------------------------------------------

    prepare_temp_directory()

    # --------------------------------------------------------
    # Driveファイル一覧取得
    # --------------------------------------------------------

    _write("=== Google Drive File List ===")

    try:

        _write(
            "Google Driveフォルダを確認しています..."
        )

        file_list = get_drive_file_list()

    except Exception as e:

        _error(
            "Google Driveフォルダ取得中に"
            "エラーが発生しました"
        )

        _error(
            f"エラー: {type(e).__name__}: {e}"
        )

        return False

    if not file_list:

        _error(
            "Google Driveからファイル情報を"
            "取得できませんでした。"
        )

        _warning(
            "Google Driveフォルダが"
            "「リンクを知っている全員」に"
            "閲覧可能になっているか確認してください。"
        )

        return False

    # --------------------------------------------------------
    # ファイル分類表示
    # --------------------------------------------------------

    counts = {
        name: 0
        for name in MODEL_DIRS
    }

    for item in file_list:

        category = item.get("category")

        if category in counts:
            counts[category] += 1

    _write(
        f"ダウンロード対象: {len(file_list)}"
    )

    for name in MODEL_DIRS:

        _write(
            f"  {name}: {counts[name]} files"
        )

    # --------------------------------------------------------
    # ダウンロード
    # --------------------------------------------------------

    success_count, failed_count = (
        download_files(file_list)
    )

    # --------------------------------------------------------
    # ダウンロード後確認
    # --------------------------------------------------------

    list_downloaded_files()

    _write("=== Download Complete Check ===")

    _write(
        f"取得ファイル数: {success_count}"
    )

    if failed_count > 0:

        _warning(
            f"⚠️ {failed_count} ファイルの取得に失敗しました。"
        )

        _warning(
            "失敗したファイルは次回起動時に再試行されます。"
        )

    # --------------------------------------------------------
    # インストール
    # --------------------------------------------------------

    if success_count > 0:

        installed = install_models()

    else:

        installed = False

    # --------------------------------------------------------
    # 最終確認
    # --------------------------------------------------------

    _write("=== Final Check ===")

    final_ok = True

    for directory_name in MODEL_DIRS:

        directory = (
            BASE_DIR / directory_name
        )

        exists = (
            directory.exists()
            and count_files(directory) > 0
        )

        _write(
            f"{directory_name}: {exists}"
        )

        if not exists:
            final_ok = False

    print_model_tree()

    if final_ok:

        _success(
            "🎉 すべてのモデルのダウンロードと"
            "配置が完了しました！"
        )

        return True

    _error(
        "❌ モデルの一部または全部を"
        "配置できませんでした。"
    )

    return False


# ============================================================
# 単独実行
# ============================================================

if __name__ == "__main__":

    ok = download_models_from_gdrive()

    if ok:
        print("モデル準備完了")
    else:
        print("モデル準備失敗")
