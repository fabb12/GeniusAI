# File: src/ui/CustumTextEdit.py (Versione con Dialogo di Ricerca)

from PyQt6.QtWidgets import (QTextEdit, QLineEdit, QDialog, QVBoxLayout,
                             QPushButton, QHBoxLayout, QApplication, QLabel, QCheckBox, QMessageBox, QComboBox)
# Import necessari per la gestione del testo, Markdown e colori
from PyQt6.QtGui import (QTextCursor, QKeySequence, QTextCharFormat, QColor,
                         QTextDocument, QShortcut, QPalette, QFont) # Aggiunto QFont
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QSettings
import re

class CustomTextEdit(QTextEdit):
    """
    Un QTextEdit personalizzato con funzionalità aggiuntive:
    - Segnale per il cambio posizione cursore.
    - Ricerca (Ctrl+F) con dialogo separato, navigazione (F3/Shift+F3) ed evidenziazione.
    - Capacità di impostare ed esportare contenuto Markdown.
    - Tentativo di rendering Markdown su incolla *solo se sostituisce tutto*.
    - Zoom del testo con Ctrl + rotellina del mouse.
    """
    cursorPositionChanged = pyqtSignal()
    timestampDoubleClicked = pyqtSignal(float)
    fontSizeChanged = pyqtSignal(int) # Nuovo segnale

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
        self.last_search_options = {}

    def wheelEvent(self, event):
        """
        Gestisce l'evento della rotellina del mouse per lo zoom del testo.
        """
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ottieni la direzione dello scroll
            angle = event.angleDelta().y()
            current_font = self.font()
            current_size = current_font.pointSize()

            if angle > 0:
                # Scroll in su, aumenta la dimensione del font
                current_font.setPointSize(current_size + 1)
            elif angle < 0:
                # Scroll in giù, diminuisci la dimensione del font (con un minimo)
                if current_size > 1:
                    current_font.setPointSize(current_size - 1)

            self.setFont(current_font)
            self.fontSizeChanged.emit(current_font.pointSize())
            event.accept()
        else:
            super().wheelEvent(event)

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

    def mouseDoubleClickEvent(self, event):
        """
        Gestisce il doppio clic del mouse per cercare un timestamp e sincronizzare il video.
        Identifica quale timecode è stato cliccato, anche se ce ne sono multipli sulla stessa riga.
        """
        super().mouseDoubleClickEvent(event)

        cursor = self.cursorForPosition(event.pos())
        block_text = cursor.block().text()
        click_pos_in_block = cursor.positionInBlock()

        # Regex per trovare tutti i possibili formati di timecode
        timecode_pattern = re.compile(r'\[((?:\d+:)?\d+:\d+(?:\.\d)?)\]')

        for match in timecode_pattern.finditer(block_text):
            start_pos, end_pos = match.span(0)

            # Controlla se la posizione del clic è all'interno di questo specifico timecode
            if start_pos <= click_pos_in_block < end_pos:
                time_str = match.group(1)
                parts = time_str.split(':')
                total_seconds = 0
                try:
                    if len(parts) == 3:  # Formato HH:MM:SS.d
                        hours = int(parts[0])
                        minutes = int(parts[1])
                        seconds = float(parts[2])
                        total_seconds = (hours * 3600) + (minutes * 60) + seconds
                    elif len(parts) == 2:  # Formato MM:SS.d
                        minutes = int(parts[0])
                        seconds = float(parts[1])
                        total_seconds = (minutes * 60) + seconds

                    if total_seconds >= 0:
                        self.timestampDoubleClicked.emit(total_seconds)
                        return  # Esci dopo aver trovato e processato il timecode corretto
                except ValueError:
                    # Se il parsing fallisce, continua a cercare altri match
                    continue

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
            self.search_dialog_instance.show()
        else:
            # Se esiste ed è visibile, portalo solo in primo piano
            self.search_dialog_instance.activateWindow()
            self.search_dialog_instance.raise_()

        # Forza il focus e seleziona il testo. L'uso del timer aiuta a garantire che
        # queste operazioni vengano eseguite dopo che il dialogo è completamente visibile.
        self.search_dialog_instance.activateWindow()
        self.search_dialog_instance.raise_()
        QTimer.singleShot(50, self.search_dialog_instance.searchComboBox.lineEdit().setFocus)
        QTimer.singleShot(50, self.search_dialog_instance.searchComboBox.lineEdit().selectAll)

    def highlight_search_results(self, search_text, case_sensitive=False, whole_words=False):
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
        highlight_format.setUnderlineColor(QColor("orange"))
        highlight_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)

        options = QTextDocument.FindFlag(0)
        if case_sensitive:
            options |= QTextDocument.FindFlag.FindCaseSensitively
        if whole_words:
            options |= QTextDocument.FindFlag.FindWholeWords

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

        # Memorizza le opzioni di ricerca per un uso futuro (es. replace all)
        self.last_search_options = {
            'search_text': search_text,
            'case_sensitive': case_sensitive,
            'whole_words': whole_words
        }

        return len(self.search_results_cursors)

    def replace_current_and_find_next(self, replace_text):
        """
        Sostituisce l'occorrenza attualmente selezionata e passa alla successiva.
        """
        if not self.search_results_cursors or self.current_search_index < 0:
            return

        # Sostituisce il testo usando il cursore memorizzato
        cursor = self.search_results_cursors[self.current_search_index]
        cursor.insertText(replace_text)

        # Riesegue la ricerca per aggiornare i cursori e le evidenziazioni
        self.highlight_search_results(
            self.last_search_options.get('search_text', ''),
            self.last_search_options.get('case_sensitive', False),
            self.last_search_options.get('whole_words', False)
        )

        # Non si sposta automaticamente al successivo, l'utente può cliccare "Cerca" o "Sostituisci" di nuovo.
        # Se vogliamo che vada al successivo, dovremmo trovare il prossimo risultato valido dopo la posizione corrente.
        # Per ora, la riesecuzione della ricerca è sufficiente.
        self.update_result_count_label()


    def replace_all_results(self, replace_text):
        """
        Sostituisce tutte le occorrenze trovate con il testo di sostituzione.
        Lavora a ritroso per evitare di invalidare le posizioni delle occorrenze successive.
        """
        if not self.search_text:
            return 0

        # Ottieni le opzioni di ricerca dall'ultima ricerca effettuata
        options = QTextDocument.FindFlag(0)
        if self.last_search_options.get('case_sensitive', False):
            options |= QTextDocument.FindFlag.FindCaseSensitively
        if self.last_search_options.get('whole_words', False):
            options |= QTextDocument.FindFlag.FindWholeWords

        # Aggiungi l'opzione per cercare all'indietro
        options |= QTextDocument.FindFlag.FindBackward

        # Inizia la ricerca dalla fine del documento
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)

        replacements_count = 0
        self.document().undoStack().beginMacro("Sostituisci Tutto")

        while True:
            # Trova l'occorrenza precedente
            cursor = self.document().find(self.search_text, cursor, options)
            if cursor.isNull():
                break  # Nessun'altra occorrenza trovata

            # Sostituisci il testo selezionato
            cursor.insertText(replace_text)
            replacements_count += 1

        self.document().undoStack().endMacro()

        # Dopo la sostituzione, puliamo le evidenziazioni ma manteniamo la ricerca attiva
        self.clear_highlights(keep_search_term=True)
        # Eseguiamo di nuovo l'evidenziazione per mostrare che non ci sono più risultati
        self.highlight_search_results(
            self.search_text,
            self.last_search_options.get('case_sensitive', False),
            self.last_search_options.get('whole_words', False)
        )
        self.update_result_count_label()

        return replacements_count

    def update_result_count_label(self):
        """
        Funzione helper per aggiornare il contatore nel dialogo di ricerca, se esiste.
        """
        if self.search_dialog_instance and self.search_dialog_instance.isVisible():
            self.search_dialog_instance.update_result_count_label()


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

    def clear_highlights(self, keep_search_term=False):
        """
        Rimuove l'evidenziazione della ricerca (sottolineatura ondulata).
        Se `keep_search_term` è True, non cancella il termine di ricerca attivo.
        """
        # Formato per rimuovere la sottolineatura
        clear_format = QTextCharFormat()
        clear_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.NoUnderline)

        # Applica il formato di pulizia solo ai risultati della ricerca memorizzati
        # È più sicuro iterare su una copia se la lista viene modificata altrove
        for cursor in list(self.search_results_cursors):
            cursor.mergeCharFormat(clear_format)

        # Pulisce lo stato della ricerca
        self.search_results_cursors = []
        self.current_search_index = -1

        if not keep_search_term:
            self.search_text = None

        # Aggiorna l'etichetta nel dialogo di ricerca, se esiste
        if self.search_dialog_instance and self.search_dialog_instance.isVisible():
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

        self.searchComboBox = QComboBox()
        self.searchComboBox.setEditable(True)
        self.searchComboBox.setPlaceholderText("Cerca...")
        self.searchComboBox.lineEdit().returnPressed.connect(self.perform_search)
        self.load_search_history()
        searchLayout.addWidget(self.searchComboBox)

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

        # Layout per opzioni e risultati
        options_layout = QHBoxLayout()

        # Checkbox per ricerca case-sensitive
        self.caseSensitiveCheck = QCheckBox("Maiuscole/minuscole")
        self.caseSensitiveCheck.setToolTip("Attiva per distinguere tra maiuscole e minuscole nella ricerca")
        options_layout.addWidget(self.caseSensitiveCheck)

        # Checkbox per ricerca parola intera
        self.wholeWordCheck = QCheckBox("Parola intera")
        self.wholeWordCheck.setToolTip("Cerca solo parole intere")
        options_layout.addWidget(self.wholeWordCheck)

        options_layout.addStretch() # Spinge la label a destra

        # Label per mostrare il numero di risultati
        self.resultCountLabel = QLabel("Risultati:")
        self.resultCountLabel.setAlignment(Qt.AlignmentFlag.AlignRight)
        options_layout.addWidget(self.resultCountLabel)

        layout.addLayout(options_layout)

        # --- Layout per la sostituzione ---
        replace_layout = QHBoxLayout()
        self.replaceLineEdit = QLineEdit()
        self.replaceLineEdit.setPlaceholderText("Sostituisci con...")
        replace_layout.addWidget(self.replaceLineEdit)

        self.replaceButton = QPushButton("Sostituisci")
        self.replaceButton.setToolTip("Sostituisce l'occorrenza corrente e trova la successiva")
        self.replaceButton.clicked.connect(self.replace_current)
        replace_layout.addWidget(self.replaceButton)

        self.replaceAllButton = QPushButton("Sostituisci Tutto")
        self.replaceAllButton.setToolTip("Sostituisce tutte le occorrenze nel documento")
        self.replaceAllButton.clicked.connect(self.replace_all)
        replace_layout.addWidget(self.replaceAllButton)

        layout.addLayout(replace_layout)

        self.setLayout(layout)
        self.searchLineEdit.setFocus()
        self.adjustSize()

        # Collega le checkbox per rieseguire la ricerca quando il loro stato cambia
        self.caseSensitiveCheck.stateChanged.connect(self.perform_search)
        self.wholeWordCheck.stateChanged.connect(self.perform_search)
        self.searchComboBox.currentIndexChanged.connect(self.combobox_selection_changed)

    def load_search_history(self):
        """Carica la cronologia delle ricerche da QSettings."""
        settings = QSettings()
        history = settings.value("SearchHistory", [], type=list)
        self.searchComboBox.addItems(history)

    def save_search_history(self, term):
        """Salva la cronologia delle ricerche in QSettings."""
        if not term:
            return

        settings = QSettings()
        history = settings.value("SearchHistory", [], type=list)

        # Rimuovi il termine se già presente per riposizionarlo in cima
        if term in history:
            history.remove(term)

        # Inserisci il nuovo termine all'inizio
        history.insert(0, term)

        # Limita la cronologia a 10 elementi
        history = history[:10]

        settings.setValue("SearchHistory", history)

        # Aggiorna il ComboBox
        self.searchComboBox.blockSignals(True)
        self.searchComboBox.clear()
        self.searchComboBox.addItems(history)
        self.searchComboBox.setCurrentText(term)
        self.searchComboBox.blockSignals(False)

    def combobox_selection_changed(self, index):
        """
        Quando un elemento viene selezionato dalla cronologia,
        esegue immediatamente la ricerca.
        """
        if index != -1: # Assicurati che sia una selezione valida
             self.perform_search()

    def replace_current(self):
        """
        Chiama il metodo di sostituzione nell'editor per l'occorrenza corrente.
        """
        replace_text = self.replaceLineEdit.text()
        self.textEdit.replace_current_and_find_next(replace_text)

    def replace_all(self):
        """
        Chiama il metodo di sostituzione di tutte le occorrenze nell'editor
        e mostra un messaggio con il numero di sostituzioni effettuate.
        """
        replace_text = self.replaceLineEdit.text()
        if not self.textEdit.get_active_search_text():
            QMessageBox.warning(self, "Attenzione", "Esegui prima una ricerca prima di sostituire.")
            return

        num_replaced = self.textEdit.replace_all_results(replace_text)
        QMessageBox.information(self, "Sostituisci Tutto", f"{num_replaced} occorrenze sono state sostituite.")
        self.update_result_count_label() # La ricerca viene pulita, quindi aggiorniamo la label


    def perform_search(self):
        """Esegue la ricerca e aggiorna la cronologia."""
        search_text = self.searchComboBox.currentText()
        case_sensitive = self.caseSensitiveCheck.isChecked()
        whole_words = self.wholeWordCheck.isChecked()

        if search_text:
            self.save_search_history(search_text) # Salva il termine cercato
            num_results = self.textEdit.highlight_search_results(search_text, case_sensitive, whole_words)

            # Aggiorna stile input se non ci sono risultati
            if num_results == 0:
                self.searchComboBox.setStyleSheet("background-color: #FFD580;")
            else:
                self.searchComboBox.setStyleSheet("")
        else:
            self.textEdit.clear_highlights()
            self.searchComboBox.setStyleSheet("")

        self.update_result_count_label()

    def update_result_count_label(self):
        """Aggiorna la label con il numero di risultati trovati, mostrando la posizione corrente."""
        search_text = self.textEdit.get_active_search_text()
        num_results = self.textEdit.get_search_results_count()
        current_index = self.textEdit.get_current_search_index()

        if not search_text:
            self.resultCountLabel.setText("Risultati:")
            return

        if num_results == 0:
            self.resultCountLabel.setText("Risultati: 0")
        else:
            # L'indice è basato su 0, quindi aggiungiamo 1 per la visualizzazione
            self.resultCountLabel.setText(f"Risultati: {current_index + 1} di {num_results}")

    def closeEvent(self, event):
        """Sovrascrive l'evento di chiusura per garantire la pulizia."""
        self.textEdit.clear_highlights()
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