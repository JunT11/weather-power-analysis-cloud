# -*- coding: utf-8 -*-
"""
Google Drive モデルダウンロード機能

Streamlit Cloud での起動時に Google Drive からモデルを自動ダウンロードします
"""

import streamlit as st
import gdown
from pathlib import Path
import os
import shutil

# Google Drive フォルダID（weather-models フォルダ全体）
GDRIVE_WEATHER_MODELS_FOLDER_ID = "11CrLEAr_ljmYx1Ib5TPpWG_kvwDElNgS"

@st.cache_resource
def download_models_from_gdrive():
    """
    Google Drive からモデルをダウンロード
    初回のみダウンロード、以降はキャッシュから使用
    
    このフォルダの構造:
    weather-models/
    ├── models/
    ├── Weather_Model/
    └── Combine_Model/
    """
    BASE_DIR = Path(__file__).resolve().parent
    temp_dir = BASE_DIR / ".gdrive_temp"
    
    try:
        st.info("📥 Google Drive からモデルをダウンロード中...（初回のみ、5-10分かかります）")
        
        # 一時ディレクトリにダウンロード
        gdown.download_folder(
            id=GDRIVE_WEATHER_MODELS_FOLDER_ID,
            output=str(temp_dir),
            quiet=False,
            use_cookies=False
        )
        
        # ダウンロードしたフォルダから models/, Weather_Model/, Combine_Model/ を抽出
        weather_models_dir = temp_dir / "weather-models"
        
        if weather_models_dir.exists():
            source_dir = weather_models_dir
        else:
            source_dir = temp_dir
        
        # 各フォルダを移動
        for folder_name in ["models", "Weather_Model", "Combine_Model"]:
            src = source_dir / folder_name
            dst = BASE_DIR / folder_name
            
            if src.exists() and not dst.exists():
                shutil.move(str(src), str(dst))
                st.success(f"✅ {folder_name} をダウンロード完了")
        
        # 一時ディレクトリを削除
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        
        st.success("🎉 すべてのモデルをダウンロードしました！")
        return True
        
    except Exception as e:
        st.error(f"❌ ダウンロード中にエラーが発生しました: {str(e)}")
        st.error("ローカルで実行するか、ネットワーク接続を確認してください。")
        
        # 一時ディレクトリをクリーンアップ
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        
        return False


def setup_models():
    """
    モデルセットアップ（起動時に実行）
    
    モデルフォルダが存在しない場合、Google Drive からダウンロードします
    """
    BASE_DIR = Path(__file__).resolve().parent
    
    # 3つのフォルダすべてが存在するかチェック
    models_exist = (
        (BASE_DIR / "models").exists() and
        (BASE_DIR / "Weather_Model").exists() and
        (BASE_DIR / "Combine_Model").exists()
    )
    
    if not models_exist:
        st.warning("⚠️ モデルが見つかりません。Google Drive からダウンロードしています...")
        
        success = download_models_from_gdrive()
        
        if not success:
            st.error("❌ モデルのダウンロードに失敗しました")
            st.info("💡 ローカルで実行する場合は、models/, Weather_Model/, Combine_Model/ が存在することを確認してください")
            st.stop()
    else:
        # モデルが存在する場合は何もしない（ログは出さない）
        pass


if __name__ == "__main__":
    # テスト用：直接実行時にモデルをダウンロード
    setup_models()
    print("✅ モデルセットアップ完了")

