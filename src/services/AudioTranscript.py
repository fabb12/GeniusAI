import os
import json
import datetime
from PyQt6.QtCore import QThread, pyqtSignal
import whisper_timestamped as whisper
import tempfile
import logging
from moviepy.editor import AudioFileClip, VideoFileClip


class TranscriptionThread(QThread):
    update_progress = pyqtSignal(int, str)  # Signal for updating progress with an index and message
    transcription_complete = pyqtSignal(str, list)  # Signal when transcription is complete, including temporary files to clean
    error_occurred = pyqtSignal(str)  # Signal for reporting errors

    def __init__(self, media_path, parent=None):
        super().__init__(parent)
        self.media_path = media_path
        self._is_running = True
        self.partial_text = ""
        self.temp_files_to_clean = []

    def run(self):
        audio_file = None
        try:
            if os.path.splitext(self.media_path)[1].lower() in ['.wav', '.mp3', '.flac', '.aac']:
                audio_file = self.media_path
            else:
                self.update_progress.emit(10, "Converting video to audio...")
                audio_file = self.convertVideoToAudio(self.media_path)
                if not audio_file or not os.path.exists(audio_file):
                    raise Exception("Video to audio conversion failed.")
                self.temp_files_to_clean.append(audio_file)

            self.update_progress.emit(20, "Loading audio...")
            audio = whisper.load_audio(audio_file)

            self.update_progress.emit(30, "Loading transcription model...")
            model = whisper.load_model("tiny", device="cpu")

            language_video = self.parent().languageComboBox.currentData()

            self.update_progress.emit(50, "Transcribing... (this may take a while)")
            result = whisper.transcribe(model, audio, language=language_video)

            self.update_progress.emit(90, "Saving transcription...")
            json_path = self.save_transcription_to_json(result, language_video)

            self.transcription_complete.emit(json_path, self.temp_files_to_clean)

        except Exception as e:
            logging.error(f"Transcription failed: {e}", exc_info=True)
            self.error_occurred.emit(str(e))
        finally:
            # The cleanup is now handled in the main thread after completion or error
            pass

    def save_transcription_to_json(self, result, language_code):
        # MoviePy is used here just to get the duration, which is also in the whisper result.
        # To reduce dependency, we could use the duration from whisper if it's reliable.
        # For now, keeping it for consistency.
        duration = 0
        try:
            if os.path.splitext(self.media_path)[1].lower() not in ['.wav', '.mp3', '.flac', '.aac']:
                 video_clip = VideoFileClip(self.media_path)
                 duration = video_clip.duration
            else:
                 audio_clip = AudioFileClip(self.media_path)
                 duration = audio_clip.duration
        except Exception as e:
            logging.warning(f"Could not get media duration using moviepy: {e}")
            # Fallback to duration from whisper result if available
            if result and 'segments' in result and result['segments']:
                duration = result['segments'][-1]['end']


        metadata = {
            "video_path": self.media_path,
            "duration": duration,
            "language": language_code,
            "transcription_date": datetime.datetime.now().isoformat(),
            "transcription_data": result
        }
        json_path = os.path.splitext(self.media_path)[0] + ".json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)
        return json_path

    def stop(self):
        self._is_running = False
        self.terminate() # Forcefully stop the thread if it's stuck

    def get_partial_transcription(self):
        # This method might be obsolete now as we get the full transcription at once.
        # Returning an empty string for now.
        return ""

    def convertVideoToAudio(self, video_file):
        logging.debug("Converting video to audio...")
        try:
            video = VideoFileClip(video_file)
            audio = video.audio

            # Create a temporary file for the audio
            temp_audio_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_audio_file_path = temp_audio_file.name
            temp_audio_file.close() # Close the file so moviepy can write to it

            audio.write_audiofile(temp_audio_file_path, codec='pcm_s16le')

            audio.close()
            video.close()

            return temp_audio_file_path
        except Exception as e:
            logging.error(f"Error converting video to audio: {e}", exc_info=True)
            return None
