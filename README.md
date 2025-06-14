# 🎬 喋る風Vtuber動画ジェネレーター

音声ファイルと2枚のアバター画像（口閉じ・口開き）をアップロードすることで、音声に同期した口パク風の動画を自動生成するWebアプリケーションです。

## ✨ 特徴

- 🎤 **音声同期**: WAV形式の音声ファイルに同期した口パクアニメーション
- 🖼️ **簡単操作**: 2枚の画像（口閉じ・口開き）をアップロードするだけ
- 🎬 **高品質出力**: 30fps、グリーンバック背景のMP4動画を生成
- 💾 **即座にダウンロード**: 生成完了後すぐにダウンロード可能
- 🔄 **自動画像調整**: 異なるサイズの画像も自動でリサイズ

## 🚀 クイックスタート

### 必要な環境
- Python 3.8以上
- FFmpeg（音声・動画処理に必要）

### FFmpegのインストール

**Windows:**
```bash
# Chocolateyを使用する場合
choco install ffmpeg

# または公式サイトからダウンロード
# https://ffmpeg.org/download.html
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

### アプリケーションの起動

1. **簡単起動（推奨）:**
   ```bash
   python setup.py
   ```

2. **手動起動:**
   ```bash
   # 依存関係をインストール
   pip install -r requirements.txt
   
   # アプリを起動
   streamlit run app.py
   ```

ブラウザで `http://localhost:8501` が自動的に開きます。

## 📝 使い方

1. **音声ファイルをアップロード**
   - WAV または MP3 形式の音声ファイルを選択

2. **口閉じ画像をアップロード**
   - キャラクターの口を閉じた状態の画像（PNG/JPG）

3. **口開き画像をアップロード**
   - キャラクターの口を開いた状態の画像（PNG/JPG）

4. **動画生成**
   - 「動画を生成する」ボタンをクリック
   - 進行状況がプログレスバーで表示されます

5. **ダウンロード**
   - 生成完了後、「動画をダウンロード」ボタンでMP4ファイルを保存

## ⚙️ 技術仕様

- **フレームレート**: 30fps
- **口パク切り替え**: 5フレームごと（約167ms間隔）
- **背景色**: グリーンバック (#00FF00)
- **対応音声形式**: WAV, MP3
- **対応画像形式**: PNG, JPG, JPEG
- **出力形式**: MP4（H.264エンコード、AAC音声）

## 🛠️ 技術スタック

- **フレームワーク**: Streamlit
- **音声処理**: pydub
- **動画生成**: moviepy
- **画像処理**: Pillow (PIL)
- **数値計算**: NumPy

## 📁 ファイル構成

```
vtuberanimation/
├── app.py              # メインアプリケーション
├── setup.py            # セットアップスクリプト
├── requirements.txt    # 依存関係
└── README.md          # このファイル
```

## 🔧 トラブルシューティング

### FFmpegエラーまたは警告
```
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
```
または
```
RuntimeWarning: Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work
```
→ FFmpegがインストールされていないか、PATHに追加されていません。上記のインストール手順を確認してください。MP3ファイルの処理にはffmpegが必要です。

### メモリエラー
→ 大きな音声ファイルや高解像度画像の場合、メモリ不足が発生する可能性があります。ファイルサイズを小さくしてお試しください。

### 画像形式エラー
→ 対応形式（PNG, JPG, JPEG）の画像をご使用ください。

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🤝 貢献

バグ報告や機能要望は、GitHubのIssuesでお知らせください。プルリクエストも歓迎します！

---

**Enjoy creating your Vtuber animations! 🎉**

#   v t u b e r a n i m a t i o n  
 