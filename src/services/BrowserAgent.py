# File: src/services/BrowserAgent.py
# Updated to support dynamic LLM selection including Google Gemini

import os
import asyncio
import logging
import json
import traceback
import time
from typing import Optional, Dict, List
import webbrowser # Keep webbrowser for potential future use if needed outside the agent

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QLabel, QPushButton, QTextEdit, QProgressDialog,
    QMessageBox, QComboBox, QCheckBox, QGroupBox,
    QFormLayout, QDialogButtonBox, QFileDialog, QRadioButton,
    QTabWidget, QWidget, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QSettings, QTimer

# --- Langchain Imports ---
# Import browser_use components (assuming these are correctly installed/located)
try:
    from browser_use.agent.service import Agent
    from browser_use.browser.browser import Browser, BrowserConfig
    from browser_use.browser.context import BrowserContextConfig
    from browser_use.controller.service import Controller
except ImportError as e:
    logging.error(f"Failed to import browser_use components: {e}. Please ensure the library is installed.")
    # Define dummy classes to prevent NameErrors if import fails, allowing UI to load
    class Agent: pass
    class Browser: pass
    class BrowserConfig: pass
    class BrowserContextConfig: pass
    class Controller: pass

# Import LLM clients
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI # Keep for potential OpenAI integration
from langchain_google_genai import ChatGoogleGenerativeAI # Import Gemini client
# Note: Ollama integration with langchain might require langchain_community

# --- Local Imports ---
from src.services.FrameExtractor import FrameExtractor # Used for guide generation
# Import configuration constants and structures
from src.config import (
    ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY, OLLAMA_ENDPOINT, # API Keys/Endpoints
    ACTION_MODELS_CONFIG, # Dictionary defining models per action
    PROMPT_BROWSER_GUIDE # Prompt for guide generation
)

# Configure Google GenAI (can be done once, potentially at app startup or here)
# FrameExtractor might also call this. It's generally safe to call multiple times.
if GOOGLE_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)
        logging.info("Google Generative AI SDK configured successfully.")
    except ImportError:
        logging.warning("google.generativeai library not found. Gemini models will not be available.")
    except Exception as e:
        logging.error(f"Failed to configure Google Generative AI SDK: {e}")
else:
    logging.warning("GOOGLE_API_KEY not found in environment. Gemini models may not work.")


