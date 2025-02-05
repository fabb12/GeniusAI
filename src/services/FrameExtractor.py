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
        """
        Initializes the FrameExtractor class.
        :param video_path: Path to the input video file.
        :param num_frames: Number of frames to extract evenly spaced throughout the video.
        :param anthropic_api_key: API key for Anthropic's Claude Vision.
        :param batch_size: Number of frames to send per request to Claude API.
        """
        self.video_path = video_path
        self.num_frames = num_frames
        self.batch_size = batch_size
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)

    def extract_frames(self):
        """
        Extracts frames from the video at equal intervals.
        :return: List of extracted frames in Base64 format.
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
        Elabora i frame in batch e produce un UNICO discorso nella lingua desiderata,
        dove Claude descrive i frame in modo sequenziale.

        :param frame_list: Lista di frame estratti (base64) e relativo timestamp in secondi.
        :param language: Lingua in cui Claude dovrà generare la descrizione (es. 'Italian', 'Spanish', 'English').
        :return: stringa contenente l'intero discorso che descrive tutti i frame.
        """
        full_discourse_parts = []
        total_batches = len(frame_list) // self.batch_size + (1 if len(frame_list) % self.batch_size != 0 else 0)

        for batch_idx in tqdm(range(total_batches), desc="Processing Batches"):
            # Prendiamo i frame di questo batch
            batch = frame_list[batch_idx * self.batch_size: (batch_idx + 1) * self.batch_size]

            messages = [{"role": "user", "content": []}]

            # Prepara un breve elenco di info di base su ciascun frame:
            #  "Frame X (mm:ss)" per passarlo a Claude in un testo riassuntivo
            frames_info_text = []
            for idx, frame in enumerate(batch):
                # Calcoliamo l'indice globale e formattiamo il timestamp
                global_index = batch_idx * self.batch_size + idx
                timestamp_seconds = frame["timestamp"]
                minutes = int(timestamp_seconds // 60)
                seconds = int(timestamp_seconds % 60)
                frames_info_text.append(
                    f"Frame {global_index} ({minutes:02d}:{seconds:02d})"
                )

            # Creiamo un prompt in cui chiediamo a Claude di generare un discorso unico
            # in {language} che descriva i frame elencati (riferendosi al 'global_index')
            text_prompt = (
                f"Please produce a cohesive explanation in {language} describing the following frames:\n"
                f"{', '.join(frames_info_text)}.\n"
                "Pretend you are narrating a video; mention key visual elements in each frame "
                "and how they connect to each other. Provide a single, continuous paragraph. "
                "Avoid extra disclaimers or code fences."
            )

            # Aggiungiamo il blocco di testo (prompt)
            messages[0]["content"].append({"type": "text", "text": text_prompt})

            try:
                # Chiamiamo l'API di Anthropic
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2048,
                    messages=messages
                )

                # Claude restituisce il discorso (testo) per questo batch
                batch_discourse = response.content[0].text.strip()

                # Lo aggiungiamo alla lista di "pezzi" di discorso
                full_discourse_parts.append(batch_discourse)

            except Exception as e:
                print(f"Error analyzing batch {batch_idx}: {e}")
                # In caso di errore, possiamo aggiungere un placeholder
                full_discourse_parts.append(f"[Errore batch {batch_idx}]")

        # Al termine, uniamo i vari “pezzi” in un singolo testo discorsivo
        final_discourse = "\n\n".join(full_discourse_parts)
        return final_discourse

    def generate_video_summary(self, frame_data):
        """
        Generates a summary of the video based on frame analysis.
        :param frame_data: JSON containing frame descriptions.
        :return: A text summary of the entire video.
        """
        descriptions = "\n".join(
            [f"Frame {d['frame_number']} at {d['timestamp']}: {d['description']}" for d in frame_data])

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Based on these frame descriptions, summarize the video's content:\n{descriptions}"}
                        ]
                    }
                ]
            )
            return response.content[0].text

        except Exception as e:
            print(f"Error generating video summary: {e}")
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
