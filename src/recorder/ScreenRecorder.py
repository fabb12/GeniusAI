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
                 audio_channels=DEFAULT_AUDIO_CHANNELS, frames=DEFAULT_FRAME_RATE, record_audio=True,
                 use_watermark=True, watermark_path=None, watermark_size=10, watermark_position="Bottom Right",
                 bluetooth_mode=False):
        super().__init__()
        self.output_path = output_path
        self.ffmpeg_path = os.path.abspath(ffmpeg_path)
        self.monitor_index = monitor_index
        self.audio_inputs = audio_inputs if audio_inputs is not None else []
        self.audio_channels = audio_channels
        self.frame_rate = frames
        self.bluetooth_mode = bluetooth_mode
        # Correctly determine if audio should be recorded
        self.record_audio = record_audio and bool(self.audio_inputs)
        self.is_running = True
        self.use_watermark = use_watermark
        self.watermark_image = watermark_path if watermark_path else WATERMARK_IMAGE
        self.watermark_size = watermark_size
        self.watermark_position = watermark_position
        self.ffmpeg_process = None

        # Check if ffmpeg.exe exists
        if not os.path.isfile(self.ffmpeg_path):
            self.error_signal.emit(f"ffmpeg.exe not found at {self.ffmpeg_path}")
            self.is_running = False

        # Check if watermark image exists
        if self.use_watermark and not os.path.isfile(self.watermark_image):
            self.error_signal.emit(f"Watermark image not found at {self.watermark_image}")
            self.use_watermark = False

    def get_monitor_offset(self):
        monitor = get_monitors()[self.monitor_index]
        return monitor.x, monitor.y, monitor.width, monitor.height

    def run(self):
        if not self.is_running:
            self.recording_stopped_signal.emit()
            return

        self.recording_started_signal.emit()

        offset_x, offset_y, screen_width, screen_height = self.get_monitor_offset()

        # Base command for video input
        ffmpeg_command = [
            self.ffmpeg_path,
            '-f', 'gdigrab',
            '-framerate', str(self.frame_rate),
            '-offset_x', str(offset_x),
            '-offset_y', str(offset_y),
            '-video_size', f'{screen_width}x{screen_height}',
            '-i', 'desktop',
        ]

        if self.use_watermark:
            ffmpeg_command.extend(['-i', self.watermark_image])

        # Add audio inputs if any
        if self.record_audio:
            for audio_device in self.audio_inputs:
                ffmpeg_command.extend(['-f', 'dshow'])
                # For Bluetooth, set device options for compatibility
                if self.bluetooth_mode:
                    ffmpeg_command.extend(['-audio_buffer_size', '100'])
                    ffmpeg_command.extend(['-sample_rate', '16000'])
                    ffmpeg_command.extend(['-channels', '1'])
                else:
                    # Provide default high-quality settings for other devices
                    ffmpeg_command.extend(['-sample_rate', '44100'])
                    ffmpeg_command.extend(['-channels', '2'])
                ffmpeg_command.extend(['-i', f'audio={audio_device}'])

        # --- Build the filter_complex string and map arguments ---
        filter_complex_parts = []
        map_args = []
        audio_codec_args = []
        num_audio_inputs = len(self.audio_inputs)

        if self.use_watermark:
            # Watermark is input 1, so video is [0:v] and watermark is [1:v]
            # Scale the watermark to be x% of the video height
            scale_filter = f"[1:v]scale=-1:ih*{self.watermark_size/100}[scaled_wm]"
            filter_complex_parts.append(scale_filter)

            # Position the watermark
            if self.watermark_position == "Top Left":
                overlay_filter = "[0:v][scaled_wm]overlay=10:10[v_out]"
            elif self.watermark_position == "Top Right":
                overlay_filter = "[0:v][scaled_wm]overlay=W-w-10:10[v_out]"
            elif self.watermark_position == "Bottom Left":
                overlay_filter = "[0:v][scaled_wm]overlay=10:H-h-10[v_out]"
            else:  # Bottom Right
                overlay_filter = "[0:v][scaled_wm]overlay=W-w-10:H-h-10[v_out]"

            filter_complex_parts.append(overlay_filter)
            map_args.extend(['-map', '[v_out]'])
            audio_input_start_index = 2  # Audio inputs start after video and watermark
        else:
            # No watermark, just map the video directly
            map_args.extend(['-map', '0:v'])
            audio_input_start_index = 1  # Audio inputs start after video

        if self.record_audio:
            if num_audio_inputs == 1:
                # Single audio input, map it directly
                map_args.extend(['-map', f'{audio_input_start_index}:a'])
                audio_codec_args = ['-c:a', 'aac', '-b:a', '192k']
            elif num_audio_inputs > 1:
                # Multiple audio inputs, merge them
                audio_merge_inputs = "".join([f"[{i+audio_input_start_index}:a]" for i in range(num_audio_inputs)])
                audio_filter = f"{audio_merge_inputs}amerge=inputs={num_audio_inputs}[a_out]"
                filter_complex_parts.append(audio_filter)
                map_args.extend(['-map', '[a_out]'])
                audio_codec_args = ['-c:a', 'aac', '-b:a', '192k', '-ac', '2']

            # The -ac and -ar options have been moved to the dshow input options for bluetooth mode
            # if self.bluetooth_mode:
            #     audio_codec_args.extend(['-ac', '1', '-ar', '8000'])

        if filter_complex_parts:
            combined_filter = ";".join(filter_complex_parts)
            ffmpeg_command.extend(['-filter_complex', combined_filter])

        ffmpeg_command.extend(map_args)

        # Add final video output options
        ffmpeg_command.extend([
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart', # Add faststart flag for robustness
        ])

        # Add audio codec options if audio is recorded
        if self.record_audio:
            ffmpeg_command.extend(audio_codec_args)

        ffmpeg_command.extend(['-y', self.output_path])

        # Use CREATE_NO_WINDOW to hide the console window
        creationflags = subprocess.CREATE_NO_WINDOW

        # Start the ffmpeg process in binary mode (remove text=True)
        self.ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, creationflags=creationflags)

        # Restore stderr reading loop for debugging
        while self.is_running:
            if self.ffmpeg_process.poll() is not None:
                break
            # Reading stderr can be useful for debugging ffmpeg issues
            line = self.ffmpeg_process.stderr.readline()
            if line:
                print(line.decode('utf-8', errors='ignore').strip())

        # Ensure recording is stopped cleanly
        if self.ffmpeg_process.poll() is None:
            self.stop_recording()

    def stop_recording(self):
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            try:
                # Write binary 'q' to stdin
                self.ffmpeg_process.stdin.write(b'q')
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
