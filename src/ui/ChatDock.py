# File: src/ui/ChatDock.py

import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QHBoxLayout, QMenu, QFileDialog, QMessageBox, QInputDialog
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
        self.font_family = "Arial"  # Default font family
        self.font_size = 14        # Default font size
        self.current_context_content = "" # To store the context text
        self.default_title = title
        self._setup_ui()

    def update_context(self, context_name, context_content):
        """Updates the chat's context and title based on the selected tab."""
        self.current_context_content = context_content
        if context_name:
            self.setTitle(context_name)
        else:
            self.setTitle(self.default_title)

    def set_font(self, font_family, font_size):
        """Sets the font for the chat history text edit."""
        self.font_family = font_family
        self.font_size = font_size

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
        Uses <div> for block-level elements to avoid extra margins from <p>.
        """
        cursor = self.history_text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        # Ensure we start on a new line if the history is not empty
        if not self.history_text_edit.toPlainText().strip() == "":
            cursor.insertBlock()

        if sender.lower() == "user":
            # User messages are on a single line, with "Tu:" and the message together.
            html = f"""
            <div style="font-family: {self.font_family}; font-size: {self.font_size}pt;">
                <span style="color: #a9d18e;"><b>Tu:</b> </span>
                <span>{message}</span>
            </div>
            """
        else:  # AI or System
            # AI messages have "AI:" on one line and the content on the next.
            import markdown
            html_message = markdown.markdown(message, extensions=['fenced_code', 'tables'])
            html = f"""
            <div style="font-family: {self.font_family}; font-size: {self.font_size}pt;">
                <span style="color: #87ceeb;"><b>AI:</b></span>
            </div>
            {html_message}
            """

        cursor.insertHtml(html.strip())

        # Ensure the view scrolls to the bottom
        self.history_text_edit.ensureCursorVisible()

    def clear_chat(self):
        """Clears the chat history."""
        self.history_text_edit.clear()

    def _show_context_menu(self, position):
        """Shows the context menu for the chat history."""
        context_menu = QMenu(self)
        save_action = context_menu.addAction("Salva Chat")
        load_action = context_menu.addAction("Carica Chat")
        context_menu.addSeparator()
        reset_action = context_menu.addAction("Reset Chat")

        action = context_menu.exec(self.history_text_edit.mapToGlobal(position))

        if action == save_action:
            self._save_chat_history()
        elif action == load_action:
            self._load_chat_history()
        elif action == reset_action:
            self.clear_chat()

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
            "HTML Files (*.html);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    chat_content = f.read()
                # Load as HTML to preserve formatting
                self.history_text_edit.setHtml(chat_content)
                QMessageBox.information(self, "Successo", "Cronologia chat caricata con successo.")
            except Exception as e:
                QMessageBox.critical(self, "Errore di Caricamento", f"Impossibile caricare il file della chat:\n{e}")

    def _save_chat_history(self):
        """Asks for a filename and saves the chat history as an HTML file in the project's 'chat' folder."""
        if not self.history_text_edit.toPlainText().strip():
            return  # Do nothing if chat is empty

        if not self.project_path:
            QMessageBox.warning(self, "Nessun Progetto Attivo", "Per favore, apri o crea un progetto prima di salvare una chat.")
            return

        file_name, ok = QInputDialog.getText(self, "Salva Chat", "Inserisci il nome del file:")
        if not ok or not file_name.strip():
            return  # User cancelled or entered empty name

        chat_dir = os.path.join(self.project_path, "chat")
        os.makedirs(chat_dir, exist_ok=True)

        # Ensure the filename ends with .html
        if not file_name.lower().endswith('.html'):
            file_name += '.html'

        file_path = os.path.join(chat_dir, file_name)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.history_text_edit.toHtml())
            QMessageBox.information(self, "Successo", f"Chat salvata con successo in:\n{file_name}")
        except Exception as e:
            QMessageBox.critical(self, "Errore di Salvataggio", f"Impossibile salvare il file della chat:\n{e}")
