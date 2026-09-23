#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit Cloud デプロイメント補助スクリプト

このスクリプトは GitHub にコードのみをプッシュするため、
モデルファイルのキャッシュをクリアします。
"""

import os
import subprocess
from pathlib import Path

def clean_git_cache():
    """
    Git キャッシュからモデルファイルを削除
    """
    print("🗑️  Git キャッシュをクリーニング中...")
    
    # キャッシュをクリア
    subprocess.run(["git", "rm", "-r", "--cached", "."], capture_output=True)
    
    print("✅ キャッシュクリア完了")

def rebuild_git_index():
    """
    .gitignore ルールに従って Git インデックスを再構築
    """
    print("🔧 Git インデックスを再構築中...")
    
    # すべてをもう一度 add
    result = subprocess.run(["git", "add", "."], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Git インデックス再構築完了")
        return True
    else:
        print(f"❌ エラー: {result.stderr}")
        return False

def get_status():
    """
    現在の Git ステータスを確認
    """
    result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
    print("\n📊 現在の変更:")
    print(result.stdout if result.stdout else "  （変更なし）")
    return result.stdout

def main():
    print("=" * 60)
    print("Streamlit Cloud デプロイメント準備スクリプト")
    print("=" * 60)
    
    # 1. 現在のディレクトリを確認
    cwd = Path.cwd()
    print(f"\n📁 作業ディレクトリ: {cwd}")
    
    # 2. .gitignore を確認
    gitignore = cwd / ".gitignore"
    if gitignore.exists():
        print("✅ .gitignore が存在します")
        print("\n📄 .gitignore の内容（モデル関連）:")
        with open(gitignore, 'r', encoding='utf-8') as f:
            for line in f:
                if 'pkl' in line or 'Model' in line or 'model' in line:
                    print(f"  {line.rstrip()}")
    else:
        print("❌ .gitignore が見つかりません")
    
    # 3. Git キャッシュをクリーニング
    print("\n" + "=" * 60)
    clean_git_cache()
    rebuild_git_index()
    
    # 4. ステータスを確認
    print("\n" + "=" * 60)
    get_status()
    
    # 5. コミット可能かチェック
    result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
    if result.stdout.strip():
        print("\n" + "=" * 60)
        print("次のコマンドを実行してください：")
        print("=" * 60)
        print('\ngit commit -m "Fix: Streamlit Cloud対応版（モデルファイル除外）"')
        print("git push origin main\n")
    else:
        print("\n✅ すべてのモデルが除外されました。準備完了！\n")

if __name__ == "__main__":
    main()
