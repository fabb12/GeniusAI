import os
import subprocess
import shutil
from PyQt6.QtCore import QThread, pyqtSignal

class LipSyncThread(QThread):
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, wav2lip_dir, checkpoint_file, video_path, audio_path, output_path, parent=None):
        super().__init__(parent)
        self.wav2lip_dir = wav2lip_dir
        self.checkpoint_file = checkpoint_file
        self.video_path = video_path
        self.audio_path = audio_path
        self.output_path = output_path
        self.process = None
        self.running = True

    def stop(self):
        self.running = False
        if self.process:
            try:
                self.process.kill()
                self.process = None
                self.error.emit("Processo di Lip-sync annullato.")
            except Exception as e:
                self.error.emit(f"Errore durante l'annullamento: {e}")

    def run(self):
        if not self.running:
            return

        try:
            # Verifica se ffmpeg è installato
            if not shutil.which("ffmpeg"):
                raise EnvironmentError("FFmpeg non è installato o non è nel percorso di sistema.")

            if not os.path.exists(self.video_path):
                raise FileNotFoundError(f"Il file video non esiste: {self.video_path}")
            if not os.path.exists(self.audio_path):
                raise FileNotFoundError(f"Il file audio non esiste: {self.audio_path}")

            command = [
                'python', os.path.join(self.wav2lip_dir, 'inference.py'),
                '--checkpoint_path', self.checkpoint_file,
                '--face', self.video_path,
                '--audio', self.audio_path,
                '--outfile', self.output_path
            ]

            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            stdout, stderr = self.process.communicate()

            if not self.running:
                return

            if self.process.returncode != 0:
                raise Exception(f"Errore Wav2Lip: {stderr.decode('utf-8', 'ignore')}")

            self.completed.emit(self.output_path)

        except Exception as e:
            if self.running:
                self.error.emit(str(e))
        finally:
            self.process = None


# Example usage (for testing purposes, can be removed)
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel

    class TestWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.thread = None
            self.layout = QVBoxLayout(self)
            self.label = QLabel("Premi 'Start' per avviare il lip-sync.")
            self.start_button = QPushButton("Start")
            self.cancel_button = QPushButton("Cancel")
            self.layout.addWidget(self.label)
            self.layout.addWidget(self.start_button)
            self.layout.addWidget(self.cancel_button)
            self.start_button.clicked.connect(self.start_sync)
            self.cancel_button.clicked.connect(self.cancel_sync)
            self.cancel_button.setEnabled(False)

        def start_sync(self):
            wav2lip_dir = "./Wav2Lip"  # Adjust path
            checkpoint = os.path.join(wav2lip_dir, "checkpoints/wav2lip_gan.pth")
            video = "path/to/your/video.mp4"
            audio = "path/to/your/audio.wav"
            output = "path/to/your/output.mp4"

            if not all(os.path.exists(p) for p in [wav2lip_dir, checkpoint, video, audio]):
                 self.label.setText("Paths not configured correctly for test.")
                 return

            self.thread = LipSyncThread(wav2lip_dir, checkpoint, video, audio, output)
            self.thread.completed.connect(self.on_completed)
            self.thread.error.connect(self.on_error)
            self.thread.start()
            self.label.setText("Lip-sync in corso...")
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)

        def cancel_sync(self):
            if self.thread:
                self.thread.stop()

        def on_completed(self, output_path):
            self.label.setText(f"Completato! File salvato in: {output_path}")
            self.reset_buttons()

        def on_error(self, message):
            self.label.setText(f"Errore: {message}")
            self.reset_buttons()

        def reset_buttons(self):
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.thread = None

    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
