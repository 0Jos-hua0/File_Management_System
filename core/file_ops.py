import subprocess
import os

def create_file(path):
    if os.path.exists(path):
        raise FileExistsError(f"File already exists: {path}")
    subprocess.run(["powershell", "New-Item", path, "-ItemType", "File"], check=True)

def delete_file(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    subprocess.run(["powershell", "Remove-Item", path, "-Force"], check=True)

def rename_file(src, dst):
    if not os.path.exists(src):
        raise FileNotFoundError(f"Source not found: {src}")
    subprocess.run(["powershell", "Rename-Item", src, dst], check=True)

def move_file(src, dst):
    if not os.path.exists(src):
        raise FileNotFoundError(f"Source not found: {src}")
    subprocess.run(["powershell", "Move-Item", src, dst], check=True)
