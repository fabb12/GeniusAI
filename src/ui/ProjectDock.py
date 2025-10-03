from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QTreeWidget, QTreeWidgetItem, QPushButton, QFormLayout, QHeaderView
from PyQt6.QtCore import Qt, pyqtSignal
from src.ui.CustomDock import CustomDock
import datetime

class ProjectDock(CustomDock):
    """
    Un dock per visualizzare e gestire un progetto .gnai, mostrando
    informazioni sul progetto e un elenco di clip con metadati.
    """
    clip_selected = pyqtSignal(str, str)
    merge_clips_requested = pyqtSignal()

    def __init__(self, title="Progetto", closable=True, parent=None):
        super().__init__(title, closable=closable, parent=parent)
        self.setToolTip("Mostra i dettagli e le clip del progetto corrente.")
        self.project_data = None
        self.project_dir = None
        self.gnai_path = None

        self._setup_ui()
        self.tree_clips.itemDoubleClicked.connect(self._on_clip_selected)
        self.btn_merge_clips.clicked.connect(self.merge_clips_requested.emit)

    def _setup_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        project_info_group = QGroupBox("Dettagli Progetto")
        form_layout = QFormLayout(project_info_group)
        self.lbl_project_name = QLabel("N/A")
        self.lbl_project_path = QLabel("N/A")
        form_layout.addRow("<b>Nome:</b>", self.lbl_project_name)
        form_layout.addRow("<b>Percorso:</b>", self.lbl_project_path)

        clips_group = QGroupBox("Clip Video")
        clips_layout = QVBoxLayout(clips_group)

        self.tree_clips = QTreeWidget()
        self.tree_clips.setColumnCount(4)
        self.tree_clips.setHeaderLabels(["Nome File", "Data", "Durata", "Dimensione"])
        self.tree_clips.setToolTip("Fai doppio click su una clip per caricarla.")
        self.tree_clips.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.btn_merge_clips = QPushButton("Unisci Clip")
        self.btn_merge_clips.setToolTip("Unisci tutte le clip in un unico video.")

        clips_layout.addWidget(self.tree_clips)
        clips_layout.addWidget(self.btn_merge_clips)

        main_layout.addWidget(project_info_group)
        main_layout.addWidget(clips_group)

        self.addWidget(main_widget)

    def _on_clip_selected(self, item, column):
        clip_filename = item.text(0)
        if self.project_data and self.project_dir:
            metadata_filename = ""
            for clip in self.project_data.get("clips", []):
                if clip.get("clip_filename") == clip_filename:
                    metadata_filename = clip.get("metadata_filename")
                    break
            self.clip_selected.emit(clip_filename, metadata_filename)

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
        self.project_data = project_data
        self.project_dir = project_dir
        self.gnai_path = gnai_path

        self.lbl_project_name.setText(project_data.get("projectName", "N/A"))
        self.lbl_project_path.setText(project_dir)

        self.tree_clips.clear()
        clips = sorted(project_data.get("clips", []), key=lambda x: x.get("creation_date", ""))

        if clips:
            for clip in clips:
                item = QTreeWidgetItem(self.tree_clips)
                item.setText(0, clip.get("clip_filename", "N/A"))
                item.setText(1, self._format_date(clip.get("creation_date")))
                item.setText(2, self._format_duration(clip.get("duration")))
                item.setText(3, self._format_size(clip.get("size")))
        else:
            item = QTreeWidgetItem(self.tree_clips)
            item.setText(0, "Nessuna clip trovata.")
            item.setDisabled(True)

    def clear_dock(self):
        self.lbl_project_name.setText("N/A")
        self.lbl_project_path.setText("N/A")
        self.tree_clips.clear()
        self.project_data = None
        self.project_dir = None
        self.gnai_path = None