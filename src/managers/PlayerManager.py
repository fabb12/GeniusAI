from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QMediaPlayer

class PlayerManager:
    def __init__(self, main_window, player_input, player_output, ui_manager):
        self.main_window = main_window
        self.player_input = player_input
        self.player_output = player_output
        self.ui_manager = ui_manager

    def load_video(self, video_path, video_title = 'Video Track'):
        """Load and play video or audio, updating UI based on file type."""
        if self.main_window.reversed_video_path and os.path.exists(self.main_window.reversed_video_path) and not video_path == self.main_window.reversed_video_path:
            try:
                os.remove(self.main_window.reversed_video_path)
                self.main_window.reversed_video_path = None
                logging.info("Cleaned up previous reversed video file.")
            except Exception as e:
                logging.error(f"Could not remove temporary reversed video file: {e}")

        self.player_input.stop()
        self.main_window.reset_view()
        self.ui_manager.speedSpinBox.setValue(1.0)
        self.ui_manager.videoSlider.resetBookmarks()

        if self.player_input.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
            QTimer.singleShot(1, lambda: self.sourceSetter(video_path))

        self.main_window.videoPathLineEdit = video_path
        self.ui_manager.transcriptionDock.setTitle(f"Trascrizione e Sintesi Audio - {os.path.basename(video_path)}")

        is_audio_only = self.is_audio_only(video_path)
        self.ui_manager.cropButton.setEnabled(not is_audio_only)

        if is_audio_only:
            self.ui_manager.fileNameLabel.setText(f"{video_title} - Traccia solo audio")
            self.ui_manager.videoCropWidget.setVisible(False)
            self.ui_manager.audioOnlyLabel.setVisible(True)
        else:
            self.ui_manager.fileNameLabel.setText(os.path.basename(video_path))
            self.ui_manager.videoCropWidget.setVisible(True)
            self.ui_manager.audioOnlyLabel.setVisible(False)

        self.main_window.updateRecentFiles(video_path)

        # Gestisce il file JSON (crea o carica) e aggiorna l'InfoDock
        self.main_window._manage_video_json(video_path)
        self.ui_manager.transcriptionTabs.setCurrentWidget(self.ui_manager.singleTranscriptionTextArea)
        if not self.main_window.transcription_original:
            self.ui_manager.transcriptionViewToggle.setEnabled(False)
            self.ui_manager.transcriptionViewToggle.setChecked(False)

    def load_video_output(self, video_path):

        self.player_output.stop()
        self.ui_manager.speedSpinBoxOutput.setValue(1.0)

        if self.player_output.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
            QTimer.singleShot(1, lambda: self.source_setter_output(video_path))

        self.ui_manager.fileNameLabelOutput.setText(os.path.basename(video_path))  # Aggiorna il nome del file sulla label
        self.main_window.videoPathLineOutputEdit = video_path
        logging.debug(f"Loaded video output: {video_path}")

        # Aggiungi questa riga per caricare la cache di estrazione anche per il player di output
        self.main_window._load_and_display_extraction_cache(video_path)

    def is_audio_only(self, file_path):
        """Check if the file is likely audio-only based on the extension."""
        audio_extensions = {'.mp3', '.wav', '.aac', '.m4a', '.flac', '.ogg'}
        ext = os.path.splitext(file_path)[1].lower()
        return ext in audio_extensions

    def source_setter(self, url):
        self.player_input.setSource(QUrl.fromLocalFile(url))
        self.player_input.play()
        self.player_input.pause()

    def source_setter_output(self, url):
        self.player_output.setSource(QUrl.fromLocalFile(url))
        self.player_output.play()
        self.player_output.pause()

    def toggle_play_pause(self, player_type='input'):
        if player_type == 'input':
            player = self.player_input
            button = self.ui_manager.playButton
            timer = self.main_window.reverseTimer
            rate = self.ui_manager.speedSpinBox.value()
            fps_func = self.get_current_fps
        else:
            player = self.player_output
            button = self.ui_manager.playButtonOutput
            timer = self.main_window.reverseTimerOutput
            rate = self.ui_manager.speedSpinBoxOutput.value()
            fps_func = self.get_current_fps_output

        if rate < 0:
            if timer.isActive():
                timer.stop()
                button.setIcon(QIcon(get_resource("play.png")))
            else:
                interval = int(1000 / (fps_func() * abs(rate)))
                if interval <= 0: interval = 20
                timer.start(interval)
                button.setIcon(QIcon(get_resource("pausa.png")))
        else:
            if player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                player.pause()
            else:
                player.play()

    def stop_video(self, player_type='input'):
        if player_type == 'input':
            self.player_input.stop()
        else:
            self.player_output.stop()

    def rewind_5_seconds(self, player_type='input'):
        player = self.player_input if player_type == 'input' else self.player_output
        current_position = player.position()
        new_position = max(0, current_position - 5000)
        player.setPosition(new_position)

    def forward_5_seconds(self, player_type='input'):
        player = self.player_input if player_type == 'input' else self.player_output
        current_position = player.position()
        new_position = current_position + 5000
        player.setPosition(new_position)

    def frame_backward(self):
        fps = self.get_current_fps()
        if fps > 0:
            current_pos = self.player_input.position()
            new_pos = current_pos - (1000 / fps)
            self.player_input.setPosition(int(new_pos))

    def frame_forward(self):
        fps = self.get_current_fps()
        if fps > 0:
            current_pos = self.player_input.position()
            new_pos = current_pos + (1000 / fps)
            self.player_input.setPosition(int(new_pos))

    def go_to_timecode(self):
        timecode_text = self.ui_manager.timecodeInput.text()
        try:
            parts = timecode_text.split(':')
            if len(parts) != 4:
                raise ValueError("Invalid timecode format")
            hours, minutes, seconds, milliseconds = map(int, parts)
            total_milliseconds = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
            self.player_input.setPosition(total_milliseconds)
        except (ValueError, IndexError):
            self.main_window.show_status_message("Formato timecode non valido. Usa HH:MM:SS:ms.", error=True)

    def set_playback_rate(self, rate, player_type='input'):
        if player_type == 'input':
            player = self.player_input
            spinbox = self.ui_manager.speedSpinBox
            timer = self.main_window.reverseTimer
            fps_func = self.get_current_fps
        else:
            player = self.player_output
            spinbox = self.ui_manager.speedSpinBoxOutput
            timer = self.main_window.reverseTimerOutput
            fps_func = self.get_current_fps_output

        if rate == 0:
            rate = 1
            spinbox.setValue(1)

        if rate > 0:
            timer.stop()
            player.setPlaybackRate(float(rate))
            if player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
                player.play()
        else:  # rate < 0
            player.pause()
            player.setPlaybackRate(1.0)
            interval = int(1000 / (fps_func() * abs(rate)))
            if interval <= 0: interval = 20
            timer.start(interval)

    def set_volume(self, value, player_type='input'):
        if player_type == 'input':
            self.main_window.audioOutput.setVolume(value / 100.0)
        else:
            self.main_window.audioOutputOutput.setVolume(value / 100.0)

    def set_position(self, position, player_type='input'):
        if player_type == 'input':
            self.player_input.setPosition(position)
        else:
            self.player_output.setPosition(position)

    def get_current_fps(self):
        try:
            return VideoFileClip(self.main_window.videoPathLineEdit).fps
        except Exception as e:
            print(f"Error getting FPS: {e}")
            return 30

    def get_current_fps_output(self):
        try:
            return VideoFileClip(self.main_window.videoPathLineOutputEdit).fps
        except Exception as e:
            print(f"Error getting FPS for output: {e}")
            return 30
