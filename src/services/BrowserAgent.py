# services/BrowserAgent.py
import os
import asyncio
import logging
import json
from typing import Optional, Dict, List
import webbrowser
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QLabel, QPushButton, QTextEdit, QProgressDialog,
    QMessageBox, QComboBox, QCheckBox, QGroupBox,
    QFormLayout, QDialogButtonBox, QFileDialog, QRadioButton,
    QTabWidget, QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QSettings

# Import browser_use components
from browser_use.agent.service import Agent
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContextConfig
from browser_use.controller.service import Controller
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
# Importa la classe FrameExtractor
from src.services.FrameExtractor import FrameExtractor
from src.config import CLAUDE_MODEL_BROWSER_AGENT
from src.config import ANTHROPIC_API_KEY, MODEL_3_5_SONNET, MODEL_3_HAIKU, PROMPT_BROWSER_GUIDE


# Modifica della classe AgentConfig nella parte superiore del file BrowserAgent.py
class AgentConfig:
    """Classe per gestire la configurazione dell'agente"""

    def __init__(self):
        from src.config import ANTHROPIC_API_KEY, CLAUDE_MODEL_BROWSER_AGENT

        self.api_key = ANTHROPIC_API_KEY
        self.settings = QSettings("ThemaConsulting", "GeniusAI")

        # Carica il modello dalle impostazioni o usa quello predefinito
        self.model_name = self.settings.value("models/browser_agent", CLAUDE_MODEL_BROWSER_AGENT)

        self.headless = False
        self.use_vision = True
        self.max_steps = 25
        self.load_from_settings()

    def load_from_settings(self):
        """Carica la configurazione dalle impostazioni salvate"""
        self.api_key = self.settings.value("agent/api_key", self.api_key)
        self.headless = self.settings.value("agent/headless", self.headless, type=bool)
        self.use_vision = self.settings.value("agent/use_vision", self.use_vision, type=bool)
        self.max_steps = self.settings.value("agent/max_steps", self.max_steps, type=int)

    def save_to_settings(self):
        """Salva la configurazione nelle impostazioni"""
        self.settings.setValue("agent/api_key", self.api_key)
        self.settings.setValue("models/browser_agent", self.model_name)
        self.settings.setValue("agent/headless", self.headless)
        self.settings.setValue("agent/use_vision", self.use_vision)
        self.settings.setValue("agent/max_steps", self.max_steps)

    def to_dict(self):
        """Restituisce un dizionario con la configurazione"""
        return {
            "api_key": self.api_key,
            "model_name": self.model_name,
            "headless": self.headless,
            "use_vision": self.use_vision,
            "max_steps": self.max_steps
        }

    def from_dict(self, config_dict):
        """Aggiorna la configurazione da un dizionario"""
        if "api_key" in config_dict:
            self.api_key = config_dict["api_key"]
        if "model_name" in config_dict:
            self.model_name = config_dict["model_name"]
        if "headless" in config_dict:
            self.headless = config_dict["headless"]
        if "use_vision" in config_dict:
            self.use_vision = config_dict["use_vision"]
        if "max_steps" in config_dict:
            self.max_steps = config_dict["max_steps"]


