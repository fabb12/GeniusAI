import os
import json
from datetime import datetime

class ProjectManager:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def get_next_untitled_project_name(self):
        i = 1
        while True:
            project_name = f"Untitled {i}"
            if not os.path.exists(os.path.join(self.base_dir, project_name)):
                return project_name
            i += 1

    def create_project(self, project_name=None, base_dir=None):
        if not project_name:
            project_name = self.get_next_untitled_project_name()

        # Usa la base_dir fornita, altrimenti quella di default
        effective_base_dir = base_dir if base_dir else self.base_dir
        project_path = os.path.join(effective_base_dir, project_name)

        # Se la base_dir è specificata, il progetto viene creato direttamente lì
        if not base_dir:
             project_path = os.path.join(self.base_dir, project_name)

        clips_path = os.path.join(project_path, "clips")
        audio_path = os.path.join(project_path, "audio")

        if os.path.exists(project_path):
            return None, "Project already exists"

        os.makedirs(clips_path)
        os.makedirs(audio_path)

        gnai_path = os.path.join(project_path, f"{project_name}.gnai")
        project_data = {
            "projectName": project_name,
            "createdAt": datetime.now().isoformat(),
            "clips": [],
            "audio_clips": [],
            "projectTranscription": "",
            "projectSummaries": {
                "combinedDetailed": "",
                "combinedMeeting": ""
            }
        }

        with open(gnai_path, 'w') as f:
            json.dump(project_data, f, indent=4)

        return project_path, gnai_path

    def load_project(self, gnai_path):
        if not os.path.exists(gnai_path):
            return None, "Project file not found"

        with open(gnai_path, 'r') as f:
            project_data = json.load(f)

        return project_data, None

    def add_clip_to_project(self, gnai_path, clip_filename, metadata_filename, duration, size, creation_date, clip_type, status="new"):
        """
        Aggiunge una clip (video o audio) al file di progetto .gnai.
        clip_type può essere 'video' o 'audio'.
        """
        if not os.path.exists(gnai_path):
            return False, "Project file not found"

        list_key = "clips" if clip_type == 'video' else "audio_clips"

        with open(gnai_path, 'r+') as f:
            project_data = json.load(f)

            # Inizializza la lista se non esiste
            if list_key not in project_data:
                project_data[list_key] = []

            # Evita di aggiungere clip duplicati
            if any(c['clip_filename'] == clip_filename for c in project_data.get(list_key, [])):
                return True, f"Clip ({clip_type}) already in project"

            now = datetime.now().isoformat()
            clip_info = {
                "clip_filename": clip_filename,
                "metadata_filename": metadata_filename,
                "addedAt": now,
                "duration": duration,
                "size": size,
                "creation_date": creation_date,
                "status": status,
                "last_seen": now
            }

            project_data[list_key].append(clip_info)

            f.seek(0)
            json.dump(project_data, f, indent=4)
            f.truncate()

        return True, f"Clip ({clip_type}) added successfully"

    def add_clip_to_project_from_path(self, gnai_path, clip_path, clip_type, status="new"):
        """
        Estrae i metadati da un percorso di clip e li aggiunge al progetto.
        """
        if not os.path.exists(clip_path):
            return False, "Clip file not found"

        try:
            # Usa il loader corretto in base al tipo
            if clip_type == 'video':
                from moviepy.editor import VideoFileClip
                media_clip = VideoFileClip(clip_path)
            else: # 'audio'
                from moviepy.editor import AudioFileClip
                media_clip = AudioFileClip(clip_path)

            with media_clip:
                duration = media_clip.duration

            size = os.path.getsize(clip_path)
            creation_date = datetime.fromtimestamp(os.path.getctime(clip_path)).isoformat()
            clip_filename = os.path.basename(clip_path)
            metadata_filename = os.path.splitext(clip_filename)[0] + ".json"

            return self.add_clip_to_project(
                gnai_path,
                clip_filename,
                metadata_filename,
                duration,
                size,
                creation_date,
                clip_type,
                status
            )
        except Exception as e:
            return False, f"Failed to process clip metadata: {e}"

    def save_project(self, gnai_path, project_data):
        """
        Salva l'intero oggetto dati del progetto nel file .gnai.
        """
        if not gnai_path:
            return False, "Invalid project path"
        try:
            with open(gnai_path, 'w') as f:
                json.dump(project_data, f, indent=4)
            return True, "Project saved successfully"
        except Exception as e:
            return False, f"Failed to save project: {e}"

    def remove_clip_from_project(self, gnai_path, clip_filename):
        """
        Rimuove una clip (video o audio) dal file di progetto .gnai.
        """
        if not os.path.exists(gnai_path):
            return False, "Project file not found"

        with open(gnai_path, 'r+') as f:
            project_data = json.load(f)
            clip_found = False

            # Cerca e rimuovi dalle clip video
            original_video_clips = project_data.get("clips", [])
            updated_video_clips = [clip for clip in original_video_clips if clip.get("clip_filename") != clip_filename]
            if len(updated_video_clips) < len(original_video_clips):
                project_data["clips"] = updated_video_clips
                clip_found = True

            # Cerca e rimuovi dalle clip audio
            original_audio_clips = project_data.get("audio_clips", [])
            updated_audio_clips = [clip for clip in original_audio_clips if clip.get("clip_filename") != clip_filename]
            if len(updated_audio_clips) < len(original_audio_clips):
                project_data["audio_clips"] = updated_audio_clips
                clip_found = True

            if not clip_found:
                return False, "Clip not found in project"

            f.seek(0)
            json.dump(project_data, f, indent=4)
            f.truncate()

        return True, "Clip removed successfully"

    def rename_clip_in_project(self, gnai_path, old_filename, new_filename):
        """
        Rinomina una clip nel file di progetto .gnai.
        """
        if not os.path.exists(gnai_path):
            return False, "Project file not found"

        with open(gnai_path, 'r+') as f:
            project_data = json.load(f)

            new_metadata_filename = os.path.splitext(new_filename)[0] + ".json"

            clip_found = False
            # Cerca e aggiorna nelle clip video
            for clip in project_data.get("clips", []):
                if clip.get("clip_filename") == old_filename:
                    clip["clip_filename"] = new_filename
                    clip["metadata_filename"] = new_metadata_filename
                    clip_found = True
                    break

            # Se non trovato, cerca e aggiorna nelle clip audio
            if not clip_found:
                for clip in project_data.get("audio_clips", []):
                    if clip.get("clip_filename") == old_filename:
                        clip["clip_filename"] = new_filename
                        clip["metadata_filename"] = new_metadata_filename
                        clip_found = True
                        break

            f.seek(0)
            json.dump(project_data, f, indent=4)
            f.truncate()

        return True, "Clip renamed successfully"

    def relink_clip(self, gnai_path, old_filename, new_filepath):
        """
        Ri-collega una clip (video o audio) offline a un nuovo percorso file.
        """
        if not os.path.exists(gnai_path):
            return False, "File di progetto non trovato"
        if not os.path.exists(new_filepath):
            return False, "Nuovo file clip non trovato"

        with open(gnai_path, 'r+') as f:
            project_data = json.load(f)
            clip_found = False

            # Cerca nelle clip video e audio
            for clip_list_key in ["clips", "audio_clips"]:
                for clip in project_data.get(clip_list_key, []):
                    if clip.get("clip_filename") == old_filename:
                        # Aggiorna i dettagli della clip
                        clip["clip_filename"] = os.path.basename(new_filepath)
                        clip["status"] = "online"
                        clip["size"] = os.path.getsize(new_filepath)
                        clip["last_seen"] = datetime.now().isoformat()
                        clip_found = True
                        break
                if clip_found:
                    break

            if not clip_found:
                return False, "Clip non trovata nel progetto"

            f.seek(0)
            json.dump(project_data, f, indent=4)
            f.truncate()

        return True, "Clip ricollegata con successo"

    def get_clip_path_by_filename(self, gnai_path, filename):
        """
        Restituisce il percorso completo di una clip dato il suo nome di file.
        """
        if not gnai_path or not os.path.exists(gnai_path):
            return None

        project_dir = os.path.dirname(gnai_path)
        clips_dir = os.path.join(project_dir, "clips")
        clip_path = os.path.join(clips_dir, filename)

        if os.path.exists(clip_path):
            return clip_path
        return None