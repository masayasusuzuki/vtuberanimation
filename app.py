import streamlit as st
import tempfile
import os
from PIL import Image
import numpy as np
from pydub import AudioSegment
from moviepy.editor import ImageClip, VideoFileClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
import io
import subprocess
import sys

def detect_voice_segments(audio_file, threshold_silence=-40, debug_mode=False):
    """音声ファイルから発音区間を検出する"""
    try:
        if debug_mode:
            st.write(f"🔍 [DEBUG] 音声ファイル読み込み開始: {os.path.basename(audio_file)}")
            st.write(f"🔍 [DEBUG] ファイルサイズ: {os.path.getsize(audio_file)} bytes")
        
        # ファイル拡張子に基づいて適切な読み込み方法を選択
        if audio_file.endswith('.wav'):
            if debug_mode:
                st.write("🔍 [DEBUG] WAVファイルとして読み込み中...")
            audio = AudioSegment.from_wav(audio_file)
        elif audio_file.endswith('.mp3'):
            if debug_mode:
                st.write("🔍 [DEBUG] MP3ファイルとして読み込み中...")
            try:
                audio = AudioSegment.from_mp3(audio_file)
            except Exception as mp3_error:
                st.error("MP3ファイルの処理にはFFmpegが必要です。WAVファイルをお試しください。")
                st.error(f"詳細: {mp3_error}")
                return [], 0
        else:
            # 自動判定を試行
            if debug_mode:
                st.write("🔍 [DEBUG] ファイル形式自動判定中...")
            try:
                audio = AudioSegment.from_file(audio_file)
            except Exception as file_error:
                st.error("対応していない音声形式です。WAVまたはMP3ファイルをお試しください。")
                st.error(f"詳細: {file_error}")
                return [], 0
        
        if debug_mode:
            st.write(f"🔍 [DEBUG] 音声読み込み成功!")
            st.write(f"🔍 [DEBUG] - 長さ: {len(audio)}ms")
            st.write(f"🔍 [DEBUG] - サンプルレート: {audio.frame_rate}Hz")
            st.write(f"🔍 [DEBUG] - チャンネル数: {audio.channels}")
        
        # 音声が正常に読み込まれたかチェック
        if len(audio) == 0:
            st.error("音声ファイルが空であるか、読み込めませんでした。")
            return [], 0
        
        # dBFSでの音量レベルを取得
        chunks = []
        chunk_length = 100  # 100ms単位で分析
        
        if debug_mode:
            st.write(f"🔍 [DEBUG] 音声解析中... ({chunk_length}ms間隔)")
        
        for i in range(0, len(audio), chunk_length):
            chunk = audio[i:i + chunk_length]
            if len(chunk) > 0:
                chunks.append(chunk.dBFS > threshold_silence)
            else:
                chunks.append(False)
        
        if debug_mode:
            speaking_chunks = sum(chunks)
            st.write(f"🔍 [DEBUG] 音声解析完了 - {len(chunks)}個のチャンク作成")
            st.write(f"🔍 [DEBUG] 発音区間: {speaking_chunks}/{len(chunks)} ({speaking_chunks/len(chunks)*100:.1f}%)")
            st.write(f"🔍 [DEBUG] 閾値: {threshold_silence}dBFS")
        
        return chunks, len(audio) / 1000.0  # duration in seconds
    except Exception as e:
        st.error(f"音声ファイルの処理中にエラーが発生しました: {e}")
        st.error("FFmpegがインストールされていない可能性があります。WAVファイルをお試しいただくか、FFmpegをインストールしてください。")
        if debug_mode:
            import traceback
            st.error(f"🔍 [DEBUG] トレースバック:\n{traceback.format_exc()}")
        return [], 0