class AgentConfig:
    """Classe per gestire la configurazione dell'agente"""

    def __init__(self):
        self.settings = QSettings("ThemaConsulting", "GeniusAI")

        # --- Load API Keys from config.py (which loads from .env) ---
        self.anthropic_api_key = ANTHROPIC_API_KEY
        self.google_api_key = GOOGLE_API_KEY
        self.openai_api_key = OPENAI_API_KEY
        # Note: Ollama doesn't typically use an API key, but an endpoint

        # --- Load Browser Agent specific settings ---
        agent_config_details = ACTION_MODELS_CONFIG.get('browser_agent', {})
        self.setting_key_model = agent_config_details.get('setting_key', 'models/browser_agent')
        self.default_model = agent_config_details.get('default', '') # Get default model for browser agent

        # Load the actual model name from QSettings, fallback to config default
        self.model_name = self.settings.value(self.setting_key_model, self.default_model)

        # Other agent settings with defaults
        self.headless = False
        self.use_vision = True # Vision capability often needed for browser agents
        self.max_steps = 25

        # Load saved values for these settings
        self.load_from_settings()

    def load_from_settings(self):
        """Carica la configurazione dalle impostazioni salvate"""
        # API Keys are loaded from environment by config.py, no need to load from QSettings usually
        # self.anthropic_api_key = self.settings.value("api_keys/anthropic", self.anthropic_api_key) # Example if storing keys
        self.model_name = self.settings.value(self.setting_key_model, self.default_model)
        self.headless = self.settings.value("agent/headless", self.headless, type=bool)
        self.use_vision = self.settings.value("agent/use_vision", self.use_vision, type=bool)
        self.max_steps = self.settings.value("agent/max_steps", self.max_steps, type=int)
        logging.debug(f"AgentConfig loaded: model={self.model_name}, headless={self.headless}, vision={self.use_vision}, steps={self.max_steps}")


    def save_to_settings(self):
        """Salva la configurazione nelle impostazioni"""
        # API Keys are typically not saved in QSettings due to security risks
        # self.settings.setValue("api_keys/anthropic", self.anthropic_api_key) # Example if storing keys
        self.settings.setValue(self.setting_key_model, self.model_name)
        self.settings.setValue("agent/headless", self.headless)
        self.settings.setValue("agent/use_vision", self.use_vision)
        self.settings.setValue("agent/max_steps", self.max_steps)
        logging.debug(f"AgentConfig saved: model={self.model_name}, headless={self.headless}, vision={self.use_vision}, steps={self.max_steps}")


    def to_dict(self):
        """Restituisce un dizionario con la configurazione"""
        return {
            "model_name": self.model_name,
            "headless": self.headless,
            "use_vision": self.use_vision,
            "max_steps": self.max_steps,
            # Include API keys if needed downstream, but be cautious
            # "anthropic_api_key": self.anthropic_api_key,
            # "google_api_key": self.google_api_key,
            # "openai_api_key": self.openai_api_key,
        }

    def from_dict(self, config_dict):
        """Aggiorna la configurazione da un dizionario"""
        # API keys usually come from environment, not dict typically
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
    log_message = pyqtSignal(str)

    def __init__(self, task: str, config: AgentConfig):
        super().__init__()
        self.task = task
        self.config = config # Use the passed AgentConfig instance
        self.running = False
        self.browser = None
        self.agent = None # Hold agent instance for potential interruption

    async def run_agent_async(self):
        """Core asynchronous logic to run the browser agent."""
        try:
            if not self.running:
                self.log_message.emit("Agent worker started but running flag is false. Aborting.")
                return

            self.progress.emit(5, "Inizializzazione configurazione...")
            self.log_message.emit(f"Using model: {self.config.model_name}")

            # --- LLM Initialization based on selected model ---
            llm = None
            model_id = self.config.model_name
            model_lower = model_id.lower()

            if model_lower.startswith("claude"):
                if not self.config.anthropic_api_key:
                    raise ValueError("Anthropic API Key non configurata.")
                llm = ChatAnthropic(
                    model_name=model_id,
                    anthropic_api_key=self.config.anthropic_api_key,
                    temperature=0.0,
                    max_tokens=4096 # Ensure sufficient tokens
                )
                self.log_message.emit(f"Inizializzato LLM: Anthropic ({model_id})")
            elif model_lower.startswith("gemini"):
                if not self.config.google_api_key:
                    raise ValueError("Google API Key non configurata.")
                # Ensure genai is configured (might have happened globally)
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=self.config.google_api_key)
                except Exception as e:
                    logging.warning(f"Re-configuring genai failed (might be ok): {e}")

                llm = ChatGoogleGenerativeAI(
                    model=model_id, # Use the full model name from config
                    google_api_key=self.config.google_api_key, # Pass key explicitly if needed
                    temperature=0.1, # Lower temp for reliability
                    convert_system_message_to_human=True # Often helpful for agents
                )
                self.log_message.emit(f"Inizializzato LLM: Google Gemini ({model_id})")

            elif model_lower.startswith("gpt"):
                 if not self.config.openai_api_key:
                     raise ValueError("OpenAI API Key non configurata.")
                 llm = ChatOpenAI(
                     model_name=model_id,
                     openai_api_key=self.config.openai_api_key,
                     temperature=0.0
                 )
                 self.log_message.emit(f"Inizializzato LLM: OpenAI ({model_id})")

            # Add Ollama support here if needed, potentially using langchain_community.ChatOllama
            # elif model_lower.startswith("ollama"):
            #     try:
            #         from langchain_community.chat_models import ChatOllama
            #         ollama_model_name = model_id.split(':', 1)[-1] # Extract model name after 'ollama:'
            #         llm = ChatOllama(model=ollama_model_name, base_url=OLLAMA_ENDPOINT, temperature=0.0)
            #         self.log_message.emit(f"Inizializzato LLM: Ollama ({ollama_model_name})")
            #     except ImportError:
            #         raise ImportError("Ollama support requires 'langchain-community'. Please install it.")
            #     except Exception as e:
            #         raise ValueError(f"Failed to initialize Ollama: {e}")

            else:
                raise ValueError(f"Modello LLM non supportato: {model_id}")

            if not self.running: return # Check running status after LLM init

            # --- Browser Setup ---
            self.progress.emit(10, "Configurazione browser...")
            browser_config = BrowserConfig(
                headless=self.config.headless,
                disable_security=True # Often needed for agent control
            )
            context_config = BrowserContextConfig(
                browser_window_size={'width': 1280, 'height': 900},
                minimum_wait_page_load_time=0.5,
                highlight_elements=True
            )

            if not self.running: return

            self.progress.emit(15, "Avvio browser...")
            self.browser = Browser(config=browser_config)
            self.log_message.emit("Browser inizializzato.")
            self.progress.emit(20, "Browser avviato")

            if not self.running: return

            # --- Controller and Agent Setup ---
            self.progress.emit(35, "Inizializzazione controller...")
            controller = Controller()
            if not self.running: return

            self.progress.emit(40, "Inizializzazione agente...")
            self.agent = Agent(
                task=self.task,
                llm=llm,
                browser=self.browser,
                controller=controller,
                use_vision=self.config.use_vision,
                max_actions_per_step=1
            )
            self.log_message.emit("Agente inizializzato.")
            self.progress.emit(45, "Agente pronto")

            # --- Progress Callback Setup ---
            async def progress_callback(state, model_output, step_num):
                if not self.running:
                    self.log_message.emit(f"Progress callback: stop requested at step {step_num}.")
                    return False # Signal to stop the agent run

                progress_pct = min(int(45 + (step_num / self.config.max_steps) * 50), 95)
                next_goal = getattr(model_output, "next_goal", "Elaborazione...") if model_output else "Inizializzazione..."

                # Log detailed state/output if needed for debugging
                self.log_message.emit(f"Step {step_num}/{self.config.max_steps}: {next_goal}")
                # Optionally log state or model_output details here

                self.progress.emit(progress_pct, str(next_goal))
                return True # Continue running

            self.agent.register_new_step_callback = progress_callback
            self.progress.emit(48, "Inizializzazione completata")

            if not self.running: return

            # --- Run Agent ---
            self.progress.emit(50, "Avvio esecuzione agente...")
            self.log_message.emit("Agent run loop starting.")

            history = await self.agent.run(max_steps=self.config.max_steps)

            # Check running flag immediately after run completes or is interrupted
            if not self.running:
                self.log_message.emit("Agent run loop interrupted by stop request.")
                self.progress.emit(100, "Operazione annullata")
                return # Exit early if stopped

            self.log_message.emit("Agent run loop finished.")
            self.progress.emit(95, "Elaborazione risultati...")
            final_result = history.final_result() if hasattr(history, 'final_result') else "Task completato (nessun risultato esplicito)."
            final_result = final_result or "Task completato senza risultato esplicito."

            self.progress.emit(99, "Task completato!")
            self.finished.emit(str(final_result)) # Ensure result is a string

        except ImportError as ie:
             error_msg = f"Errore di importazione: {str(ie)}. Assicurati che tutte le librerie necessarie (browser_use, langchain, etc.) siano installate."
             self.error.emit(error_msg)
             logging.error(error_msg, exc_info=True)
        except ValueError as ve: # Catch configuration errors (like missing keys)
             error_msg = f"Errore di configurazione: {str(ve)}"
             self.error.emit(error_msg)
             logging.error(error_msg, exc_info=False) # Don't need full traceback for config error
        except Exception as e:
            # Catch-all for other runtime errors
            error_details = traceback.format_exc()
            error_msg = f"Errore nell'esecuzione dell'agente: {type(e).__name__}: {str(e)}"
            self.error.emit(error_msg + f"\n\nDettagli:\n{error_details}")
            logging.error(f"Errore in BrowserAgentWorker: {e}", exc_info=True)
        finally:
            # --- Cleanup ---
            self.log_message.emit("Inizio pulizia risorse worker...")
            if self.browser:
                try:
                    self.progress.emit(98, "Chiusura browser...")
                    await self.browser.close()
                    self.progress.emit(100, "Browser chiuso con successo")
                    self.log_message.emit("Browser chiuso.")
                except Exception as browser_close_err:
                    self.log_message.emit(f"Errore durante chiusura browser: {browser_close_err}")
                    logging.error(f"Errore nella chiusura del browser: {browser_close_err}")
            self.browser = None
            self.agent = None # Clear agent reference
            self.log_message.emit("Pulizia risorse worker completata.")
            # Ensure running is false if we exit due to error or completion
            self.running = False


    def run(self):
        """Starts the asynchronous agent execution."""
        try:
            self.running = True
            self.log_message.emit("Worker run() started.")
            # Get or create an event loop for this thread
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            loop.run_until_complete(self.run_agent_async())
            self.log_message.emit("Worker run() finished.")

        except Exception as e:
            # Catch errors occurring during asyncio setup/run
            error_details = traceback.format_exc()
            self.log_message.emit(f"Errore fatale nel worker run(): {str(e)}\n{error_details}")
            self.error.emit(f"Errore fatale nel worker: {str(e)}\n{error_details}")
        finally:
            self.running = False # Ensure flag is reset

    def stop(self):
        """Requests the agent to stop processing."""
        self.log_message.emit("Richiesta di arresto ricevuta nel worker.")
        self.running = False # Set flag to false, checked within run_agent_async and callback
        # The agent loop should check self.running or the callback should return False
        # We don't forcefully kill the thread here, we signal it to stop gracefully.


