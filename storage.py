"""Storage: the only place that reads and writes the JSON data files."""

import json
import os
import shutil

# The data folder sits next to this file, no matter where the program is started from.
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


class Storage:
    def __init__(self, data_dir=DEFAULT_DATA_DIR):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def _path(self, filename):
        return os.path.join(self.data_dir, filename)

    def load(self, filename, default):
        """Return the data from a JSON file, or `default` if the file is missing or empty."""
        path = self._path(filename)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return default
        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            # The file is damaged: keep a copy so nothing is lost, then start fresh.
            backup = path + ".broken"
            shutil.copy(path, backup)
            print(f"Warning: {filename} is damaged. A copy was saved as {os.path.basename(backup)}.")
            return default

    def save(self, filename, data):
        """Write data to a JSON file. Writing to a temp file first avoids half-written files."""
        path = self._path(filename)
        temp_path = path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        os.replace(temp_path, path)