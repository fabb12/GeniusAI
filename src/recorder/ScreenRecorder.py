import subprocess
from screeninfo import get_monitors
from PyQt6.QtCore import QThread, pyqtSignal
import os
from src.config import WATERMARK_IMAGE
from src.config import DEFAULT_AUDIO_CHANNELS, DEFAULT_FRAME_RATE

class ScreenRecorder(QThread):
    error_signal = pyqtSignal(str)
    recording_started_signal = pyqtSignal()
    recording_stopped_signal = pyqtSignal()

    def __init__(self, output_path, ffmpeg_path='ffmpeg.exe', monitor_index=0, audio_inputs=None,
                 audio_channels=DEFAULT_AUDIO_CHANNELS, frames=DEFAULT_FRAME_RATE, record_audio=True):
        super().__init__()
        self.output_path = output_path
        self.ffmpeg_path = os.path.abspath(ffmpeg_path)
        self.monitor_index = monitor_index
        self.audio_inputs = audio_inputs if audio_inputs is not None else []
        self.audio_channels = audio_channels
        self.frame_rate = frames
        self.record_audio = record_audio and self.audio_inputs
        self.is_running = True
        self.watermark_image = WATERMARK_IMAGE
        self.ffmpeg_process = None

        # Check if ffmpeg.exe exists
        if not os.path.isfile(self.ffmpeg_path):
            self.error_signal.emit(f"ffmpeg.exe not found at {self.ffmpeg_path}")
            self.is_running = False

        # Check if watermark image exists
        if not os.path.isfile(self.watermark_image):
            self.error_signal.emit(f"Watermark image not found at {self.watermark_image}")
            self.is_running = False

    def get_monitor_offset(self):
        monitor = get_monitors()[self.monitor_index]
        return monitor.x, monitor.y, monitor.width, monitor.height

    def run(self):
        if not self.is_running:
            self.recording_stopped_signal.emit()
            return

        self.recording_started_signal.emit()

        offset_x, offset_y, screen_width, screen_height = self.get_monitor_offset()

        # Base command for video and watermark inputs
        ffmpeg_command = [
            self.ffmpeg_path,
            '-f', 'gdigrab',
            '-framerate', str(self.frame_rate),
            '-offset_x', str(offset_x),
            '-offset_y', str(offset_y),
            '-video_size', f'{screen_width}x{screen_height}',
            '-i', 'desktop',
            '-i', self.watermark_image,
        ]

        # Add audio inputs if any
        if self.record_audio:
            for audio_device in self.audio_inputs:
                ffmpeg_command.extend(['-f', 'dshow', '-i', f'audio={audio_device}'])

        # --- Build the filter_complex string and map arguments ---
        video_filter = "[0:v][1:v]overlay=W-w-10:H-h-10[v_out]"
        num_audio_inputs = len(self.audio_inputs)

        filter_parts = [video_filter]
        map_args = ['-map', '[v_out]']
        audio_codec_args = []

        if self.record_audio:
            if num_audio_inputs == 1:
                # One audio input, map it directly. Audio is input [2:a]
                map_args.extend(['-map', '2:a'])
                audio_codec_args = ['-c:a', 'aac', '-b:a', '192k']
            elif num_audio_inputs > 1:
                # Multiple audio inputs, merge them.
                audio_merge_inputs = "".join([f"[{i+2}:a]" for i in range(num_audio_inputs)])
                audio_filter = f"{audio_merge_inputs}amerge=inputs={num_audio_inputs}[a_out]"
                filter_parts.append(audio_filter)
                map_args.extend(['-map', '[a_out]'])
                audio_codec_args = ['-c:a', 'aac', '-b:a', '192k', '-ac', '2']

        # Combine filter parts
        combined_filter = ";".join(filter_parts)
        ffmpeg_command.extend(['-filter_complex', combined_filter])
        ffmpeg_command.extend(map_args)

        # Add final video output options
        ffmpeg_command.extend([
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-pix_fmt', 'yuv420p',
        ])

        # Add audio codec options if audio is recorded
        if self.record_audio:
            ffmpeg_command.extend(audio_codec_args)

        ffmpeg_command.extend(['-y', self.output_path])

        # Use CREATE_NO_WINDOW to hide the console window
        creationflags = subprocess.CREATE_NO_WINDOW

        self.ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, creationflags=creationflags, text=True, errors='ignore')

        while self.is_running:
            # Non-blocking read from stderr
            if self.ffmpeg_process.poll() is not None:
                break
            try:
                # This loop is mainly to keep the thread alive.
                # A more sophisticated implementation might read stderr to report progress.
                self.msleep(100)
            except Exception:
                break

        # Ensure recording is stopped cleanly
        if self.ffmpeg_process.poll() is None:
            self.stop_recording()

    def stop_recording(self):
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            try:
                self.ffmpeg_process.stdin.write('q\n')
                self.ffmpeg_process.stdin.flush()
                self.ffmpeg_process.wait(timeout=5)
            except (OSError, ValueError, BrokenPipeError, subprocess.TimeoutExpired) as e:
                self.error_signal.emit(f"ffmpeg did not terminate gracefully, killing process. Error: {str(e)}")
                self.ffmpeg_process.kill()
                self.ffmpeg_process.wait()

        self.is_running = False
        self.recording_stopped_signal.emit()

    def stop(self):
        self.is_running = False
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
             self.stop_recording()
        else:
            self.recording_stopped_signal.emit()