class BrowserAgentWorker(QObject):
    """Worker class per eseguire l'agente browser in un thread separato"""

    finished = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    error = pyqtSignal(str)

    def __init__(self, task: str, config: AgentConfig):
        super().__init__()
        self.task = task
        self.config = config
        self.running = False

    async def run_agent_async(self):
        browser = None
        try:
            # Configurazione browser
            browser_config = BrowserConfig(
                headless=self.config.headless,
                disable_security=True
            )

            # Inizializza browser context config
            context_config = BrowserContextConfig(
                browser_window_size={'width': 1280, 'height': 900},
                minimum_wait_page_load_time=0.5,
                highlight_elements=True
            )

            # Inizializza il browser
            browser = Browser(config=browser_config)

            # Crea LLM basato sul modello selezionato
            if "claude" in self.config.model_name.lower():
                llm = ChatAnthropic(
                    model_name=self.config.model_name,
                    anthropic_api_key=self.config.api_key,
                    temperature=0.0
                )
            else:
                llm = ChatOpenAI(
                    model_name=self.config.model_name,
                    openai_api_key=self.config.api_key,
                    temperature=0.0
                )

            # Inizializza controller
            controller = Controller()

            # Inizializza agente con progress tracking
            agent = Agent(
                task=self.task,
                llm=llm,
                browser=browser,
                controller=controller,
                use_vision=self.config.use_vision,
                max_actions_per_step=1
            )

            # Definisci e registra la callback per l'avanzamento
            async def progress_callback(state, model_output, step_num):
                if not self.running:
                    return
                progress_pct = min(int((step_num / self.config.max_steps) * 100), 99)
                goal = getattr(model_output, "next_goal", "Elaborazione...") if model_output else "Inizializzazione..."
                self.progress.emit(progress_pct, str(goal))

            # Registra la callback correttamente
            agent.register_new_step_callback = progress_callback

            # Esegui l'agente
            self.running = True
            history = await agent.run(max_steps=self.config.max_steps)

            if not self.running:
                return

            # Ottieni il risultato finale
            final_result = history.final_result() or "Task completato senza risultato esplicito."

            # Emetti il risultato
            self.progress.emit(100, "Task completato!")
            self.finished.emit(final_result)

        except Exception as e:
            if self.running:
                import traceback
                error_details = traceback.format_exc()
                self.error.emit(f"Errore nell'esecuzione dell'agente: {str(e)}\n\n{error_details}")
                logging.error(f"Errore in BrowserAgentWorker: {e}", exc_info=True)
        finally:
            # Assicurati che il browser venga chiuso alla fine
            if browser:
                try:
                    await browser.close()
                except Exception as e:
                    logging.error(f"Errore nella chiusura del browser: {e}")

    def run(self):
        asyncio.run(self.run_agent_async())

    def stop(self):
        self.running = False


class AgentRunThread(QThread):
    """Thread per eseguire il browser agent"""

    def __init__(self, worker):
        super().__init__()
        self.worker = worker

    def run(self):
        self.worker.run()

    def stop(self):
        self.worker.stop()
        self.wait()


