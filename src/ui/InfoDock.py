import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout, QSizePolicy
from PyQt6.QtCore import Qt

# Si presume che CustomDock sia una classe simile a un QWidget con un metodo addWidget,
# come nel codice originale dell'utente.
from src.ui.CustomDock import CustomDock


# Codice di fallback per testare se CustomDock non è disponibile.
# Questo fallback non funzionerà se si esegue il codice così com'è a causa della
# differenza tra setWidget e addWidget. La correzione è nel codice principale.
# try:
#     from src.ui.CustomDock import CustomDock
# except ImportError:
#     from PyQt6.QtWidgets import QDockWidget as CustomDock


class InfoDock(CustomDock):
    """
    Un dock informativo che visualizza i metadati di un file multimediale
    con uno stile moderno, chiaro e facilmente manutenibile.
    """

    def __init__(self, title="Informazioni Video", parent=None):
        super().__init__(title, parent=parent)
        self.setToolTip("Mostra i dettagli del video selezionato.")

        self.DEFAULT_TEXT = "Non disponibile"
        self.info_labels = {}  # Dizionario per memorizzare le etichette dei valori

        # Centralizza la definizione dei campi per una facile manutenzione
        # Formato: "Nome visualizzato": "chiave_dati"
        self.fields = {
            "File": "video_path",
            "Durata": "duration",
            "Lingua": "language",
            "Data Video": "video_date",
            "Data Trascrizione": "transcription_date",
            "Data Riassunto": "summary_date",
            "Riassunto Generato": "summary_generated",
            "Riassunto Integrato": "summary_generated_integrated"
        }

        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        """Crea e organizza i widget dell'interfaccia utente."""
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)  # Aggiunge un po' di respiro

        # GroupBox che si espande per riempire lo spazio
        info_group = QGroupBox("Dettagli del Media")
        info_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Layout a form per una presentazione pulita chiave-valore
        form_layout = QFormLayout(info_group)
        form_layout.setVerticalSpacing(15)  # Aumenta lo spazio verticale tra le righe
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        # Creazione dinamica delle etichette
        for display_name, data_key in self.fields.items():
            key_label = QLabel(f"<b>{display_name}</b>")
            value_label = QLabel(self.DEFAULT_TEXT)
            value_label.setWordWrap(True)
            value_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

            form_layout.addRow(key_label, value_label)
            self.info_labels[data_key] = value_label

        main_layout.addWidget(info_group)

        # --- CORREZIONE QUI ---
        # Usa addWidget() come definito dalla tua classe base CustomDock,
        # invece di setWidget() che appartiene a QDockWidget.
        self.addWidget(main_widget)

    def _apply_styles(self):
        """Applica uno stylesheet per un aspetto più grande, chiaro e moderno."""
        self.setStyleSheet("""
            QGroupBox {
                background-color: #f7f7f7;
                font-size: 18px;
                font-weight: bold;
                border: 1px solid #c0c0c0;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 5px 10px;
                background-color: #e0e0e0;
                border-radius: 4px;
            }
            /* Stile per le etichette delle chiavi (es. "Durata") */
            QLabel[text*="<b>"] { /* Selettore alternativo per le etichette in grassetto */
                font-size: 14px;
                font-weight: bold;
                color: #333;
            }
            /* Stile per le etichette dei valori */
            QFormLayout > QLabel:not([text*="<b>"]) {
                font-size: 14px;
                color: #555;
                padding-left: 5px; /* Spazio tra chiave e valore */
            }
        """)

    def _format_date(self, date_string):
        """Formatta una data in formato ISO in un formato leggibile."""
        if not date_string or date_string == self.DEFAULT_TEXT:
            return self.DEFAULT_TEXT
        try:
            # Rimuove la 'Z' se presente, non sempre gestita da fromisoformat
            if isinstance(date_string, str) and date_string.endswith('Z'):
                date_string = date_string[:-1] + '+00:00'
            dt = datetime.datetime.fromisoformat(date_string)
            return dt.strftime("%d/%m/%Y, ore %H:%M")
        except (ValueError, TypeError):
            return date_string  # Ritorna la stringa originale se il formato non è valido

    def update_info(self, info_dict):
        """Popola le etichette con i dati da un dizionario."""
        if not info_dict:
            self.clear_info()
            return

        for data_key, label in self.info_labels.items():
            value = info_dict.get(data_key)  # Usa get senza default per distinguere chiave assente da valore None

            if value is None or value == '':
                formatted_value = self.DEFAULT_TEXT
            else:
                # Formattazione speciale per campi specifici
                if data_key == "duration" and isinstance(value, (int, float)):
                    mins, secs = divmod(int(value), 60)
                    formatted_value = f"{mins} minuti e {secs} secondi"
                elif "date" in data_key:
                    formatted_value = self._format_date(value)
                elif "generated" in data_key:
                    formatted_value = "Sì" if value else "No"
                else:
                    formatted_value = str(value)

            label.setText(formatted_value)

    def clear_info(self):
        """Resetta tutte le etichette al valore predefinito."""
        for label in self.info_labels.values():
            label.setText(self.DEFAULT_TEXT)