class AgentRunThread(QThread):
    """Thread wrapper for executing the BrowserAgentWorker"""

    finished = pyqtSignal() # Signals when the thread itself has finished execution
    log_message = pyqtSignal(str) # Forwards log messages

    def __init__(self, worker: BrowserAgentWorker):
        super().__init__()
        self.worker = worker
        # Forward log messages from worker to the main thread via this thread's signal
        self.worker.log_message.connect(self.log_message)
        self.terminated_cleanly = False

    def run(self):
        """Executes the worker's run method."""
        try:
            self.log_message.emit("Thread dell'agente avviato.")
            self.worker.run() # This blocks until the worker's run method completes
            self.terminated_cleanly = True # Mark clean termination if worker.run() finishes
            self.log_message.emit("Thread dell'agente: worker.run() completato.")
        except Exception as e:
            # Catch unexpected errors *within the thread's execution*
            self.terminated_cleanly = False
            error_details = traceback.format_exc()
            self.log_message.emit(f"Errore critico nel thread dell'agente: {str(e)}\n{error_details}")
            # Optionally emit an error signal from the thread itself if needed
            # self.error.emit(f"Errore thread: {str(e)}")
        finally:
            self.log_message.emit(f"Thread dell'agente terminato (pulito: {self.terminated_cleanly}).")
            self.finished.emit() # Signal that the thread object has finished

    def stop(self):
        """Initiates the graceful stop process."""
        self.log_message.emit("Richiesta di arresto inoltrata al worker.")
        if self.worker:
            self.worker.stop() # Signal the worker to stop its async task


