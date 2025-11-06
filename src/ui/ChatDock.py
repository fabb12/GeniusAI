# File: src/ui/ChatDock.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QHBoxLayout
from PyQt6.QtCore import pyqtSignal
from src.ui.CustomDock import CustomDock

class ChatDock(CustomDock):
    """
    A dock widget that provides a chat interface to interact with summaries.
    """
    sendMessage = pyqtSignal(str)  # Signal to send the user's query

    def __init__(self, title="Chat Riassunto", closable=True, parent=None):
        super().__init__(title, closable=closable, parent=parent)
        self.setToolTip("Interroga il riassunto attualmente selezionato.")
        self._setup_ui()

    def _setup_ui(self):
        """Sets up the UI components of the dock."""
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 1. Chat History Display
        self.history_text_edit = QTextEdit()
        self.history_text_edit.setReadOnly(True)
        self.history_text_edit.setPlaceholderText("La cronologia della chat apparirà qui...")
        main_layout.addWidget(self.history_text_edit)

        # 2. User Input Area
        input_layout = QHBoxLayout()
        self.input_line_edit = QLineEdit()
        self.input_line_edit.setPlaceholderText("Scrivi la tua domanda qui...")
        self.input_line_edit.returnPressed.connect(self._on_send_clicked)
        input_layout.addWidget(self.input_line_edit)

        self.send_button = QPushButton("Invia")
        self.send_button.clicked.connect(self._on_send_clicked)
        input_layout.addWidget(self.send_button)

        main_layout.addLayout(input_layout)
        self.addWidget(main_widget)

    def _on_send_clicked(self):
        """Handles the send button click or return press in the input field."""
        query = self.input_line_edit.text().strip()
        if query:
            self.add_message("User", query)
            self.sendMessage.emit(query)
            self.input_line_edit.clear()

    def add_message(self, sender, message):
        """
        Adds a message to the chat history, formatting it based on the sender.
        """
        if sender.lower() == "user":
            formatted_message = f'<p style="color: #a9d18e;"><b>Tu:</b><br>{message}</p>'
        else: # AI or System
            # Basic markdown-to-HTML conversion for simple formatting like bold and lists
            import markdown
            html_message = markdown.markdown(message)
            formatted_message = f'<p style="color: #87ceeb;"><b>AI:</b></p>{html_message}'

        self.history_text_edit.append(formatted_message)

    def clear_chat(self):
        """Clears the chat history."""
        self.history_text_edit.clear()
