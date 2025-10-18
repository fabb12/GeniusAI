import json
from PyQt6.QtCore import QPoint, QSize, QRect
from PyQt6.QtWidgets import QFileDialog, QMessageBox
import logging
from src.config import DOCK_SETTINGS_FILE
from src.config import DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT

class DockSettingsManager:
    def __init__(self, main_window, docks, parent):
        self.parent = parent
        self.main_window = main_window
        self.docks = docks
        self.settings_file = DOCK_SETTINGS_FILE

    def save_settings(self, settings_file=None):
        """
        Salva la geometria della finestra principale, lo stato dell'area dei dock
        e la configurazione granulare di ogni singolo dock (visibilità, geometria).
        """
        if not settings_file:
            settings_file = self.settings_file

        area = self.main_window.centralWidget()
        state = area.saveState()

        docks_config = {}
        for name, dock in self.docks.items():
            geom = dock.geometry()
            docks_config[name] = {
                'visible': dock.isVisible(),
                'geometry': [geom.x(), geom.y(), geom.width(), geom.height()]
            }

        settings = {
            'main_window': {
                'width': self.main_window.size().width(),
                'height': self.main_window.size().height(),
                'x': self.main_window.pos().x(),
                'y': self.main_window.pos().y()
            },
            'dock_state': state,
            'docks_config': docks_config
        }
        try:
            with open(settings_file, 'w') as file:
                json.dump(settings, file, indent=4)
            logging.info(f"Impostazioni del layout salvate in {settings_file}.")
            return True
        except IOError as e:
            logging.error(f"Errore durante il salvataggio del file di layout {settings_file}: {e}")
            return False

    def load_settings(self, settings_file=None):
        """
        Carica e applica la geometria della finestra, lo stato dell'area dei dock
        e la configurazione individuale di ogni dock.
        """
        if not settings_file:
            settings_file = self.settings_file

        try:
            with open(settings_file, 'r') as file:
                settings = json.load(file)

            # Ripristina dimensioni e posizione della finestra principale
            main_window_settings = settings.get('main_window', {})
            self.main_window.resize(
                QSize(main_window_settings.get('width', DEFAULT_WINDOW_WIDTH),
                      main_window_settings.get('height', DEFAULT_WINDOW_HEIGHT)))
            self.main_window.move(QPoint(main_window_settings.get('x', 100), main_window_settings.get('y', 100)))

            # Ripristina lo stato generale dell'area dei dock
            dock_state = settings.get('dock_state')
            if dock_state:
                area = self.main_window.centralWidget()
                area.restoreState(dock_state)
                logging.info("Stato generale dei dock ripristinato.")

            # Applica la configurazione granulare (visibilità e geometria) a ogni dock
            docks_config = settings.get('docks_config')
            if docks_config:
                for name, config in docks_config.items():
                    if name in self.docks:
                        dock = self.docks[name]
                        # Applica la visibilità prima di tutto
                        dock.setVisible(config.get('visible', True))

                        # Se il dock deve essere visibile, applica la geometria
                        if config.get('visible', True):
                            geom_data = config.get('geometry')
                            if geom_data and len(geom_data) == 4:
                                dock.setGeometry(QRect(*geom_data))
                logging.info("Configurazione granulare dei dock applicata.")
            else:
                logging.warning("Nessuna configurazione granulare trovata. Alcuni stati potrebbero non essere ripristinati.")

            self.main_window.updateViewMenu()

        except FileNotFoundError:
            logging.warning(f"File di impostazioni '{settings_file}' non trovato. Caricamento del layout di default.")
            self.loadDefaultLayout()
        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"File di impostazioni '{settings_file}' corrotto o malformato ({e}). Caricamento del layout di default.")
            QMessageBox.critical(self.main_window, "Errore di Caricamento",
                                 f"Il file di layout '{settings_file}' è corrotto o non valido.\n"
                                 "Verrà caricato il layout di default.")
            self.loadDefaultLayout()

    def save_layout_as(self):
        """Apre un dialogo per salvare il layout corrente in un file JSON."""
        filePath, _ = QFileDialog.getSaveFileName(self.main_window, "Salva Layout", "", "JSON Files (*.json)")
        if filePath:
            if self.save_settings(filePath):
                QMessageBox.information(self.main_window, "Successo", f"Layout salvato con successo in:\n{filePath}")
            else:
                QMessageBox.critical(self.main_window, "Errore", f"Impossibile salvare il layout in:\n{filePath}")

    def load_layout_from(self):
        """Apre un dialogo per caricare un layout da un file JSON."""
        filePath, _ = QFileDialog.getOpenFileName(self.main_window, "Carica Layout", "", "JSON Files (*.json)")
        if filePath:
            self.load_settings(filePath)

    def set_workspace(self, workspace_name):
        """Imposta la visibilità dei dock in base al workspace selezionato."""

        # Nascondi tutti i dock prima di impostare il nuovo layout
        for dock in self.docks.values():
            dock.setVisible(False)

        if workspace_name == "Registrazione":
            self.docks['recordingDock'].setVisible(True)
            self.docks['videoPlayerOutput'].setVisible(True)
            self.docks['projectDock'].setVisible(True)
        elif workspace_name == "Confronto":
            self.docks['videoPlayerDock'].setVisible(True)
            self.docks['videoPlayerOutput'].setVisible(True)
        elif workspace_name == "Trascrizione":
            self.docks['videoPlayerDock'].setVisible(True)
            self.docks['transcriptionDock'].setVisible(True)
            self.docks['projectDock'].setVisible(True)
        elif workspace_name == "Default":
            self.docks['videoNotesDock'].setVisible(True)
            self.docks['projectDock'].setVisible(True)
            self.docks['videoPlayerDock'].setVisible(True)
            self.docks['videoPlayerOutput'].setVisible(True)
            self.docks['transcriptionDock'].setVisible(True)
            self.docks['editingDock'].setVisible(True)
            self.docks['audioDock'].setVisible(True)

        self.main_window.updateViewMenu()

    def loadRecordingLayout(self):
        """Carica il layout per la registrazione video."""
        self.set_workspace("Registrazione")

    def loadComparisonLayout(self):
        """Carica il layout per confrontare due video."""
        self.set_workspace("Confronto")

    def loadTranscriptionLayout(self):
        """Carica il layout per la trascrizione."""
        self.set_workspace("Trascrizione")

    def loadDefaultLayout(self):
        """Carica il layout di default con i dock principali."""
        self.set_workspace("Default")
