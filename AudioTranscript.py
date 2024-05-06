import os
from PyQt6.QtCore import QThread, pyqtSignal

class TranscriptionThread(QThread):
    update_progress = pyqtSignal(int, str)  # Signal for updating progress with an index and message
    transcription_complete = pyqtSignal(str, list)  # Signal when transcription is complete, including temporary files to clean
    error_occurred = pyqtSignal(str)  # Signal for reporting errors

    def __init__(self, media_path, parent=None):
        super().__init__(parent)
        self.media_path = media_path
        self.temp_files = []  # To track all temporary files for cleanup

    def run(self):
        try:
            if os.path.splitext(self.media_path)[1].lower() in ['.wav', '.mp3', '.flac', '.aac']:
                audio_file = self.media_path
            else:
                # Convert video to audio and track the temporary audio file for cleanup
                audio_file = self.parent().convertVideoToAudio(self.media_path)
                if not audio_file or not os.path.exists(audio_file):
                    raise Exception("La conversione del video in audio è fallita o il file non esiste.")
                self.temp_files.append(audio_file)  # Add to temporary files list

            chunks = self.parent().splitAudio(audio_file)
            transcription = ""
            last_timestamp = None

            for index, (chunk, start_time) in enumerate(chunks):
                text, start_time, _ = self.parent().transcribeAudioChunk(chunk, start_time)

                start_mins, start_secs = divmod(start_time // 1000, 60)
                current_time_in_seconds = (start_mins * 60) + start_secs

                if last_timestamp is None or (current_time_in_seconds - last_timestamp >= 30):
                    transcription += f"[{start_mins:02d}:{start_secs:02d}] {text}\n\n"
                    last_timestamp = current_time_in_seconds
                else:
                    transcription += f"{text}\n\n"

                self.update_progress.emit(index + 1, f"Trascrizione {index + 1}/{len(chunks)}")

            self.transcription_complete.emit(transcription, self.temp_files)  # Emit completion along with temp files
        except Exception as e:
            self.error_occurred.emit(str(e))  # Emit error signal

