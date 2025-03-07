import anthropic
import base64
import cv2
import json
import numpy as np
import sys
from moviepy.editor import VideoFileClip
from tqdm import tqdm

class FrameExtractor:
    def __init__(self, video_path, num_frames, anthropic_api_key, batch_size=5):
        self.video_path = video_path
        self.num_frames = num_frames
        self.batch_size = batch_size
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)

    def extract_frames(self):
        """
        Estrae i frame a intervalli equidistanti e ritorna una lista contenente il frame in base64
        insieme al rispettivo timestamp.
        """
        video = VideoFileClip(self.video_path)
        duration = video.duration
        timestamps = np.linspace(0, duration, self.num_frames, endpoint=False)
        frame_list = []

        cap = cv2.VideoCapture(self.video_path)
        for timestamp in timestamps:
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            success, frame = cap.read()
            if success:
                _, buffer = cv2.imencode(".jpg", frame)
                frame_base64 = base64.b64encode(buffer).decode("utf-8")
                frame_list.append({"data": frame_base64, "timestamp": timestamp})
        cap.release()
        return frame_list

    def analyze_frames_batch(self, frame_list, language):
        """
        Invia i frame a Claude in batch e riceve un JSON per ciascun frame,
        contenente 'frame' e 'description'. Converte il timestamp in formato mm:ss
        e ritorna un array di descrizioni dettagliate per ogni frame.
        """
        frame_data = []
        total_batches = len(frame_list) // self.batch_size + (1 if len(frame_list) % self.batch_size != 0 else 0)

        for batch_idx in tqdm(range(total_batches), desc="Processing Batches"):
            batch = frame_list[batch_idx * self.batch_size: (batch_idx + 1) * self.batch_size]
            messages = [{"role": "user", "content": []}]

            # Aggiungo ogni frame (con la sua immagine) al prompt
            for idx, frame in enumerate(batch):
                current_index = batch_idx * self.batch_size + idx
                messages[0]["content"].append({"type": "text", "text": f"Frame {current_index}:"})
                messages[0]["content"].append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": frame["data"],
                    },
                })

            # Prompt per richiedere un array JSON con le informazioni per ciascun frame
            messages[0]["content"].append({
                "type": "text",
                "text": f"""
                Please return a strict JSON array in {language}. 
                There are {len(batch)} frames here. 
                Each element must be an object like:
                {{
                  "frame": <LOCAL_INDEX>,
                  "description": "<text describing the frame>"
                }}
                Do not include extra text or disclaimers besides the JSON array.
                """
            })

            try:
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2048,
                    messages=messages
                )
                raw_text = response.content[0].text.strip()

                # Parsing del JSON restituito
                frames_json = json.loads(raw_text)

                for item in frames_json:
                    local_index = item["frame"]
                    desc = item["description"]

                    # Calcolo dell'indice globale
                    frame_number = batch_idx * self.batch_size + local_index

                    # Converto il timestamp in minuti e secondi (mm:ss)
                    timestamp_seconds = batch[local_index]['timestamp']
                    minutes = int(timestamp_seconds // 60)
                    seconds = int(timestamp_seconds % 60)

                    frame_data.append({
                        "frame_number": frame_number,
                        "description": desc.strip(),
                        "timestamp": f"{minutes:02d}:{seconds:02d}",
                    })

            except json.JSONDecodeError as e:
                print(f"Errore nel parsing JSON: {e}")
            except Exception as e:
                print(f"Error analyzing batch {batch_idx}: {e}")

        return frame_data

    def get_video_duration(self):
        """
        Restituisce la durata del video in secondi.
        """
        video = VideoFileClip(self.video_path)
        return video.duration

    import os

    def generate_video_summary(self, frame_data, language):
        """
        Genera un discorso finale narrativo che descriva l'intero video tutorial.
        Il testo, da utilizzare come presentazione orale, deve essere fluido e chiaro,
        senza riferimenti a timestamp o numeri di frame, e deve includere pause
        nel formato <break time="Xs" />, dove il valore di X può variare in base al ritmo del discorso.
        La lunghezza del discorso deve essere approssimativamente pari al minutaggio del video.
        """
        import os

        # Assicurati che get_video_duration() ritorni un valore numerico (float o int)
        video_duration = float(self.get_video_duration())
        video_duration_minutes = video_duration / 60

        # Utilizzo solo le descrizioni estratte, senza riferimenti tecnici
        descriptions = [fd['description'] for fd in frame_data]
        joined_descriptions = "\n".join(descriptions)

        # Leggi il prompt dal file
        file_path = os.path.join(os.path.dirname(__file__), "prompt_frames_for_agent.txt")
        with open(file_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()

        # Qui passo video_duration_minutes come float,
        # così il placeholder {video_duration_minutes:.2f} nel file potrà formattarlo correttamente.
        prompt_text = prompt_template.format(
            language=language,
            joined_descriptions=joined_descriptions,
            video_duration_minutes=video_duration_minutes
        )

        messages = [{"role": "user", "content": []}]
        messages[0]["content"].append({
            "type": "text",
            "text": prompt_text
        })

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                messages=messages
            )
            return response.content[0].text.strip()

        except Exception as e:
            print(f"Error generating final summary: {e}")
            return None

    def process_video(self, output_json="video_analysis.json", language="italiano"):
        """
        Esegue l'intero processo: estrazione dei frame, analisi dei frame e generazione del discorso finale.
        Salva l'analisi in un file JSON.
        """
        print("Estrazione dei frame...")
        frames = self.extract_frames()
        print(f"Frame estratti: {len(frames)}.")

        print("Analisi dei frame con Claude Vision...")
        frame_data = self.analyze_frames_batch(frames, language)

        print("Generazione del discorso finale del video...")
        summary = self.generate_video_summary(frame_data, language)

        output = {
            "frames": frame_data,
            "video_summary": summary
        }

        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=4, ensure_ascii=False)

        print(f"Analisi del video salvata in {output_json}")
        print("\nDiscorso Finale del Video:\n", summary)


if __name__ == "__main__":
    if len(sys.argv) < 4 or len(sys.argv) > 5:
        print("Usage: python  frameextractor.py <video_path> <num_frames> <anthropic_api_key> [language]")
        sys.exit(1)

    video_path = sys.argv[1]
    num_frames = int(sys.argv[2])
    anthropic_api_key = sys.argv[3]
    language = sys.argv[4] if len(sys.argv) == 5 else "italiano"

    extractor = FrameExtractor(video_path, num_frames, anthropic_api_key)
    extractor.process_video(language=language)
