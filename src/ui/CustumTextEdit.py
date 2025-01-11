from PyQt6.QtWidgets import QTextEdit, QLineEdit, QDialog, QVBoxLayout, QPushButton
from PyQt6.QtGui import QTextCursor, QKeySequence, QTextCharFormat, QColor
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QShortcut

class CustomTextEdit(QTextEdit):
    cursorPositionChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Crea un'istanza di QShortcut per la ricerca (Ctrl + F)
        self.searchShortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.searchShortcut.activated.connect(self.openSearchDialog)

        # Per memorizzare lo stato di ricerca
        self.search_text = None

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        self.cursorPositionChanged.emit()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.cursorPositionChanged.emit()

    def insertFromMimeData(self, source):
        if source.hasText():
            plain_text = source.text()
            self.insertPlainText(plain_text)
        else:
            super().insertFromMimeData(source)
        self.cursorPositionChanged.emit()

    def openSearchDialog(self):
        """Apre la finestra di dialogo per cercare nel testo."""
        searchDialog = SearchDialog(self, self.parentWidget())  # Passa l'istanza principale
        searchDialog.exec()

    def highlight_search_results(self, search_text):
        """Evidenzia tutte le corrispondenze nel testo."""
        # Cancella le evidenziazioni precedenti
        self.clear_highlights()

        # Formato per evidenziare il testo
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor("red"))

        # Imposta il cursore all'inizio del documento
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        # Cerca tutte le occorrenze della stringa
        search_results = []
        while True:
            cursor = self.document().find(search_text, cursor)
            if cursor.isNull():
                break
            search_results.append(cursor)
            # Evidenzia il testo trovato
            cursor.mergeCharFormat(highlight_format)

        return search_results

    def clear_highlights(self):
        """Cancella tutte le evidenziazioni di testo."""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        # Cancella il formato speciale per tutto il testo
        self.selectAll()
        self.setTextBackgroundColor(QColor(Qt.GlobalColor.transparent))
        self.moveCursor(QTextCursor.MoveOperation.Start)  # Resetta il cursore


class SearchDialog(QDialog):
    def __init__(self, textEdit, main_window, parent=None):
        super().__init__(parent)
        self.textEdit = textEdit
        self.main_window = main_window  # Salva il riferimento alla finestra principale

        self.setWindowTitle("Cerca nel testo")
        self.setModal(True)

        # Applica lo stesso foglio di stile della finestra principale
        self.setStyleSheet(self.main_window.styleSheet())

        # Layout principale
        layout = QVBoxLayout()

        # Campo di input per la stringa di ricerca
        self.searchLineEdit = QLineEdit()
        self.searchLineEdit.setPlaceholderText("Inserisci la stringa da cercare...")
        layout.addWidget(self.searchLineEdit)

        # Pulsante per cercare
        searchButton = QPushButton("Cerca")
        searchButton.clicked.connect(self.search)
        layout.addWidget(searchButton)

        self.setLayout(layout)

    def search(self):
        search_text = self.searchLineEdit.text().strip()
        if search_text:
            self.textEdit.highlight_search_results(search_text)
