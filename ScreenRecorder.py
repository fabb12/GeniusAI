import numpy as np
import cv2
import pyautogui
from PyQt6.QtCore import QThread, pyqtSignal
import sounddevice as sd
import wave
import time
class ScreenRecorder(QThread):
    error_signal = pyqtSignal(str)

    def __init__(self, video_writer, audio_path, region=None, audio_input=0, audio_channels=2):
        super().__init__()
        self.video_writer = video_writer
        self.audio_path = audio_path
        self.region = region
        self.audio_input = audio_input
        self.audio_channels = audio_channels
        self.is_running = True
        self.start_time = None

    def run(self):
        audio_rate = 44100
        audio_buffer = []
        frame_rate = 25  # Tentativo di catturare 25 frame al secondo
        frame_period = 1.0 / frame_rate

        def audio_callback(indata, frames, time, status):
            if status:
                self.error_signal.emit(str(status))
            audio_buffer.extend(indata.copy())

        stream = sd.InputStream(device=self.audio_input, channels=self.audio_channels, samplerate=audio_rate, callback=audio_callback)
        stream.start()
        self.start_time = time.time()

        try:
            while self.is_running:
                current_time = time.time()
                if current_time - self.start_time >= frame_period:
                    self.start_time = current_time
                    img = pyautogui.screenshot(region=self.region) if self.region else pyautogui.screenshot()
                    frame = np.array(img)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self.video_writer.write(frame)
        finally:
            stream.stop()
            if audio_buffer:
                self.save_audio(audio_buffer, audio_rate)
            else:
                self.error_signal.emit("No audio data to save.")

    def save_audio(self, audio_buffer, audio_rate):
        audio_data = np.concatenate(audio_buffer, axis=0)
        scaled_audio_data = np.int16(audio_data / np.max(np.abs(audio_data)) * 32767)
        with wave.open(self.audio_path, 'w') as wav_file:
            wav_file.setnchannels(self.audio_channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(audio_rate)
            wav_file.writeframes(scaled_audio_data.tobytes())

    def stop(self):
        self.is_running = False
        self.wait()
