
# -*- coding: utf-8 -*-
"""
Streamlit Cloud 用モデルダウンローダー

Google Drive 上の「モデル一式ZIP」を1ファイルだけ gdown で取得し、
models / Weather_Model / Combine_Model / UP_Model とルート直下へ展開する。

設計方針:
- Google Drive API / google.oauth2 は使用しない
- gdown.download_folder() は使用しない
- Google Drive のHTML解析もしない
- 1個のZIPファイルだけをダウンロードする
- 最大3回リトライ
- 途中まで配置済みのモデルは再利用
- ZIP内の日本語ファイル名に対応
- ZIP Slip（パストラバーサル）を防止
- 必要ファイルを明示的に検証する
- filelock でモデル準備処理の同時実行を防ぐ
- ロック取得後にモデルの状態を再確認する
"""

from __future__ import annotations

import os
import shutil
import time
import zipfile
from pathlib import Path
from typing import Iterable

import gdown
from filelock import FileLock, Timeout

try:
    import streamlit as st
except ImportError:
    st = None


# ============================================================
# 基本設定
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / ".gdrive_temp"
ZIP_CACHE = TEMP_DIR / "weather-models.zip"
EXTRACT_DIR = TEMP_DIR / "extracted"

# モデル準備処理の排他制御用ロックファイル
MODEL_LOCK = BASE_DIR / ".model_download.lock"

MODEL_DIRS = [
    "models",
    "Weather_Model",
    "Combine_Model",
    "UP_Model",
]

# Google Drive にアップロードした「モデル一式ZIP」のファイルID。
# 環境変数 GDRIVE_MODEL_ZIP_ID を優先する。
GDRIVE_ZIP_FILE_ID = os.getenv(
    "GDRIVE_MODEL_ZIP_ID",
    "ここにGoogle DriveのZIPファイルIDを設定",
).strip()

MAX_RETRIES = 3
RETRY_WAIT_SECONDS = 5
MIN_VALID_FILE_SIZE = 1

# 別セッションが処理中の場合、最大10分間ロック取得を待つ
LOCK_TIMEOUT_SECONDS = 600


# ============================================================
# 表示ヘルパー
# ============================================================
def _write(message: str) -> None:
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
# 必要ファイル一覧
# ============================================================
def _required_root_files() -> list[str]:
    return [
        "model_toden_power_weather.pkl",
        "scaler_toden_power_weather.pkl",
        "feature_cols_toden.pkl",
        "model_tohoku_power_weather.pkl",
        "scaler_tohoku_power_weather.pkl",
        "feature_cols_tohoku.pkl",
    ]


def _required_models_files() -> list[str]:
    files: list[str] = []

    for location in ("kumagaya", "sendai"):
        for element in ("原子力", "風力発電実績", "水力"):
            files.append(f"models/model_{location}_{element}.pkl")

        files.append(f"models/scaler_{location}.pkl")

    return files


def _required_weather_files() -> list[str]:
    files: list[str] = []

    for location in ("kumagaya", "sendai"):
        for element in (
            "気温",
            "相対湿度",
            "降水量",
            "風速",
            "日射量",
            "天気",
        ):
            files.append(
                f"Weather_Model/model_{location}_{element}.pkl"
            )

        files.append(f"Weather_Model/scaler_{location}.pkl")

    return files


def _required_up_model_files() -> list[str]:
    """UP_Model に必要なモデル・メタデータファイルを返す。"""
    files: list[str] = []

    for location in ("kumagaya", "sendai"):
        for element in ("火力", "原子力", "水力", "太陽光", "風力"):
            files.append(
                f"UP_Model/up_model_{location}_{element}.pkl"
            )

        files.append(
            f"UP_Model/UnitP_Model_metadata_{location}.json"
        )

    return files


