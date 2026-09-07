import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class DownloadHistoryEntry:
    title: str
    url: str
    video_id: str
    author: str
    resolution: str
    audio_only: bool
    file_path: str
    file_size: int
    download_time: str
    duration: int
    thumbnail_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DownloadHistoryEntry":
        return cls(**data)


class HistoryManager:
    def __init__(self, history_file: Optional[str] = None):
        if history_file is None:
            app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
            history_dir = os.path.join(app_data, "YTVidDownloader")
            os.makedirs(history_dir, exist_ok=True)
            history_file = os.path.join(history_dir, "download_history.json")
        
        self.history_file = history_file
        self._history: List[DownloadHistoryEntry] = []
        self._load()

    def _load(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._history = [DownloadHistoryEntry.from_dict(item) for item in data]
            except Exception:
                self._history = []

    def _save(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([entry.to_dict() for entry in self._history], f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def add_entry(self, entry: DownloadHistoryEntry):
        self._history.insert(0, entry)
        if len(self._history) > 500:
            self._history = self._history[:500]
        self._save()

    def get_history(self) -> List[DownloadHistoryEntry]:
        return self._history

    def clear_history(self):
        self._history = []
        self._save()

    def remove_entry(self, index: int):
        if 0 <= index < len(self._history):
            self._history.pop(index)
            self._save()

    def get_entry(self, index: int) -> Optional[DownloadHistoryEntry]:
        if 0 <= index < len(self._history):
            return self._history[index]
        return None