def create_mouth_animation_video(audio_file, mouth_closed_img, mouth_open_img, output_path, debug_mode=False, max_image_size=512, voice_threshold=-40):
    """口パク動画を生成する"""
    try:
        if debug_mode:
            st.write("🔍 [DEBUG] 動画生成開始")
            st.write(f"🔍 [DEBUG] 音声ファイル: {audio_file}")
            st.write(f"🔍 [DEBUG] 出力パス: {output_path}")
        
        # 音声の発音区間を検出
        if debug_mode:
            st.write("🔍 [DEBUG] 音声解析開始...")
        
        voice_segments, duration = detect_voice_segments(audio_file, voice_threshold, debug_mode)
        
        if debug_mode:
            st.write(f"🔍 [DEBUG] 音声解析完了 - 長さ: {duration}秒, セグメント数: {len(voice_segments)}")
        
        if duration == 0:
            st.error("音声ファイルの長さが取得できませんでした")
            return False
        
        # 画像を読み込み
        if debug_mode:
            st.write("🔍 [DEBUG] 画像読み込み開始...")
        
        closed_img = Image.open(mouth_closed_img)
        open_img = Image.open(mouth_open_img)
        
        if debug_mode:
            st.write(f"🔍 [DEBUG] 口閉じ画像: {closed_img.size} {closed_img.mode}")
            st.write(f"🔍 [DEBUG] 口開き画像: {open_img.size} {open_img.mode}")
        
        # 画像サイズを統一（大きい方に合わせる）
        max_width = max(closed_img.width, open_img.width)
        max_height = max(closed_img.height, open_img.height)
        
        if debug_mode:
            st.write(f"🔍 [DEBUG] 統一サイズ: {max_width}x{max_height}")
        
        # メモリ使用量を抑えるため、画像サイズを制限
        MAX_DIMENSION = max_image_size  # ユーザーが設定した最大サイズ
        original_width, original_height = max_width, max_height
        
        if max_width > MAX_DIMENSION or max_height > MAX_DIMENSION:
            # アスペクト比を保持しながらリサイズ
            ratio = min(MAX_DIMENSION / max_width, MAX_DIMENSION / max_height)
            new_width = int(max_width * ratio)
            new_height = int(max_height * ratio)
            max_width, max_height = new_width, new_height
            
            # ユーザーに自動リサイズを通知
            st.info(f"📏 **画像サイズ自動調整**: {original_width}×{original_height} → {new_width}×{new_height}")
            st.info(f"💡 メモリ使用量削減のため、アスペクト比を保持したまま{MAX_DIMENSION}px以下にリサイズしました")
            
            if debug_mode:
                st.write(f"🔍 [DEBUG] 画像サイズを制限: {new_width}x{new_height} (リサイズ比率: {ratio:.2f})")
        else:
            st.success(f"✅ **画像サイズ**: {max_width}×{max_height} （{MAX_DIMENSION}px以下のため調整不要）")
        
        # 画像をリサイズしてRGBに変換（メモリ使用量削減）
        closed_img = closed_img.resize((max_width, max_height), Image.Resampling.LANCZOS)
        open_img = open_img.resize((max_width, max_height), Image.Resampling.LANCZOS)
        
        # RGBAをRGBに変換してメモリ使用量を25%削減
        if closed_img.mode == 'RGBA':
            closed_img = closed_img.convert('RGB')
        if open_img.mode == 'RGBA':
            open_img = open_img.convert('RGB')
            
        if debug_mode:
            st.write(f"🔍 [DEBUG] 最終画像設定: {max_width}x{max_height}, モード: {closed_img.mode}")
        
        # 30fps想定で動画を生成
        fps = 30
        frame_duration = 1.0 / fps
        
        if debug_mode:
            st.write(f"🔍 [DEBUG] 動画設定: {fps}fps, フレーム時間: {frame_duration:.4f}秒")
        
        # 長い音声の場合は警告を表示
        if duration > 120:  # 2分以上
            st.warning(f"⚠️ 音声が長いです（{duration:.1f}秒）。メモリ不足の可能性があります。2分以下の音声を推奨します。")
            if duration > 300:  # 5分以上は制限
                st.error("❌ 音声が長すぎます（5分以上）。処理を中止します。より短い音声をお使いください。")
                return False
        
        # メモリ効率的なフレーム生成（一度に全フレームを保持しない）
        total_frames = int(duration * fps)
        frame_switch_interval = 3  # 3フレームごとに切り替え
        
        if debug_mode:
            st.write(f"🔍 [DEBUG] フレーム生成開始... 総フレーム数: {total_frames}")
            estimated_memory = (max_width * max_height * 3 * total_frames) / (1024**3)  # GB
            st.write(f"🔍 [DEBUG] 推定メモリ使用量: {estimated_memory:.2f}GB")
        
        # 最適化された動画作成：バッチ処理
        batch_size = 150 if total_frames > 600 else 100  # フレーム数に応じてバッチサイズを調整
        clips = []
        
        if debug_mode:
            st.write(f"🔍 [DEBUG] バッチサイズ: {batch_size}フレーム、バッチ数: {(total_frames + batch_size - 1) // batch_size}")
        
        # 進行状況表示用
        progress_text = st.empty()
        progress_bar_batch = st.progress(0)
        total_batches = (total_frames + batch_size - 1) // batch_size
        
        for batch_idx, batch_start in enumerate(range(0, total_frames, batch_size)):
            batch_end = min(batch_start + batch_size, total_frames)
            batch_frames = []
            
            # 進行状況を更新
            progress_pct = (batch_idx + 1) / total_batches
            progress_bar_batch.progress(progress_pct)
            progress_text.text(f"フレーム処理中... {batch_idx + 1}/{total_batches} バッチ ({batch_start}-{batch_end})")
            
            if debug_mode:
                st.write(f"🔍 [DEBUG] バッチ処理中: {batch_start}-{batch_end} ({batch_end - batch_start}フレーム)")
            
            for frame_idx in range(batch_start, batch_end):
                current_time = frame_idx * frame_duration
                segment_index = min(int(current_time * 10), len(voice_segments) - 1)
                
                # 発音区間かどうかチェック
                is_speaking = segment_index < len(voice_segments) and voice_segments[segment_index]
                
                if debug_mode and frame_idx < batch_start + 5:  # 最初の5フレームをデバッグ
                    st.write(f"🔍 [DEBUG] フレーム{frame_idx}: 時間{current_time:.2f}s, セグメント{segment_index}, 発音中: {is_speaking}")
                
                if is_speaking:
                    # 発音区間では5フレームごとに口の開閉を切り替え
                    cycle_position = (frame_idx // frame_switch_interval) % 2
                    use_open_mouth = cycle_position == 1
                    frame_img = open_img if use_open_mouth else closed_img
                    
                    if debug_mode and frame_idx < batch_start + 5:
                        st.write(f"🔍 [DEBUG] サイクル位置: {cycle_position}, 口開き: {use_open_mouth}")
                else:
                    # 無音区間では口を閉じる
                    frame_img = closed_img
                
                batch_frames.append(np.array(frame_img))
            
            if batch_frames:
                # バッチのフレームを個別のクリップに変換してから結合
                batch_clips = []
                for frame in batch_frames:
                    frame_clip = ImageClip(frame, duration=frame_duration)
                    batch_clips.append(frame_clip)
                
                # バッチ内のクリップを結合
                if len(batch_clips) == 1:
                    batch_clip = batch_clips[0]
                else:
                    batch_clip = concatenate_videoclips(batch_clips, method="compose")
                
                clips.append(batch_clip)
                
                # メモリクリーンアップ
                del batch_frames
                del batch_clips
                
                if debug_mode:
                    st.write(f"🔍 [DEBUG] バッチクリップ作成完了: バッチ{len(clips)} 処理済み")
        
        # プログレスバーをクリーンアップ
        progress_bar_batch.empty()
        progress_text.empty()
        
        if not clips:
            st.error("フレームの生成に失敗しました")
            return False
        
        if debug_mode:
            st.write(f"🔍 [DEBUG] 全バッチ処理完了: {len(clips)}個のバッチクリップを作成")
        
        # 背景をグリーンバックに設定（RGB画像では不要だが、念のため定義）
        green_background = np.full((max_height, max_width, 3), [0, 255, 0], dtype=np.uint8)
        
        if debug_mode:
            st.write(f"🔍 [DEBUG] グリーンバック背景設定: {max_width}x{max_height}")
        
        # 動画クリップを作成
        if debug_mode:
            st.write("🔍 [DEBUG] MoviePyクリップ結合開始...")
        
        try:
            # バッチで作成されたクリップを結合
            if debug_mode:
                st.write(f"🔍 [DEBUG] {len(clips)}個のバッチクリップを結合中...")
            
            video_clip = concatenate_videoclips(clips, method="compose")
            video_clip = video_clip.set_fps(fps)
            
            if debug_mode:
                st.write(f"🔍 [DEBUG] 動画クリップ作成完了: {video_clip.duration:.2f}秒")
            
        except Exception as clip_error:
            if debug_mode:
                st.error(f"🔍 [DEBUG] クリップ結合エラー: {clip_error}")
            
            # フォールバック: 最初のクリップのみ使用
            if debug_mode:
                st.write("🔍 [DEBUG] フォールバック方法を試行...")
            
            video_clip = clips[0] if clips else ImageClip(np.array(closed_img), duration=duration).set_fps(fps)
        
        # 音声を追加
        if debug_mode:
            st.write("🔍 [DEBUG] 音声クリップ作成中...")
        
        audio_clip = AudioFileClip(audio_file)
        final_video = video_clip.set_audio(audio_clip)
        
        if debug_mode:
            st.write(f"🔍 [DEBUG] 最終動画作成完了: {final_video.duration:.2f}秒")
            st.write(f"🔍 [DEBUG] 出力開始: {output_path}")
        
        # 動画を出力
        final_video.write_videofile(
            output_path,
            fps=fps,
            audio_codec='aac',
            codec='libx264',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            verbose=debug_mode,
            logger='bar' if not debug_mode else None
        )
        
        if debug_mode:
            st.write("🔍 [DEBUG] 動画出力完了")
        
        # クリップを閉じてメモリを解放
        video_clip.close()
        audio_clip.close()
        final_video.close()
        
        if debug_mode:
            st.write("🔍 [DEBUG] リソースクリーンアップ完了")
        
        return True
        
    except Exception as e:
        st.error(f"動画生成中にエラーが発生しました: {e}")
        if debug_mode:
            import traceback
            st.error(f"🔍 [DEBUG] 詳細トレースバック:\n{traceback.format_exc()}")
        return False

def check_ffmpeg():
    """FFmpegがインストールされているかチェック"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def main():
    st.set_page_config(
        page_title="喋る風Vtuber動画ジェネレーター",
        page_icon="🎬",
        layout="centered"
    )
    
    st.title("🎬 喋る風Vtuber動画ジェネレーター")
    st.markdown("音声ファイルと口の開閉画像をアップロードして、口パク動画を生成します。")
    
    # FFmpegの状態をチェック
    ffmpeg_available = check_ffmpeg()
    if ffmpeg_available:
        st.success("✅ FFmpeg が利用可能です。WAV・MP3ファイルに対応しています。")
    else:
        st.warning("⚠️ FFmpeg が見つかりません。MP3ファイルの処理ができない可能性があります。WAVファイルをご利用ください。")
        with st.expander("FFmpegのインストール方法"):
            st.code("winget install ffmpeg")
            st.markdown("インストール後、アプリケーションを再起動してください。")
    
    # 対応形式の案内
    st.info("💡 **対応形式**: WAV・MP3音声ファイル、PNG・JPG画像ファイル")
    st.info("⏰ **推奨**: 音声長2分以下、画像サイズ512px以下（メモリ使用量削減のため）")
    
    # 詳細設定
    with st.expander("⚙️ 詳細設定"):
        max_image_size = st.slider(
            "最大画像サイズ (px)", 
            min_value=256, 
            max_value=1024, 
            value=512, 
            step=64,
            help="画像の最大サイズを設定します。大きいほど高画質ですが、メモリを多く使用します"
        )
        st.write(f"選択されたサイズ: {max_image_size}×{max_image_size}px以下に自動調整されます")
        
        st.divider()
        
        voice_threshold = st.slider(
            "音声検出感度",
            min_value=-60,
            max_value=-20,
            value=-40,
            step=5,
            help="値が大きいほど検出感度が高くなります。-40が推奨値です"
        )
        st.write(f"設定値: {voice_threshold}dBFS（小さい音も検出: {voice_threshold > -45}）")
    
    # セッション状態の初期化
    if 'generated_video' not in st.session_state:
        st.session_state.generated_video = None
    
    # デフォルト画像の初期化
    if 'default_mouth_closed' not in st.session_state:
        try:
            with open('博士 口閉じ.png', 'rb') as f:
                st.session_state.default_mouth_closed = f.read()
        except FileNotFoundError:
            st.session_state.default_mouth_closed = None
    
    if 'default_mouth_open' not in st.session_state:
        try:
            with open('博士 口開け.png', 'rb') as f:
                st.session_state.default_mouth_open = f.read()
        except FileNotFoundError:
            st.session_state.default_mouth_open = None
    
    # ファイルアップロードセクション
    st.header("📁 ファイルアップロード")
    
    # 処理モードの選択
    processing_mode = st.radio(
        "処理モードを選択してください",
        ["シングルモード（1つずつ処理）", "バッチモード（複数を自動処理）"],
        help="バッチモードでは複数の音声ファイルを一度にアップロードして自動処理できます"
    )
    
    # 音声ファイルのアップロード
    st.subheader("1. 音声ファイル (.wav/.mp3)")
    if processing_mode == "シングルモード（1つずつ処理）":
        audio_files = st.file_uploader(
            "音声ファイルを選択してください",
            type=['wav', 'mp3'],
            help="WAV または MP3 形式の音声ファイルをアップロードしてください"
        )
        # シングルモード用に配列に変換
        audio_files = [audio_files] if audio_files else []
    else:
        audio_files = st.file_uploader(
            "音声ファイルを選択してください（複数選択可能）",
            type=['wav', 'mp3'],
            accept_multiple_files=True,
            help="WAV または MP3 形式の音声ファイルを複数選択できます"
        )
        if audio_files:
            st.info(f"📁 {len(audio_files)}個のファイルが選択されています")
            
            # ファイル順序の設定
            st.subheader("📋 ファイル処理順序")
            sort_option = st.radio(
                "処理順序を選択してください",
                ["ファイル名順（A-Z）", "ファイル名順（Z-A）", "追加順を維持", "手動並び替え"],
                index=0,  # デフォルトはファイル名順
                help="ファイルの処理順序を選択できます"
            )
            
            # ファイル順序の表示と並び替え
            if sort_option == "ファイル名順（A-Z）":
                audio_files = sorted(audio_files, key=lambda x: x.name)
            elif sort_option == "ファイル名順（Z-A）":
                audio_files = sorted(audio_files, key=lambda x: x.name, reverse=True)
            elif sort_option == "手動並び替え":
                st.info("💡 下記の順序で処理されます。順序を変更したい場合は、ファイルを再選択してください。")
                
                # ファイル順序の手動調整UIを作成
                reordered_files = []
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write("**現在の順序:**")
                    for idx, file in enumerate(audio_files):
                        st.write(f"{idx + 1}. {file.name}")
                
                with col2:
                    st.write("**並び替えボタン:**")
                    if len(audio_files) > 1:
                        for idx in range(len(audio_files)):
                            col_up, col_down = st.columns(2)
                            with col_up:
                                if st.button("⬆️", key=f"up_{idx}", disabled=idx==0):
                                    # ファイルを上に移動
                                    audio_files[idx], audio_files[idx-1] = audio_files[idx-1], audio_files[idx]
                                    st.rerun()
                            with col_down:
                                if st.button("⬇️", key=f"down_{idx}", disabled=idx==len(audio_files)-1):
                                    # ファイルを下に移動
                                    audio_files[idx], audio_files[idx+1] = audio_files[idx+1], audio_files[idx]
                                    st.rerun()
            # "追加順を維持"の場合はそのまま
            
            # 処理順序のプレビュー表示
            st.write("**📋 最終処理順序:**")
            for idx, file in enumerate(audio_files):
                file_size = file.size / (1024 * 1024) if hasattr(file, 'size') else 0
                st.write(f"🎵 **{idx + 1}.** {file.name} {f'({file_size:.1f}MB)' if file_size > 0 else ''}")
            
            # 処理時間の推定
            estimated_time = len(audio_files) * 30  # ファイル1つあたり約30秒と仮定
            st.info(f"⏰ **推定処理時間**: 約{estimated_time//60}分{estimated_time%60}秒（{len(audio_files)}ファイル × 約30秒）")
            st.divider()
    
    # 口閉じ画像のアップロード
    st.subheader("2. 口閉じ画像")
    
    # デフォルト画像使用オプション
    use_default_closed = st.checkbox("デフォルト画像を使用 (@博士 口閉じ.png)", 
                                   value=st.session_state.default_mouth_closed is not None,
                                   disabled=st.session_state.default_mouth_closed is None)
    
    if use_default_closed and st.session_state.default_mouth_closed:
        # デフォルト画像をuploadedfile形式で作成
        mouth_closed = io.BytesIO(st.session_state.default_mouth_closed)
        mouth_closed.name = "博士 口閉じ.png"
        mouth_closed.seek(0)  # ファイルポインタを先頭に移動
        st.success("✅ デフォルト画像「@博士 口閉じ.png」を使用しています")
    else:
        mouth_closed = st.file_uploader(
            "口を閉じた状態の画像を選択してください",
            type=['png', 'jpg', 'jpeg'],
            help="PNG または JPG 形式の画像をアップロードしてください"
        )
    
    # 口開き画像のアップロード
    st.subheader("3. 口開き画像")
    
    # デフォルト画像使用オプション
    use_default_open = st.checkbox("デフォルト画像を使用 (@博士 口開け.png)", 
                                 value=st.session_state.default_mouth_open is not None,
                                 disabled=st.session_state.default_mouth_open is None)
    
    if use_default_open and st.session_state.default_mouth_open:
        # デフォルト画像をuploadedfile形式で作成
        mouth_open = io.BytesIO(st.session_state.default_mouth_open)
        mouth_open.name = "博士 口開け.png"
        mouth_open.seek(0)  # ファイルポインタを先頭に移動
        st.success("✅ デフォルト画像「@博士 口開け.png」を使用しています")
    else:
        mouth_open = st.file_uploader(
            "口を開いた状態の画像を選択してください",
            type=['png', 'jpg', 'jpeg'],
            help="PNG または JPG 形式の画像をアップロードしてください"
        )
    
    # アップロードされた画像のプレビュー
    if mouth_closed and mouth_open:
        col1, col2 = st.columns(2)
        with col1:
            if use_default_closed and st.session_state.default_mouth_closed:
                # デフォルト画像の場合はバイナリデータをio.BytesIOに変換してから表示
                st.image(io.BytesIO(st.session_state.default_mouth_closed), caption="口閉じ画像 (デフォルト)", width=200)
            else:
                st.image(mouth_closed, caption="口閉じ画像", width=200)
        with col2:
            if use_default_open and st.session_state.default_mouth_open:
                # デフォルト画像の場合はバイナリデータをio.BytesIOに変換してから表示
                st.image(io.BytesIO(st.session_state.default_mouth_open), caption="口開き画像 (デフォルト)", width=200)
            else:
                st.image(mouth_open, caption="口開き画像", width=200)
    
    # 動画生成ボタン
    st.header("🎬 動画生成")
    
    # デバッグモードの選択
    debug_mode = st.checkbox("🔍 デバッグモード（詳細な情報を表示）", value=False)
    
    # ボタンのラベルを処理モードに応じて変更
    audio_count = len(audio_files) if audio_files else 0
    button_label = "動画を生成する" if processing_mode == "シングルモード（1つずつ処理）" else f"バッチ処理を開始する（{audio_count}個のファイル）"
    button_disabled = not (audio_files and len([f for f in audio_files if f is not None]) > 0 and mouth_closed and mouth_open)
    
    if st.button(button_label, type="primary", disabled=button_disabled):
        if audio_files and mouth_closed and mouth_open and len([f for f in audio_files if f is not None]) > 0:
            # バッチ処理かシングル処理かを判定
            valid_audio_files = [f for f in audio_files if f is not None]
            is_batch_mode = len(valid_audio_files) > 1
            
            # プログレスバーを表示
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # バッチ処理用のセッション状態初期化
            if 'batch_videos' not in st.session_state:
                st.session_state.batch_videos = []
            if 'batch_video_names' not in st.session_state:
                st.session_state.batch_video_names = []
            
            # バッチ処理開始時にクリア
            if is_batch_mode:
                st.session_state.batch_videos = []
                st.session_state.batch_video_names = []
            
            try:
                if is_batch_mode:
                    st.subheader(f"🚀 バッチ処理開始（{len(valid_audio_files)}個のファイル）")
                
                # 口画像の一時ファイルを作成（全処理で共通使用）
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_closed:
                    tmp_closed.write(mouth_closed.read())
                    tmp_closed_path = tmp_closed.name
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_open:
                    tmp_open.write(mouth_open.read())
                    tmp_open_path = tmp_open.name
                
                successful_videos = 0
                failed_videos = 0
                
                # 各音声ファイルを処理
                for file_idx, audio_file in enumerate(valid_audio_files):
                    if debug_mode:
                        st.write(f"🔍 [DEBUG] ファイル {file_idx + 1}/{len(valid_audio_files)}: {audio_file.name}")
                    
                    # 全体の進行状況を更新
                    overall_progress = (file_idx / len(valid_audio_files)) * 100
                    progress_bar.progress(int(overall_progress))
                    status_text.text(f"処理中... ({file_idx + 1}/{len(valid_audio_files)}) {audio_file.name}")
                    
                    # 現在のファイル用コンテナ
                    if is_batch_mode:
                        with st.expander(f"📹 {file_idx + 1}. {audio_file.name}", expanded=False):
                            file_status = st.empty()
                            file_progress = st.progress(0)
                    else:
                        file_status = status_text
                        file_progress = progress_bar
                    
                    try:
                        file_status.text(f"音声ファイル処理中: {audio_file.name}")
                        file_progress.progress(25)
                        
                        # 音声ファイルの一時ファイルを作成
                        file_extension = '.wav' if audio_file.name.endswith('.wav') else '.mp3'
                        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_audio:
                            tmp_audio.write(audio_file.read())
                            tmp_audio_path = tmp_audio.name
                        
                        if debug_mode:
                            st.write(f"🔍 [DEBUG] 一時ファイル作成: {tmp_audio_path}")
                        
                        file_progress.progress(50)
                        file_status.text(f"音声解析中: {audio_file.name}")
                        
                        # 出力ファイルパス（ファイル名に基づいて生成）
                        base_name = os.path.splitext(audio_file.name)[0]
                        output_path = tempfile.mktemp(suffix=f'_{base_name}.mp4')
                        
                        file_progress.progress(75)
                        file_status.text(f"動画作成中: {audio_file.name}")
                        
                        # 動画生成
                        success = create_mouth_animation_video(
                            tmp_audio_path, tmp_closed_path, tmp_open_path, output_path, debug_mode, max_image_size, voice_threshold
                        )
                        
                        if success:
                            file_progress.progress(100)
                            file_status.text(f"✅ 完了: {audio_file.name}")
                            
                            # 生成された動画を読み込み
                            with open(output_path, 'rb') as f:
                                video_data = f.read()
                            
                            if is_batch_mode:
                                # バッチモードでは配列に追加
                                st.session_state.batch_videos.append(video_data)
                                st.session_state.batch_video_names.append(f"{base_name}.mp4")
                                
                                # ファイルサイズ表示
                                file_size = len(video_data) / (1024 * 1024)
                                st.success(f"✅ 生成完了: {base_name}.mp4 ({file_size:.1f}MB)")
                            else:
                                # シングルモードでは従来通り
                                st.session_state.generated_video = video_data
                                st.session_state.video_path = output_path
                            
                            successful_videos += 1
                            
                        else:
                            file_progress.progress(0)
                            file_status.text(f"❌ 失敗: {audio_file.name}")
                            if is_batch_mode:
                                st.error(f"❌ {audio_file.name} の処理に失敗しました")
                            failed_videos += 1
                        
                        # 音声ファイルの一時ファイルをクリーンアップ
                        try:
                            os.unlink(tmp_audio_path)
                        except:
                            pass
                        
                    except Exception as file_error:
                        file_progress.progress(0)
                        file_status.text(f"❌ エラー: {audio_file.name}")
                        if is_batch_mode:
                            st.error(f"❌ {audio_file.name} でエラー: {file_error}")
                        failed_videos += 1
                
                # 全体の処理完了
                progress_bar.progress(100)
                
                if is_batch_mode:
                    status_text.text("🎉 バッチ処理完了！")
                    st.success(f"🎉 バッチ処理完了！ 成功: {successful_videos}個, 失敗: {failed_videos}個")
                    
                    if successful_videos > 0:
                        st.info(f"📹 {successful_videos}個の動画が生成されました。下記のダウンロードセクションから個別にダウンロードできます。")
                else:
                    # シングルモードの場合のプレビュー表示
                    if successful_videos > 0:
                        status_text.text("動画生成完了！")
                        st.success("✅ 動画が正常に生成されました！")
                        
                        # プレビュー表示
                        st.subheader("🎬 プレビュー")
                        try:
                            video_file = open(st.session_state.video_path, 'rb')
                            video_bytes = video_file.read()
                            st.video(video_bytes)
                            video_file.close()
                            
                            # 動画情報を表示
                            if st.session_state.generated_video:
                                file_size = len(st.session_state.generated_video) / (1024 * 1024)
                                st.info(f"📊 **動画情報**: ファイルサイズ {file_size:.1f}MB")
                            
                        except Exception as preview_error:
                            st.warning(f"⚠️ プレビュー表示エラー: {preview_error}")
                            st.info("💡 動画は正常に生成されました。ダウンロードしてご確認ください。")
                
                # 口画像の一時ファイルをクリーンアップ
                for temp_file in [tmp_closed_path, tmp_open_path]:
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
                        
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"❌ 処理中にエラーが発生しました: {e}")
                if debug_mode:
                    import traceback
                    st.error(f"🔍 [DEBUG] トレースバック:\n{traceback.format_exc()}")
        else:
            st.warning("⚠️ すべてのファイルをアップロードしてください。")
    
    # ダウンロードセクション
    has_single_video = 'generated_video' in st.session_state and st.session_state.generated_video is not None
    has_batch_videos = 'batch_videos' in st.session_state and len(st.session_state.batch_videos) > 0
    
    if has_single_video or has_batch_videos:
        st.header("📥 ダウンロード")
        
        # シングルモードのダウンロード
        if has_single_video:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.session_state.generated_video is not None:
                    st.download_button(
                        label="🎬 動画をダウンロード (.mp4)",
                        data=st.session_state.generated_video,
                        file_name="vtuber_animation.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )
                else:
                    st.error("動画データが見つかりません")
            
            with col2:
                if st.button("🗑️ プレビューをクリア", use_container_width=True):
                    # 一時ファイルも削除
                    if 'video_path' in st.session_state and os.path.exists(st.session_state.video_path):
                        try:
                            os.unlink(st.session_state.video_path)
                        except:
                            pass
                    
                    # セッション状態をクリア
                    st.session_state.generated_video = None
                    if 'video_path' in st.session_state:
                        del st.session_state.video_path
                    st.rerun()
        
        # バッチモードのダウンロード
        if has_batch_videos:
            st.subheader(f"📁 バッチ処理結果（{len(st.session_state.batch_videos)}個の動画）")
            
            # 全体統計
            total_size = sum(len(video) for video in st.session_state.batch_videos) / (1024 * 1024)
            st.info(f"📊 **合計サイズ**: {total_size:.1f}MB")
            
            # 個別ダウンロードボタン
            for idx, (video_data, file_name) in enumerate(zip(st.session_state.batch_videos, st.session_state.batch_video_names)):
                file_size = len(video_data) / (1024 * 1024)
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.download_button(
                        label=f"📹 {file_name} ({file_size:.1f}MB)",
                        data=video_data,
                        file_name=file_name,
                        mime="video/mp4",
                        key=f"download_{idx}",
                        use_container_width=True
                    )
                with col2:
                    if st.button("🗑️", key=f"delete_{idx}", help=f"{file_name}を削除"):
                        # 該当する動画を削除
                        st.session_state.batch_videos.pop(idx)
                        st.session_state.batch_video_names.pop(idx)
                        st.rerun()
            
            # 全件クリアボタン
            st.divider()
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("📥 すべて一括ダウンロード準備", use_container_width=True):
                    st.info("💡 個別の動画ダウンロードボタンをお使いください。Webブラウザの制限により、複数ファイルの一括ダウンロードはサポートされていません。")
            
            with col2:
                if st.button("🗑️ すべてクリア", type="secondary", use_container_width=True):
                    st.session_state.batch_videos = []
                    st.session_state.batch_video_names = []
                    st.rerun()

if __name__ == "__main__":
    main() 