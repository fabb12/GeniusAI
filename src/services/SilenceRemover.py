import os
from PyQt6.QtCore import QThread, pyqtSignal
from moviepy.editor import VideoFileClip, concatenate_videoclips
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

class SilenceRemoverThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, video_path, silence_threshold_db, min_silence_len_ms, output_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.silence_threshold_db = silence_threshold_db
        self.min_silence_len_ms = min_silence_len_ms
        self.output_path = output_path

    def run(self):
        try:
            if not os.path.exists(self.video_path):
                self.error.emit(f"File not found: {self.video_path}")
                return

            self.progress.emit(5)

            # Load video and export its audio to a temporary file for pydub
            video = VideoFileClip(self.video_path)
            temp_audio_path = "temp_audio_for_silence_detection.wav"
            video.audio.write_audiofile(temp_audio_path, codec='pcm_s16le')

            self.progress.emit(20)

            # Load the audio with pydub
            audio_segment = AudioSegment.from_wav(temp_audio_path)

            self.progress.emit(30)

            # Detect non-silent chunks
            # pydub works with milliseconds
            # The threshold is in dBFS (decibels relative to full scale)
            nonsilent_chunks = detect_nonsilent(
                audio_segment,
                min_silence_len=self.min_silence_len_ms,
                silence_thresh=self.silence_threshold_db,
                seek_step=1
            )

            if not nonsilent_chunks:
                self.error.emit("No non-silent parts found. The entire video might be silent.")
                video.close()
                os.remove(temp_audio_path)
                return

            self.progress.emit(50)

            # Create video clips from the non-silent timestamps
            # Timestamps from pydub are in ms, convert to seconds for moviepy
            clips = [video.subclip(start_ms / 1000, end_ms / 1000) for start_ms, end_ms in nonsilent_chunks]

            self.progress.emit(70)

            # Concatenate the clips
            final_clip = concatenate_videoclips(clips)

            self.progress.emit(80)

            # Write the final video file
            final_clip.write_videofile(
                self.output_path,
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                codec="libx264",
                audio_codec="aac",
                fps=video.fps if video.fps else 24,
                ffmpeg_params=['-pix_fmt', 'yuv420p', '-fflags', '+genpts']
            )

            video.close()
            final_clip.close()
            os.remove(temp_audio_path)

            self.progress.emit(100)
            self.finished.emit(self.output_path)

        except Exception as e:
            # Clean up temp file on error
            if 'temp_audio_path' in locals() and os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
            self.error.emit(f"An error occurred during silence removal: {str(e)}")