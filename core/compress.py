import subprocess
import os

def zip_folder(source, dest_zip):
    if not os.path.exists(source):
        raise FileNotFoundError(f"Source not found: {source}")
    subprocess.run([
        "powershell",
        "Compress-Archive",
        "-Path", source,
        "-DestinationPath", dest_zip
    ], check=True)

def unzip_file(zip_path, dest_folder):
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"Zip file not found: {zip_path}")
    subprocess.run([
        "powershell",
        "Expand-Archive",
        "-Path", zip_path,
        "-DestinationPath", dest_folder,
        "-Force"
    ], check=True)
