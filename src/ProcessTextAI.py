import anthropic
from PyQt6.QtCore import QThread, pyqtSignal
antrophic_key = "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"
model_3_5_sonnet = "claude-3-5-sonnet-20240620"
model_3_haiku = "claude-3-haiku-20240307"

class ProcessTextAI(QThread):
    update_progress = pyqtSignal(int, str)
    process_complete = pyqtSignal(str)
    process_error = pyqtSignal(str)

    def __init__(self, text, api_key, language, parent=None):
        super().__init__(parent)
        self.text = text
        self.api_key = api_key
        self.language = language
        self.result = None

    def run(self):
        try:
            self.result, input_tokens, output_tokens = self.computeText(self.text)
            self.process_complete.emit(self.result)
            print(f"Token di input utilizzati: {input_tokens}")
            print(f"Token di output utilizzati: {output_tokens}")
        except Exception as e:
            self.process_error.emit(f"Errore durante la computazione del testo: {e}")

    def computeText(self, text):
        client = anthropic.Anthropic(api_key=antrophic_key)
        message = client.messages.create(
            model=model_3_5_sonnet,
            max_tokens=8192,
            temperature=0.7,
            system=(
                f"You are an expert in text transcription and formatting. Your task is to process the following "
                f"transcribed text from an audio recording. Format the text correctly, fix punctuation, and remove any "
                f"fillers or unclear words, ensuring the meaning is preserved. The final result should be in {self.language}, "
                f"divided into clear paragraphs where appropriate. Do not add any additional text or commentary, return only the formatted text."
            ),
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
        testo_resultante = message.content[0].text
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens

        return testo_resultante, input_tokens, output_tokens
