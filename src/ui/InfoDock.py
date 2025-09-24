import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox
from PyQt6.QtCore import Qt
from src.ui.CustomDock import CustomDock

class InfoDock(CustomDock):
    def __init__(self, title="Informazioni Video", parent=None):
        super().__init__(title, parent=parent, closable=True)
        self.setToolTip("Dock informativo che mostra i metadati del video.")

        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Create a group box
        info_group = QGroupBox("Dettagli Media")
        group_layout = QVBoxLayout(info_group)

        # --- Labels to display information ---
        self.video_path_label = self._create_info_label(group_layout, "Path:")
        self.duration_label = self._create_info_label(group_layout, "Durata:")
        self.language_label = self._create_info_label(group_layout, "Lingua:")
        self.video_date_label = self._create_info_label(group_layout, "Data Video:")
        self.transcription_date_label = self._create_info_label(group_layout, "Data Trascrizione:")
        self.summary_date_label = self._create_info_label(group_layout, "Data Riassunto:")

        # --- Labels for summaries (optional, can be text edits if needed) ---
        self.summary_label = self._create_info_label(group_layout, "Riassunto:")
        self.summary_integrated_label = self._create_info_label(group_layout, "Riassunto Integrato:")

        main_layout.addWidget(info_group)
        self.addWidget(main_widget)

    def _create_info_label(self, layout, text):
        """Helper to create a label pair and add it to the layout."""
        container = QWidget()
        label_layout = QVBoxLayout(container)
        label_layout.setContentsMargins(0, 0, 0, 5) # Add some spacing below

        key_label = QLabel(f"<b>{text}</b>")
        value_label = QLabel("N/A")
        value_label.setWordWrap(True) # Allow text to wrap

        label_layout.addWidget(key_label)
        label_layout.addWidget(value_label)

        layout.addWidget(container)
        return value_label

    def update_info(self, info_dict):
        """
        Populates the labels with data from a dictionary.
        """
        if not info_dict:
            self.clear_info()
            return

        # Use .get() to avoid errors if a key is missing
        self.video_path_label.setText(os.path.basename(info_dict.get("video_path", "N/A")))

        duration_sec = info_dict.get("duration")
        if isinstance(duration_sec, (int, float)):
            mins, secs = divmod(int(duration_sec), 60)
            self.duration_label.setText(f"{mins}m {secs}s")
        else:
            self.duration_label.setText("N/A")

        self.language_label.setText(info_dict.get("language", "N/A"))
        self.video_date_label.setText(info_dict.get("video_date", "N/A"))
        self.transcription_date_label.setText(info_dict.get("transcription_date", "N/A"))
        self.summary_date_label.setText(info_dict.get("summary_date", "N/A"))

        # For summaries, you might want to show a snippet or just "Generato"
        summary_gen = info_dict.get("summary_generated", "")
        self.summary_label.setText("Sì" if summary_gen else "No")

        summary_int = info_dict.get("summary_generated_integrated", "")
        self.summary_integrated_label.setText("Sì" if summary_int else "No")

    def clear_info(self):
        """Clears all the labels."""
        self.video_path_label.setText("N/A")
        self.duration_label.setText("N/A")
        self.language_label.setText("N/A")
        self.video_date_label.setText("N/A")
        self.transcription_date_label.setText("N/A")
        self.summary_date_label.setText("N/A")
        self.summary_label.setText("N/A")
        self.summary_integrated_label.setText("N/A")