def _required_combine_files() -> list[str]:
    combinations = [
        ("原子力", "01"),
        ("火力", "02"),
        ("水力", "03"),
        ("太陽光発電実績", "04"),
        ("風力発電実績", "05"),
        ("原子力_火力", "06"),
        ("原子力_水力", "07"),
        ("原子力_太陽光発電実績", "08"),
        ("原子力_風力発電実績", "09"),
        ("火力_水力", "10"),
        ("火力_太陽光発電実績", "11"),
        ("火力_風力発電実績", "12"),
        ("水力_太陽光発電実績", "13"),
        ("水力_風力発電実績", "14"),
        ("太陽光発電実績_風力発電実績", "15"),
        ("原子力_火力_水力", "16"),
        ("原子力_火力_太陽光発電実績", "17"),
        ("原子力_火力_風力発電実績", "18"),
        ("原子力_水力_太陽光発電実績", "19"),
        ("原子力_水力_風力発電実績", "20"),
        ("原子力_太陽光発電実績_風力発電実績", "21"),
        ("火力_水力_太陽光発電実績", "22"),
        ("火力_水力_風力発電実績", "23"),
        ("火力_太陽光発電実績_風力発電実績", "24"),
        ("水力_太陽光発電実績_風力発電実績", "25"),
        ("原子力_火力_水力_太陽光発電実績", "26"),
        ("原子力_火力_水力_風力発電実績", "27"),
        ("原子力_火力_太陽光発電実績_風力発電実績", "28"),
        ("原子力_水力_太陽光発電実績_風力発電実績", "29"),
        ("火力_水力_太陽光発電実績_風力発電実績", "30"),
        ("原子力_火力_水力_太陽光発電実績_風力発電実績", "31"),
    ]

    files: list[str] = []

    for location in ("toden", "tohoku"):
        for combination_name, number in combinations:
            prefix = f"Combine_Model/"

            files.append(
                f"{prefix}model_{location}_{number}_{combination_name}.pkl"
            )
            files.append(
                f"{prefix}scaler_{location}_{number}_{combination_name}.pkl"
            )
            files.append(
                f"{prefix}info_{location}_{number}_{combination_name}.json"
            )

    return files


def get_required_model_files() -> list[str]:
    """アプリが必要とする全モデルファイルを返す。"""
    return (
        _required_root_files()
        + _required_models_files()
        + _required_weather_files()
        + _required_up_model_files()
        + _required_combine_files()
    )


# ============================================================
# ファイル確認
# ============================================================
def _is_valid_file(path: Path) -> bool:
    try:
        return (
            path.is_file()
            and path.stat().st_size >= MIN_VALID_FILE_SIZE
        )
    except OSError:
        return False


def get_missing_model_files() -> list[str]:
    return [
        relative
        for relative in get_required_model_files()
        if not _is_valid_file(BASE_DIR / relative)
    ]


def get_existing_model_count() -> int:
    required = get_required_model_files()

    return sum(
        1
        for relative in required
        if _is_valid_file(BASE_DIR / relative)
    )


def check_models_complete() -> bool:
    return len(get_missing_model_files()) == 0


# ============================================================
# ZIPダウンロード
# ============================================================
def _get_zip_file_id() -> str:
    value = os.getenv(
        "GDRIVE_MODEL_ZIP_ID",
        GDRIVE_ZIP_FILE_ID,
    ).strip()

    if (
        not value
        or value == "ここにGoogle DriveのZIPファイルIDを設定"
    ):
        raise RuntimeError(
            "Google DriveのモデルZIPファイルIDが設定されていません。"
            "GDRIVE_MODEL_ZIP_ID を Streamlit Secrets / "
            "環境変数に設定してください。"
        )

    return value


