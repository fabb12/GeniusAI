import numpy as np
import cv2
import pyautogui
from PyQt6.QtCore import QThread, pyqtSignal
import pyaudio
import wave
import time
import os

class ScreenRecorder(QThread):
    error_signal = pyqtSignal(str)
    recording_started_signal = pyqtSignal()
    recording_stopped_signal = pyqtSignal()

    def __init__(self, video_writer, audio_path, region=None, audio_input=0, audio_channels=2):
        super().__init__()
        self.video_writer = video_writer
        self.audio_path = audio_path
        self.region = region
        self.audio_input = audio_input
        self.audio_channels = audio_channels
        self.is_running = True
        self.frame_rate = 25  # Frames per second
        self.audio_rate = 44100  # Audio sample rate
        self.p = pyaudio.PyAudio()
        self.frame_period = 1.0 / self.frame_rate

    def run(self):
        self.recording_started_signal.emit()
        audio_buffer = []
        next_frame_time = time.time()

        # Open audio stream with PyAudio
        stream = self.p.open(format=pyaudio.paInt16,
                             channels=self.audio_channels,
                             rate=self.audio_rate,
                             input=True,
                             input_device_index=self.audio_input,
                             frames_per_buffer=1024)
        stream.start_stream()

        try:
            while self.is_running:
                current_time = time.time()
                if current_time >= next_frame_time:
                    img = pyautogui.screenshot(region=self.region) if self.region else pyautogui.screenshot()
                    frame = np.array(img)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self.video_writer.write(frame)
                    next_frame_time += self.frame_period

                # Read and buffer audio data
                audio_data = stream.read(1024, exception_on_overflow=False)
                audio_buffer.append(audio_data)
        except Exception as e:
            self.error_signal.emit(f"Recording error: {str(e)}")
        finally:
            stream.stop_stream()
            stream.close()
            self.save_audio(audio_buffer)
            self.recording_stopped_signal.emit()
            self.p.terminate()

    def save_audio(self, audio_buffer):
        try:
            with wave.open(self.audio_path, 'wb') as wf:
                wf.setnchannels(self.audio_channels)
                wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.audio_rate)
                wf.writeframes(b''.join(audio_buffer))
        except Exception as e:
            self.error_signal.emit(f"Failed to save audio: {str(e)}")

    def stop(self):
        self.is_running = False
        self.wait()
