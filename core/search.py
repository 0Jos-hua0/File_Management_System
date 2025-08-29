import subprocess

def search_files(directory, pattern):
    cmd = [
        "powershell",
        "Get-ChildItem",
        directory,
        "-Recurse",
        "-Filter",
        pattern,
        "| Select-Object -ExpandProperty FullName"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip().splitlines() if result.stdout else []
