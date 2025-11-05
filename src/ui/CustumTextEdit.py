# File: src/ui/CustumTextEdit.py (Versione con Dialogo di Ricerca)

from PyQt6.QtWidgets import (QTextEdit, QLineEdit, QDialog, QVBoxLayout, QGridLayout,
                             QPushButton, QHBoxLayout, QApplication, QLabel, QCheckBox, QMessageBox, QComboBox)
# Import necessari per la gestione del testo, Markdown e colori
from PyQt6.QtGui import (QTextCursor, QKeySequence, QTextCharFormat, QColor,
                         QTextDocument, QPalette, QFont, QPixmap, QTextImageFormat) # Aggiunto QFont
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QSettings, QUrl
from PyQt6.QtWidgets import QMenu
import re
import time
import base64
from .ImageCropDialog import ImageCropDialog
from services.utils import get_frame_at_timestamp
from .ImageSizeDialog import ResizedImageDialog

class CustomTextDocument(QTextDocument):
    def loadResource(self, type, name):
        """
        Loads the resource for the given type and name.
        This is overridden to handle the custom 'frame://' scheme.
        """
        if type == QTextDocument.ResourceType.ImageResource and name.scheme() == 'frame':
            # The resource is already in the document's cache, added via addResource.
            # The base implementation will retrieve it for us.
            return super().loadResource(type, name)
        return super().loadResource(type, name)

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
    insert_frame_requested = pyqtSignal(float, int)
    frame_edit_requested = pyqtSignal(str)
    fontSizeChanged = pyqtSignal(int) # Nuovo segnale

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDocument(CustomTextDocument(self))
        # Memorizza l'istanza del dialogo di ricerca per evitare duplicati
        self.search_dialog_instance = None

        # Stato della ricerca
        self.search_text = None
        self.current_search_index = -1
        self.search_results_cursors = []
        self.last_search_options = {}
        self.resizing_image = None
        self.resizing_start_pos = None
        self.image_metadata = {}

    def insert_image_with_metadata(self, displayed_image, width, height, video_path, timestamp, original_image=None):
        """
        Inserts an image as a document resource and stores its metadata.
        The video path is base64 encoded to avoid invalid characters in the URI.
        """
        # Codifica il percorso del video in Base64 per garantire un URI valido
        safe_video_path = base64.urlsafe_b64encode(video_path.encode()).decode()
        image_name = f"frame_{safe_video_path}_{timestamp}_{time.time()}"
        uri = QUrl(f"frame://{image_name}")

        # Add the QImage object directly as a resource.
        self.document().addResource(QTextDocument.ResourceType.ImageResource, uri, displayed_image)

        cursor = self.textCursor()
        image_format = QTextImageFormat()
        image_format.setName(uri.toString())
        image_format.setWidth(width)
        image_format.setHeight(height)

        cursor.insertImage(image_format)

        # Store metadata
        image_to_store = original_image if original_image is not None else displayed_image
        self.image_metadata[image_name] = {
            'video_path': video_path,
            'timestamp': timestamp,
            'original_image': image_to_store
        }
        return image_name

    def find_nearest_timecode(self, cursor_pos):
        """Finds the nearest timecode to the given cursor position."""
        doc = self.document()
        timecode_pattern = re.compile(r'\[((?:\d+:)?\d+:\d+(?:\.\d)?)\]')

        nearest_timecode = None
        min_distance = float('inf')

        block = doc.begin()
        while block.isValid():
            block_text = block.text()
            for match in timecode_pattern.finditer(block_text):
                time_str = match.group(1)
                from src.services.utils import parse_timestamp_to_seconds
                total_seconds = parse_timestamp_to_seconds(time_str)

                if total_seconds is not None:
                    match_pos = block.position() + match.start()
                    distance = abs(cursor_pos - match_pos)

                    if distance < min_distance:
                        min_distance = distance
                        nearest_timecode = total_seconds

            block = block.next()

        return nearest_timecode

    def contextMenuEvent(self, event):
        """
        Shows a custom context menu. "Insert Frame" is always available if timecodes exist.
        """
        cursor = self.cursorForPosition(event.pos())

        # Check for image context first
        image_format = self.get_image_format_at_cursor(cursor)
        if image_format and image_format.name().startswith("frame://"):
            menu = QMenu(self)
            edit_action = menu.addAction("Modifica Frame")
            delete_action = menu.addAction("Rimuovi Frame")
            action = menu.exec(event.globalPos())

            if action == edit_action:
                image_name = image_format.name().replace("frame://", "")
                self.frame_edit_requested.emit(image_name)
            elif action == delete_action:
                cursor.beginEditBlock()
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.endEditBlock()
            return

        # If not on an image, create the general context menu
        menu = QMenu(self)

        # Find the nearest timecode to the click position
        nearest_timecode = self.find_nearest_timecode(cursor.position())

        insert_frame_action = menu.addAction("Inserisci frame")
        # Disable the action if no timecode is found in the document
        if nearest_timecode is None:
            insert_frame_action.setEnabled(False)

        # Add standard actions (Copy, Paste, etc.)
        standard_menu = self.createStandardContextMenu()
        if standard_menu and standard_menu.actions():
            menu.addSeparator()
            menu.addActions(standard_menu.actions())

        action = menu.exec(event.globalPos())

        if action == insert_frame_action and nearest_timecode is not None:
            # Emit the signal with the nearest timecode and the current cursor position for insertion
            self.insert_frame_requested.emit(nearest_timecode, cursor.position())

    def crop_image(self, image_format):
        """
        Extracts the image name from the format and calls the cropping handler.
        """
        uri_string = image_format.name()
        if uri_string.startswith("frame://"):
            image_name = uri_string[len("frame://"):]
            self.handle_crop_image(image_name)

    def handle_crop_image(self, image_name):
        metadata = self.image_metadata.get(image_name)
        if not metadata:
            return

        original_image = metadata['original_image']
        pixmap = QPixmap.fromImage(original_image)

        dialog = ImageCropDialog(pixmap, self.window())
        if dialog.exec():
            crop_rect = dialog.get_crop_rect()
            cropped_pixmap = pixmap.copy(crop_rect)
            cropped_image = cropped_pixmap.toImage()

            # Update the image resource and replace it in the document
            self.update_image_resource(image_name, cropped_image, crop_rect.width(), crop_rect.height())

    def update_image_resource(self, image_name, new_image, new_width, new_height):
        uri = QUrl(f"frame://{image_name}")
        # Update the resource in the document's cache
        self.document().addResource(QTextDocument.ResourceType.ImageResource, uri, new_image)

        # Update the metadata with the new cropped image
        if image_name in self.image_metadata:
            self.image_metadata[image_name]['original_image'] = new_image

        # Find all instances of the image in the document and update them
        cursor = QTextCursor(self.document())
        while not cursor.isNull() and not cursor.atEnd():
            cursor = self.document().find(uri.toString(), cursor, QTextDocument.FindFlag.FindCaseSensitively)
            if not cursor.isNull():
                char_format = cursor.charFormat()
                if char_format.isImageFormat():
                    image_format = char_format.toImageFormat()
                    if image_format.name() == uri.toString():
                        # Update the size of the image format
                        image_format.setWidth(new_width)
                        image_format.setHeight(new_height)

                        # Apply the updated format
                        temp_cursor = QTextCursor(cursor)
                        temp_cursor.setPosition(cursor.selectionStart())
                        temp_cursor.setPosition(cursor.selectionEnd(), QTextCursor.MoveMode.KeepAnchor)
                        temp_cursor.setCharFormat(image_format)

        # Force a relayout of the document to ensure the new image is displayed
        self.document().adjustSize()
        self.viewport().update()

    def _get_fps(self, video_path):
        import cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        return fps if fps > 0 else 30

    def handle_previous_frame(self, image_name):
        metadata = self.image_metadata.get(image_name)
        if not metadata:
            return

        fps = self._get_fps(metadata['video_path'])
        new_timestamp = max(0, metadata['timestamp'] - (1 / fps))

        new_image = get_frame_at_timestamp(metadata['video_path'], new_timestamp)
        if new_image:
            self.update_image_resource(image_name, new_image, new_image.width(), new_image.height())
            metadata['timestamp'] = new_timestamp

    def handle_next_frame(self, image_name):
        metadata = self.image_metadata.get(image_name)
        if not metadata:
            return

        fps = self._get_fps(metadata['video_path'])
        new_timestamp = metadata['timestamp'] + (1 / fps)

        new_image = get_frame_at_timestamp(metadata['video_path'], new_timestamp)
        if new_image:
            self.update_image_resource(image_name, new_image, new_image.width(), new_image.height())
            metadata['timestamp'] = new_timestamp

    def get_image_format_at_cursor(self, cursor):
        char_format = cursor.charFormat()
        if char_format.isImageFormat():
            return char_format.toImageFormat()
        return None

    def resize_image(self, image_format):
        dialog = ResizedImageDialog(image_format.width(), image_format.height(), self)
        if dialog.exec():
            new_width, new_height = dialog.get_new_size()
            self.update_image_size(image_format, new_width, new_height)

    def update_image_size(self, image_format, width, height):
        if not image_format.isValid():
            return

        cursor = self.textCursor()
        if not cursor.hasSelection():
            # If no text is selected, find the image under the cursor
            cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, 1)

        if cursor.charFormat().isImageFormat():
            image_format.setWidth(width)
            image_format.setHeight(height)
            cursor.setCharFormat(image_format)

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
        cursor = self.cursorForPosition(event.pos())
        self.resizing_image = self.get_image_format_at_cursor(cursor)
        if self.resizing_image:
            self.resizing_start_pos = event.pos()
            self.setTextCursor(cursor)
        else:
            super().mousePressEvent(event)
        self.cursorPositionChanged.emit()

    def mouseMoveEvent(self, event):
        if self.resizing_image and self.resizing_start_pos:
            delta = event.pos() - self.resizing_start_pos
            new_width = self.resizing_image.width() + delta.x()
            new_height = self.resizing_image.height() + delta.y()
            if new_width > 10 and new_height > 10:
                self.update_image_size(self.resizing_image, new_width, new_height)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.resizing_image = None
        self.resizing_start_pos = None
        super().mouseReleaseEvent(event)

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
            # Il genitore del dialogo deve essere la finestra principale per un comportamento corretto
            parent_window = self.window()
            self.search_dialog_instance = SearchDialog(self, parent_window)
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
        self.clear_highlights()
        self.search_text = search_text # Memorizza il termine di ricerca attivo

        if not search_text:
            self.update_result_count_label()
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


    def replace_all_results(self, search_text, replace_text, case_sensitive, whole_words):
        """
        Sostituisce tutte le occorrenze di `search_text` con `replace_text`.
        Questa operazione è unica e non dipende da una ricerca precedente.
        """
        if not search_text:
            return 0

        options = QTextDocument.FindFlag(0)
        if case_sensitive:
            options |= QTextDocument.FindFlag.FindCaseSensitively
        if whole_words:
            options |= QTextDocument.FindFlag.FindWholeWords
        # Cerca all'indietro per evitare che le sostituzioni invalidino le posizioni dei risultati successivi
        options |= QTextDocument.FindFlag.FindBackward

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        replacements_count = 0
        self.document().undoStack().beginMacro("Sostituisci Tutto")
        while True:
            cursor = self.document().find(search_text, cursor, options)
            if cursor.isNull():
                break
            # Sostituisce il testo mantenendo il formato del testo sostituito
            cursor.insertText(replace_text)
            replacements_count += 1
        self.document().undoStack().endMacro()

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

    def clear_highlights(self):
        """
        Rimuove l'evidenziazione della ricerca e resetta completamente lo stato della ricerca.
        """
        # Formato per rimuovere la sottolineatura
        clear_format = QTextCharFormat()
        clear_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.NoUnderline)

        # Applica il formato di pulizia ai risultati memorizzati
        for cursor in self.search_results_cursors:
            cursor.mergeCharFormat(clear_format)

        # Pulisce completamente lo stato della ricerca
        self.search_results_cursors = []
        self.current_search_index = -1
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

        # Layout principale a griglia per un'organizzazione più compatta
        layout = QGridLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # --- Riga 0: Campi di ricerca e navigazione ---
        find_label = QLabel("Cerca:")
        self.searchComboBox = QComboBox()
        self.searchComboBox.setEditable(True)
        self.searchComboBox.setPlaceholderText("Trova...")
        self.searchComboBox.lineEdit().returnPressed.connect(self.perform_search)
        self.load_search_history()

        searchButton = QPushButton("Cerca")
        searchButton.setToolTip("Cerca il testo (Invio)")
        searchButton.clicked.connect(self.perform_search)

        prevButton = QPushButton("↑")
        prevButton.setToolTip("Risultato precedente (Shift+F3)")
        prevButton.setFixedSize(28, 28)
        prevButton.clicked.connect(self.textEdit.find_previous_result)

        nextButton = QPushButton("↓")
        nextButton.setToolTip("Risultato successivo (F3)")
        nextButton.setFixedSize(28, 28)
        nextButton.clicked.connect(self.textEdit.find_next_result)

        layout.addWidget(find_label, 0, 0)
        layout.addWidget(self.searchComboBox, 0, 1, 1, 2) # Occupa 2 colonne
        layout.addWidget(searchButton, 0, 3)
        layout.addWidget(prevButton, 0, 4)
        layout.addWidget(nextButton, 0, 5)

        # --- Riga 1: Campi di sostituzione ---
        replace_label = QLabel("Sostituisci:")
        self.replaceLineEdit = QLineEdit()
        self.replaceLineEdit.setPlaceholderText("Sostituisci con...")

        self.replaceButton = QPushButton("Sostituisci")
        self.replaceButton.setToolTip("Sostituisce l'occorrenza corrente")
        self.replaceButton.clicked.connect(self.replace_current)

        self.replaceAllButton = QPushButton("Sostituisci Tutto")
        self.replaceAllButton.setToolTip("Sostituisce tutte le occorrenze")
        self.replaceAllButton.clicked.connect(self.replace_all)

        layout.addWidget(replace_label, 1, 0)
        layout.addWidget(self.replaceLineEdit, 1, 1, 1, 2)
        layout.addWidget(self.replaceButton, 1, 3)
        layout.addWidget(self.replaceAllButton, 1, 4, 1, 2) # Occupa 2 colonne

        # --- Riga 2: Opzioni di ricerca e contatore risultati ---
        options_layout = QHBoxLayout()
        self.caseSensitiveCheck = QCheckBox("Maiuscole/minuscole")
        self.wholeWordCheck = QCheckBox("Parola intera")
        options_layout.addWidget(self.caseSensitiveCheck)
        options_layout.addWidget(self.wholeWordCheck)
        options_layout.addStretch()

        self.resultCountLabel = QLabel("Risultati: N/A")
        self.resultCountLabel.setAlignment(Qt.AlignmentFlag.AlignRight)
        options_layout.addWidget(self.resultCountLabel)

        layout.addLayout(options_layout, 2, 0, 1, 6) # Occupa tutta la larghezza

        self.setLayout(layout)
        self.searchComboBox.setFocus()
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
        Sostituisce tutte le occorrenze del testo di ricerca con il testo di sostituzione,
        utilizzando le opzioni di ricerca correnti.
        """
        search_text = self.searchComboBox.currentText()
        replace_text = self.replaceLineEdit.text()
        case_sensitive = self.caseSensitiveCheck.isChecked()
        whole_words = self.wholeWordCheck.isChecked()

        if not search_text:
            QMessageBox.warning(self, "Nessun Termine", "Inserisci un termine di ricerca prima di sostituire.")
            return

        # Esegue la sostituzione
        num_replaced = self.textEdit.replace_all_results(search_text, replace_text, case_sensitive, whole_words)

        # Mostra un messaggio con il numero di sostituzioni
        QMessageBox.information(self, "Sostituisci Tutto", f"Sono state sostituite {num_replaced} occorrenze.")

        # Pulisce le evidenziazioni e resetta lo stato della ricerca
        self.textEdit.clear_highlights()
        self.update_result_count_label()


    def perform_search(self):
        """Esegue la ricerca e aggiorna la cronologia."""
        search_text = self.searchComboBox.currentText()
        case_sensitive = self.caseSensitiveCheck.isChecked()
        whole_words = self.wholeWordCheck.isChecked()

        if search_text:
            self.save_search_history(search_text) # Salva il termine cercato
            num_results = self.textEdit.highlight_search_results(search_text, case_sensitive, whole_words)

            # Aggiorna stile input in base al risultato
            if num_results == 0:
                # Giallo avviso con testo nero per leggibilità
                self.searchComboBox.setStyleSheet("background-color: #FFD580; color: black;")
            else:
                # Resetta allo stile di default
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
            self.resultCountLabel.setText("Risultati: N/A")
            return

        if num_results == 0:
            self.resultCountLabel.setText("Nessun risultato")
        else:
            # L'indice è basato su 0, quindi aggiungiamo 1 per la visualizzazione
            self.resultCountLabel.setText(f"{current_index + 1} di {num_results}")

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