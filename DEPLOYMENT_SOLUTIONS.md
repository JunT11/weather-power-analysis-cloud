# 🚀 Streamlit Cloud デプロイ - トラブルシューティング

## 問題

モデルファイル（`.pkl`）が大きすぎて GitHub の 100MB サイズ制限を超えています。

```
❌ Error: File ... exceeds GitHub's file size limit of 100.00 MB
```

---

## ✅ 推奨される解決策

### **方案 A: Streamlit Secrets & クラウドストレージを使用（推奨）**

#### ステップ1: モデルファイルをクラウドストレージにアップロード

以下から選択してください：

**Option 1: Google Drive（無料・最も簡単）**
1. Google Drive に `models/`, `Weather_Model/`, `Combine_Model/` を作成
2. `streamlit_secrets.toml` に Google Drive の認証情報を設定
3. 実行時にダウンロード

**Option 2: AWS S3（有料・高速）**
1. AWS S3 に モデルフォルダをアップロード
2. IAM キーを取得
3. `streamlit_secrets.toml` に設定

**Option 3: HuggingFace Hub（無料）**
1. HuggingFace にモデルをアップロード
2. 実行時にダウンロード

#### ステップ2: コードを修正

```python
# streamlit_app.py の先頭に追加
import gdown  # Google Drive ダウンロード
import os

def download_models_from_cloud():
    """
    クラウドストレージからモデルをダウンロード
    """
    # Google Drive のフォルダID
    folder_id = "YOUR_GOOGLE_DRIVE_FOLDER_ID"
    
    # ダウンロード先
    download_dir = Path(__file__).parent / "models"
    
    # ダウンロード
    gdown.download_folder(id=folder_id, output=str(download_dir))

# アプリ起動時に実行
if not os.path.exists("models"):
    download_models_from_cloud()
```

#### ステップ3: requirements.txt に追加

```
gdown>=4.7.1  # Google Drive ダウンロード用
```

---

### **方案 B: ローカル開発用 / クラウドデプロイ用を分離**

#### ローカル開発（モデルあり）
```bash
streamlit run Weather_Analysis_Power_Prediction.py
```

#### Streamlit Cloud デプロイ（機能限定版）

GitHub には以下のみをプッシュ：
- `.py` ファイル（コード）
- `requirements.txt`
- `README.md`
- `.streamlit/`
- `data/` （CSVファイルのみ）

モデルが見つからない場合のエラーハンドリング：
```python
try:
    model = load_model(...)
except FileNotFoundError:
    st.warning("⚠️ モデルファイルがクラウドで利用できません")
    st.info("このアプリはローカルでの使用を想定しています")
    st.stop()
```

---

### **方案 C: 実装方針（最も簡潔）**

GitHub に push するのは **コードのみ** にして、モデルは別途管理：

#### 1. ローカルで実行する場合
```bash
# 前提: models/, Weather_Model/, Combine_Model/ がすべてローカルに存在
streamlit run streamlit_app.py
```

#### 2. Streamlit Cloud で実行する場合
- コードのみが push される
- クラウドでエラーが出ないように、モデル不在時の処理を追加

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODELS_AVAILABLE = (BASE_DIR / "models").exists()

if not MODELS_AVAILABLE:
    import streamlit as st
    st.error("モデルがこの環境では利用できません")
    st.info("ローカルで実行してください")
    st.stop()
```

---

## 🔧 すぐに実装できる方法

### ステップ1: 現在の状態をリセット

```powershell
cd c:\Users\taj2hig\Work_Space\Other\O5_Weather\Weather_Analysis_New_3

# GitHub 削除（クラウドの大きいリポを削除）
# https://github.com/JunT11/Weather_Data_Analysis_new にアクセス
# Settings → Delete this repository

# 新しいリポを作成
# https://github.com/new
```

### ステップ2: コードのみをプッシュ（新しいリポ）

```powershell
cd c:\Users\taj2hig\Work_Space\Other\O5_Weather\Weather_Analysis_New_3

# 既存のGitをリセット
rm -r .git

# 新しいリポに
git init
git remote add origin https://github.com/YOUR_USERNAME/weather-analysis-power-prediction.git

# コードのみを push（.gitignore でモデル除外）
git add -A
git commit -m "Streamlit Cloud対応版（コードのみ）"
git push -u origin main
```

### ステップ3: Streamlit Cloud でデプロイ

通常通りデプロイしてください。モデルがない場合のエラーハンドリングが組み込まれています。

---

## 📊 各方案の比較

| 方案 | 難易度 | コスト | 多人数対応 | 推奨度 |
|------|--------|-------|----------|--------|
| **A: クラウドストレージ** | 中 | 無料 | ✅ | ⭐⭐⭐ |
| **B: 分離版** | 低 | 無料 | ✅ | ⭐⭐ |
| **C: コード限定** | 低 | 無料 | ❌ | ⭐ |

---

## 💡 推奨手順（方案A - Google Drive）

```powershell
# 1. Google Drive にモデルをアップロード
#    フォルダID を控えておく

# 2. .gitignore確認
# モデルが除外されているか確認
cat .gitignore

# 3. 新規リポ作成
git init
git remote add origin https://github.com/YOUR_USERNAME/weather-cloud.git

# 4. コードのみを push
git add .
git commit -m "Streamlit Cloud対応版"
git push -u origin main

# 5. Streamlit Cloud でデプロイ
# 自動で再デプロイされます
```

---

## 📝 次のステップ

1. **どの方案を選びますか？** (A/B/C)
2. **Google Drive / AWS S3 など、ストレージの決定**
3. **新しい GitHub リポの作成**
4. **Streamlit Cloud へのデプロイ**

ご質問があればお知らせください！
