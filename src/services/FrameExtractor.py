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

    def analyze_frames_batch(self, frame_list):
        """
        Sends frames in batches to Claude Vision API for analysis.
        :param frame_list: List of extracted frames (base64 encoded).
        :return: JSON with metadata and descriptions.
        """
        frame_data = []
        total_batches = len(frame_list) // self.batch_size + (1 if len(frame_list) % self.batch_size != 0 else 0)

        for batch_idx in tqdm(range(total_batches), desc="Processing Batches"):
            batch = frame_list[batch_idx * self.batch_size : (batch_idx + 1) * self.batch_size]
            messages = [{"role": "user", "content": []}]

            for idx, frame in enumerate(batch):
                messages[0]["content"].append({"type": "text", "text": f"Frame {batch_idx * self.batch_size + idx}:"})
                messages[0]["content"].append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": frame["data"],
                    },
                })

            messages[0]["content"].append({"type": "text", "text": "Describe each frame separately."})

            try:
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2048,
                    messages=messages
                )

                descriptions = response.content[0].text.split("\n")  # Split responses for multiple images
                for i, desc in enumerate(descriptions):
                    frame_data.append({
                        "frame_number": batch_idx * self.batch_size + i,
                        "description": desc.strip(),
                        "timestamp": f"{batch[i]['timestamp']:.2f} sec",
                    })

            except Exception as e:
                print(f"Error analyzing batch {batch_idx}: {e}")

        return frame_data

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
#Test