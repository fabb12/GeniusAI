import numpy as np
import cv2
import pyautogui
from PyQt6.QtCore import QThread, pyqtSignal
import sounddevice as sd
import wave
import time
from moviepy.config import change_settings
import os
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
        self.frame_rate = 25  # Frame per second
        self.audio_rate = 44100  # Audio sample rate


        # Imposta il percorso di ffmpeg relativamente al percorso di esecuzione dello script
        ffmpeg_executable_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg.exe')
        change_settings({"FFMPEG_BINARY": ffmpeg_executable_path})
        print (ffmpeg_executable_path)


    def run(self):
        frame_period = 1.0 / self.frame_rate
        audio_buffer = []

        def audio_callback(indata, frames, time, status):
            if status:
                self.error_signal.emit(str(status))
            audio_buffer.append((indata.copy(), time.inputBufferAdcTime))

        stream = sd.InputStream(device=self.audio_input, channels=self.audio_channels, samplerate=self.audio_rate, callback=audio_callback)
        stream.start()
        self.start_time = time.time()

        try:
            while self.is_running:
                current_time = time.time()
                if current_time - self.start_time >= frame_period:
                    self.start_time += frame_period
                    img = pyautogui.screenshot(region=self.region) if self.region else pyautogui.screenshot()
                    frame = np.array(img)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    # Get current mouse position and draw a red circle
                    mouse_x, mouse_y = pyautogui.position()
                    cv2.circle(frame, (mouse_x, mouse_y), 10, (0, 0, 255), -1)  # Red circle

                    self.video_writer.write(frame)
        finally:
            stream.stop()
            if audio_buffer:
                self.save_audio(audio_buffer)
            else:
                self.error_signal.emit("No audio data to save.")

    def save_audio(self, audio_buffer):
        flat_buffer = np.concatenate([buf for buf, t in audio_buffer], axis=0)
        scaled_audio_data = np.int16(flat_buffer / np.max(np.abs(flat_buffer)) * 32767)
        with wave.open(self.audio_path, 'w') as wav_file:
            wav_file.setnchannels(self.audio_channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.audio_rate)
            wav_file.writeframes(scaled_audio_data.tobytes())

    def stop(self):
        self.is_running = False
        self.wait()
