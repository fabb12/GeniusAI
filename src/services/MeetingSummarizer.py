import anthropic
from PyQt6.QtCore import QThread, pyqtSignal, QSettings
from src.config import ANTHROPIC_API_KEY, CLAUDE_MODEL_SUMMARY, PROMPT_MEETING_SUMMARY


class MeetingSummarizer(QThread):
    update_progress = pyqtSignal(int, str)
    process_complete = pyqtSignal(str)
    process_error = pyqtSignal(str)

    def __init__(self, text, language, parent=None):
        super().__init__(parent)
        self.text = text
        self.language = language
        self.result = None

        # Carica il modello dalle impostazioni
        settings = QSettings("ThemaConsulting", "GeniusAI")
        self.claude_model = settings.value("models/summary", CLAUDE_MODEL_SUMMARY)

    def run(self):
        try:
            self.update_progress.emit(10, "Inizializzazione riassunto riunione...")
            self.result, input_tokens, output_tokens = self.summarizeMeeting(self.text)

            self.update_progress.emit(100, "Riassunto completato!")
            self.process_complete.emit(self.result)
            print(f"Token di input utilizzati: {input_tokens}")
            print(f"Token di output utilizzati: {output_tokens}")
        except Exception as e:
            self.process_error.emit(f"Errore durante il riassunto della riunione: {e}")

    def summarizeMeeting(self, text):
        self.update_progress.emit(30, "Analisi della trascrizione della riunione...")
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # Leggi il prompt dal file
        with open(PROMPT_MEETING_SUMMARY, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # Formatta il prompt
        system_prompt = prompt_template.format(language=self.language)

        self.update_progress.emit(50, "Generazione del riassunto...")
        message = client.messages.create(
            model=self.claude_model,
            max_tokens=4096,
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

        # Estrai il testo risultante e i token utilizzati
        self.update_progress.emit(80, "Elaborazione risultati...")
        testo_resultante = message.content[0].text
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens

        return testo_resultante, input_tokens, output_tokens