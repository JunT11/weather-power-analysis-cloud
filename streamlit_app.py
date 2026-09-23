"""
Streamlit Cloud Entry Point
このファイルはStreamlit Cloudでのエントリーポイントです

Google Drive からモデルを自動ダウンロードしてアプリを起動します
"""

import sys
import traceback

# モデルセットアップを実行
try:
    from model_downloader import setup_models
    setup_models()  # Google Drive からモデルをダウンロード
except ImportError:
    pass  # model_downloader が存在しない場合はスキップ
except Exception as e:
    import streamlit as st
    st.warning(f"⚠️ モデルセットアップ時に警告: {str(e)}")

# メインアプリケーションを実行
try:
    from Weather_Analysis_Power_Prediction import main
    main()
    
except ModuleNotFoundError as e:
    import streamlit as st
    st.error(f"❌ モジュールが見つかりません: {str(e)}")
    st.error("requirements.txt が正しくインストールされているか確認してください")
    st.text("Full traceback:")
    st.text(traceback.format_exc())
    
except FileNotFoundError as e:
    import streamlit as st
    st.error(f"❌ ファイルが見つかりません: {str(e)}")
    st.error("必要なモデルファイルが見つかりません。")
    st.info("ローカルで実行するか、Streamlit Cloud でのデプロイを確認してください。")
    st.text("Full traceback:")
    st.text(traceback.format_exc())
    
except Exception as e:
    import streamlit as st
    st.error(f"❌ エラーが発生しました: {str(e)}")
    st.text("Full traceback:")
    st.text(traceback.format_exc())

