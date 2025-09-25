import os
import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout, QSizePolicy
from PyQt6.QtCore import Qt
from src.ui.CustomDock import CustomDock

class InfoDock(CustomDock):
    def __init__(self, title="Informazioni Video", parent=None):
        super().__init__(title, parent=parent, closable=True)
        self.setToolTip("Dock informativo che mostra i metadati del video.")

        # Main widget
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Create a group box
        info_group = QGroupBox("Dettagli Media")

        # Use QFormLayout for a cleaner key-value presentation
        form_layout = QFormLayout(info_group)
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        # --- Labels to display information ---
        self.video_path_label = self._create_info_label()
        self.duration_label = self._create_info_label()
        self.language_label = self._create_info_label()
        self.video_date_label = self._create_info_label()
        self.transcription_date_label = self._create_info_label()
        self.summary_date_label = self._create_info_label()
        self.summary_label = self._create_info_label()
        self.summary_integrated_label = self._create_info_label()

        # Add rows to the form layout
        form_layout.addRow("<b>Path:</b>", self.video_path_label)
        form_layout.addRow("<b>Durata:</b>", self.duration_label)
        form_layout.addRow("<b>Lingua:</b>", self.language_label)
        form_layout.addRow("<b>Data Video:</b>", self.video_date_label)
        form_layout.addRow("<b>Data Trascrizione:</b>", self.transcription_date_label)
        form_layout.addRow("<b>Data Riassunto:</b>", self.summary_date_label)
        form_layout.addRow("<b>Riassunto:</b>", self.summary_label)
        form_layout.addRow("<b>Riassunto Integrato:</b>", self.summary_integrated_label)

        main_layout.addWidget(info_group)
        self.addWidget(main_widget)

        self._apply_styles()

    def _create_info_label(self):
        """Helper to create a value label for the form layout."""
        label = QLabel("N/A")
        label.setWordWrap(True)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return label

    def _apply_styles(self):
        """Applies a modern stylesheet to the widget."""
        self.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
                background-color: transparent;
            }
            QLabel {
                font-size: 12px;
                padding: 2px;
            }
        """)

    def _format_date(self, date_string):
        """Formats an ISO date string to a more readable format."""
        if not date_string or date_string == "N/A":
            return "N/A"
        try:
            dt = datetime.datetime.fromisoformat(date_string)
            return dt.strftime("%d/%m/%Y %H:%M:%S")
        except (ValueError, TypeError):
            return date_string

    def update_info(self, info_dict):
        """
        Populates the labels with data from a dictionary.
        """
        if not info_dict:
            self.clear_info()
            return

        # Use .get() to avoid errors if a key is missing
        self.video_path_label.setText(info_dict.get("video_path", "N/A"))

        duration_sec = info_dict.get("duration")
        if isinstance(duration_sec, (int, float)):
            mins, secs = divmod(int(duration_sec), 60)
            self.duration_label.setText(f"{mins}m {secs}s")
        else:
            self.duration_label.setText("N/A")

        self.language_label.setText(info_dict.get("language", "N/A"))

        self.video_date_label.setText(self._format_date(info_dict.get("video_date")))
        self.transcription_date_label.setText(self._format_date(info_dict.get("transcription_date")))
        self.summary_date_label.setText(self._format_date(info_dict.get("summary_date")))

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