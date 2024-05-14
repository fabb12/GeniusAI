import numpy as np
import cv2
from PyQt6.QtCore import QThread, pyqtSignal
import pyaudio
import wave
import time
from mss import mss

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
        frame_times = []

        stream = self.p.open(format=pyaudio.paInt16,
                             channels=self.audio_channels,
                             rate=self.audio_rate,
                             input=True,
                             input_device_index=self.audio_input,
                             frames_per_buffer=1024)
        stream.start_stream()

        with mss() as sct:
            next_frame_time = time.time()
            start_time = next_frame_time  # Registra il tempo di inizio della registrazione
            try:
                while self.is_running:
                    current_time = time.time()
                    if current_time >= next_frame_time:
                        if self.region:
                            img = sct.grab(self.region)
                        else:
                            img = sct.grab(sct.monitors[0])
                        frame = np.array(img)
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                        self.video_writer.write(frame)
                        frame_times.append(current_time - start_time)  # Registra il delta tempo
                        next_frame_time += self.frame_period

                    audio_data = stream.read(1024, exception_on_overflow=False)
                    audio_buffer.append((current_time - start_time, audio_data))  # Registra il delta tempo
            except Exception as e:
                self.error_signal.emit(f"Recording error: {str(e)}")
            finally:
                stream.stop_stream()
                stream.close()
                self.save_audio(audio_buffer, frame_times)
                self.recording_stopped_signal.emit()
                self.p.terminate()

    def save_audio(self, audio_buffer, frame_times):
        try:
            with wave.open(self.audio_path, 'wb') as wf:
                wf.setnchannels(self.audio_channels)
                wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.audio_rate)
                # Scrivi un file audio completo
                audio_data_full = b''.join([data[1] for data in audio_buffer])
                wf.writeframes(audio_data_full)
        except Exception as e:
            self.error_signal.emit(f"Failed to save audio: {str(e)}")

    def stop(self):
        self.is_running = False
        self.wait()

