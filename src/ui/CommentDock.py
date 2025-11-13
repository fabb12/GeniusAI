from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import pyqtSignal
from src.ui.CustomDock import CustomDock
from src.ui.CustomTextEdit import CustomTextEdit
import json

class CommentDock(CustomDock):
    sendToChat = pyqtSignal(str)

    def __init__(self, title="Commenti Video", closable=True, parent=None):
        super().__init__(title, closable=closable, parent=parent)
        self._setup_ui()

    def _setup_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        self.comment_area = CustomTextEdit(self)
        self.comment_area.setReadOnly(True)
        self.comment_area.setPlaceholderText("I commenti del video appariranno qui...")
        main_layout.addWidget(self.comment_area)

        button_layout = QHBoxLayout()
        self.load_button = QPushButton("Carica Commenti")
        self.load_button.clicked.connect(self.load_comments)
        button_layout.addWidget(self.load_button)

        self.send_to_chat_button = QPushButton("Invia alla Chat")
        self.send_to_chat_button.clicked.connect(self.send_comments_to_chat)
        button_layout.addWidget(self.send_to_chat_button)

        main_layout.addLayout(button_layout)
        self.addWidget(main_widget)

    def load_comments(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Carica File Commenti",
            "",
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    comments = json.load(f)

                self.comment_area.clear()
                for comment in comments:
                    self.comment_area.append(f"<b>{comment['author']}</b>: {comment['text']}\n")

            except Exception as e:
                QMessageBox.critical(self, "Errore di Caricamento", f"Impossibile caricare il file dei commenti:\n{e}")

    def send_comments_to_chat(self):
        comments_text = self.comment_area.toPlainText()
        if comments_text.strip():
            self.sendToChat.emit(comments_text)
        else:
            QMessageBox.warning(self, "Nessun Commento", "Nessun commento da inviare alla chat.")
