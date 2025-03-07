import anthropic
from PyQt6.QtCore import QThread, pyqtSignal, QSettings
import os
from dotenv import load_dotenv
from src.config import ANTHROPIC_API_KEY, CLAUDE_MODEL_TEXT_PROCESSING,PROMPT_TEXT_SUMMARY,PROMPT_TEXT_FIX

load_dotenv()


class ProcessTextAI(QThread):
    update_progress = pyqtSignal(int, str)
    process_complete = pyqtSignal(str)
    process_error = pyqtSignal(str)

    def __init__(self, text, language, mode="summary", parent=None):
        super().__init__(parent)
        self.text = text
        self.language = language
        self.result = None
        self.mode = mode  # Aggiunto il parametro mode per scegliere l'operazione

        # Carica il modello dalle impostazioni
        settings = QSettings("ThemaConsulting", "GeniusAI")
        self.claude_model = settings.value("models/text_processing", CLAUDE_MODEL_TEXT_PROCESSING)

    def run(self):
        try:
            if self.mode == "summary":
                self.result, input_tokens, output_tokens = self.computeText(self.text)
            elif self.mode == "fix":
                self.result, input_tokens, output_tokens = self.computeTextFix(self.text)
            else:
                raise ValueError("Modalità sconosciuta. Usa 'summary' o 'fix'.")

            self.process_complete.emit(self.result)
            print(f"Token di input utilizzati: {input_tokens}")
            print(f"Token di output utilizzati: {output_tokens}")
        except Exception as e:
            self.process_error.emit(f"Errore durante la computazione del testo: {e}")

    def computeText(self, text):
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # Leggi il prompt dal file
        with open(PROMPT_TEXT_SUMMARY, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # Formatta il prompt
        system_prompt = prompt_template.format(language=self.language)

        message = client.messages.create(
            model=self.claude_model,
            max_tokens=8192,
            temperature=0.7,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{text}\n\nAssistant:"
                        }
                    ]
                }
            ]
        )

        # Il resto del codice rimane invariato...

        # Estrai il testo risultante e i token utilizzati
        testo_resultante = message.content[0].text
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens

        return testo_resultante, input_tokens, output_tokens

    def computeTextFix(self, text):
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # Leggi il prompt dal file
        with open(PROMPT_TEXT_FIX, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # Formatta il prompt
        system_prompt = prompt_template.format(language=self.language)

        message = client.messages.create(
            model=self.claude_model,
            max_tokens=8192,
            temperature=0.7,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{text}\n\nAssistant:"
                        }
                    ]
                }
            ]
        )

        # Il resto del codice rimane invariato...
        # Estrai il testo risultante e i token utilizzati
        testo_resultante = message.content[0].text
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens

        return testo_resultante, input_tokens, output_tokens