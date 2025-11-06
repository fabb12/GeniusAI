from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QTreeWidget, QTreeWidgetItem, QPushButton, QFormLayout, QHeaderView, QMenu, QHBoxLayout, QInputDialog, QFileDialog
from PyQt6.QtCore import Qt, pyqtSignal, QFileSystemWatcher, QTimer, QEvent
from PyQt6.QtGui import QIcon
from src.ui.CustomDock import CustomDock
from src.config import get_resource
import datetime
import os
import json
from pathlib import Path
from bs4 import BeautifulSoup

class ProjectDock(CustomDock):
    """
    Un dock per visualizzare e gestire un progetto .gnai, mostrando
    informazioni sul progetto e un elenco di clip con metadati.
    """
    clip_selected = pyqtSignal(str, str)
    open_in_input_player_requested = pyqtSignal(str)
    open_in_output_player_requested = pyqtSignal(str)
    rename_clip_requested = pyqtSignal(str, str)
    rename_from_summary_requested = pyqtSignal(str)
    merge_clips_requested = pyqtSignal()
    open_folder_requested = pyqtSignal()
    delete_clip_requested = pyqtSignal(str)
    relink_clip_requested = pyqtSignal(str, str)
    project_clips_folder_changed = pyqtSignal() # Segnale generico di modifica
    batch_transcribe_requested = pyqtSignal()
    batch_summarize_requested = pyqtSignal()
    separate_audio_requested = pyqtSignal(str)

    def __init__(self, title="Progetto", closable=True, parent=None):
        super().__init__(title, closable=closable, parent=parent)
        self.setToolTip("Mostra i dettagli e le clip del progetto corrente.")
        self.project_data = None
        self.project_dir = None
        self.gnai_path = None

        self.file_watcher = QFileSystemWatcher(self)
        self.file_watcher.directoryChanged.connect(self.on_directory_changed)

        self.sync_timer = QTimer(self)
        self.sync_timer.setSingleShot(True)
        self.sync_timer.setInterval(1500)  # Attendi 1.5 secondi per la stabilità del file
        self.sync_timer.timeout.connect(self.project_clips_folder_changed.emit)

        self._setup_ui()
        self.btn_merge_clips.clicked.connect(self.merge_clips_requested.emit)
        self.tree_clips.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_clips.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_clips.installEventFilter(self)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyPress and source is self.tree_clips:
            if event.key() == Qt.Key.Key_F2:
                item = self.tree_clips.currentItem()
                if item and item.parent(): # Assicura che sia una clip e non una cartella radice
                    self._trigger_rename(item)
                    return True
        return super().eventFilter(source, event)

    def _trigger_rename(self, item):
        """Avvia la logica di rinomina per un dato item."""
        if not self.project_dir or item.isDisabled() or not item.parent():
            return

        status = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if status == "offline":
            # Potresti voler gestire la rinomina di clip offline in modo diverso o non permetterla
            return

        clip_filename = item.text(0)
        base_name, extension = os.path.splitext(clip_filename)
        new_base_name, ok = QInputDialog.getText(self, "Rinomina Clip", "Nuovo nome:", text=base_name)
        if ok and new_base_name:
            new_filename = new_base_name + extension
            self.rename_clip_requested.emit(clip_filename, new_filename)

    def on_directory_changed(self, path):
        """
        Slot che viene chiamato quando la cartella monitorata cambia.
        Avvia un timer per evitare esecuzioni multiple e dare tempo al file di essere scritto.
        """
        self.sync_timer.start()

    def show_context_menu(self, position):
        """Mostra il menu contestuale per l'area delle clip."""
        item = self.tree_clips.itemAt(position)
        if not self.project_dir or not item or item.isDisabled() or not item.parent():
            return

        # Estrai tutti i dati necessari dall'item PRIMA di mostrare il menu.
        # Questo previene un RuntimeError se l'item viene cancellato dall'azione del menu.
        status = item.data(0, Qt.ItemDataRole.UserRole + 1)
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        clip_filename = item.text(0)
        is_audio_clip = item.parent().text(0) == "Clip Audio"

        menu = QMenu()

        if status == "offline":
            relink_action = menu.addAction("Riaggancia file...")
            remove_action = menu.addAction("Rimuovi dal progetto")

            action = menu.exec(self.tree_clips.mapToGlobal(position))

            if action == relink_action:
                new_filepath, _ = QFileDialog.getOpenFileName(self, "Seleziona nuovo file clip", "", "Video Files (*.mp4 *.avi *.mov);;All Files (*)")
                if new_filepath:
                    self.relink_clip_requested.emit(clip_filename, new_filepath) # Usa la variabile locale
            elif action == remove_action:
                self.delete_clip_requested.emit(clip_filename) # Usa la variabile locale

        else:  # 'online' o altri stati
            if not file_path or not os.path.exists(file_path):
                 # Anche se è online, il file potrebbe essere stato spostato/cancellato
                return

            open_input_action = menu.addAction("Apri nel player di input")
            open_output_action = menu.addAction("Apri nel player di output")
            menu.addSeparator()

            # Aggiungi "Separa Audio" solo per le clip video
            if not is_audio_clip:
                separate_audio_action = menu.addAction("Separa Audio")
                menu.addSeparator()

            # Verifica se esiste un riassunto per abilitare l'azione
            has_summary = False
            json_path = os.path.splitext(file_path)[0] + ".json"
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                    summary_text = json_data.get("summaries", {}).get("detailed", "")
                    if summary_text and summary_text.strip():
                        has_summary = True
                except (json.JSONDecodeError, IOError):
                    pass # Errore nel JSON, lo consideriamo come senza riassunto

            rename_action = menu.addAction("Rinomina")
            rename_from_summary_action = menu.addAction("Auto-Rinomina")
            rename_from_summary_action.setEnabled(has_summary)
            if not has_summary:
                rename_from_summary_action.setToolTip("Azione disabilitata: nessun riassunto dettagliato trovato per questa clip.")

            delete_action = menu.addAction("Rimuovi dal progetto")

            action = menu.exec(self.tree_clips.mapToGlobal(position))

            if action == open_input_action:
                self.open_in_input_player_requested.emit(file_path)
            elif action == open_output_action:
                self.open_in_output_player_requested.emit(file_path)
            elif 'separate_audio_action' in locals() and action == separate_audio_action:
                self.separate_audio_requested.emit(file_path)
            elif action == rename_action:
                self._trigger_rename(item)
            elif action == rename_from_summary_action:
                self.rename_from_summary_requested.emit(clip_filename)
            elif action == delete_action:
                self.delete_clip_requested.emit(clip_filename) # Usa la variabile locale

    def _setup_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        project_info_group = QGroupBox("Dettagli Progetto")
        project_info_layout = QVBoxLayout(project_info_group) # Layout verticale
        form_layout = QFormLayout()
        self.lbl_project_name = QLabel("N/A")
        self.lbl_project_path = QLabel("N/A")
        form_layout.addRow("<b>Nome:</b>", self.lbl_project_name)
        form_layout.addRow("<b>Percorso:</b>", self.lbl_project_path)

        project_info_layout.addLayout(form_layout) # Aggiungi il form layout

        # Pulsante per aprire la cartella
        self.btn_open_folder = QPushButton("Apri Cartella Progetto")
        self.btn_open_folder.clicked.connect(self.open_folder_requested.emit)
        project_info_layout.addWidget(self.btn_open_folder)

        clips_group = QGroupBox("Clip Progetto")
        clips_layout = QVBoxLayout(clips_group)

        self.tree_clips = QTreeWidget()
        self.tree_clips.setColumnCount(6)
        self.tree_clips.setHeaderLabels(["Nome File", "Data", "Durata", "Dimensione", "Trascrizione", "Riassunto"])
        self.tree_clips.setToolTip("Fai doppio click su una clip per caricarla.")
        self.tree_clips.itemDoubleClicked.connect(self._on_clip_selected)

        header = self.tree_clips.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch) # Stretch "Nome File"

        clips_layout.addWidget(self.tree_clips)

        # Layout per i pulsanti sotto la lista delle clip
        buttons_layout = QHBoxLayout()
        self.btn_merge_clips = QPushButton("Unisci Clip")
        self.btn_merge_clips.setToolTip("Unisci tutte le clip in un unico video.")
        buttons_layout.addWidget(self.btn_merge_clips)

        self.btn_batch_transcribe = QPushButton("Trascrivi Tutti i Video")
        self.btn_batch_transcribe.setToolTip("Trascrive tutti i video nel progetto.")
        self.btn_batch_transcribe.clicked.connect(self.batch_transcribe_requested.emit)
        buttons_layout.addWidget(self.btn_batch_transcribe)

        self.btn_batch_summarize = QPushButton("Genera Riassunto Multiplo")
        self.btn_batch_summarize.setToolTip("Genera un riassunto combinato da tutte le trascrizioni.")
        self.btn_batch_summarize.clicked.connect(self.batch_summarize_requested.emit)
        buttons_layout.addWidget(self.btn_batch_summarize)

        buttons_layout.addStretch()

        self.btn_refresh_clips = QPushButton()
        self.btn_refresh_clips.setIcon(QIcon(get_resource("sync.png")))
        self.btn_refresh_clips.setToolTip("Aggiorna la lista delle clip")
        self.btn_refresh_clips.clicked.connect(self.project_clips_folder_changed.emit)
        self.btn_refresh_clips.setFixedSize(32, 32)
        buttons_layout.addWidget(self.btn_refresh_clips)

        clips_layout.addLayout(buttons_layout)

        main_layout.addWidget(project_info_group)
        main_layout.addWidget(clips_group)

        self.addWidget(main_widget)

    def _on_clip_selected(self, item, column):
        clip_path = item.data(0, Qt.ItemDataRole.UserRole) # Get full path from item data
        clip_filename = item.text(0)

        # Se il percorso completo è disponibile, usalo
        if clip_path and os.path.exists(clip_path):
            self.clip_selected.emit(clip_path, "") # Emetti il percorso completo
            return

        # Altrimenti, gestisci come una clip di progetto
        if self.project_data and self.project_dir:
            metadata_filename = ""
            clip_list_name = "clips"
            subfolder = "clips"

            if item.parent() and item.parent().text(0) == "Clip Audio":
                clip_list_name = "audio_clips"
                subfolder = "audio"

            for clip in self.project_data.get(clip_list_name, []):
                if clip.get("clip_filename") == clip_filename:
                    metadata_filename = clip.get("metadata_filename")
                    break

            # Costruisci il percorso completo per le clip di progetto
            project_clip_path = os.path.join(self.project_dir, subfolder, clip_filename)
            self.clip_selected.emit(project_clip_path, metadata_filename)

    def _format_duration(self, seconds):
        if not isinstance(seconds, (int, float)) or seconds < 0:
            return "00:00"
        mins, secs = divmod(int(seconds), 60)
        return f"{mins:02d}:{secs:02d}"

    def _format_size(self, size_bytes):
        if not isinstance(size_bytes, (int, float)) or size_bytes < 0:
            return "0 B"
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes/1024:.1f} KB"
        else:
            return f"{size_bytes/1024**2:.1f} MB"

    def _format_date(self, date_string):
        try:
            return datetime.datetime.fromisoformat(date_string).strftime("%d/%m/%Y %H:%M")
        except (ValueError, TypeError):
            return "N/A"

    def load_project_data(self, project_data, project_dir, gnai_path):
        # Rimuovi i percorsi precedenti dal watcher
        if self.file_watcher.directories():
            self.file_watcher.removePaths(self.file_watcher.directories())

        self.project_data = project_data
        self.project_dir = project_dir
        self.gnai_path = gnai_path

        self.lbl_project_name.setText(project_data.get("projectName", "N/A"))
        self.lbl_project_path.setText(project_dir)

        self.tree_clips.clear()

        # Funzione helper per popolare le righe dell'albero
        def populate_tree(clips, subfolder, root_text):
            if not clips:
                return

            root_item = QTreeWidgetItem(self.tree_clips)
            root_item.setText(0, root_text)
            root_item.setExpanded(True)

            clips_dir = os.path.join(project_dir, subfolder)
            if os.path.exists(clips_dir):
                self.file_watcher.addPath(clips_dir)

            for clip in clips:
                item = QTreeWidgetItem(root_item)
                clip_filename = clip.get("clip_filename", "N/A")
                full_path = os.path.join(clips_dir, clip_filename)

                # --- Carica dati JSON ---
                has_transcription = "❌"
                has_summary = "❌"
                json_path = os.path.splitext(full_path)[0] + ".json"
                if os.path.exists(json_path):
                    try:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            json_data = json.load(f)
                        # Funzione helper per verificare se il contenuto HTML ha testo visibile
                        def html_has_text(html_content):
                            if not html_content or not html_content.strip():
                                return False
                            soup = BeautifulSoup(html_content, 'html.parser')
                            return soup.get_text(strip=True) != ""

                        # Verifica che il contenuto esista e non sia una stringa vuota/whitespace
                        transcription_original = json_data.get("transcription_original", "")
                        transcription_corrected = json_data.get("transcription_corrected", "")
                        if html_has_text(transcription_original) or html_has_text(transcription_corrected):
                            has_transcription = "✔️"

                        summaries = json_data.get("summaries", {})
                        # Controlla tutti i possibili riassunti
                        if any(html_has_text(summary) for summary in summaries.values()):
                            has_summary = "✔️"
                    except (json.JSONDecodeError, IOError):
                        pass # Il file JSON potrebbe essere corrotto o vuoto

                # Imposta l'icona in base allo stato
                status = clip.get("status", "N/A")
                if status == "online":
                    item.setIcon(0, QIcon(get_resource("online.png")))
                elif status == "offline":
                    item.setIcon(0, QIcon(get_resource("offline.png")))

                item.setText(0, clip_filename)
                item.setToolTip(0, full_path) # Tooltip con percorso completo
                item.setText(1, self._format_date(clip.get("creation_date")))
                item.setText(2, self._format_duration(clip.get("duration")))
                item.setText(3, self._format_size(clip.get("size")))
                item.setText(4, has_transcription)
                item.setText(5, has_summary)

                # Salva il percorso completo e lo stato per un facile accesso
                item.setData(0, Qt.ItemDataRole.UserRole, full_path)
                item.setData(0, Qt.ItemDataRole.UserRole + 1, status)

        # Carica clip video e audio
        project_clips = sorted(project_data.get("clips", []), key=lambda x: x.get("creation_date", ""))
        populate_tree(project_clips, "clips", "Clip Video")

        audio_clips = sorted(project_data.get("audio_clips", []), key=lambda x: x.get("creation_date", ""))
        populate_tree(audio_clips, "audio", "Clip Audio")

        # Carica file dalla cartella 'downloads' del progetto (invariato)
        download_folder_path = os.path.join(project_dir, "downloads")
        if os.path.exists(download_folder_path):
            download_root = QTreeWidgetItem(self.tree_clips)
            download_root.setText(0, "Downloads")
            download_root.setExpanded(True)

            media_extensions = {".mp4", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".aac"}

            for filename in os.listdir(download_folder_path):
                file_path = os.path.join(download_folder_path, filename)
                if os.path.isfile(file_path) and os.path.splitext(filename)[1].lower() in media_extensions:
                    item = QTreeWidgetItem(download_root)
                    item.setText(0, filename)
                    item.setToolTip(0, file_path)

                    try:
                        stat = os.stat(file_path)
                        item.setText(1, self._format_date(datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()))
                        item.setText(2, "N/A")
                        item.setText(3, self._format_size(stat.st_size))
                        item.setData(0, Qt.ItemDataRole.UserRole, file_path)
                    except (OSError, ValueError):
                        item.setText(1, "N/A")
                        item.setText(2, "N/A")
                        item.setText(3, "N/A")

        if self.tree_clips.topLevelItemCount() == 0:
            item = QTreeWidgetItem(self.tree_clips)
            item.setText(0, "Nessuna clip trovata.")
            item.setDisabled(True)

    def clear_project(self):
        """Resetta il dock allo stato iniziale, pulendo i dati del progetto."""
        if self.file_watcher.directories():
            self.file_watcher.removePaths(self.file_watcher.directories())
        self.lbl_project_name.setText("N/A")
        self.lbl_project_path.setText("N/A")
        self.tree_clips.clear()
        self.project_data = None
        self.project_dir = None
        self.gnai_path = None

        # Aggiungi un item placeholder per chiarezza
        item = QTreeWidgetItem(self.tree_clips)
        item.setText(0, "Nessun progetto caricato.")
        item.setDisabled(True)