# File: src/ui/CustumTextEdit.py (Versione con Dialogo di Ricerca)

from PyQt6.QtWidgets import (QTextEdit, QLineEdit, QDialog, QVBoxLayout,
                             QPushButton, QHBoxLayout, QApplication, QLabel) # Aggiunto QLabel
# Import necessari per la gestione del testo, Markdown e colori
from PyQt6.QtGui import (QTextCursor, QKeySequence, QTextCharFormat, QColor,
                         QTextDocument, QShortcut, QPalette) # Aggiunto QShortcut, QPalette
from PyQt6.QtCore import pyqtSignal, Qt

class CustomTextEdit(QTextEdit):
    """
    Un QTextEdit personalizzato con funzionalità aggiuntive:
    - Segnale per il cambio posizione cursore.
    - Ricerca (Ctrl+F) con dialogo separato, navigazione (F3/Shift+F3) ed evidenziazione.
    - Capacità di impostare ed esportare contenuto Markdown.
    - Tentativo di rendering Markdown su incolla *solo se sostituisce tutto*.
    """
    cursorPositionChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Crea un'istanza di QShortcut per la ricerca (Ctrl + F)
        self.searchShortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.searchShortcut.activated.connect(self.openSearchDialog)

        # Memorizza l'istanza del dialogo di ricerca per evitare duplicati
        self.search_dialog_instance = None

        # Stato della ricerca
        self.search_text = None
        self.current_search_index = -1
        self.search_results_cursors = []

    def setMarkdownContent(self, markdown_text):
        """
        Imposta il contenuto del QTextEdit interpretando la stringa fornita come Markdown.
        Questo convertirà il Markdown in formato Rich Text visualizzabile.
        """
        self.setMarkdown(markdown_text)
        self.cursorPositionChanged.emit() # Emetti segnale dopo modifica

    def toMarkdown(self, features=QTextDocument.MarkdownFeature.MarkdownDialectGitHub):
        """
        Restituisce il contenuto del QTextEdit come stringa Markdown.
        Utilizza il metodo nativo di QTextDocument.

        Args:
            features: Opzioni per specificare il dialetto Markdown (Default: GitHub).

        Returns:
            str: Il contenuto formattato come Markdown.
        """
        return super().toMarkdown(features)

    def keyPressEvent(self, event):
        """Gestisce gli eventi di pressione dei tasti."""
        super().keyPressEvent(event)
        self.cursorPositionChanged.emit()

        # Gestione navigazione ricerca (F3 / Shift+F3)
        if event.key() == Qt.Key.Key_F3:
            if self.search_results_cursors:
                if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                    self.find_previous_result()
                else:
                    self.find_next_result()
                # Aggiorna il contatore nel search dialog se è aperto
                if self.search_dialog_instance and not self.search_dialog_instance.isHidden():
                    self.search_dialog_instance.update_result_count_label()
                event.accept() # Consuma l'evento F3/Shift+F3


    def mousePressEvent(self, event):
        """Gestisce gli eventi di pressione del mouse."""
        super().mousePressEvent(event)
        self.cursorPositionChanged.emit()

    def insertFromMimeData(self, source):
        """
        Gestisce l'inserimento di dati dagli appunti (incolla).
        Tenta di renderizzare come Markdown solo se l'incolla sostituisce
        l'intero contenuto dell'editor. Altrimenti, incolla come testo semplice.
        """
        if source.hasText():
            text_to_paste = source.text()
            cursor = self.textCursor()

            is_replacing_all = (self.document().isEmpty() or
                                (cursor.hasSelection() and cursor.selection().toPlainText() == self.toPlainText()))

            if is_replacing_all:
                try:
                    self.setMarkdownContent(text_to_paste)
                except Exception as e:
                    print(f"Errore durante il rendering Markdown su incolla, incollando come testo semplice: {e}")
                    self.clear()
                    self.insertPlainText(text_to_paste)
                    self.cursorPositionChanged.emit() # Emetti solo se non fatto da setMarkdownContent
            else:
                self.insertPlainText(text_to_paste)
                self.cursorPositionChanged.emit()
        else:
            super().insertFromMimeData(source)
            self.cursorPositionChanged.emit() # Emetti anche per altri tipi di dati incollati

    def openSearchDialog(self):
        """
        Apre la finestra di dialogo di ricerca o la porta in primo piano
        se già esistente, impostando il focus e selezionando il testo.
        """
        if self.search_dialog_instance is None or not self.search_dialog_instance.isVisible():
            # Crea una nuova istanza se non esiste o non è visibile
            parent_widget = self.parent() # Ottieni il parent (TGeniusAI)
            self.search_dialog_instance = SearchDialog(self, parent_widget)
            # Collega il segnale `finished` per sapere quando viene chiuso
            self.search_dialog_instance.finished.connect(self.on_search_dialog_closed)
            self.search_dialog_instance.show()
        else:
            # Se esiste ed è visibile, portalo solo in primo piano
            self.search_dialog_instance.activateWindow()
            self.search_dialog_instance.raise_()

        # In entrambi i casi, imposta il focus e seleziona il testo nel QLineEdit
        self.search_dialog_instance.searchLineEdit.setFocus()
        self.search_dialog_instance.searchLineEdit.selectAll()

    def on_search_dialog_closed(self):
        """Slot chiamato quando il dialogo di ricerca viene chiuso."""
        # Rimuovi le evidenziazioni quando il dialogo viene chiuso
        self.clear_highlights()
        # Opzionale: resetta l'istanza del dialogo per ricrearlo la prossima volta
        # self.search_dialog_instance = None

    def highlight_search_results(self, search_text, case_sensitive=False):
        """
        Evidenzia tutte le corrispondenze nel testo e memorizza i cursori.
        Restituisce il numero di risultati trovati.
        """
        self.search_text = search_text
        self.current_search_index = -1
        self.search_results_cursors = []
        self.clear_highlights()

        if not search_text:
            return 0

        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor("yellow"))
        highlight_format.setForeground(QColor("black"))

        options = QTextDocument.FindFlag(0)
        if case_sensitive:
            options |= QTextDocument.FindFlag.FindCaseSensitively

        cursor = QTextCursor(self.document())
        while True:
            cursor = self.document().find(search_text, cursor, options)
            if cursor.isNull():
                break
            self.search_results_cursors.append(QTextCursor(cursor))
            cursor.mergeCharFormat(highlight_format)

        if self.search_results_cursors:
            self.current_search_index = 0
            self.move_to_result(self.current_search_index)

        # Aggiorna il contatore nel search dialog se è aperto
        if self.search_dialog_instance and not self.search_dialog_instance.isHidden():
            self.search_dialog_instance.update_result_count_label()

        return len(self.search_results_cursors)

    def find_next_result(self):
        """Passa alla prossima occorrenza trovata."""
        if not self.search_results_cursors:
            return

        self.current_search_index = (self.current_search_index + 1) % len(self.search_results_cursors)
        self.move_to_result(self.current_search_index)
        # Aggiorna il contatore nel search dialog se è aperto
        if self.search_dialog_instance and not self.search_dialog_instance.isHidden():
             self.search_dialog_instance.update_result_count_label()


    def find_previous_result(self):
        """Passa alla precedente occorrenza trovata."""
        if not self.search_results_cursors:
            return

        self.current_search_index -= 1
        if self.current_search_index < 0:
            self.current_search_index = len(self.search_results_cursors) - 1
        self.move_to_result(self.current_search_index)
        # Aggiorna il contatore nel search dialog se è aperto
        if self.search_dialog_instance and not self.search_dialog_instance.isHidden():
             self.search_dialog_instance.update_result_count_label()

    def move_to_result(self, index):
        """Sposta il cursore e la vista sul risultato all'indice specificato."""
        if 0 <= index < len(self.search_results_cursors):
            temp_cursor = self.search_results_cursors[index]
            self.setTextCursor(temp_cursor)
            self.ensureCursorVisible()

    def clear_highlights(self):
        """Cancella tutte le evidenziazioni di testo create dalla ricerca."""
        if not self.search_text:
             return

        # Formato di default per rimuovere lo sfondo
        default_format = QTextCharFormat()
        palette = self.palette()
        default_bg_color = palette.color(QPalette.ColorRole.Base) # Colore base del widget
        default_fg_color = palette.color(QPalette.ColorRole.Text) # Colore testo del widget
        default_format.setBackground(default_bg_color)
        default_format.setForeground(default_fg_color)

        # Applica il formato di default alle aree precedentemente evidenziate
        temp_cursor = QTextCursor(self.document())
        for saved_cursor in self.search_results_cursors:
            temp_cursor.setPosition(saved_cursor.selectionStart())
            temp_cursor.setPosition(saved_cursor.selectionEnd(), QTextCursor.MoveMode.KeepAnchor)
            # Applica il formato neutro per rimuovere l'evidenziazione specifica
            temp_cursor.setCharFormat(default_format)

        self.search_results_cursors = []
        self.current_search_index = -1
        self.search_text = None

        # Aggiorna il contatore nel search dialog se è aperto
        if self.search_dialog_instance and not self.search_dialog_instance.isHidden():
             self.search_dialog_instance.update_result_count_label()

    # Metodi getter per permettere a SearchDialog di leggere lo stato
    def get_current_search_index(self):
        return self.current_search_index

    def get_search_results_count(self):
        return len(self.search_results_cursors)

    def get_active_search_text(self):
        return self.search_text


