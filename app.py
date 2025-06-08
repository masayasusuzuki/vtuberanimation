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
    
    # ファイルアップロードセクション
    st.header("📁 ファイルアップロード")
    
    # 音声ファイルのアップロード
    st.subheader("1. 音声ファイル (.wav/.mp3)")
    audio_file = st.file_uploader(
        "音声ファイルを選択してください",
        type=['wav', 'mp3'],
        help="WAV または MP3 形式の音声ファイルをアップロードしてください"
    )
    
    # 口閉じ画像のアップロード
    st.subheader("2. 口閉じ画像")
    mouth_closed = st.file_uploader(
        "口を閉じた状態の画像を選択してください",
        type=['png', 'jpg', 'jpeg'],
        help="PNG または JPG 形式の画像をアップロードしてください"
    )
    
    # 口開き画像のアップロード
    st.subheader("3. 口開き画像")
    mouth_open = st.file_uploader(
        "口を開いた状態の画像を選択してください",
        type=['png', 'jpg', 'jpeg'],
        help="PNG または JPG 形式の画像をアップロードしてください"
    )
    
    # アップロードされた画像のプレビュー
    if mouth_closed and mouth_open:
        col1, col2 = st.columns(2)
        with col1:
            st.image(mouth_closed, caption="口閉じ画像", width=200)
        with col2:
            st.image(mouth_open, caption="口開き画像", width=200)
    
    # 動画生成ボタン
    st.header("🎬 動画生成")
    
    # デバッグモードの選択
    debug_mode = st.checkbox("🔍 デバッグモード（詳細な情報を表示）", value=False)
    
    if st.button("動画を生成する", type="primary", disabled=not (audio_file and mouth_closed and mouth_open)):
        if audio_file and mouth_closed and mouth_open:
            # プログレスバーを表示
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                status_text.text("動画を生成中...")
                progress_bar.progress(25)
                
                if debug_mode:
                    st.write("🔍 [DEBUG] 一時ファイル作成開始...")
                
                # 一時ファイルを作成
                file_extension = '.wav' if audio_file.name.endswith('.wav') else '.mp3'
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_audio:
                    tmp_audio.write(audio_file.read())
                    tmp_audio_path = tmp_audio.name
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_closed:
                    tmp_closed.write(mouth_closed.read())
                    tmp_closed_path = tmp_closed.name
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_open:
                    tmp_open.write(mouth_open.read())
                    tmp_open_path = tmp_open.name
                
                if debug_mode:
                    st.write(f"🔍 [DEBUG] 一時ファイル作成完了:")
                    st.write(f"  - 音声: {tmp_audio_path}")
                    st.write(f"  - 口閉じ: {tmp_closed_path}")
                    st.write(f"  - 口開き: {tmp_open_path}")
                
                progress_bar.progress(50)
                status_text.text("音声を解析中...")
                
                # 出力ファイルパス
                output_path = tempfile.mktemp(suffix='.mp4')
                
                progress_bar.progress(75)
                status_text.text("動画を作成中...")
                
                # 動画生成
                success = create_mouth_animation_video(
                    tmp_audio_path, tmp_closed_path, tmp_open_path, output_path, debug_mode, max_image_size, voice_threshold
                )
                
                if success:
                    progress_bar.progress(100)
                    status_text.text("動画生成完了！")
                    
                    # 生成された動画をセッション状態に保存
                    with open(output_path, 'rb') as f:
                        st.session_state.generated_video = f.read()
                    
                    # 動画情報を保存（プレビュー用）
                    st.session_state.video_path = output_path
                    
                    st.success("✅ 動画が正常に生成されました！")
                    
                    # プレビュー表示
                    st.subheader("🎬 プレビュー")
                    try:
                        # 動画ファイルを直接表示
                        video_file = open(output_path, 'rb')
                        video_bytes = video_file.read()
                        st.video(video_bytes)
                        video_file.close()
                        
                        # 動画情報を表示
                        file_size = len(st.session_state.generated_video) / (1024 * 1024)  # MB
                        st.info(f"📊 **動画情報**: ファイルサイズ {file_size:.1f}MB")
                        
                    except Exception as preview_error:
                        st.warning(f"⚠️ プレビュー表示エラー: {preview_error}")
                        st.info("💡 動画は正常に生成されました。ダウンロードしてご確認ください。")
                    
                    # 一時ファイルをクリーンアップ（出力動画以外）
                    for temp_file in [tmp_audio_path, tmp_closed_path, tmp_open_path]:
                        try:
                            os.unlink(temp_file)
                        except:
                            pass
                    # 出力動画は後でクリーンアップ（プレビュー表示のため保持）
                else:
                    progress_bar.empty()
                    status_text.empty()
                    st.error("❌ 動画生成に失敗しました。")
                    
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"❌ エラーが発生しました: {e}")
        else:
            st.warning("⚠️ すべてのファイルをアップロードしてください。")
    
    # ダウンロードボタン
    if st.session_state.generated_video:
        st.header("📥 ダウンロード")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.download_button(
                label="🎬 動画をダウンロード (.mp4)",
                data=st.session_state.generated_video,
                file_name="vtuber_animation.mp4",
                mime="video/mp4",
                use_container_width=True
            )
        
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

if __name__ == "__main__":
    main() 