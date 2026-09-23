# 🔄 新規リポジトリ作成 - ステップバイステップ

## 問題点

古い Git 履歴にモデルファイルが残っているため、現在のリポジトリではサイズ制限を超えてしまいます。

**解決方法**: 新しいリポジトリを作成し、**コードのみ**を push します。

---

## 📋 実行手順

### ステップ1: 古いリポジトリをバックアップ

```powershell
# 古いリポジトリフォルダをバックアップ
cd c:\Users\taj2hig\Work_Space\Other\O5_Weather\Weather_Analysis_New_3
cd ..
cp -r Weather_Analysis_New_3 Weather_Analysis_New_3_backup
```

### ステップ2: 新しい GitHub リポジトリを作成

1. https://github.com/new にアクセス
2. リポジトリ名を入力（例: `weather-power-analysis-cloud`）
3. **Public** を選択
4. **Do not initialize with README** を選択
5. **Create repository** をクリック

新しいリポジトリの URL をコピー：
```
https://github.com/YOUR_USERNAME/weather-power-analysis-cloud.git
```

### ステップ3: ローカルで Git をリセット

```powershell
cd c:\Users\taj2hig\Work_Space\Other\O5_Weather\Weather_Analysis_New_3

# 古い Git 設定を削除
rm -r .git

# 新しい Git リポジトリを初期化
git init
git branch -M main

# 新しいリモートを追加
git remote add origin https://github.com/YOUR_USERNAME/weather-power-analysis-cloud.git
```

### ステップ4: コードのみを commit

```powershell
# .gitignore が正しく設定されていることを確認
cat .gitignore | Select-String -Pattern "pkl|Model"

# コードをステージング（モデルは除外される）
git add .

# 状態を確認（モデルファイルがないことを確認）
git status
```

**重要**: 以下が表示されて **いない** ことを確認：
```
models/
Weather_Model/
Combine_Model/
*.pkl
```

### ステップ5: コミットとプッシュ

```powershell
# コミット
git commit -m "Initial commit: Streamlit Cloud対応版"

# プッシュ
git push -u origin main
```

✅ **成功!** リポジトリが GitHub に作成されました。

---

## 🚀 Streamlit Cloud でのデプロイ

1. https://share.streamlit.io にアクセス
2. **「Create App」** をクリック
3. 以下を入力：
   - **Repository**: `YOUR_USERNAME/weather-power-analysis-cloud`
   - **Branch**: `main`
   - **Main file path**: `streamlit_app.py`
4. **Deploy** をクリック

✅ アプリが自動デプロイされます！

---

## 📝 .gitignore の確認

以下が含まれていることを確認してください：

```
# Model files - Streamlit Cloud deployment用にはローカルのみ使用
*.pkl
model_*.pkl
scaler_*.pkl
feature_cols_*.pkl
models/
Weather_Model/
Combine_Model/
```

---

## ⚠️ よくある質問

### Q: ローカルでモデルを使いたいのに、Streamlit Cloud では動かないのでは？

**A**: はい、その通りです。2つの方法があります：

**方法1: ローカル開発のみ（推奨）**
- ローカルの `streamlit run streamlit_app.py` で完全に使用
- GitHub には コードのみを置く

**方法2: Streamlit Cloud で完全に動かす（高度）**
- Google Drive / AWS S3 からモデルをダウンロード
- コードを修正してダウンロード機能を追加
- 詳細は `DEPLOYMENT_SOLUTIONS.md` を参照

---

## 🧹 クリーンアップ（オプション）

```powershell
# 古いリポジトリをバックアップ後、削除
cd c:\Users\taj2hig\Work_Space\Other\O5_Weather
rm -r Weather_Analysis_New_3  # 古いフォルダを削除
```

---

## 📞 デバッグ

`git push` でエラーが出た場合：

```powershell
# 認証情報をリセット
git config --global user.email "your_email@example.com"
git config --global user.name "Your Name"

# もう一度 push
git push -u origin main --force
```

それでもダメな場合は、`git remote -v` でリモート URL を確認してください。
