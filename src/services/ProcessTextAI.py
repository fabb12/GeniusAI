import anthropic
from PyQt6.QtCore import QThread, pyqtSignal
import os
from dotenv import load_dotenv
from src.config import ANTHROPIC_API_KEY, MODEL_3_5_SONNET, MODEL_3_HAIKU

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
        message = client.messages.create(
            model=MODEL_3_5_SONNET,
            max_tokens=8192,
            temperature=0.7,
            system=(
                f"You are an expert in summarization and content organization. Your task is to process the following "
                f"transcribed text from an audio recording and create a concise and well-organized summary. Highlight the main "
                f"points while preserving the original meaning and context. Ensure the summary is written in clear and coherent "
                f"language ({self.language}), divided into logical sections or bullet points where appropriate. Fix punctuation, "
                f"remove redundancies, and exclude unclear words or irrelevant details. Return only the summary, without any additional commentary or explanations."

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

    def computeTextFix(self, text):
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=MODEL_3_5_SONNET,
            max_tokens=8192,
            temperature=0.7,
            system=(
                f"You are an expert in text editing and formatting. Your task is to process the following text that contains timecodes "
                f"and transcriptions from an audio recording. Keep the timecodes exactly as they are and retain the original structure. "
                f"Fix the grammar, punctuation, and sentence structure to ensure clarity and logical flow. Resolve unclear terms where possible, "
                f"but do not remove any valid information or modify the timecodes. Return only the corrected text, without any additional commentary or explanations."

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