class UnifiedBrowserAgentDialog(QDialog):
    """Dialog unificato per configurare ed eseguire l'agente browser"""

    def __init__(self, parent=None, agent_config=None, transcription_text=None):
        super().__init__(parent)
        self.setWindowTitle("Browser Agent - Configurazione ed Esecuzione")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        # Use provided config or create a new one
        self.agent_config = agent_config if agent_config else AgentConfig()
        self.transcription_text = transcription_text or ""
        self.agent_thread = None
        self.worker = None # Hold reference to worker for stopping
        self.result = None
        self.progressDialog = None # Hold reference to progress dialog

        # Timer to check if the thread finished unexpectedly
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.timeout.connect(self.checkThreadStatus)

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        tabWidget = QTabWidget()
        configTab = QWidget()
        taskTab = QWidget()

        # --- Configurazione Tab ---
        configLayout = QVBoxLayout(configTab)

        # API Key section (Simplified - relies on environment loading)
        apiGroup = QGroupBox("API Keys (Caricate da .env)")
        apiLayout = QFormLayout()
        apiLayout.addRow("Anthropic Key:", QLabel("Caricata" if self.agent_config.anthropic_api_key else "Non Trovata"))
        apiLayout.addRow("Google Key:", QLabel("Caricata" if self.agent_config.google_api_key else "Non Trovata"))
        apiLayout.addRow("OpenAI Key:", QLabel("Caricata" if self.agent_config.openai_api_key else "Non Trovata"))
        # Optional: Add field to override, but generally discouraged
        # self.apiKeyOverrideEdit = QLineEdit()
        # self.apiKeyOverrideEdit.setPlaceholderText("Incolla qui per sovrascrivere (opzionale)")
        # apiLayout.addRow("Override Key:", self.apiKeyOverrideEdit)
        apiGroup.setLayout(apiLayout)
        configLayout.addWidget(apiGroup)

        # Model selection
        modelGroup = QGroupBox("Selezione Modello AI per Browser Agent")
        modelLayout = QFormLayout()
        self.modelCombo = QComboBox()

        # Populate ComboBox from config.py
        browser_agent_config = ACTION_MODELS_CONFIG.get('browser_agent', {})
        allowed_models = browser_agent_config.get('allowed', [])
        if not allowed_models:
            self.modelCombo.addItem("Nessun modello configurato")
            self.modelCombo.setEnabled(False)
        else:
            self.modelCombo.addItems(allowed_models)
            # Select the currently configured model
            index = self.modelCombo.findText(self.agent_config.model_name)
            if index >= 0:
                self.modelCombo.setCurrentIndex(index)
            elif self.modelCombo.count() > 0:
                 self.modelCombo.setCurrentIndex(0) # Fallback to first if saved one not found

        modelLayout.addRow("Modello:", self.modelCombo)
        modelGroup.setLayout(modelLayout)
        configLayout.addWidget(modelGroup)

        # Browser options
        browserGroup = QGroupBox("Opzioni Browser")
        browserLayout = QFormLayout()
        self.headlessCheck = QCheckBox("Esegui browser in modalità headless (senza interfaccia grafica)")
        self.headlessCheck.setChecked(self.agent_config.headless)
        self.visionCheck = QCheckBox("Usa capacità di visione del modello (se supportate)")
        self.visionCheck.setChecked(self.agent_config.use_vision)
        self.stepsEdit = QLineEdit(str(self.agent_config.max_steps))
        browserLayout.addRow("", self.headlessCheck)
        browserLayout.addRow("", self.visionCheck)
        browserLayout.addRow("Numero Massimo Passi:", self.stepsEdit)
        browserGroup.setLayout(browserLayout)
        configLayout.addWidget(browserGroup)

        # Save button
        saveConfigButton = QPushButton("Salva Configurazione Corrente")
        saveConfigButton.clicked.connect(self.saveConfiguration)
        configLayout.addWidget(saveConfigButton)
        configLayout.addStretch() # Push content to top


        # --- Esecuzione Tab ---
        taskLayout = QVBoxLayout(taskTab)

        # Task source selection
        taskSourceGroup = QGroupBox("Fonte del Task")
        taskSourceLayout = QVBoxLayout()
        self.manualTaskRadio = QRadioButton("Inserisci manualmente il task")
        self.transcriptionTaskRadio = QRadioButton("Usa il testo della trascrizione come contesto")
        taskSourceLayout.addWidget(self.manualTaskRadio)
        taskSourceLayout.addWidget(self.transcriptionTaskRadio)
        taskSourceGroup.setLayout(taskSourceLayout)
        taskLayout.addWidget(taskSourceGroup)

        # Set default task source
        if self.transcription_text:
            self.transcriptionTaskRadio.setChecked(True)
        else:
            self.manualTaskRadio.setChecked(True)
            self.transcriptionTaskRadio.setEnabled(False) # Disable if no transcription

        # Task input
        taskGroup = QGroupBox("Descrizione Task")
        taskLayout2 = QVBoxLayout()
        self.taskEdit = QTextEdit()
        self.taskEdit.setPlaceholderText("Inserisci il task per il browser agent o verrà usato il contesto della trascrizione...")
        taskLayout2.addWidget(self.taskEdit)
        taskGroup.setLayout(taskLayout2)
        taskLayout.addWidget(taskGroup)

        # Connect radios to update task text
        self.manualTaskRadio.toggled.connect(self.updateTaskSource)
        # transcriptionTaskRadio toggle is implicitly handled by updateTaskSource

        # Run/Stop Buttons
        btnLayout = QHBoxLayout()
        self.runButton = QPushButton("Esegui Agent")
        self.runButton.clicked.connect(self.runAgent)
        self.stopButton = QPushButton("Ferma Agent")
        self.stopButton.clicked.connect(self.stopAgent)
        self.stopButton.setEnabled(False)
        btnLayout.addWidget(self.runButton)
        btnLayout.addWidget(self.stopButton)
        taskLayout.addLayout(btnLayout)

        # Log and Result Display
        resultGroup = QGroupBox("Log e Risultati")
        resultLayout = QVBoxLayout()
        logLabel = QLabel("Log di esecuzione:")
        resultLayout.addWidget(logLabel)
        self.logEdit = QTextEdit()
        self.logEdit.setReadOnly(True)
        self.logEdit.setMaximumHeight(200) # Adjust height as needed
        resultLayout.addWidget(self.logEdit)
        resultLabel = QLabel("Risultato dell'operazione:")
        resultLayout.addWidget(resultLabel)
        self.resultEdit = QTextEdit()
        self.resultEdit.setReadOnly(True)
        resultLayout.addWidget(self.resultEdit)
        resultGroup.setLayout(resultLayout)
        taskLayout.addWidget(resultGroup)

        # --- Final Setup ---
        tabWidget.addTab(configTab, "Configurazione")
        tabWidget.addTab(taskTab, "Esecuzione")
        layout.addWidget(tabWidget)

        closeButton = QPushButton("Chiudi Finestra")
        closeButton.clicked.connect(self.accept) # Use accept to close dialog
        layout.addWidget(closeButton)

        self.setLayout(layout)
        self.updateTaskSource() # Initial population of task field


    def saveConfiguration(self):
        """Salva le impostazioni correnti nel QSettings."""
        try:
            max_steps = int(self.stepsEdit.text())
        except ValueError:
            QMessageBox.warning(self, "Errore Input", "Il numero massimo di passi deve essere un numero intero.")
            return

        # Update config object from UI elements
        self.agent_config.model_name = self.modelCombo.currentText()
        self.agent_config.headless = self.headlessCheck.isChecked()
        self.agent_config.use_vision = self.visionCheck.isChecked()
        self.agent_config.max_steps = max_steps
        # API Keys are not saved from UI here, rely on environment

        # Save the updated config object to QSettings
        self.agent_config.save_to_settings()
        self.addLogMessage("Configurazione salvata.")
        # QMessageBox.information(self, "Configurazione Salvata", "La configurazione dell'agente è stata salvata.")


    def updateTaskSource(self):
        """Aggiorna il campo task basato sulla selezione radio e sulla trascrizione disponibile."""
        if self.transcriptionTaskRadio.isChecked() and self.transcription_text:
            # Use a more direct prompt if using transcription as context
            self.taskEdit.setPlainText(
                f"Utilizzando il seguente testo come contesto principale, esegui le operazioni richieste o rispondi alla domanda implicita nel testo:\n\n"
                f"---\nCONTEXT START\n---\n"
                f"{self.transcription_text}\n"
                f"---\nCONTEXT END\n---\n\n"
                f"Obiettivo: Svolgi il compito descritto o implicito nel contesto fornito."
            )
            self.taskEdit.setReadOnly(True) # Prevent editing when using transcription
        elif self.manualTaskRadio.isChecked():
            self.taskEdit.setReadOnly(False)
            # Clear only if it was previously set by transcription
            if self.taskEdit.toPlainText().startswith("Utilizzando il seguente testo"):
                 self.taskEdit.clear()
            self.taskEdit.setPlaceholderText("Inserisci qui il task specifico per l'agente browser...")


    def addLogMessage(self, message):
        """Aggiunge un messaggio al log con timestamp e forza l'aggiornamento UI."""
        if not hasattr(self, 'logEdit'): return # Guard against calls after UI destroyed
        try:
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            log_entry = f"[{timestamp}] {message}"
            self.logEdit.append(log_entry)
            # Scroll to bottom
            cursor = self.logEdit.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.logEdit.setTextCursor(cursor)
            QApplication.processEvents() # Ensure UI updates
        except RuntimeError:
            # Handle cases where the widget might be deleted
            logging.warning("Tried to log message but logEdit might be deleted.")


    def runAgent(self):
        """Prepara e avvia l'esecuzione dell'agente."""
        self.saveConfiguration() # Save current settings before running

        task = self.taskEdit.toPlainText().strip()
        if not task:
            QMessageBox.warning(self, "Task Mancante", "Inserisci un task o seleziona l'opzione per usare la trascrizione.")
            return

        # Basic check if the selected model likely requires a key that isn't set
        model_lower = self.agent_config.model_name.lower()
        key_missing = False
        if model_lower.startswith("claude") and not self.agent_config.anthropic_api_key:
            key_missing = True
            provider = "Anthropic"
        elif model_lower.startswith("gemini") and not self.agent_config.google_api_key:
            key_missing = True
            provider = "Google"
        elif model_lower.startswith("gpt") and not self.agent_config.openai_api_key:
            key_missing = True
            provider = "OpenAI"

        if key_missing:
             QMessageBox.warning(self, "API Key Mancante", f"La API key per {provider} non sembra essere configurata nell'ambiente (.env). L'agente potrebbe non funzionare.")
             # Allow proceeding, but warn the user.

        # --- UI State Update ---
        self.runButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.logEdit.clear()
        self.resultEdit.clear()

        # --- Logging Start ---
        self.addLogMessage("=== AVVIO AGENTE BROWSER ===")
        self.addLogMessage(f"Task: {task[:100]}...") # Log truncated task
        self.addLogMessage(f"Configurazione: {self.agent_config.to_dict()}")
        self.addLogMessage("Inizializzazione in corso...")

        # --- Progress Dialog ---
        if self.progressDialog: # Close previous if exists
             self.progressDialog.close()
        self.progressDialog = QProgressDialog("Esecuzione browser agent...", "Annulla", 0, 100, self)
        self.progressDialog.setWindowTitle("Progresso Agent")
        self.progressDialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progressDialog.setMinimumDuration(0)
        self.progressDialog.canceled.connect(self.stopAgent)
        self.progressDialog.show()
        self.progressDialog.raise_()
        self.progressDialog.activateWindow()

        # --- Stop Existing Thread ---
        if self.agent_thread and self.agent_thread.isRunning():
            self.addLogMessage("Tentativo di fermare un thread agente precedente...")
            self.stopAgent() # Gracefully stop previous run

        # --- Create Worker and Thread ---
        try:
            self.worker = BrowserAgentWorker(task=task, config=self.agent_config)
            # Connect signals from worker
            self.worker.progress.connect(self.updateProgress)
            self.worker.finished.connect(self.onAgentFinished)
            self.worker.error.connect(self.onAgentError)
            # log_message signal is connected within AgentRunThread constructor

            self.agent_thread = AgentRunThread(self.worker)
            # Connect signals from thread
            self.agent_thread.finished.connect(self.onThreadFinished) # Handles UI reset
            self.agent_thread.log_message.connect(self.addLogMessage) # Forward logs

            self.agent_thread.start() # Start the thread
            self.cleanup_timer.start(500) # Start checking thread status
            self.addLogMessage("Thread agente avviato.")

        except Exception as init_error:
            self.addLogMessage(f"Errore durante l'inizializzazione del worker/thread: {init_error}")
            QMessageBox.critical(self, "Errore Inizializzazione", f"Impossibile avviare l'agente: {init_error}")
            self.onThreadFinished() # Reset UI


    def checkThreadStatus(self):
        """Verifica se il thread è terminato inaspettatamente."""
        if self.agent_thread and not self.agent_thread.isRunning() and self.stopButton.isEnabled():
            # Thread finished, but stop button is still enabled (meaning it wasn't a clean stop triggered by UI)
            self.addLogMessage("ATTENZIONE: Thread terminato inaspettatamente o completato senza disabilitare il pulsante stop.")
            self.onThreadFinished() # Reset UI state


    def stopAgent(self):
        """Inizia il processo di arresto dell'agente."""
        self.addLogMessage("\n=== ARRESTO RICHIESTO DALL'UTENTE ===")
        if not self.agent_thread or not self.agent_thread.isRunning():
            self.addLogMessage("Nessun agente in esecuzione da fermare.")
            self.onThreadFinished() # Ensure UI is reset even if nothing was running
            return

        if self.progressDialog:
            self.progressDialog.setLabelText("Arresto agente in corso...")
            self.progressDialog.setEnabled(False) # Disable cancel button during stop process

        # Signal the thread/worker to stop
        try:
            self.agent_thread.stop() # This signals the worker via its stop() method
            self.addLogMessage("Segnale di stop inviato al worker.")
        except Exception as e:
            self.addLogMessage(f"Errore durante l'invio del segnale di stop: {e}")

        # Non bloccare l'UI qui aspettando. onThreadFinished gestirà il reset.
        # Il worker.stop() imposta self.running = False, che dovrebbe interrompere il ciclo async.


    def updateProgress(self, value, message):
        """Aggiorna il dialog di progresso."""
        if self.progressDialog and not self.progressDialog.wasCanceled():
            self.progressDialog.setValue(value)
            self.progressDialog.setLabelText(f"Agente: {message}")
        # Log message is handled separately by addLogMessage


    def onAgentFinished(self, result):
        """Chiamato quando il worker emette il segnale 'finished'."""
        # Questo viene chiamato dal worker thread, prima che AgentRunThread finisca.
        self.addLogMessage(f"Agente ha completato l'esecuzione con successo.")
        self.result = result
        if hasattr(self, 'resultEdit'):
            self.resultEdit.setPlainText(str(result))
        # Non chiudere il progress dialog qui, onThreadFinished lo farà.


    def onAgentError(self, error_message):
        """Chiamato quando il worker emette il segnale 'error'."""
        self.addLogMessage(f"ERRORE dall'agente: {error_message}")
        if hasattr(self, 'resultEdit'):
            self.resultEdit.setPlainText(f"Si è verificato un errore:\n\n{error_message}")
        # Non chiudere il progress dialog qui, onThreadFinished lo farà.


    def onThreadFinished(self):
        """Chiamato quando AgentRunThread emette il segnale 'finished'."""
        self.addLogMessage("Thread agente terminato. Pulizia UI...")
        # Reset UI state regardless of success/failure/cancel
        self.runButton.setEnabled(True)
        self.stopButton.setEnabled(False)

        if self.progressDialog:
            self.progressDialog.close()
            self.progressDialog = None

        # Stop the cleanup timer
        self.cleanup_timer.stop()

        # Clean up references
        self.worker = None
        self.agent_thread = None

        self.addLogMessage("=== OPERAZIONE TERMINATA ===")


    def closeEvent(self, event):
        """Gestisce la chiusura della finestra di dialogo."""
        self.addLogMessage("Tentativo di chiusura del dialogo.")
        if self.agent_thread and self.agent_thread.isRunning():
            reply = QMessageBox.question(self, 'Conferma Chiusura',
                                         'L\'agente è ancora in esecuzione. Fermarlo e chiudere?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                self.addLogMessage("Chiusura confermata, arresto agente...")
                self.stopAgent()
                # Give it a moment to process stop signal before accepting close
                QTimer.singleShot(500, event.accept) # Accept after a short delay
            else:
                self.addLogMessage("Chiusura annullata dall'utente.")
                event.ignore() # Don't close
        else:
            self.addLogMessage("Nessun agente in esecuzione, chiusura immediata.")
            event.accept() # Close immediately


class BrowserAgent:
    """
    Classe principale per integrare la funzionalità dell'agente browser
    nell'applicazione principale.
    """
    def __init__(self, parent=None):
        self.parent = parent # Reference to the main application window (TGeniusAI instance)
        self.agent_config = AgentConfig() # Manages agent settings
        self.frame_data = None # Stores data from frame extraction if used for guide generation
        self.current_dialog = None # Keep track of the currently open dialog

    def getTranscriptionText(self):
        """Ottiene il testo dalla transcriptionTextArea del parent."""
        if self.parent and hasattr(self.parent, 'transcriptionTextArea'):
            return self.parent.transcriptionTextArea.toPlainText().strip()
        return ""

    def showAgentDialog(self):
        """Mostra il dialog unificato di configurazione ed esecuzione."""
        # Close existing dialog if open
        if self.current_dialog:
             try:
                 self.current_dialog.close()
             except RuntimeError: # Handle case where it might already be deleted
                 pass
             self.current_dialog = None

        # Pass current transcription text to the dialog
        transcription = self.getTranscriptionText()
        self.current_dialog = UnifiedBrowserAgentDialog(self.parent, self.agent_config, transcription)
        self.current_dialog.show() # Use show() instead of exec() for non-blocking


    # --- Methods called from TGeniusAI ---
    def showConfigDialog(self):
        """Alias per mostrare il dialog (azione da menu/toolbar)."""
        self.showAgentDialog()

    def runAgent(self):
        """Alias per mostrare il dialog (azione da menu/toolbar)."""
        self.showAgentDialog()


    def generate_operational_guide(self, video_path=None, num_frames=5, language="italiano"):
        """
        Estrae frame, li analizza con il modello VISION configurato, genera una
        guida testuale usando il modello BROWSER AGENT configurato, e la
        inserisce nella transcriptionTextArea.
        """
        # Get the currently selected vision model from settings
        vision_model_config = ACTION_MODELS_CONFIG.get('frame_extractor', {})
        vision_model_key = vision_model_config.get('setting_key', 'models/frame_extractor')
        vision_default = vision_model_config.get('default', '')
        settings = QSettings("ThemaConsulting", "GeniusAI")
        vision_model_name = settings.value(vision_model_key, vision_default)

        logging.info(f"Inizio generazione guida operativa (Vision model: {vision_model_name})")

        if not vision_model_name:
             QMessageBox.critical(self.parent, "Errore Configurazione", "Nessun modello AI configurato per l'estrazione frame (visione).")
             return False

        # Use the main window's video path if not provided
        if not video_path:
            if hasattr(self.parent, 'videoPathLineEdit') and self.parent.videoPathLineEdit:
                video_path = self.parent.videoPathLineEdit
            else:
                QMessageBox.warning(self.parent, "Video Mancante", "Carica un video prima di generare la guida.")
                return False

        # --- Progress Dialog ---
        progress_dialog = QProgressDialog("Generazione Guida Operativa...", "Annulla", 0, 100, self.parent)
        progress_dialog.setWindowTitle("Progresso Guida")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setValue(0)
        progress_dialog.show()

        try:
            # --- 1. Extract Frames using FrameExtractor ---
            progress_dialog.setLabelText("Estrazione frame...")
            progress_dialog.setValue(10)
            QApplication.processEvents() # Update UI

            # FrameExtractor uses the model set in its own settings key
            extractor = FrameExtractor(
                video_path=video_path,
                num_frames=num_frames,
                # API keys are read within FrameExtractor based on its selected model
            )
            frames = extractor.extract_frames()
            if not frames: raise ValueError("Estrazione frame fallita.")
            progress_dialog.setValue(25)
            QApplication.processEvents()

            # --- 2. Analyze Frames (using the *vision* model) ---
            progress_dialog.setLabelText(f"Analisi frame con {extractor.selected_model}...")
            frame_data = extractor.analyze_frames_batch(frames, language)
            if not frame_data: raise ValueError("Analisi frame fallita o nessun risultato.")
            self.frame_data = frame_data # Store for potential later use
            progress_dialog.setValue(50)
            QApplication.processEvents()

            # --- 3. Prepare prompt for Guide Generation ---
            progress_dialog.setLabelText("Preparazione prompt guida...")
            descriptions = [fd['description'] for fd in frame_data]
            joined_descriptions = "\n".join(f"- {desc}" for desc in descriptions if desc)
            if not joined_descriptions: raise ValueError("Nessuna descrizione valida dai frame.")

            if not os.path.exists(PROMPT_BROWSER_GUIDE):
                 raise FileNotFoundError(f"File prompt guida non trovato: {PROMPT_BROWSER_GUIDE}")
            with open(PROMPT_BROWSER_GUIDE, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            prompt = prompt_template.format(
                joined_descriptions=joined_descriptions,
                language=language
            )
            progress_dialog.setValue(60)
            QApplication.processEvents()

            # --- 4. Generate Guide (using the *browser agent's text* model) ---
            guide_model_name = self.agent_config.model_name # Model selected for the agent itself
            progress_dialog.setLabelText(f"Generazione guida con {guide_model_name}...")
            logging.info(f"Generazione guida testuale con: {guide_model_name}")

            guide_text = ""
            input_tokens, output_tokens = 0, 0 # Placeholder for token counts

            # Select LLM client based on the agent's model
            model_lower = guide_model_name.lower()

            if model_lower.startswith("claude"):
                 if not self.agent_config.anthropic_api_key: raise ValueError("Anthropic API Key mancante per generare la guida.")
                 client = anthropic.Anthropic(api_key=self.agent_config.anthropic_api_key)
                 response = client.messages.create(
                     model=guide_model_name, max_tokens=4000, messages=[{"role": "user", "content": prompt}]
                 )
                 guide_text = response.content[0].text
                 input_tokens = response.usage.input_tokens
                 output_tokens = response.usage.output_tokens

            elif model_lower.startswith("gemini"):
                 if not self.agent_config.google_api_key: raise ValueError("Google API Key mancante per generare la guida.")
                 # Assumes genai is configured
                 model = genai.GenerativeModel(guide_model_name)
                 response = model.generate_content(prompt)
                 guide_text = response.text

            elif model_lower.startswith("gpt"):
                 if not self.agent_config.openai_api_key: raise ValueError("OpenAI API Key mancante per generare la guida.")
                 client = ChatOpenAI(model_name=guide_model_name, openai_api_key=self.agent_config.openai_api_key)
                 response = client.invoke(prompt) # Langchain style invocation
                 guide_text = response.content

            # Add Ollama or other models here if needed...

            else:
                raise ValueError(f"Modello {guide_model_name} non supportato per la generazione della guida.")

            progress_dialog.setValue(90)
            logging.info(f"Guida generata - Input Tokens: {input_tokens}, Output Tokens: {output_tokens}")
            QApplication.processEvents()

            # --- 5. Update UI ---
            if hasattr(self.parent, 'transcriptionTextArea'):
                self.parent.transcriptionTextArea.setPlainText(guide_text.strip())
            progress_dialog.setValue(100)
            progress_dialog.close()
            QMessageBox.information(self.parent, "Guida Operativa Generata",
                                    "Guida generata e inserita nell'area di trascrizione.")
            return True

        except (FileNotFoundError, ValueError, Exception) as e:
            # Handle specific and general errors
            if progress_dialog: progress_dialog.close()
            error_msg = f"Errore durante la generazione della guida: {str(e)}"
            QMessageBox.critical(self.parent, "Errore", error_msg)
            logging.error(error_msg, exc_info=True)
            return False


    def create_guide_agent(self):
        """
        Metodo completo che:
        1. Genera la guida operativa (estrae frame, analizza, genera testo guida)
        2. (Opzionale) Mostra il dialog dell'agente per l'esecuzione successiva
        """
        # Ottieni parametri dalla UI principale
        video_path = None
        if hasattr(self.parent, 'videoPathLineEdit') and self.parent.videoPathLineEdit:
            video_path = self.parent.videoPathLineEdit
        else:
            QMessageBox.warning(self.parent, "Video Mancante", "Carica un video prima.")
            return

        num_frames = 5
        if hasattr(self.parent, 'frameCountSpin'):
            num_frames = self.parent.frameCountSpin.value()

        language = "italiano"
        if hasattr(self.parent, 'languageComboBox'):
            language = self.parent.languageComboBox.currentText()

        # Genera la guida e inseriscila nella text area
        success = self.generate_operational_guide(video_path, num_frames, language)

        # Se la guida è stata generata con successo, potresti voler mostrare
        # automaticamente il dialog dell'agente per il passo successivo.
        if success:
             logging.info("Guida generata, mostrando il dialogo dell'agente...")
             # self.showAgentDialog() # Rimuoviamo l'apertura automatica, l'utente può cliccare "Run Agent"