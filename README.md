# BrontoBase File Manager

A cross-platform file manager with a GUI, built in Python. It uses PowerShell commands for file operations on Windows.

## Features
- Create, delete, rename, and move files/folders
- Search files and folders
- Zip/unzip files
- Custom GUI with PyQt5

## Project Structure
```
file_manager/
│── main.py               # Entry point
│── requirements.txt      # Dependencies list
│── README.md             # Project info
│
├── gui/                  # GUI-related code
│   ├── __init__.py
│   ├── window.py         # Main app window
│   └── widgets.py        # Custom buttons, dialogs, etc.
│
├── core/                 # Core file operations
│   ├── __init__.py
│   ├── file_ops.py       # Create, delete, rename, move
│   ├── search.py         # Search functionality
│   └── compress.py       # Zip/unzip handling
│
├── assets/               # Icons, images, etc. for GUI
│   └── icons/            
│
└── tests/                # Unit tests
    └── test_file_ops.py
```

## Setup
1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Run the application:
   ```
   python main.py
   ```

## Testing
Run unit tests with:
```
pytest tests/
```

## Platform
- Windows (uses PowerShell for file operations)
- Python 3.7+
