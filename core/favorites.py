import os
import json
from pathlib import Path
from typing import List, Dict, Optional


class FavoritesManager:
    """Handles favorites functionality for the file manager"""
    
    def __init__(self, app_name: str = "BrontoBase"):
        self.app_name = app_name
        self.favorites_file = self._get_favorites_file_path()
    
    def _get_favorites_file_path(self) -> str:
        """Get the path to the favorites storage file"""
        app_data = os.path.join(os.path.expanduser("~"), "AppData", "Local", self.app_name)
        os.makedirs(app_data, exist_ok=True)
        return os.path.join(app_data, "favorites.json")
    
    def load_favorites(self) -> List[Dict[str, str]]:
        """Load favorites from storage"""
        if os.path.exists(self.favorites_file):
            try:
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []
    
    def save_favorites(self, favorites: List[Dict[str, str]]) -> bool:
        """Save favorites to storage"""
        try:
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(favorites, f, indent=2, ensure_ascii=False)
            return True
        except IOError:
            return False
    
    def add_favorite(self, path: str) -> bool:
        """Add a file or folder to favorites"""
        if not os.path.exists(path):
            return False
        
        favorites = self.load_favorites()
        
        # Check if already in favorites
        if any(fav['path'] == path for fav in favorites):
            return False
        
        favorite_item = {
            'name': os.path.basename(path),
            'path': path,
            'type': 'folder' if os.path.isdir(path) else 'file',
            'added_date': str(Path(path).stat().st_mtime)
        }
        
        favorites.append(favorite_item)
        return self.save_favorites(favorites)
    
    def remove_favorite(self, path: str) -> bool:
        """Remove a favorite item"""
        favorites = self.load_favorites()
        original_count = len(favorites)
        favorites = [fav for fav in favorites if fav['path'] != path]
        
        if len(favorites) < original_count:
            return self.save_favorites(favorites)
        return False
    
    def is_favorite(self, path: str) -> bool:
        """Check if a path is in favorites"""
        favorites = self.load_favorites()
        return any(fav['path'] == path for fav in favorites)
    
    def get_favorites(self) -> List[Dict[str, str]]:
        """Get all favorites"""
        favorites = self.load_favorites()
        # Filter out non-existent paths
        valid_favorites = [fav for fav in favorites if os.path.exists(fav['path'])]
        
        # Update the storage if some favorites were removed
        if len(valid_favorites) != len(favorites):
            self.save_favorites(valid_favorites)
        
        return valid_favorites
    
    def get_favorite_by_path(self, path: str) -> Optional[Dict[str, str]]:
        """Get a specific favorite by path"""
        favorites = self.load_favorites()
        for fav in favorites:
            if fav['path'] == path:
                return fav
        return None
    
    def clear_favorites(self) -> bool:
        """Clear all favorites"""
        return self.save_favorites([])
    
    def get_favorites_count(self) -> int:
        """Get the number of favorites"""
        return len(self.get_favorites())