class SearchDialog(QDialog):
    """
    Finestra di dialogo non modale per cercare nel testo,
    attivando la ricerca su Invio o click del pulsante "Cerca".
    """
    def __init__(self, textEdit: CustomTextEdit, parent=None):
        super().__init__(parent)
        self.textEdit = textEdit
        self.main_window = parent

        self.setWindowTitle("Cerca")
        self.setModal(False)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint) # Tool e sempre in primo piano

        # Prova ad applicare lo stile
        if self.main_window and hasattr(self.main_window, 'styleSheet'):
             try: self.setStyleSheet(self.main_window.styleSheet())
             except Exception as e: print(f"Warning: Impossibile applicare stylesheet: {e}")

        # Layout principale
        layout = QVBoxLayout(self) # Usiamo QVBoxLayout per aggiungere la label
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Layout per input e pulsanti di navigazione/cerca
        searchLayout = QHBoxLayout()

        self.searchLineEdit = QLineEdit()
        self.searchLineEdit.setPlaceholderText("Cerca...")
        # --- Ricerca su Invio ---
        self.searchLineEdit.returnPressed.connect(self.perform_search)
        searchLayout.addWidget(self.searchLineEdit)

        # Pulsante Cerca esplicito
        searchButton = QPushButton("Cerca")
        searchButton.setToolTip("Cerca (Invio)")
        searchButton.clicked.connect(self.perform_search)
        searchLayout.addWidget(searchButton)

        # Pulsante Precedente
        prevButton = QPushButton("↑")
        prevButton.setToolTip("Precedente (Shift+F3)")
        prevButton.setFixedSize(25, 25)
        prevButton.clicked.connect(self.textEdit.find_previous_result)
        searchLayout.addWidget(prevButton)

        # Pulsante Successivo
        nextButton = QPushButton("↓")
        nextButton.setToolTip("Successivo (F3)")
        nextButton.setFixedSize(25, 25)
        nextButton.clicked.connect(self.textEdit.find_next_result)
        searchLayout.addWidget(nextButton)

        layout.addLayout(searchLayout)

        # Label per mostrare il numero di risultati
        self.resultCountLabel = QLabel("Risultati: N/A")
        self.resultCountLabel.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.resultCountLabel)

        # Opzione Case Sensitive (Potrebbe essere aggiunta qui se necessaria)

        self.setLayout(layout)
        self.searchLineEdit.setFocus()
        self.adjustSize()

    def perform_search(self):
        """Esegue la ricerca quando viene premuto Invio o il pulsante Cerca."""
        search_text = self.searchLineEdit.text()
        # case_sensitive = self.caseSensitiveCheck.isChecked() # Se aggiungi checkbox
        if search_text:
            num_results = self.textEdit.highlight_search_results(search_text) # case_sensitive)
            self.update_result_count_label() # Aggiorna subito dopo la ricerca
            # Aggiorna stile input se non ci sono risultati
            if num_results == 0:
                self.searchLineEdit.setStyleSheet("background-color: #FFDDDD;") # Rosso chiaro
            else:
                self.searchLineEdit.setStyleSheet("") # Stile default
        else:
            self.textEdit.clear_highlights() # Cancella se il campo è vuoto
            self.update_result_count_label() # Aggiorna anche quando cancella
            self.searchLineEdit.setStyleSheet("") # Stile default

    def update_result_count_label(self):
        """Aggiorna la label con il numero di risultati trovati."""
        # Legge lo stato direttamente da textEdit usando i metodi getter
        if self.textEdit.get_active_search_text() is None:
             self.resultCountLabel.setText("Risultati: N/A")
        elif self.textEdit.get_search_results_count() == 0:
             self.resultCountLabel.setText("Risultati: 0")
        else:
             current = self.textEdit.get_current_search_index() + 1
             total = self.textEdit.get_search_results_count()
             self.resultCountLabel.setText(f"Risultati: {current}/{total}")

    def closeEvent(self, event):
        """Operazioni da eseguire alla chiusura del dialogo."""
        # La pulizia viene fatta da on_search_dialog_closed in CustomTextEdit
        super().closeEvent(event)

    def keyPressEvent(self, event):
        """Gestisce la pressione di tasti nel dialogo."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_F3: # Inoltra F3 e Shift+F3 all'editor
             if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                  self.textEdit.find_previous_result()
             else:
                  self.textEdit.find_next_result()
             # Aggiorna la label dei risultati nel dialogo
             self.update_result_count_label()
             event.accept()
        else:
            super().keyPressEvent(event)