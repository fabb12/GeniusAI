import subprocess
import re
from screeninfo import get_monitors
from PyQt6.QtCore import QThread, pyqtSignal
import os
from src.config import WATERMARK_IMAGE
from src.config import DEFAULT_AUDIO_CHANNELS, DEFAULT_FRAME_RATE

class ScreenRecorder(QThread):
    error_signal = pyqtSignal(str)
    recording_started_signal = pyqtSignal()
    recording_stopped_signal = pyqtSignal()
    stats_updated = pyqtSignal(dict)

    def __init__(self, output_path, ffmpeg_path='ffmpeg.exe', monitor_index=0, audio_inputs=None,
                 audio_channels=DEFAULT_AUDIO_CHANNELS, frames=DEFAULT_FRAME_RATE, record_audio=True,
                 use_watermark=True, watermark_path=None, watermark_size=10, watermark_position="Bottom Right",
                 bluetooth_mode=False, audio_volume=1.0,
                 record_webcam=False, webcam_device=None, webcam_position="Bottom Right", video_codec='libx264'):
        super().__init__()
        self.output_path = output_path
        self.ffmpeg_path = os.path.abspath(ffmpeg_path)
        self.monitor_index = monitor_index
        self.audio_inputs = audio_inputs if audio_inputs is not None else []
        self.audio_channels = audio_channels
        self.frame_rate = frames
        self.bluetooth_mode = bluetooth_mode
        self.audio_volume = audio_volume
        # Correctly determine if audio should be recorded
        self.record_audio = record_audio and bool(self.audio_inputs)
        self.is_running = True
        self.use_watermark = use_watermark
        self.watermark_image = watermark_path if watermark_path else WATERMARK_IMAGE
        self.watermark_size = watermark_size
        self.watermark_position = watermark_position
        self.ffmpeg_process = None

        # Webcam settings
        self.record_webcam = record_webcam
        self.webcam_device = webcam_device
        self.webcam_position = webcam_position
        self.video_codec = video_codec

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

        # --- Input Management ---
        input_count = 1  # Starts with 1 for the screen grab
        webcam_input_index = -1
        watermark_input_index = -1

        if self.record_webcam and self.webcam_device:
            ffmpeg_command.extend(['-f', 'dshow', '-i', f'video={self.webcam_device}'])
            webcam_input_index = input_count
            input_count += 1

        if self.use_watermark:
            ffmpeg_command.extend(['-i', self.watermark_image])
            watermark_input_index = input_count
            input_count += 1

        audio_input_start_index = input_count
        if self.record_audio:
            for audio_device in self.audio_inputs:
                ffmpeg_command.extend(['-f', 'dshow'])
                if self.bluetooth_mode:
                    ffmpeg_command.extend(['-audio_buffer_size', '100'])
                ffmpeg_command.extend(['-i', f'audio={audio_device}'])

        # --- Filter and Mapping Management ---
        filter_complex_parts = []
        map_args = []
        audio_codec_args = []

        # --- Video Filter Chain ---
        video_filters_applied = (self.record_webcam and webcam_input_index != -1) or \
                                (self.use_watermark and watermark_input_index != -1)

        if video_filters_applied:
            last_video_stream_label = "[0:v]"
            if self.record_webcam and webcam_input_index != -1:
                pip_scale_filter = f"[{webcam_input_index}:v]scale=iw/4:-2[pip]"
                filter_complex_parts.append(pip_scale_filter)

                overlay_positions = {"Top Left": "10:10", "Top Right": "W-w-10:10", "Bottom Left": "10:H-h-10", "Bottom Right": "W-w-10:H-h-10"}
                position = overlay_positions.get(self.webcam_position, "W-w-10:H-h-10")

                output_label = "[v_out]" if not (self.use_watermark and watermark_input_index != -1) else "[v_with_pip]"
                pip_overlay_filter = f"{last_video_stream_label}[pip]overlay={position}{output_label}"
                filter_complex_parts.append(pip_overlay_filter)
                last_video_stream_label = output_label

            if self.use_watermark and watermark_input_index != -1:
                wm_scale_filter = f"[{watermark_input_index}:v]scale=-1:ih*{self.watermark_size/100}[scaled_wm]"
                filter_complex_parts.append(wm_scale_filter)

                overlay_positions = {"Top Left": "10:10", "Top Right": "W-w-10:10", "Bottom Left": "10:H-h-10", "Bottom Right": "W-w-10:H-h-10"}
                position = overlay_positions.get(self.watermark_position, "W-w-10:H-h-10")

                wm_overlay_filter = f"{last_video_stream_label}[scaled_wm]overlay={position}[v_out]"
                filter_complex_parts.append(wm_overlay_filter)

        # --- Audio Filter Chain ---
        audio_filters_applied = False
        if self.record_audio:
            num_audio_inputs = len(self.audio_inputs)
            apply_volume_filter = self.audio_volume and self.audio_volume != 1.0
            audio_filters_applied = num_audio_inputs > 1 or apply_volume_filter

            if audio_filters_applied:
                last_audio_stream_label = ""
                if num_audio_inputs > 1:
                    audio_merge_inputs = "".join([f"[{i + audio_input_start_index}:a]" for i in range(num_audio_inputs)])
                    merge_filter = f"{audio_merge_inputs}amerge=inputs={num_audio_inputs}[a_merged]"
                    filter_complex_parts.append(merge_filter)
                    last_audio_stream_label = "[a_merged]"
                else:
                    last_audio_stream_label = f"[{audio_input_start_index}:a]"

                if apply_volume_filter:
                    volume_filter = f"{last_audio_stream_label}volume={self.audio_volume}[a_out]"
                    filter_complex_parts.append(volume_filter)

            audio_codec_args = ['-c:a', 'aac', '-b:a', '192k']
            if num_audio_inputs > 1:
                audio_codec_args.extend(['-ac', '2'])

        # --- Assemble Command ---
        if filter_complex_parts:
            # If only audio filters are applied, we must pass the video stream through the filter graph as well
            if not video_filters_applied and audio_filters_applied:
                filter_complex_parts.insert(0, "[0:v]null[v_out]")

            ffmpeg_command.extend(['-filter_complex', ";".join(filter_complex_parts)])

        # --- Mapping ---
        if video_filters_applied or (not video_filters_applied and audio_filters_applied):
            map_args.extend(['-map', '[v_out]'])
        else:
            map_args.extend(['-map', '0:v'])

        if self.record_audio:
            if audio_filters_applied:
                map_args.extend(['-map', '[a_out]'])
            else:
                map_args.extend(['-map', f'{audio_input_start_index}:a'])

        ffmpeg_command.extend(map_args)

        # Add final video output options
        ffmpeg_command.extend([
            '-c:v', self.video_codec,
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

        # Regex to parse ffmpeg's progress output
        stats_regex = re.compile(
            r"frame=\s*(?P<frame>\d+)\s+"
            r"fps=\s*(?P<fps>[\d.]+)\s+"
            r"q=(?P<q>[\d.-]+)\s+"
            r"size=\s*(?P<size>\d+)kB\s+"
            r"time=(?P<time>[\d:.]+)\s+"
            r"bitrate=\s*(?P<bitrate>[\d.]+)kbits/s"
        )

        while self.is_running:
            if self.ffmpeg_process.poll() is not None:
                break

            line = self.ffmpeg_process.stderr.readline()
            if line:
                line_str = line.decode('utf-8', errors='ignore').strip()
                match = stats_regex.search(line_str)
                if match:
                    stats = match.groupdict()
                    self.stats_updated.emit(stats)
                print(line_str) # for debugging

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
