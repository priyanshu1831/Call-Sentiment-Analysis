import os
import json
from datetime import datetime

class FileStorage:
    def __init__(self, base_dir="data/user_data"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
    
    def get_user_directory(self, user_id):
        user_dir = os.path.join(self.base_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def save_transcript(self, user_id, file_obj, filename):
        user_dir = self.get_user_directory(user_id)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{os.path.basename(filename)}"
        file_path = os.path.join(user_dir, safe_filename)
        
        with open(file_path, 'wb') as f:
            f.write(file_obj.getvalue())
        
        return safe_filename
    
    def save_analysis(self, user_id, filename, analysis_data):
        user_dir = self.get_user_directory(user_id)
        analysis_dir = os.path.join(user_dir, 'analysis')
        os.makedirs(analysis_dir, exist_ok=True)
        
        analysis_file = os.path.join(
            analysis_dir,
            f"{os.path.splitext(filename)[0]}_analysis.json"
        )
        
        with open(analysis_file, 'w') as f:
            json.dump(analysis_data, f, indent=2)
        
        return analysis_file