from PyQt6.QtWidgets import QMainWindow

from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtGui import QIcon
from src.config import get_resource


class PlayerManager:
    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window

    def setup_connections(self):
        mw = self.main_window
        mw.playButton.clicked.connect(self.togglePlayPause)
        mw.stopButton.clicked.connect(self.stopVideo)
        mw.rewindButton.clicked.connect(self.rewind5Seconds)
        mw.forwardButton.clicked.connect(self.forward5Seconds)

    def togglePlayPause(self):
        mw = self.main_window
        rate = mw.speedSpinBox.value()
        if rate < 0:
            if mw.reverseTimer.isActive():
                mw.reverseTimer.stop()
                mw.playButton.setIcon(QIcon(get_resource("play.png")))
            else:
                interval = int(1000 / (mw.get_current_fps() * abs(rate)))
                if interval <= 0: interval = 20
                mw.reverseTimer.start(interval)
                mw.playButton.setIcon(QIcon(get_resource("pausa.png")))
        else:
            from PyQt6.QtMultimedia import QMediaPlayer
            if mw.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                mw.player.pause()
                mw.playButton.setIcon(QIcon(get_resource("play.png")))
            else:
                mw.player.play()
                mw.playButton.setIcon(QIcon(get_resource("pausa.png")))

    def stopVideo(self):
        self.main_window.player.stop()

    def rewind5Seconds(self):
        current_position = self.main_window.player.position()
        new_position = max(0, current_position - 5000)
        self.main_window.player.setPosition(new_position)

    def forward5Seconds(self):
        current_position = self.main_window.player.position()
        new_position = current_position + 5000
        self.main_window.player.setPosition(new_position)
