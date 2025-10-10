import os
import json
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
        if total_files == 0:
            self.completed.emit()
            return

        for i, video_path in enumerate(self.video_paths):
            if not self._is_running:
                self.error.emit("Batch transcription cancelled by user.")
                return

            self.progress.emit(i + 1, total_files, f"Transcribing {i+1}/{total_files}: {os.path.basename(video_path)}...")

            loop = QEventLoop()

            # Reset state for the new transcription
            self.last_result = None
            self.last_error = None

            # Create the transcription thread for the single file
            single_file_thread = TranscriptionThread(video_path, self.main_window)

            # Connect signals to slots that will quit the event loop
            single_file_thread.completed.connect(self._on_single_completed)
            single_file_thread.error.connect(self._on_single_error)

            single_file_thread.completed.connect(loop.quit)
            single_file_thread.error.connect(loop.quit)

            single_file_thread.start()
            loop.exec()  # Block until the single file transcription is done

            # Clean up the thread
            single_file_thread.deleteLater()

            if self.last_error:
                error_message = f"Failed to transcribe {os.path.basename(video_path)}: {self.last_error}"
                self.error.emit(error_message)
                # Optionally, you could decide to stop the whole batch on first error
                # return
                continue # Or continue with the next file

            if self.last_result:
                try:
                    json_path, _ = self.last_result
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    transcribed_text = data.get('transcription_raw', '')
                    self.file_transcribed.emit(os.path.basename(video_path), transcribed_text)
                except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
                    self.error.emit(f"Could not read result for {os.path.basename(video_path)}: {e}")

        if self._is_running:
            self.progress.emit(total_files, total_files, "Batch transcription complete.")
            self.completed.emit()

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