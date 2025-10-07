from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QTreeWidget, QTreeWidgetItem, QPushButton, QFormLayout, QHeaderView, QMenu, QHBoxLayout, QInputDialog
from PyQt6.QtCore import Qt, pyqtSignal, QFileSystemWatcher, QTimer
from PyQt6.QtGui import QIcon
from src.ui.CustomDock import CustomDock
from src.config import get_resource
import datetime
import os
from pathlib import Path

class ProjectDock(CustomDock):
    """
    Un dock per visualizzare e gestire un progetto .gnai, mostrando
    informazioni sul progetto e un elenco di clip con metadati.
    """
    clip_selected = pyqtSignal(str, str)
    open_in_input_player_requested = pyqtSignal(str)
    open_in_output_player_requested = pyqtSignal(str)
    rename_clip_requested = pyqtSignal(str, str)
    merge_clips_requested = pyqtSignal()
    open_folder_requested = pyqtSignal()
    delete_clip_requested = pyqtSignal(str)
    project_clips_folder_changed = pyqtSignal() # Segnale generico di modifica

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
        self.tree_clips.itemDoubleClicked.connect(self._on_clip_selected)
        self.btn_merge_clips.clicked.connect(self.merge_clips_requested.emit)
        self.tree_clips.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_clips.customContextMenuRequested.connect(self.show_context_menu)

    def on_directory_changed(self, path):
        """
        Slot che viene chiamato quando la cartella monitorata cambia.
        Avvia un timer per evitare esecuzioni multiple e dare tempo al file di essere scritto.
        """
        self.sync_timer.start()

    def show_context_menu(self, position):
        """Mostra il menu contestuale per l'area delle clip."""
        item = self.tree_clips.itemAt(position)
        if not self.project_dir or not item or item.isDisabled():
            return

        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path or not os.path.exists(file_path):
            return

        menu = QMenu()

        open_input_action = menu.addAction("Apri nel player di input")
        open_output_action = menu.addAction("Apri nel player di output")
        menu.addSeparator()
        rename_action = menu.addAction("Rinomina")
        delete_action = menu.addAction("Rimuovi dal progetto")

        action = menu.exec(self.tree_clips.mapToGlobal(position))

        if action == open_input_action:
            self.open_in_input_player_requested.emit(file_path)
        elif action == open_output_action:
            self.open_in_output_player_requested.emit(file_path)
        elif action == rename_action:
            old_filename = item.text(0)
            base_name, extension = os.path.splitext(old_filename)
            new_base_name, ok = QInputDialog.getText(self, "Rinomina Clip", "Nuovo nome:", text=base_name)
            if ok and new_base_name:
                new_filename = new_base_name + extension
                self.rename_clip_requested.emit(old_filename, new_filename)
        elif action == delete_action:
            clip_filename = item.text(0)
            self.delete_clip_requested.emit(clip_filename)

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

        clips_group = QGroupBox("Clip Video")
        clips_layout = QVBoxLayout(clips_group)

        self.tree_clips = QTreeWidget()
        self.tree_clips.setColumnCount(4)
        self.tree_clips.setHeaderLabels(["Nome File", "Data", "Durata", "Dimensione"])
        self.tree_clips.setToolTip("Fai doppio click su una clip per caricarla.")
        self.tree_clips.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        clips_layout.addWidget(self.tree_clips)

        # Layout per i pulsanti sotto la lista delle clip
        buttons_layout = QHBoxLayout()
        self.btn_merge_clips = QPushButton("Unisci Clip")
        self.btn_merge_clips.setToolTip("Unisci tutte le clip in un unico video.")
        buttons_layout.addWidget(self.btn_merge_clips)

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
            for clip in self.project_data.get("clips", []):
                if clip.get("clip_filename") == clip_filename:
                    metadata_filename = clip.get("metadata_filename")
                    break

            # Costruisci il percorso completo per le clip di progetto
            project_clip_path = os.path.join(self.project_dir, "clips", clip_filename)
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

        # Carica clip del progetto
        project_clips = sorted(project_data.get("clips", []), key=lambda x: x.get("creation_date", ""))
        clips_dir = os.path.join(project_dir, "clips")
        if os.path.exists(clips_dir):
            self.file_watcher.addPath(clips_dir)

        if project_clips:
            project_clips_root = QTreeWidgetItem(self.tree_clips)
            project_clips_root.setText(0, "Clip del Progetto")
            project_clips_root.setExpanded(True)

            for clip in project_clips:
                item = QTreeWidgetItem(project_clips_root)
                item.setText(0, clip.get("clip_filename", "N/A"))
                item.setText(1, self._format_date(clip.get("creation_date")))
                item.setText(2, self._format_duration(clip.get("duration")))
                item.setText(3, self._format_size(clip.get("size")))
                # Salva il percorso completo per un facile accesso
                full_path = os.path.join(clips_dir, clip.get("clip_filename", ""))
                item.setData(0, Qt.ItemDataRole.UserRole, full_path)

        # Carica file dalla cartella 'downloads' del progetto
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

                    try:
                        stat = os.stat(file_path)
                        item.setText(1, self._format_date(datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()))
                        item.setText(2, "N/A") # Durata non calcolata per performance
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