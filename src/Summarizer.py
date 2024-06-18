from PyQt6.QtCore import QThread, pyqtSignal
from transformers import pipeline, AutoTokenizer

class SummarizerThread(QThread):
    update_progress = pyqtSignal(int, str)
    summarization_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, input_text, summary_length, parent=None):
        super().__init__(parent)
        self.input_text = input_text
        self.summary_length = summary_length
        self.summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        self.tokenizer = AutoTokenizer.from_pretrained("facebook/bart-large-cnn")

    def run(self):
        try:
            chunks = self.split_text_into_chunks(self.input_text, 1024)
            summaries = []
            total_chunks = len(chunks)
            for i, chunk in enumerate(chunks):
                chunk_length = len(chunk.split())
                max_length = min(self.summary_length, chunk_length)
                min_length = max_length // 2
                summary = self.summarizer(chunk, max_length=max_length, min_length=min_length, do_sample=False)
                summaries.append(summary[0]['summary_text'])
                self.update_progress.emit(int(((i + 1) / total_chunks) * 100), f"Summarizing chunk {i + 1}/{total_chunks}")
            full_summary = self.summarizer(" ".join(summaries), max_length=self.summary_length, min_length=self.summary_length // 2, do_sample=False)
            self.summarization_complete.emit(full_summary[0]['summary_text'])
        except Exception as e:
            self.error_occurred.emit(str(e))

    def split_text_into_chunks(self, text, max_length):
        tokens = self.tokenizer.encode(text, add_special_tokens=False)
        chunks = [tokens[i:i + max_length] for i in range(0, len(tokens), max_length)]
        return [self.tokenizer.decode(chunk) for chunk in chunks]