def download_model_zip() -> Path:
    """
    モデルZIPを取得する。

    この関数は download_models_from_gdrive() がロックを
    取得した状態で呼び出すことを前提とする。
    """
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    file_id = _get_zip_file_id()

    if _is_valid_file(ZIP_CACHE):
        # ZIPとして正常かも確認してから再利用する
        try:
            with zipfile.ZipFile(ZIP_CACHE, "r") as zf:
                if zf.testzip() is None:
                    _write(f"既存のZIPを再利用します: {ZIP_CACHE}")
                    return ZIP_CACHE
        except (OSError, zipfile.BadZipFile):
            pass

        _warning("既存のZIPが破損しているため、再取得します。")

    url = f"https://drive.google.com/uc?id={file_id}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _write(f"📦 モデルZIP取得 {attempt}/{MAX_RETRIES}")

            if ZIP_CACHE.exists():
                try:
                    ZIP_CACHE.unlink()
                except OSError:
                    pass

            result = gdown.download(
                url=url,
                output=str(ZIP_CACHE),
                quiet=False,
                resume=False,
            )

            if result is None or not _is_valid_file(ZIP_CACHE):
                raise RuntimeError(
                    "モデルZIPを取得できませんでした"
                )

            # HTMLなどをZIPとして誤認しないよう検証
            with zipfile.ZipFile(ZIP_CACHE, "r") as zf:
                bad = zf.testzip()

                if bad is not None:
                    raise RuntimeError(
                        f"取得したZIPが破損しています: {bad}"
                    )

            _success(
                "✅ モデルZIP取得成功 "
                f"({ZIP_CACHE.stat().st_size / 1024 / 1024:.1f} MB)"
            )

            return ZIP_CACHE

        except Exception as exc:
            _warning(
                f"⚠️ ZIP取得失敗 ({attempt}/{MAX_RETRIES}): "
                f"{type(exc).__name__}: {exc}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT_SECONDS)

    raise RuntimeError("モデルZIPの取得に失敗しました")


# ============================================================
# ZIP安全展開
# ============================================================
def _safe_zip_members(
    zf: zipfile.ZipFile,
) -> Iterable[tuple[zipfile.ZipInfo, Path]]:
    root = EXTRACT_DIR.resolve()

    for info in zf.infolist():
        # ZIP内のパス区切りを統一し、危険なパスを拒否する
        normalized_name = info.filename.replace("\\", "/")
        member = Path(normalized_name)

        if (
            member.is_absolute()
            or ".." in member.parts
            or "\x00" in normalized_name
        ):
            raise RuntimeError(
                f"安全でないZIPパスです: {info.filename}"
            )

        # Windowsドライブ形式も拒否
        if member.parts and ":" in member.parts[0]:
            raise RuntimeError(
                f"安全でないZIPパスです: {info.filename}"
            )

        target = (EXTRACT_DIR / member).resolve()

        try:
            target.relative_to(root)
        except ValueError:
            raise RuntimeError(
                f"安全でないZIPパスです: {info.filename}"
            )

        yield info, target


def extract_model_zip(zip_path: Path) -> Path:
    if EXTRACT_DIR.exists():
        shutil.rmtree(EXTRACT_DIR)

    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

    _write("📂 モデルZIPを展開しています...")

    with zipfile.ZipFile(zip_path, "r") as zf:
        bad = zf.testzip()

        if bad is not None:
            raise RuntimeError(f"ZIPが破損しています: {bad}")

        members = list(_safe_zip_members(zf))

        for info, target in members:
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)

            with zf.open(info, "r") as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)

    _success("✅ ZIP展開完了")

    return EXTRACT_DIR


# ============================================================
# ZIP構造の吸収
# ============================================================
def _find_extracted_file(
    root: Path,
    relative: str,
) -> Path | None:
    direct = root / relative

    if _is_valid_file(direct):
        return direct

    # ZIPが weather-models/ などの配下になっている場合に対応
    target_parts = Path(relative).parts
    target_length = len(target_parts)

    candidates = root.rglob(Path(relative).name)

    for candidate in candidates:
        try:
            rel_parts = candidate.relative_to(root).parts
        except ValueError:
            continue

        if not _is_valid_file(candidate):
            continue

        if (
            len(rel_parts) >= target_length
            and tuple(rel_parts[-target_length:]) == tuple(target_parts)
        ):
            return candidate

    return None


def install_missing_models(
    extracted_root: Path,
) -> tuple[int, list[str]]:
    """
    不足しているモデルだけ配置する。

    既に存在する正常ファイルは再利用する。
    """
    required = get_required_model_files()
    installed = 0
    missing: list[str] = []

    _write("=== Model Installation ===")

    for relative in required:
        destination = BASE_DIR / relative

        if _is_valid_file(destination):
            continue

        source = _find_extracted_file(extracted_root, relative)

        if source is None:
            missing.append(relative)
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        installed += 1

    return installed, missing


