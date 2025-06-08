#!/usr/bin/env python3
"""
Vtuber動画ジェネレーターのセットアップスクリプト
"""

import subprocess
import sys
import os

def install_requirements():
    """必要なパッケージをインストールする"""
    print("📦 必要なパッケージをインストール中...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ パッケージのインストールが完了しました！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ パッケージのインストールに失敗しました: {e}")
        return False

def run_app():
    """Streamlitアプリを起動する"""
    print("🚀 アプリケーションを起動中...")
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
    except KeyboardInterrupt:
        print("\n👋 アプリケーションを終了しました。")
    except Exception as e:
        print(f"❌ アプリケーションの起動に失敗しました: {e}")

def main():
    print("🎬 喋る風Vtuber動画ジェネレーター セットアップ")
    print("=" * 50)
    
    # 必要なファイルの存在確認
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt が見つかりません。")
        return
    
    if not os.path.exists("app.py"):
        print("❌ app.py が見つかりません。")
        return
    
    # パッケージインストール
    if install_requirements():
        print("\n" + "=" * 50)
        print("🎬 準備完了！アプリケーションを起動します...")
        print("ブラウザで http://localhost:8501 が開きます")
        print("終了するには Ctrl+C を押してください")
        print("=" * 50)
        run_app()
    else:
        print("❌ セットアップに失敗しました。")

if __name__ == "__main__":
    main() 