class UnifiedBrowserAgentDialog(QDialog):
    """Dialog unificato per configurare ed eseguire l'agente browser"""

    def __init__(self, parent=None, agent_config=None, transcription_text=None):
        super().__init__(parent)
        self.setWindowTitle("Browser Agent - Configurazione ed Esecuzione")
        self.setMinimumWidth(700)
        self.agent_config = agent_config or AgentConfig()
        self.transcription_text = transcription_text or ""
        self.agent_thread = None
        self.result = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Crea un widget con tab per separare configurazione ed esecuzione
        tabWidget = QTabWidget()
        configTab = QWidget()
        taskTab = QWidget()

        # Configurazione UI del tab di configurazione
        configLayout = QVBoxLayout(configTab)

        # API Key section
        apiGroup = QGroupBox("API Key")
        apiLayout = QFormLayout()
        self.apiKeyEdit = QLineEdit(self.agent_config.api_key)
        self.apiKeyEdit.setEchoMode(QLineEdit.EchoMode.Password)
        apiLayout.addRow("API Key:", self.apiKeyEdit)
        apiGroup.setLayout(apiLayout)
        configLayout.addWidget(apiGroup)

        # Model selection
        modelGroup = QGroupBox("Selezione Modello")
        modelLayout = QFormLayout()
        self.modelCombo = QComboBox()
        self.modelCombo.addItems([
            "claude-3-7-sonnet-20250219",
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307",
            "gpt-4-turbo",
            "gpt-4o"
        ])
        # Trova e seleziona il modello corrente
        index = self.modelCombo.findText(self.agent_config.model_name)
        if index >= 0:
            self.modelCombo.setCurrentIndex(index)
        modelLayout.addRow("Modello:", self.modelCombo)
        modelGroup.setLayout(modelLayout)
        configLayout.addWidget(modelGroup)

        # Browser options
        browserGroup = QGroupBox("Opzioni Browser")
        browserLayout = QFormLayout()
        self.headlessCheck = QCheckBox("Esegui browser in modalità headless")
        self.headlessCheck.setChecked(self.agent_config.headless)
        self.visionCheck = QCheckBox("Usa capacità visione")
        self.visionCheck.setChecked(self.agent_config.use_vision)
        self.stepsEdit = QLineEdit(str(self.agent_config.max_steps))
        browserLayout.addRow("", self.headlessCheck)
        browserLayout.addRow("", self.visionCheck)
        browserLayout.addRow("Passi Massimi:", self.stepsEdit)
        browserGroup.setLayout(browserLayout)
        configLayout.addWidget(browserGroup)

        # Pulsante per salvare configurazione
        saveConfigButton = QPushButton("Salva Configurazione")
        saveConfigButton.clicked.connect(self.saveConfiguration)
        configLayout.addWidget(saveConfigButton)

        # Configurazione UI del tab di esecuzione task
        taskLayout = QVBoxLayout(taskTab)

        # Task source selection
        taskSourceGroup = QGroupBox("Fonte del Task")
        taskSourceLayout = QVBoxLayout()

        self.manualTaskRadio = QRadioButton("Inserire manualmente il task")
        self.transcriptionTaskRadio = QRadioButton("Usa il testo dalla trascrizione come contesto")

        # Set default based on whether transcription is available
        if self.transcription_text:
            self.transcriptionTaskRadio.setChecked(True)
        else:
            self.manualTaskRadio.setChecked(True)
            self.transcriptionTaskRadio.setEnabled(False)

        taskSourceLayout.addWidget(self.manualTaskRadio)
        taskSourceLayout.addWidget(self.transcriptionTaskRadio)
        taskSourceGroup.setLayout(taskSourceLayout)
        taskLayout.addWidget(taskSourceGroup)

        # Task input
        taskGroup = QGroupBox("Descrizione Task")
        taskLayout2 = QVBoxLayout()
        self.taskEdit = QTextEdit()
        self.taskEdit.setPlaceholderText("Inserisci il task per il browser agent...")
        taskLayout2.addWidget(self.taskEdit)
        taskGroup.setLayout(taskLayout2)
        taskLayout.addWidget(taskGroup)

        # Connect task source radio buttons
        self.manualTaskRadio.toggled.connect(self.updateTaskSource)
        self.transcriptionTaskRadio.toggled.connect(self.updateTaskSource)

        # Buttons for running and stopping
        btnLayout = QHBoxLayout()
        self.runButton = QPushButton("Esegui Agent")
        self.runButton.clicked.connect(self.runAgent)
        self.stopButton = QPushButton("Ferma Agent")
        self.stopButton.clicked.connect(self.stopAgent)
        self.stopButton.setEnabled(False)
        btnLayout.addWidget(self.runButton)
        btnLayout.addWidget(self.stopButton)
        taskLayout.addLayout(btnLayout)

        # Result display
        resultGroup = QGroupBox("Risultati Agent")
        resultLayout = QVBoxLayout()
        self.resultEdit = QTextEdit()
        self.resultEdit.setReadOnly(True)
        resultLayout.addWidget(self.resultEdit)
        resultGroup.setLayout(resultLayout)
        taskLayout.addWidget(resultGroup)

        # Aggiungi i tab al widget
        tabWidget.addTab(configTab, "Configurazione")
        tabWidget.addTab(taskTab, "Esecuzione")

        layout.addWidget(tabWidget)

        # Close button
        closeButton = QPushButton("Chiudi")
        closeButton.clicked.connect(self.close)
        layout.addWidget(closeButton)

        self.setLayout(layout)

        # Initialize task text
        self.updateTaskSource()

    def saveConfiguration(self):
        config_dict = {
            "api_key": self.apiKeyEdit.text(),
            "model_name": self.modelCombo.currentText(),
            "headless": self.headlessCheck.isChecked(),
            "use_vision": self.visionCheck.isChecked(),
            "max_steps": int(self.stepsEdit.text())
        }
        self.agent_config.from_dict(config_dict)
        self.agent_config.save_to_settings()
        QMessageBox.information(self, "Configurazione Salvata",
                                "La configurazione dell'agente è stata salvata con successo.")

    def updateTaskSource(self):
        """Aggiorna il contenuto del campo task in base alla fonte selezionata"""
        if self.transcriptionTaskRadio.isChecked() and self.transcription_text:
            self.taskEdit.setPlainText(
                f"Basato sul seguente contesto, esegui una ricerca completa sul web:\n\n"
                f"{self.transcription_text}\n\n"
                f"Esegui una ricerca approfondita per trovare le informazioni più rilevanti riguardo a questo argomento."
            )
        elif self.manualTaskRadio.isChecked():
            self.taskEdit.clear()
            self.taskEdit.setPlaceholderText("Inserisci il task per il browser agent...")

    def runAgent(self):
        # Prima salva la configurazione
        #self.saveConfiguration()

        task = self.taskEdit.toPlainText().strip()
        if not task:
            QMessageBox.warning(self, "Task Mancante", "Inserisci un task per l'agente.")
            return

        if not self.agent_config.api_key:
            QMessageBox.warning(self, "API Key Mancante", "Configura una API key.")
            return

        self.runButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.resultEdit.clear()

        # Aggiungi debug info
        self.resultEdit.append(
            f"Configurazione agente:\n- API Key: {'Configurata' if self.agent_config.api_key else 'Mancante'}\n- Modello: {self.agent_config.model_name}\n- Headless: {self.agent_config.headless}\n- Max steps: {self.agent_config.max_steps}\n\nAvvio agente in corso...\n")

        # Create progress dialog
        self.progressDialog = QProgressDialog("Esecuzione browser agent...", "Annulla", 0, 100, self)
        self.progressDialog.setWindowTitle("Progresso Agent")
        self.progressDialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progressDialog.canceled.connect(self.stopAgent)

        if self.agent_thread and self.agent_thread.isRunning():
            self.stopAgent()

        # Crea nuovi worker e thread
        self.worker = BrowserAgentWorker(task=task, config=self.agent_config)
        self.worker.progress.connect(self.updateProgress)
        self.worker.finished.connect(self.onAgentFinished)
        self.worker.error.connect(self.onAgentError)

        self.agent_thread = AgentRunThread(self.worker)
        self.agent_thread.start()

        self.progressDialog.show()

    def stopAgent(self):
        if self.agent_thread and self.agent_thread.isRunning():
            self.progressDialog.setLabelText("Arresto agente...")
            self.agent_thread.stop()

    def updateProgress(self, value, message):
        if self.progressDialog and not self.progressDialog.wasCanceled():
            self.progressDialog.setValue(value)
            self.progressDialog.setLabelText(f"Esecuzione agente: {message}")

    def onAgentFinished(self, result):
        if self.progressDialog:
            self.progressDialog.close()

        self.result = result

        # Formatta il risultato in modo più leggibile
        formatted_result = f"=== RISULTATO DELL'AGENTE ===\n\n{result}\n\n"

        # Visualizza il risultato nella finestra di dialogo dell'agente
        self.resultEdit.setPlainText(formatted_result)

        # Riattiva i pulsanti
        self.runButton.setEnabled(True)
        self.stopButton.setEnabled(False)

        # Mostra un messaggio di completamento
        QMessageBox.information(self, "Operazione Completata",
                                "L'agente ha completato il task con successo!")

    def onAgentError(self, error_message):
        if self.progressDialog:
            self.progressDialog.close()

        # Formatta l'errore in modo più leggibile
        formatted_error = f"=== ERRORE DURANTE L'ESECUZIONE ===\n\n{error_message}\n\n"

        # Visualizza l'errore nella finestra di dialogo dell'agente
        self.resultEdit.setPlainText(formatted_error)

        # Riattiva i pulsanti
        self.runButton.setEnabled(True)
        self.stopButton.setEnabled(False)

        # Mostra un messaggio di errore
        QMessageBox.critical(self, "Errore Agent", "Si è verificato un errore durante l'esecuzione dell'agente.")


