from PyQt6.QtCore import QThread, pyqtSignal
from youtube_comment_downloader.downloader import YoutubeCommentDownloader
import json

class CommentDownloader(QThread):
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url, output_path, parent=None):
        super().__init__(parent)
        self.url = url
        self.output_path = output_path
        self.running = True

    def run(self):
        try:
            self.progress.emit(10, "Avvio del download dei commenti...")
            downloader = YoutubeCommentDownloader()
            comments = downloader.get_comments_from_url(self.url, sort_by=0)

            if not self.running:
                return

            self.progress.emit(50, "Salvataggio dei commenti in corso...")
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(list(comments), f, ensure_ascii=False, indent=4)

            if self.running:
                self.progress.emit(100, "Download completato.")
                self.completed.emit(self.output_path)
        except Exception as e:
            if self.running:
                self.error.emit(str(e))

    def stop(self):
        self.running = False
