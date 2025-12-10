import os
import subprocess
import re
from typing import List, Dict, Optional
from pathlib import Path


class FileSearcher:
    """Enhanced file search functionality"""
    
    def __init__(self):
        self.search_results = []
    
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
    
    def search_files_windows_style(self, search_term: str, file_types: str = "", search_directory: str = "") -> List[Dict[str, any]]:
        """Windows-style search that finds files with similar names across the file system"""
        import difflib
        
        if not search_term.strip():
            return []
        
        # Parse file types
        extensions = []
        if file_types.strip():
            extensions = [ext.strip().lower() for ext in file_types.split(",")]
            # Add dot if not present
            extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]
        
        # Build PowerShell command for system-wide search
        if search_directory and os.path.exists(search_directory):
            # Search in specific directory
            base_path = search_directory
        else:
            # Search across all drives
            base_path = "C:\\"
        
        try:
            # Build file filter
            file_filter = ""
            if extensions:
                ext_filter = ",".join([f"*{ext}" for ext in extensions])
                file_filter = f"-Include {ext_filter}"
            
            # Search for files with similar names
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-ChildItem -Path '{base_path}' -Recurse -File {file_filter} | Where-Object {{$_.Name -like '*{search_term}*'}} | Select-Object FullName, Name, Length, LastWriteTime, Extension | Sort-Object Name"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().splitlines()
                results = []
                
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 4:
                            # Parse the output (format: FullName Name Length LastWriteTime Extension)
                            full_path = parts[0]
                            name = parts[1]
                            size = int(parts[2]) if parts[2].isdigit() else 0
                            modified = ' '.join(parts[3:-1]) if len(parts) > 4 else parts[3]
                            extension = parts[-1] if len(parts) > 4 else ""
                            
                            # Calculate similarity score
                            similarity = difflib.SequenceMatcher(None, search_term.lower(), name.lower()).ratio()
                            
                            results.append({
                                'path': full_path,
                                'name': name,
                                'size': size,
                                'modified': modified,
                                'extension': extension,
                                'similarity': similarity
                            })
                
                # Sort by similarity score (highest first)
                results.sort(key=lambda x: x['similarity'], reverse=True)
                
                # Limit results to top 100
                return results[:100]
            
            return []
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception):
            return []


# Legacy function for backward compatibility
def search_files(directory, pattern):
    """Legacy search function for backward compatibility"""
    searcher = FileSearcher()
    return searcher.search_files(directory, pattern)
