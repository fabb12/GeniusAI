import pygetwindow as gw
import time
from threading import Thread
from screeninfo import get_monitors

class TeamsCallRecorder(Thread):
    def __init__(self, video_audio_manager):
        super().__init__()
        self.video_audio_manager = video_audio_manager
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            self.check_for_teams_call()
            time.sleep(5)  # Controlla ogni 5 secondi

    def check_for_teams_call(self):
        if not self.video_audio_manager.autoRecordTeamsCheckBox.isChecked():
            return  # Non fare nulla se la checkbox non è selezionata

        windows = gw.getWindowsWithTitle("Microsoft Teams")
        for window in windows:
            if "in call" in window.title.lower():
                if not self.video_audio_manager.is_recording:
                    self.start_recording(window)
                return

        # Se nessuna chiamata è attiva, ferma la registrazione
        if self.video_audio_manager.is_recording:
            self.video_audio_manager.stopScreenRecording()

    def start_recording(self, window):
        self.video_audio_manager.select_screen_for_window(window)
        self.video_audio_manager.startScreenRecording()

    def stop(self):
        self.running = False
