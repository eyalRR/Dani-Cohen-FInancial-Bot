import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
import os

class History:
    """Manages the run history for the financial bot."""
    
    def __init__(self, history_file: str = "run_history.json"):
        self.history_file = Path(history_file)
        print(f"loading history from: {self.history_file}")
        self.history = self._load_history()
    
    def _load_history(self) -> Dict:
        """Load history from JSON file."""
        if not self.history_file.exists():
            return {}
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading history file: {e}")
            return {}
    
    def save_history(self) -> None:
        """Save current history to JSON file."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except IOError as e:
            print(f"Error saving history file: {e}")
    
    
    def get_timestamp(self, timestamp_name: str) -> Optional[datetime]:
        """Get timestamp datetime object from history."""
        str_timestamp = self.history.get(f'last_{timestamp_name}')
        if str_timestamp:
            try:
                return datetime.fromisoformat(str_timestamp)
            except (ValueError, TypeError) as e:
                print(f"Error parsing timestamp {timestamp_name}: {e}")
                return None
        return None

    def get_timestamp_delta(self, timestamp_name: str, now: datetime=None) -> timedelta:
        """Get time delta since last timestamp. Returns a very large delta if no timestamp exists."""
        if now is None:
            now = datetime.now()
        timestamp = self.get_timestamp(timestamp_name)
        if timestamp:
            return now - timestamp
        # Return a very large delta if no timestamp exists
        return timedelta(days=999)

    def update_timestamp(self, timestamp_name: str, now: datetime=None) -> None:
        """Update the last analysis timestamp for specified type."""
        if now is None:
            now = datetime.now()
        self.history[f'last_{timestamp_name}'] = now.isoformat()
        self.save_history()
    
    def is_timestamp_in_current_month(self, timestamp_name: str, now: datetime=None) -> bool:
        """Return true if last timestamp accord during this month."""
        if now is None:
            now = datetime.now()
        timestamp = self.get_timestamp(timestamp_name)
        if timestamp is not None:
            return timestamp.month == now.month
        # Return false if no timestamp exists
        return False
    
    def get_history(self) -> Dict:
        return self.history.copy()
    
    def set_history(self, history: Dict) -> None:
        self.history = history.copy()
        self.save_history() 