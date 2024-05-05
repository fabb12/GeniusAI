import sys
from PyQt6.QtCore import QThread, pyqtSignal, QUrl
class VideoLoaderThread(QThread):
    videoLoaded = pyqtSignal(str, str)  # Passa video_path e video_title al main thread

    def __init__(self, video_path, video_title='Video Track'):
        super().__init__()
        self.video_path = video_path
        self.video_title = video_title

    def run(self):
        # Qui, assumiamo che il setSource e altre operazioni siano thread-safe,
        # altrimenti queste operazioni dovrebbero essere delegate al thread principale.
        self.videoLoaded.emit(self.video_path, self.video_title)
