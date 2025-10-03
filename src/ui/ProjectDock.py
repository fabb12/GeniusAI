from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QListWidget, QPushButton, QFormLayout
from PyQt6.QtCore import Qt, pyqtSignal
from src.ui.CustomDock import CustomDock

class ProjectDock(CustomDock):
    """
    Un dock per visualizzare e gestire un progetto .gnai, mostrando
    informazioni sul progetto e un elenco di clip.
    """
    clip_selected = pyqtSignal(str, str)  # Segnale per notificare la selezione di una clip
    merge_clips_requested = pyqtSignal()   # Segnale per richiedere l'unione delle clip

    def __init__(self, title="Progetto", closable=True, parent=None):
        super().__init__(title, closable=closable, parent=parent)
        self.setToolTip("Mostra i dettagli e le clip del progetto corrente.")
        self.project_data = None
        self.project_dir = None
        self.gnai_path = None

        self._setup_ui()
        self.list_clips.itemDoubleClicked.connect(self._on_clip_selected)
        self.btn_merge_clips.clicked.connect(self.merge_clips_requested.emit)


    def _setup_ui(self):
        """Crea e organizza i widget dell'interfaccia utente."""
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # GroupBox per le informazioni del progetto
        project_info_group = QGroupBox("Dettagli Progetto")
        form_layout = QFormLayout(project_info_group)
        self.lbl_project_name = QLabel("N/A")
        self.lbl_project_path = QLabel("N/A")
        form_layout.addRow("<b>Nome:</b>", self.lbl_project_name)
        form_layout.addRow("<b>Percorso:</b>", self.lbl_project_path)

        # GroupBox per le clip
        clips_group = QGroupBox("Clip Video")
        clips_layout = QVBoxLayout(clips_group)
        self.list_clips = QListWidget()
        self.list_clips.setToolTip("Fai doppio click su una clip per caricarla.")

        self.btn_merge_clips = QPushButton("Unisci Clip")
        self.btn_merge_clips.setToolTip("Unisci tutte le clip in un unico video.")

        clips_layout.addWidget(self.list_clips)
        clips_layout.addWidget(self.btn_merge_clips)

        main_layout.addWidget(project_info_group)
        main_layout.addWidget(clips_group)

        self.addWidget(main_widget)

    def _on_clip_selected(self, item):
        """Gestisce il doppio click su una clip."""
        clip_filename = item.text()
        if self.project_data and self.project_dir:
            # Trova i metadati associati
            metadata_filename = ""
            for clip in self.project_data.get("clips", []):
                if clip.get("clip_filename") == clip_filename:
                    metadata_filename = clip.get("metadata_filename")
                    break
            self.clip_selected.emit(clip_filename, metadata_filename)


    def load_project_data(self, project_data, project_dir, gnai_path):
        """Carica i dati del progetto nel dock."""
        self.project_data = project_data
        self.project_dir = project_dir
        self.gnai_path = gnai_path

        self.lbl_project_name.setText(project_data.get("projectName", "N/A"))
        self.lbl_project_path.setText(project_dir)

        self.list_clips.clear()
        clips = project_data.get("clips", [])
        if clips:
            for clip in clips:
                self.list_clips.addItem(clip.get("clip_filename"))
        else:
            self.list_clips.addItem("Nessuna clip trovata.")

    def clear_dock(self):
        """Resetta il dock allo stato iniziale."""
        self.lbl_project_name.setText("N/A")
        self.lbl_project_path.setText("N/A")
        self.list_clips.clear()
        self.project_data = None
        self.project_dir = None
        self.gnai_path = None