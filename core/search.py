import os
import subprocess
import re
from typing import List, Dict, Optional
from pathlib import Path
from difflib import SequenceMatcher


class FileSearcher:
    """Enhanced file search functionality like Windows File Explorer"""
    
    def __init__(self):
        self.search_results = []
    
    def search_files_windows_style(self, search_text: str, file_type: str = "", search_directory: str = "") -> List[Dict[str, any]]:
        """Search files like Windows File Explorer with fuzzy matching"""
        if not search_text.strip():
            return []
        
        # If no directory specified, search from root drives
        if not search_directory:
            search_directories = self._get_search_directories()
        else:
            search_directories = [search_directory]
        
        all_results = []
        
        for directory in search_directories:
            if os.path.exists(directory):
                results = self._search_directory_windows_style(directory, search_text, file_type)
                all_results.extend(results)
        
        # Sort by relevance (similarity score)
        all_results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return all_results
    
    def _get_search_directories(self) -> List[str]:
        """Get directories to search in (like Windows File Explorer)"""
        directories = []
        
        # Add user's home directory and common folders
        home_dir = os.path.expanduser("~")
        if os.path.exists(home_dir):
            directories.append(home_dir)
        
        # Add Windows drives
        if os.name == 'nt':
            import string
            for drive in string.ascii_uppercase:
                drive_path = f"{drive}:\\"
                if os.path.exists(drive_path):
                    directories.append(drive_path)
        
        return directories
    
    def _search_directory_windows_style(self, directory: str, search_text: str, file_type: str = "") -> List[Dict[str, any]]:
        """Search a directory with Windows-style fuzzy matching"""
        results = []
        search_text_lower = search_text.lower()
        
        try:
            # Build PowerShell command for recursive search
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-ChildItem -Path '{directory}' -Recurse -File | Select-Object FullName, Name, Length, LastWriteTime, Extension"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().splitlines()
                
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 4:
                            file_path = parts[0]
                            file_name = parts[1]
                            file_size = int(parts[2]) if parts[2].isdigit() else 0
                            file_extension = parts[3] if len(parts) > 3 else ""
                            modified_date = ' '.join(parts[4:]) if len(parts) > 4 else ""
                            
                            # Check if file matches search criteria
                            if self._matches_search_criteria(file_name, file_extension, search_text_lower, file_type):
                                similarity = self._calculate_similarity(file_name, search_text)
                                
                                results.append({
                                    'path': file_path,
                                    'name': file_name,
                                    'size': file_size,
                                    'extension': file_extension,
                                    'modified': modified_date,
                                    'similarity': similarity
                                })
        
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception):
            pass
        
        return results
    
    def _matches_search_criteria(self, file_name: str, file_extension: str, search_text: str, file_type: str) -> bool:
        """Check if file matches search criteria"""
        file_name_lower = file_name.lower()
        file_ext_lower = file_extension.lower().lstrip('.')
        
        # Check if search text is in filename (case insensitive)
        if search_text in file_name_lower:
            # If file type is specified, check if it matches
            if file_type:
                return file_type.lower() in file_ext_lower
            return True
        
        # Check for partial matches (like Windows File Explorer)
        search_words = search_text.split()
        for word in search_words:
            if word in file_name_lower:
                # If file type is specified, check if it matches
                if file_type:
                    return file_type.lower() in file_ext_lower
                return True
        
        return False
    
    def _calculate_similarity(self, file_name: str, search_text: str) -> float:
        """Calculate similarity score between filename and search text"""
        file_name_lower = file_name.lower()
        search_text_lower = search_text.lower()
        
        # Exact match gets highest score
        if file_name_lower == search_text_lower:
            return 1.0
        
        # Starts with search text gets high score
        if file_name_lower.startswith(search_text_lower):
            return 0.9
        
        # Contains search text gets medium score
        if search_text_lower in file_name_lower:
            return 0.7
        
        # Use sequence matcher for fuzzy matching
        similarity = SequenceMatcher(None, file_name_lower, search_text_lower).ratio()
        
        # Boost score if search text is a substring
        if search_text_lower in file_name_lower:
            similarity += 0.3
        
        return min(similarity, 1.0)
    
    def search_files(self, directory: str, pattern: str, recursive: bool = True) -> List[str]:
        """Search for files using PowerShell Get-ChildItem"""
        if not os.path.exists(directory):
            return []
        
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-ChildItem -Path '{directory}' -Recurse:{str(recursive).lower()} -Filter '{pattern}' | Select-Object -ExpandProperty FullName"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout:
                return [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
            return []
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception):
            return []
    
    def search_by_content(self, directory: str, search_text: str, file_extensions: Optional[List[str]] = None) -> List[str]:
        """Search for files containing specific text"""
        if not os.path.exists(directory):
            return []
        
        try:
            # Build file filter
            file_filter = ""
            if file_extensions:
                extensions = ",".join([f"*.{ext}" for ext in file_extensions])
                file_filter = f"-Include {extensions}"
            
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-ChildItem -Path '{directory}' -Recurse {file_filter} | Select-String -Pattern '{search_text}' -List | Select-Object -ExpandProperty Filename | Get-Unique"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and result.stdout:
                return [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
            return []
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception):
            return []
    
    def search_by_size(self, directory: str, min_size: Optional[int] = None, max_size: Optional[int] = None) -> List[Dict[str, any]]:
        """Search for files by size range (in bytes)"""
        if not os.path.exists(directory):
            return []
        
        try:
            size_filter = ""
            if min_size is not None and max_size is not None:
                size_filter = f"| Where-Object {{$_.Length -ge {min_size} -and $_.Length -le {max_size}}}"
            elif min_size is not None:
                size_filter = f"| Where-Object {{$_.Length -ge {min_size}}}"
            elif max_size is not None:
                size_filter = f"| Where-Object {{$_.Length -le {max_size}}}"
            
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-ChildItem -Path '{directory}' -Recurse -File {size_filter} | Select-Object FullName, Length, LastWriteTime"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().splitlines()
                results = []
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            results.append({
                                'path': parts[0],
                                'size': int(parts[1]) if parts[1].isdigit() else 0,
                                'modified': ' '.join(parts[2:])
                            })
                return results
            return []
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception):
            return []
    
    def search_by_date(self, directory: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, any]]:
        """Search for files by date range"""
        if not os.path.exists(directory):
            return []
        
        try:
            date_filter = ""
            if start_date and end_date:
                date_filter = f"| Where-Object {{$_.LastWriteTime -ge '{start_date}' -and $_.LastWriteTime -le '{end_date}'}}"
            elif start_date:
                date_filter = f"| Where-Object {{$_.LastWriteTime -ge '{start_date}'}}"
            elif end_date:
                date_filter = f"| Where-Object {{$_.LastWriteTime -le '{end_date}'}}"
            
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-ChildItem -Path '{directory}' -Recurse -File {date_filter} | Select-Object FullName, Length, LastWriteTime"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().splitlines()
                results = []
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            results.append({
                                'path': parts[0],
                                'size': int(parts[1]) if parts[1].isdigit() else 0,
                                'modified': ' '.join(parts[2:])
                            })
                return results
            return []
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception):
            return []
    
    def format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"


# Legacy function for backward compatibility
def search_files(directory, pattern):
    """Legacy search function for backward compatibility"""
    searcher = FileSearcher()
    return searcher.search_files(directory, pattern)
