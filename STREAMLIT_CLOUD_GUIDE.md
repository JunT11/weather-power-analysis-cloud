# 🚀 Streamlit Cloud デプロイガイド

このドキュメントでは、このアプリケーションをStreamlit Cloudで複数人が使用できるようにセットアップする手順を説明します。

## 📋 前提条件

1. **GitHubアカウント** - ソースコード管理用
2. **Streamlit Cloudアカウント** - アプリ公開用（https://streamlit.io/cloud で無料作成可能）
3. **Git** - ローカル環境にインストール済み

## 🔧 ステップ1: GitHubにリポジトリを作成

### 1.1 GitHubにログイン
https://github.com にアクセスしてログイン

### 1.2 新しいリポジトリを作成
- **Repository name**: `weather-analysis-power-prediction` (例)
- **Description**: `気象データから電力供給構成を予測するStreamlitアプリ`
- **Public** を選択（複数人がアクセスするため）
- README の作成は不要（すでに存在）

### 1.3 ローカルからGitHubにプッシュ

PowerShellまたはコマンドプロンプトを開き、以下を実行：

```powershell
cd c:\Users\taj2hig\Work_Space\Other\O5_Weather\Weather_Analysis_New_3

# Gitの初期化（未実施の場合）
git init

# リモートリポジトリを追加
git remote add origin https://github.com/YOUR_USERNAME/weather-analysis-power-prediction.git

# ローカルブランチをメインに変更（必要な場合）
git branch -M main

# すべてのファイルをステージング
git add .

# コミット
git commit -m "Initial commit: Streamlit Cloud対応版"

# GitHubにプッシュ
git push -u origin main
```

## 🌐 ステップ2: Streamlit Cloudでアプリをデプロイ

### 2.1 Streamlit Cloudにログイン
https://share.streamlit.io にアクセス

### 2.2 「新しいアプリ」をデプロイ

1. **「Create app」** をクリック
2. 以下を入力：
   - **Repository**: `YOUR_USERNAME/weather-analysis-power-prediction`
   - **Branch**: `main`
   - **Main file path**: `streamlit_app.py`

3. **「Deploy」** をクリック

### 2.3 デプロイの確認

- アプリが自動でビルド・デプロイされます（1-5分）
- 完了後、URLが割り当てられます
- 例: `https://weather-analysis-power-prediction.streamlit.app`

## 👥 複数人でのアクセス

### ユーザーとの共有

デプロイ完了後のURLをメール、Slack、チャットなどで共有：

```
🔗 アプリURL: https://weather-analysis-power-prediction.streamlit.app
```

### アクセス権の設定（オプション）

Streamlit Cloudでアプリ設定で、以下の設定が可能：
- **Public** - 誰でもアクセス可能
- **Private** - 招待ユーザーのみ

## 📊 複数ユーザー間の特徴

このアプリケーションは以下の機能で複数ユーザーをサポート：

✅ **セッション独立**: 各ユーザーのセッションが独立
✅ **キャッシング**: `@st.cache_resource` で モデルやデータを効率的に共有
✅ **大規模ファイル対応**: 最大200MBまでのCSVアップロード対応
✅ **リアルタイム予測**: 複数ユーザーが同時に使用可能

## 🔄 更新・修正方法

アプリケーションを更新する場合：

```powershell
# ローカルで変更・テスト
# 例: Weather_Analysis_Power_Prediction.py を編集

# 変更をコミット
git add .
git commit -m "Fix: 予測精度を改善"

# GitHubにプッシュ
git push origin main
```

**Streamlit Cloudは自動でGitHubリポジトリを監視し、`main`ブランチへのプッシュを検出すると自動でアプリを再デプロイします。**

## 🛠️ トラブルシューティング

### デプロイエラーが出た場合

1. **Streamlit Cloud のログを確認**
   - アプリダッシュボード → 「View logs」

2. **よくあるエラー**

| エラー | 原因 | 解決方法 |
|--------|------|--------|
| `ModuleNotFoundError` | パッケージが requirements.txt にない | requirements.txt を追加して git push |
| `FileNotFoundError` | モデルファイルが見つからない | models/ フォルダがGitにコミットされているか確認 |
| `Path issues` | パスが正しく設定されていない | `BASE_DIR` を使用（既に修正済み） |

### ローカルでテストする場合

```powershell
# ローカルで Streamlit を実行
streamlit run streamlit_app.py
```

ブラウザで `http://localhost:8501` にアクセス

## 📁 ディレクトリ構造（GitHub用）

```
weather-analysis-power-prediction/
├── streamlit_app.py                    ← エントリーポイント
├── Weather_Analysis_Power_Prediction.py ← メインアプリ
├── requirements.txt                     ← 依存パッケージ
├── README.md                           ← プロジェクト説明
├── .streamlit/
│   └── config.toml                     ← Streamlit設定
├── .gitignore
├── models/                             ← モデルファイル
│   ├── model_kumagaya_*.pkl
│   ├── scaler_kumagaya_*.pkl
│   └── ...
├── Weather_Model/                      ← 気象予測モデル
│   └── ...
├── Combine_Model/                      ← 複合モデル
│   └── ...
└── data/                               ← データファイル
    └── *.csv
```

## 📝 重要なポイント

### ✅ すべてのファイルをコミット
- **含める**: Python ファイル、requirements.txt、.streamlit/, models/, data/
- **除外する**: `__pycache__/`, `.env`, `.streamlit/secrets.toml` (`.gitignore` で自動除外)

### 📦 ファイルサイズの注意
- Streamlit Cloudのファイルサイズ制限: 1リポジトリあたり2GB以下推奨
- 大量のモデルファイルがある場合、別ストレージの使用も検討

### 🔐 秘密情報の管理
- API キー、パスワードなどは `.streamlit/secrets.toml` に保存
- Streamlit Cloud側で環境変数として設定

## 💡 便利なコマンド

```powershell
# リポジトリの状態を確認
git status

# コミット履歴を確認
git log

# 最新の変更をプッシュ
git add . ; git commit -m "更新内容"; git push origin main

# リモートのデフォルトブランチを確認
git remote -v
```

## 📞 サポート・参考

- **Streamlit公式ドキュメント**: https://docs.streamlit.io
- **Streamlit Cloudデプロイガイド**: https://docs.streamlit.io/streamlit-cloud/get-started
- **GitHub連携**: https://docs.streamlit.io/streamlit-cloud/get-started/deploy-an-app

---

🎉 **完了！** これであなたのアプリは複数人で使用できるようになりました。
