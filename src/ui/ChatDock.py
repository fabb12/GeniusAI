# File: src/ui/ChatDock.py

import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QHBoxLayout, QMenu, QFileDialog, QMessageBox
from PyQt6.QtCore import pyqtSignal, Qt
from src.ui.CustomDock import CustomDock
from src.ui.CustomTextEdit import CustomTextEdit

class ChatDock(CustomDock):
    """
    A dock widget that provides a chat interface to interact with summaries.
    """
    sendMessage = pyqtSignal(str)  # Signal to send the user's query

    def __init__(self, title="Chat Riassunto", closable=True, parent=None):
        super().__init__(title, closable=closable, parent=parent)
        self.setToolTip("Interroga il riassunto attualmente selezionato.")
        self.project_path = None
        self._setup_ui()

    def set_project_path(self, path):
        """Sets the current project path to enable project-specific actions."""
        self.project_path = path

    def _setup_ui(self):
        """Sets up the UI components of the dock."""
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 1. Chat History Display
        self.history_text_edit = CustomTextEdit(self)
        self.history_text_edit.setReadOnly(True)
        self.history_text_edit.setPlaceholderText("La cronologia della chat apparirà qui...")
        self.history_text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_text_edit.customContextMenuRequested.connect(self._show_context_menu)
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

    def _show_context_menu(self, position):
        """Shows the context menu for the chat history."""
        context_menu = QMenu(self)
        save_action = context_menu.addAction("Salva Chat")
        load_action = context_menu.addAction("Carica Chat")
        action = context_menu.exec(self.history_text_edit.mapToGlobal(position))

        if action == save_action:
            self._save_chat_history()
        elif action == load_action:
            self._load_chat_history()

    def _load_chat_history(self):
        """Opens a file dialog to load a chat history from the project's 'chat' folder."""
        if not self.project_path:
            QMessageBox.warning(self, "Nessun Progetto Attivo", "Per favore, apri o crea un progetto prima di caricare una chat.")
            return

        chat_dir = os.path.join(self.project_path, "chat")
        if not os.path.isdir(chat_dir):
            QMessageBox.information(self, "Nessuna Chat Salvata", "Nessuna chat salvata trovata per questo progetto.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Carica Cronologia Chat",
            chat_dir,
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    chat_content = f.read()
                # Carica come testo semplice, non HTML, perché è così che viene salvato
                self.history_text_edit.setPlainText(chat_content)
                QMessageBox.information(self, "Successo", "Cronologia chat caricata con successo.")
            except Exception as e:
                QMessageBox.critical(self, "Errore di Caricamento", f"Impossibile caricare il file della chat:\n{e}")

    def _save_chat_history(self):
        """Opens a file dialog to save the chat history within the project's 'chat' folder."""
        if not self.history_text_edit.toPlainText().strip():
            return  # Do nothing if chat is empty

        if not self.project_path:
            QMessageBox.warning(self, "Nessun Progetto Attivo", "Per favore, apri o crea un progetto prima di salvare una chat.")
            return

        chat_dir = os.path.join(self.project_path, "chat")
        os.makedirs(chat_dir, exist_ok=True)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salva Cronologia Chat",
            chat_dir,  # Default directory
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.history_text_edit.toPlainText())
                QMessageBox.information(self, "Successo", f"Chat salvata con successo in:\n{os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Errore di Salvataggio", f"Impossibile salvare il file della chat:\n{e}")
