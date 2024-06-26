import ctypes.wintypes
import subprocess
from screeninfo import get_monitors
from PyQt6.QtCore import QThread, pyqtSignal
import os

class ScreenRecorder(QThread):
    error_signal = pyqtSignal(str)
    recording_started_signal = pyqtSignal()
    recording_stopped_signal = pyqtSignal()

    def __init__(self, output_path, ffmpeg_path='ffmpeg.exe', monitor_index=0, audio_input=None, audio_channels=2, frames=25, record_audio=True):
        super().__init__()
        self.output_path = output_path
        self.ffmpeg_path = os.path.abspath(ffmpeg_path)
        self.monitor_index = monitor_index
        self.audio_input = audio_input
        self.audio_channels = audio_channels
        self.frame_rate = frames
        self.record_audio = record_audio
        self.is_running = True

        # Check if ffmpeg.exe exists
        if not os.path.isfile(self.ffmpeg_path):
            self.error_signal.emit(f"ffmpeg.exe not found at {self.ffmpeg_path}")
            self.is_running = False

    def get_monitor_offset(self):
        monitor = get_monitors()[self.monitor_index]
        return monitor.x, monitor.y, monitor.width, monitor.height

    def run(self):
        self.recording_started_signal.emit()

        offset_x, offset_y, screen_width, screen_height = self.get_monitor_offset()

        ffmpeg_command = [
            self.ffmpeg_path,  # Use the provided ffmpeg path
            '-f', 'gdigrab',  # For Windows screen capture
            '-framerate', str(self.frame_rate),
            '-offset_x', str(offset_x),
            '-offset_y', str(offset_y),
            '-video_size', f'{screen_width}x{screen_height}',
            '-i', 'desktop',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-pix_fmt', 'yuv420p',
            '-y', self.output_path
        ]

        if self.record_audio and self.audio_input:
            ffmpeg_command.extend([
                '-f', 'dshow',  # For Windows audio capture
                '-i', f'audio={self.audio_input}',  # Use the correct audio input
                '-c:a', 'aac',
                '-b:a', '192k'
            ])

        # Use CREATE_NO_WINDOW to hide the console window
        creationflags = subprocess.CREATE_NO_WINDOW

        self.ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, creationflags=creationflags)

        while self.is_running:
            output = self.ffmpeg_process.stderr.readline()
            if output:
                print(output.decode().strip())
            if self.ffmpeg_process.poll() is not None:
                break

        self.stop_recording()

    def stop_recording(self):
        self.is_running = False
        if self.ffmpeg_process:
            # Send 'q' to ffmpeg process to stop recording gracefully
            try:
                self.ffmpeg_process.stdin.write(b'q')
                self.ffmpeg_process.stdin.flush()
            except Exception as e:
                self.error_signal.emit(f"Error sending 'q' to ffmpeg process: {str(e)}")

            self.ffmpeg_process.wait()
        self.recording_stopped_signal.emit()

    def stop(self):
        self.is_running = False
        self.stop_recording()
