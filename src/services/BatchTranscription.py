import os
import json
import datetime
from PyQt6.QtCore import QThread, pyqtSignal, QEventLoop
from src.services.AudioTranscript import TranscriptionThread

class BatchTranscriptionThread(QThread):
    """
    A QThread to sequentially transcribe a batch of video files.
    """
    # Signal to report overall progress (current_file_index, total_files, message)
    progress = pyqtSignal(int, int, str)

    # Signal emitted when a single file has been successfully transcribed (file_path, transcribed_text)
    file_transcribed = pyqtSignal(str, str)

    # Signal emitted with the full combined text when the batch is complete
    batch_completed = pyqtSignal(str)

    # Signal emitted when the entire batch is complete
    completed = pyqtSignal()

    # Signal for reporting errors
    error = pyqtSignal(str)

    def __init__(self, video_paths, parent=None):
        super().__init__(parent)
        self.video_paths = video_paths
        self.main_window = parent  # The parent is expected to be the main window
        self._is_running = True
        self.last_result = None
        self.last_error = None

    def run(self):
        total_files = len(self.video_paths)
        transcriptions_map = {}

        if total_files == 0:
            self.completed.emit()
            return

        for i, video_path in enumerate(self.video_paths):
            if not self._is_running:
                self.error.emit("Batch transcription cancelled by user.")
                return

            self.progress.emit(i + 1, total_files, f"Checking {i+1}/{total_files}: {os.path.basename(video_path)}...")

            json_path = os.path.splitext(video_path)[0] + ".json"
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    transcribed_text = data.get('transcription_original') or data.get('transcription_raw')
                    if transcribed_text and transcribed_text.strip():
                        self.progress.emit(i + 1, total_files, f"Found existing transcription for {os.path.basename(video_path)}.")
                        self.file_transcribed.emit(os.path.basename(video_path), transcribed_text)
                        transcriptions_map[video_path] = transcribed_text
                        QThread.msleep(100) # Give UI time to update
                        continue # Skip to the next file
                except (json.JSONDecodeError, Exception) as e:
                    self.error.emit(f"Could not read existing JSON for {os.path.basename(video_path)}: {e}. Re-transcribing.")

            self.progress.emit(i + 1, total_files, f"Transcribing {i+1}/{total_files}: {os.path.basename(video_path)}...")

            loop = QEventLoop()
            self.last_result = None
            self.last_error = None

            single_file_thread = TranscriptionThread(video_path, main_window=self.main_window)
            single_file_thread.completed.connect(self._on_single_completed)
            single_file_thread.error.connect(self._on_single_error)
            single_file_thread.completed.connect(loop.quit)
            single_file_thread.error.connect(loop.quit)

            single_file_thread.start()
            loop.exec()
            single_file_thread.deleteLater()

            if self.last_error:
                self.error.emit(f"Failed to transcribe {os.path.basename(video_path)}: {self.last_error}")
                continue

            if self.last_result:
                try:
                    result_json_path, _ = self.last_result
                    with open(result_json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    transcribed_text = data.get('transcription_original') or data.get('transcription_raw', '')
                    if transcribed_text:
                        transcriptions_map[video_path] = transcribed_text
                        self.file_transcribed.emit(os.path.basename(video_path), transcribed_text)
                except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
                    self.error.emit(f"Could not read result for {os.path.basename(video_path)}: {e}")

        if self._is_running:
            self.progress.emit(total_files, total_files, "Finalizing and saving transcriptions...")
            self._save_all_transcriptions(transcriptions_map)
            combined_text = "\n\n---\n\n".join(transcriptions_map.values())
            self.batch_completed.emit(combined_text)
            self.completed.emit()

    def _save_all_transcriptions(self, transcriptions_map):
        language_code = self.main_window.languageComboBox.currentData()
        for video_path, text in transcriptions_map.items():
            json_path = os.path.splitext(video_path)[0] + ".json"
            try:
                data = {}
                if os.path.exists(json_path):
                    with open(json_path, 'r', encoding='utf-8') as f:
                        try:
                            data = json.load(f)
                        except json.JSONDecodeError:
                            data = {}

                data['transcription_original'] = text
                data['transcription_raw'] = text
                data['transcription_date'] = datetime.datetime.now().isoformat()
                if not data.get('language'):
                    data['language'] = language_code

                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                self.error.emit(f"Failed to save final JSON for {os.path.basename(video_path)}: {e}")


    def _on_single_completed(self, result):
        self.last_result = result
        self.last_error = None

    def _on_single_error(self, error_message):
        self.last_result = None
        self.last_error = error_message

    def stop(self):
        self._is_running = False
        self.terminate() # Forcefully stop if needed
        self.wait()