class BrowserAgent:
    """
    Classe principale per l'integrazione della funzionalità dell'agente browser
    con l'applicazione di elaborazione video
    """

    def __init__(self, parent=None):
        self.parent = parent
        self.agent_config = AgentConfig()
        self.frame_data = None

    def getTranscriptionText(self):
        """Ottiene il testo dalla transcriptionTextArea del parent"""
        if self.parent and hasattr(self.parent, 'transcriptionTextArea'):
            return self.parent.transcriptionTextArea.toPlainText()
        return ""

    def showAgentDialog(self):
        """Mostra il dialog unificato di configurazione ed esecuzione"""
        dialog = UnifiedBrowserAgentDialog(self.parent, self.agent_config, self.getTranscriptionText())
        dialog.exec()

    # Questi metodi sono mantenuti per compatibilità con il codice esistente
    def showConfigDialog(self):
        """Reindirizza al nuovo dialog unificato"""
        return self.showAgentDialog()

    def runAgent(self):
        """Reindirizza al nuovo dialog unificato"""
        return self.showAgentDialog()

    def generate_operational_guide(self, video_path=None, num_frames=5, language="italiano"):
        """
        Estrae i frame dal video, genera una guida operativa basata
        sulle descrizioni dei frame e la inserisce nella transcriptionTextArea
        """
        try:
            # Se non viene fornito un percorso del video, usa quello attualmente caricato nell'applicazione
            if not video_path:
                if hasattr(self.parent, 'videoPathLineEdit') and self.parent.videoPathLineEdit:
                    video_path = self.parent.videoPathLineEdit
                else:
                    QMessageBox.warning(self.parent, "Video mancante",
                                        "Nessun video caricato. Carica prima un video.")
                    return False

            # Mostra un dialog di progresso
            progress_dialog = QProgressDialog("Estrazione e analisi dei frame in corso...", "Annulla", 0, 100,
                                              self.parent)
            progress_dialog.setWindowTitle("Generazione Guida Operativa")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setValue(0)

            # 1. Estrai i frame dal video utilizzando la funzionalità di FrameExtractor
            progress_dialog.setLabelText("Estrazione dei frame dal video...")
            progress_dialog.setValue(10)

            # Carica il modello dalle impostazioni
            settings = QSettings("ThemaConsulting", "GeniusAI")
            claude_model = settings.value("models/browser_agent", CLAUDE_MODEL_BROWSER_AGENT)

            # Crea un'istanza di FrameExtractor
            extractor = FrameExtractor(
                video_path=video_path,
                num_frames=num_frames,
                anthropic_api_key=self.agent_config.api_key
            )

            # Estrai i frame
            progress_dialog.setLabelText("Estraendo i frame dal video...")
            frames = extractor.extract_frames()

            # 2. Analizza i frame con il modello di visione
            progress_dialog.setLabelText("Analizzando i frame con AI Vision...")
            progress_dialog.setValue(30)
            frame_data = extractor.analyze_frames_batch(frames, language)

            # 3. Prepara il testo unito delle descrizioni
            descriptions = [fd['description'] for fd in frame_data]
            joined_descriptions = "\n".join(descriptions)

            # 4. Leggi il prompt per la guida operativa dal file
            with open(PROMPT_BROWSER_GUIDE, 'r', encoding='utf-8') as f:
                prompt_template = f.read()

            # Formatta il prompt
            prompt = prompt_template.format(
                joined_descriptions=joined_descriptions,
                language=language
            )

            # 5. Genera la guida operativa usando Anthropic
            progress_dialog.setLabelText("Generazione della guida operativa in corso...")
            progress_dialog.setValue(60)

            # Importa Anthropic se non è già stato importato
            from anthropic import Anthropic
            client = Anthropic(api_key=self.agent_config.api_key)

            # Chiama l'API
            response = client.messages.create(
                model=claude_model,  # Usa il modello dalle impostazioni
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # 6. Estrai il testo della risposta
            guide_text = response.content[0].text

            # 7. Inserisci il testo nella transcriptionTextArea
            progress_dialog.setLabelText("Aggiornamento interfaccia...")
            progress_dialog.setValue(90)

            if hasattr(self.parent, 'transcriptionTextArea'):
                self.parent.transcriptionTextArea.setPlainText(guide_text)

            # 8. Salva i dati dei frame per riferimento futuro
            self.frame_data = frame_data

            # Chiudi il dialog di progresso
            progress_dialog.setValue(100)
            progress_dialog.close()

            # Mostra un messaggio di conferma
            QMessageBox.information(self.parent, "Guida Operativa Generata",
                                    "La guida operativa è stata generata con successo e inserita nell'area di trascrizione.")

            return True

        except Exception as e:
            # Gestisci gli errori
            if 'progress_dialog' in locals():
                progress_dialog.close()
            QMessageBox.critical(self.parent, "Errore",
                                 f"Si è verificato un errore durante la generazione della guida: {str(e)}")
            logging.error(f"Errore nella generazione della guida operativa: {e}", exc_info=True)
            return False

    def create_guide_agent(self):
        """
        Metodo completo che:
        1. Estrai i frame dal video
        2. Genera una guida operativa
        3. Lancia l'agente browser
        """
        # Verifica se è caricato un video
        video_path = None
        if hasattr(self.parent, 'videoPathLineEdit') and self.parent.videoPathLineEdit:
            video_path = self.parent.videoPathLineEdit
        else:
            QMessageBox.warning(self.parent, "Video mancante",
                                "Nessun video caricato. Carica prima un video.")
            return

        # Ottieni il numero di frame da estrarre
        num_frames = 5  # Valore predefinito
        if hasattr(self.parent, 'frameCountSpin'):
            num_frames = self.parent.frameCountSpin.value()

        # Ottieni la lingua
        language = "italiano"  # Default
        if hasattr(self.parent, 'languageComboBox'):
            language = self.parent.languageComboBox.currentText()

        # Genera la guida operativa
        self.generate_operational_guide(video_path, num_frames, language)