# ============================================================
# ロック内で実行するモデル準備処理
# ============================================================
def _download_models_unlocked(force: bool = False) -> bool:
    """
    ロック取得済みの状態でモデルを準備する。

    この関数を直接呼び出さず、
    download_models_from_gdrive() から呼び出すこと。
    """
    existing = get_existing_model_count()
    total = len(get_required_model_files())

    _write("=== Model Check (Locked) ===")
    _write(f"必要ファイル: {total}")
    _write(f"存在ファイル: {existing}")

    if not force and existing == total:
        _success("✅ 必要なモデルはすべて揃っています。")
        return True

    missing = get_missing_model_files()
    _warning(f"不足ファイル: {len(missing)}")

    if missing and len(missing) <= 10:
        for name in missing:
            _write(f"  - {name}")

    try:
        zip_path = download_model_zip()
        extracted_root = extract_model_zip(zip_path)

        installed, zip_missing = install_missing_models(
            extracted_root
        )

        _write(f"配置したファイル: {installed}")

        if zip_missing:
            _error("❌ ZIP内に必要ファイルが不足しています。")

            for name in zip_missing[:30]:
                _write(f"  - {name}")

            if len(zip_missing) > 30:
                _write(f"  ... 他 {len(zip_missing) - 30} 件")

            return False

    except Exception as exc:
        _error(
            "❌ モデル準備に失敗しました: "
            f"{type(exc).__name__}: {exc}"
        )
        return False

    final_missing = get_missing_model_files()
    final_count = get_existing_model_count()

    _write("=== Final Model Check ===")
    _write(f"存在ファイル: {final_count}/{total}")

    if final_missing:
        _error(
            f"❌ まだ不足しているファイル: {len(final_missing)}"
        )

        for name in final_missing[:30]:
            _write(f"  - {name}")

        return False

    _success("🎉 すべてのモデルファイルの準備が完了しました！")

    return True


# ============================================================
# メイン：排他制御付きの公開関数
# ============================================================
def download_models_from_gdrive(force: bool = False) -> bool:
    """
    必要モデルを揃える。

    1. ロックを取得する
    2. ロック取得後にモデルの状態を再確認する
    3. すべて揃っていればGoogle Driveへアクセスしない
    4. 不足していればZIPを取得し、不足分を配置する
    5. 処理終了時にロックを解放する

    force=True の場合は、モデルが揃っていても準備処理を実行する。
    ただし、既存ファイルを強制的に上書きする機能ではない。
    """
    try:
        _write("🔒 モデル準備ロックを取得しています...")

        # 同一ファイルシステムを共有する処理同士を排他制御
        with FileLock(
            str(MODEL_LOCK),
            timeout=LOCK_TIMEOUT_SECONDS,
        ):
            _write("🔓 モデル準備ロックを取得しました。")

            # 重要：
            # ロック取得前の確認結果は信用せず、
            # ロック取得後に必ず状態を再確認する。
            existing = get_existing_model_count()
            total = len(get_required_model_files())

            _write("=== Model Check ===")
            _write(f"必要ファイル: {total}")
            _write(f"存在ファイル: {existing}")

            if not force and existing == total:
                _success("✅ 必要なモデルはすべて揃っています。")
                return True

            # ロック内でダウンロード・展開・配置を実行
            return _download_models_unlocked(force=force)

    except Timeout:
        _error(
            "❌ モデル準備ロックの取得がタイムアウトしました。"
            f" {LOCK_TIMEOUT_SECONDS} 秒以内に他の処理が終了しませんでした。"
        )
        return False

    except Exception as exc:
        _error(
            "❌ モデル準備処理でエラーが発生しました: "
            f"{type(exc).__name__}: {exc}"
        )
        return False


# ============================================================
# 単独実行
# ============================================================
if __name__ == "__main__":
    ok = download_models_from_gdrive()

    print(
        "モデル準備完了" if ok else "モデル準備失敗"
    )
