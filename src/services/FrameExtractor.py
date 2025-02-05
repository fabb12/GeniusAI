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
        Estrae i frame a intervalli equidistanti
        e ritorna una lista con base64 e timestamp.
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
        1) Invia i frame a Claude in batch.
        2) Claude restituisce un JSON con 'frame' e 'description' per ciascun frame.
        3) Converte i secondi in mm:ss e popola frame_data.
        4) Ritorna l'array di descrizioni dettagliate per ogni frame (non il discorso finale).
        """
        frame_data = []
        total_batches = len(frame_list) // self.batch_size + (1 if len(frame_list) % self.batch_size != 0 else 0)

        for batch_idx in tqdm(range(total_batches), desc="Processing Batches"):
            batch = frame_list[batch_idx * self.batch_size : (batch_idx + 1) * self.batch_size]
            messages = [{"role": "user", "content": []}]

            # Allego i frame sotto forma di immagine + un prompt
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

            # Prompt per un array JSON
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

                # Esegui il parsing JSON
                frames_json = json.loads(raw_text)

                for item in frames_json:
                    local_index = item["frame"]
                    desc = item["description"]

                    # Indice globale
                    frame_number = batch_idx * self.batch_size + local_index

                    # timestamp e formattazione
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

    def generate_video_summary(self, frame_data, language):
        """
        Dato un array di descrizioni frame_data, chiede a Claude di generare
        un discorso finale che descriva l'intero video.
        """
        # Creiamo un testo di input con info su ogni frame
        # Esempio: "Frame 0 (02:00): Descrizione..."
        frames_info = []
        for fd in frame_data:
            frames_info.append(
                f"Frame {fd['frame_number']} ({fd['timestamp']}): {fd['description']}"
            )
        joined_info = "\n".join(frames_info)

        messages = [{"role": "user", "content": []}]
        messages[0]["content"].append({
            "type": "text",
            "text": f"""
Genera un testo discorsivo in {language} che descriva l'intero video.
Ecco le informazioni estratte dai frame:

{joined_info}

Fornisci una narrazione finale coesa, come se presentassi il video
dall'inizio alla fine, utilizzando i dettagli dei frame. 
            """
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

    def process_video(self, output_json="video_analysis.json"):
        """
        Extracts frames, analyzes them, and generates a video summary.
        :param output_json: Path to save JSON file with frame descriptions.
        """
        print("Extracting frames...")
        frames = self.extract_frames()
        print(f"Extracted {len(frames)} frames.")

        print("Analyzing frames with Claude Vision...")
        frame_data = self.analyze_frames_batch(frames)

        print("Generating video summary...")
        summary = self.generate_video_summary(frame_data)

        with open(output_json, "w", encoding="utf-8") as f:
            json.dump({"frames": frame_data, "video_summary": summary}, f, indent=4)

        print(f"Video analysis saved to {output_json}")
        print("\nVideo Summary:\n", summary)


# ===========================
#  MAIN: Esegui come script
# ===========================
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python frameextractor.py <video_path> <num_frames> <anthropic_api_key>")
        sys.exit(1)

    video_path = sys.argv[1]
    num_frames = int(sys.argv[2])
    anthropic_api_key = sys.argv[3]

    extractor = FrameExtractor(video_path, num_frames, anthropic_api_key)
    extractor.process_video()
