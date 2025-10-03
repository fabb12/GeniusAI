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

    def create_project(self, project_name=None):
        if not project_name:
            project_name = self.get_next_untitled_project_name()

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

    def add_clip_to_project(self, gnai_path, clip_filename, metadata_filename):
        if not os.path.exists(gnai_path):
            return False, "Project file not found"

        with open(gnai_path, 'r+') as f:
            project_data = json.load(f)

            clip_info = {
                "clip_filename": clip_filename,
                "metadata_filename": metadata_filename,
                "addedAt": datetime.now().isoformat()
            }

            project_data["clips"].append(clip_info)

            f.seek(0)
            json.dump(project_data, f, indent=4)
            f.truncate()

        return True, "Clip added successfully"