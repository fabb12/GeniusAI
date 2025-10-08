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

        if os.path.exists(project_path):
            return None, "Project already exists"

        os.makedirs(clips_path)

        gnai_path = os.path.join(project_path, f"{project_name}.gnai")
        project_data = {
            "projectName": project_name,
            "createdAt": datetime.now().isoformat(),
            "clips": []
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

    def add_clip_to_project(self, gnai_path, clip_filename, metadata_filename, duration, size, creation_date, status="new"):
        if not os.path.exists(gnai_path):
            return False, "Project file not found"

        with open(gnai_path, 'r+') as f:
            project_data = json.load(f)

            # Evita di aggiungere clip duplicati
            if any(c['clip_filename'] == clip_filename for c in project_data.get('clips', [])):
                return True, "Clip already in project"

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

            project_data["clips"].append(clip_info)

            f.seek(0)
            json.dump(project_data, f, indent=4)
            f.truncate()

        return True, "Clip added successfully"

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
        Rimuove una clip dal file di progetto .gnai.
        """
        if not os.path.exists(gnai_path):
            return False, "Project file not found"

        with open(gnai_path, 'r+') as f:
            project_data = json.load(f)

            original_clips = project_data.get("clips", [])
            # Filtra le clip, mantenendo solo quelle che non corrispondono al nome del file da eliminare
            project_data["clips"] = [clip for clip in original_clips if clip.get("clip_filename") != clip_filename]

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

            for clip in project_data.get("clips", []):
                if clip.get("clip_filename") == old_filename:
                    clip["clip_filename"] = new_filename
                    clip["metadata_filename"] = new_metadata_filename
                    break

            f.seek(0)
            json.dump(project_data, f, indent=4)
            f.truncate()

        return True, "Clip renamed successfully"