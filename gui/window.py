import os
import json
import pickle
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter,
    QTreeView, QTableView, QPushButton, QListView, QStackedWidget, QRadioButton, QButtonGroup,
    QMessageBox, QInputDialog, QStatusBar, QFileSystemModel, QFrame, QHeaderView, QFileDialog,
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter,
    QTreeView, QTableView, QPushButton, QListView, QStackedWidget, QRadioButton, QButtonGroup,
    QMessageBox, QInputDialog, QStatusBar, QFileSystemModel, QFrame, QHeaderView, QFileDialog,
    QMenu, QDialog, QLineEdit, QComboBox, QCheckBox, QTextEdit, QProgressBar, QGroupBox, QApplication,
    QTabWidget, QFormLayout, QFontComboBox, QSpinBox
)
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QSize, QDir, QFileInfo, QDateTime
from PyQt5.QtGui import QIcon, QPalette, QColor, QLinearGradient, QStandardItemModel, QStandardItem, QFont

# Assume core modules exist in a 'core' directory
# from core import NavigationHistory, FavoritesManager, FileSearcher

# ---- Mock core modules for standalone execution ----
class NavigationHistory:
    def __init__(self):
        self.history = []
        self.current_index = -1
    def add_to_history(self, path):
        if self.current_index < len(self.history) - 1:
            self.history = self.history[:self.current_index + 1]
        self.history.append(path)
        self.current_index += 1
    def go_back(self):
        if self.current_index > 0:
            self.current_index -= 1
            return self.history[self.current_index]
        return None
    def go_forward(self):
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            return self.history[self.current_index]
        return None

class FavoritesManager:
    def __init__(self, filepath='favorites.json'):
        self.filepath = filepath
        self.favorites = self._load()
    def _load(self):
        try:
            with open(self.filepath, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    def _save(self):
        with open(self.filepath, 'w') as f:
            json.dump(self.favorites, f, indent=4)
    def get_favorites(self):
        return self.favorites
    def add_favorite(self, path):
        if not os.path.exists(path) or any(fav['path'] == path for fav in self.favorites):
            return False
        name = os.path.basename(path)
        fav_type = 'file' if os.path.isfile(path) else 'folder'
        self.favorites.append({'name': name, 'path': path, 'type': fav_type})
        self._save()
        return True
    def remove_favorite(self, path):
        initial_len = len(self.favorites)
        self.favorites = [fav for fav in self.favorites if fav['path'] != path]
        if len(self.favorites) < initial_len:
            self._save()
            return True
        return False

class FileSearcher:
    def search_files(self, directory, pattern, recursive=True):
        results = []
        for root, _, files in os.walk(directory):
            for name in files:
                if pattern in name: # Simple substring search
                    results.append(os.path.join(root, name))
            if not recursive:
                break
        return results
    def search_by_content(self, directory, content, extensions=None): return []
    def search_by_size(self, directory, min_size, max_size): return []
    def search_by_date(self, directory, start_date, end_date): return []
    def format_size(self, size_bytes):
        if size_bytes < 1024: return f"{size_bytes} B"
        elif size_bytes < 1024**2: return f"{size_bytes/1024:.2f} KB"
        elif size_bytes < 1024**3: return f"{size_bytes/1024**2:.2f} MB"
        else: return f"{size_bytes/1024**3:.2f} GB"

# ---- add imports for ctypes known folders ----
import sys
import ctypes
from ctypes import wintypes


class DirsOnlyProxyModel(QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row, source_parent):
        index = self.sourceModel().index(source_row, 0, source_parent)
        return self.sourceModel().isDir(index)

class FileSystemProxyModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.show_extensions = True

    def set_show_extensions(self, show):
        self.show_extensions = show
        # Invalidate data to trigger refresh
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount(), 0))
        # Sometimes layoutChanged is needed for deeper refresh
        self.layoutChanged.emit()

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and index.column() == 0 and not self.show_extensions:
            # Get original name
            source_index = self.mapToSource(index)
            # QFileSystemModel uses the file name for display
            original_name = self.sourceModel().data(source_index, Qt.DisplayRole)
            if original_name and not self.sourceModel().isDir(source_index):
                return os.path.splitext(original_name)[0]
        return super().data(index, role)


# ---- Known Folders support ----
if sys.platform.startswith('win'):
    _SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
    _SHGetKnownFolderPath.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar_p)]
    _SHGetKnownFolderPath.restype = ctypes.c_long

    def _get_known_folder_path(folder_guid_str: str) -> str:
        path_ptr = ctypes.c_wchar_p()
        guid = ctypes.c_buffer(16)
        ctypes.windll.ole32.CLSIDFromString(ctypes.c_wchar_p(folder_guid_str), ctypes.byref(guid))
        hr = _SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(path_ptr))
        if hr != 0:
            return ""
        return path_ptr.value or ""

    # KNOWNFOLDERID constants
    FOLDERID_Documents = '{FDD39AD0-238F-46AF-ADB4-6C85480369C7}'
    FOLDERID_Pictures  = '{33E28130-4E1E-4676-835A-98395C3BC3BB}'
    FOLDERID_Videos    = '{18989B1D-99B5-455B-841C-AB7C74E4DDFC}'
    FOLDERID_Music     = '{4BD8D571-6D19-48D3-BE97-422220080E43}'
    FOLDERID_Downloads = '{374DE290-123F-4565-9164-39C4925E467B}'
else:
    def _get_known_folder_path(folder_guid_str: str) -> str:
        return ""
    FOLDERID_Documents = FOLDERID_Pictures = FOLDERID_Videos = FOLDERID_Music = FOLDERID_Downloads = ""


def resolve_special_folder(label: str) -> str:
    """Return the best path for a Windows special folder. Falls back to common locations and OneDrive."""
    user = str(Path.home())
    if sys.platform.startswith('win'):
        try_map = {
            'Documents': _get_known_folder_path(FOLDERID_Documents),
            'Images':    _get_known_folder_path(FOLDERID_Pictures),
            'Videos':    _get_known_folder_path(FOLDERID_Videos),
            'Music':     _get_known_folder_path(FOLDERID_Music),
            'Downloads': _get_known_folder_path(FOLDERID_Downloads),
            'OneDrive':  os.environ.get('OneDrive') or os.path.join(user, 'OneDrive')
        }
        path = try_map.get(label) or ""
        if path and os.path.exists(path):
            return path
    # Fallbacks (including OneDrive-local conventions)
    onedrive_base = os.environ.get('OneDrive') or os.path.join(user, 'OneDrive')
    fallback_map = {
        'Documents': [os.path.join(onedrive_base, 'Documents'), os.path.join(user, 'Documents'), os.path.join(user, 'My Documents')],
        'Images':    [os.path.join(onedrive_base, 'Pictures'),  os.path.join(user, 'Pictures'),  os.path.join(user, 'My Pictures')],
        'Videos':    [os.path.join(onedrive_base, 'Videos'),    os.path.join(user, 'Videos'),    os.path.join(user, 'My Videos')],
        'Music':     [os.path.join(onedrive_base, 'Music'),     os.path.join(user, 'Music'),     os.path.join(user, 'My Music')],
        'Downloads': [os.path.join(user, 'Downloads')],
        'OneDrive':  [onedrive_base],
    }
    for candidate in fallback_map.get(label, []):
        if candidate and os.path.exists(candidate):
            return candidate
    return user


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BrontoASPHERE File Manager")
        self.setGeometry(100, 100, 1400, 850) # Increased size for better layout

        # Initialize core modules first
        self.navigation_history = NavigationHistory()
        self.favorites_manager = FavoritesManager()
        self.file_searcher = FileSearcher()

        # --- Create a centralized icon manager ---
        self._create_icons()

        # Apply dark theme
        self.apply_dark_theme()

        # === Header Section (Row 1) ===
        header_row = QWidget()
        header_row.setStyleSheet("background: #20201f; border-bottom: 1px solid #1a1a1a;")
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 5)
        header_layout.setSpacing(10)
        header_row.setFixedHeight(50)

        self.header_buttons = {}
        for section in ["File", "Home", "Settings"]:
            btn = QPushButton(section)
            btn.setCheckable(True)
            btn.setMinimumHeight(35)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #333333; color: #ffd700; border: 1px solid #555555;
                    border-radius: 4px; padding: 5px 15px;
                }
                QPushButton:hover { background-color: #444444; border: 1px solid #ffd700; }
                QPushButton:checked {
                    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ffd700, stop: 1 #b8860b);
                    color: #000000; font-weight: bold; border: 1px solid #ffd700;
                }
            """)
            btn.clicked.connect(lambda checked, s=section: self.switch_header_section(s))
            header_layout.addWidget(btn)
            self.header_buttons[section] = btn
        header_row.setLayout(header_layout)

        # === Ribbon Options Row (Row 2) ===
        self.ribbon_options_row = QWidget()
        self.ribbon_options_row.setStyleSheet("background: #20201f; border-bottom: 2px solid #20201f;")
        self.ribbon_options_layout = QHBoxLayout()
        self.ribbon_options_layout.setContentsMargins(10, 5, 10, 5)
        self.ribbon_options_layout.setSpacing(15)
        self.ribbon_options_row.setFixedHeight(95)
        self.ribbon_options_row.setLayout(self.ribbon_options_layout)

        # === NEW: Address Bar Section (Row 3) ===
        address_bar_container = QWidget()
        address_bar_container.setStyleSheet("background-color: #20201f;")
        address_layout = QHBoxLayout()
        address_layout.setContentsMargins(55, 0, 55, 0)
        address_bar_container.setFixedHeight(50)
        
        self.path_edit = QLineEdit()
        
        self.path_edit.setFixedHeight(30)
        self.path_edit.setStyleSheet("""
            QLineEdit {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 4px;
                padding-left: 10px;
                color: #ccc;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border: 1px solid #ffd700;
            }
        """)
        self.path_edit.returnPressed.connect(self.on_path_entered)
        address_layout.addWidget(self.path_edit)
        address_bar_container.setLayout(address_layout)

        # Set initial section
        self.header_section = "File"
        self.switch_header_section("Home") # Default to Home for a more useful initial view

        # === File System Model ===
        self.model = QFileSystemModel()
        self.model.setRootPath('')
        self.model.setFilter(self.model.filter() |  QDir.Hidden) # Show hidden files

        # === Combined Navigation Tree (Quick Access + Drives) ===
        self.nav_model = QStandardItemModel()
        self.nav_model.setHorizontalHeaderLabels(["Navigation"])
        self.nav_tree = QTreeView()
        self.nav_tree.setModel(self.nav_model)
        self.nav_tree.setHeaderHidden(False)
        self.nav_tree.setStyleSheet("""
            QTreeView {
                background:#20201f; color:#ccc; border:none;
                alternate-background-color:#333333; outline: 0;
                font-size: 10pt; /* Uniform font size */
            }
            QTreeView::item { padding: 6px; border: none; }
            QTreeView::item:selected {
                background-color: rgba(255, 215, 0, 0.2); /* Semi-transparent gold */
                color: #ffd700;
                border-left: 3px solid #ffd700;
            }
            QTreeView::item:hover:!selected { background-color: #383838; }
            QTreeView::branch { background-color: transparent; }
        """)

        # Style the tree view header specifically
        self.nav_tree.header().setStyleSheet("""
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3c3c3c, stop:1 #20201f);
                color: #ffd700; padding: 5px; border: 1px solid #555;
                font-weight: bold; border-bottom: 2px solid #555;
            }
        """)

        self.build_navigation_tree()
        self.nav_tree.expanded.connect(self.on_nav_expanded)
        self.nav_tree.clicked.connect(self.on_nav_clicked)
        self.nav_tree.doubleClicked.connect(self.on_nav_double_clicked)
        self.nav_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.nav_tree.customContextMenuRequested.connect(self.on_nav_context_menu)

        # === Proxy Model ===
        self.proxy_model = FileSystemProxyModel()
        self.proxy_model.setSourceModel(self.model)

        # === File View (QTableView - List View) ===
        self.file_view = QTableView()
        self.file_view.setModel(self.proxy_model)
        # We need to map the root path to the proxy index
        root_idx = self.model.index(self.model.rootPath())
        self.file_view.setRootIndex(self.proxy_model.mapFromSource(root_idx))
        self.file_view.setSelectionBehavior(QTableView.SelectRows)
        self.file_view.setAlternatingRowColors(True)

        self.file_view.setStyleSheet("""
    QTableView {
        background:#111111;
        color:#ccc;
        alternate-background-color:#181818;
        border:none; outline: 0;
        font-size: 10pt;
    }
    QTableView::item { padding: 5px; border: none; }
    QTableView::item:selected {
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #b8860b, stop:1 #ffd700);
        color:#000; font-weight:bold;
    }
    QTableView::item:hover:!selected {
        background-color: #2b2b2b;
    }
    QScrollBar:vertical, QScrollBar:horizontal {
        border: none; background: #181818;
        width: 12px; height: 12px;
    }
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
        background: #444444; border-radius: 6px; min-height: 20px;
    }
    QScrollBar::handle:hover { background: #555555; }
    QScrollBar::add-line, QScrollBar::sub-line { border: none; background: none; }
    QTableCornerButton::section { background: #20201f; border: none; }
""")

        # Style the file view headers
        header_style = """
            QHeaderView { background: #20201f; }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3c3c3c, stop:1 #20201f);
                color: #ffd700; padding: 5px; border: none; border-right: 1px solid #555;
                font-weight: bold;
            }
        """
        self.file_view.horizontalHeader().setStyleSheet(header_style)
        self.file_view.verticalHeader().setStyleSheet(header_style)

        # Ensure important columns are visible and sized
        header = self.file_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        self.file_view.setColumnWidth(0, 350)
        self.file_view.setColumnWidth(1, 120)
        self.file_view.setColumnWidth(2, 140)
        self.file_view.setColumnWidth(3, 170)

        self.file_view.doubleClicked.connect(self.open_file)
        self.file_view.setSortingEnabled(True)
        self.file_view.sortByColumn(3, Qt.DescendingOrder)
        self.file_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_view.customContextMenuRequested.connect(self.on_file_context_menu)

        # === Grid View (QListView) ===
        self.file_grid_view = QListView()
        self.file_grid_view.setModel(self.proxy_model)
        self.file_grid_view.setRootIndex(self.proxy_model.mapFromSource(root_idx))
        self.file_grid_view.setViewMode(QListView.IconMode)
        self.file_grid_view.setIconSize(QSize(64, 64))
        self.file_grid_view.setGridSize(QSize(100, 100))
        self.file_grid_view.setResizeMode(QListView.Adjust)
        self.file_grid_view.setUniformItemSizes(True)
        self.file_grid_view.setWordWrap(True)
        self.file_grid_view.setSelectionMode(QListView.ExtendedSelection)
        self.file_grid_view.setStyleSheet("""
            QListView {
                background: #111111; color: #ccc; border: none; outline: 0;
            }
            QListView::item {
                padding: 5px; border: none; border-radius: 5px;
            }
            QListView::item:selected {
                background-color: rgba(255, 215, 0, 0.3);
                border: 1px solid #ffd700;
                color: #ffd700;
            }
        """)
        self.file_grid_view.doubleClicked.connect(self.open_file)
        self.file_grid_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_grid_view.customContextMenuRequested.connect(self.on_file_context_menu)

        # === View Stack ===
        self.view_stack = QStackedWidget()
        self.view_stack.addWidget(self.file_view)      # Index 0: List
        self.view_stack.addWidget(self.file_grid_view) # Index 1: Grid

        # === Splitter ===
        tree_and_files_splitter = QSplitter(Qt.Horizontal)
        tree_and_files_splitter.setStyleSheet("""
            QSplitter::handle {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #555, stop:0.5 #333, stop:1 #555);
                width: 4px;
            }
            QSplitter::handle:hover { background-color:#ffd700; }
        """)
        tree_and_files_splitter.addWidget(self.nav_tree)
        tree_and_files_splitter.addWidget(self.view_stack)

        tree_and_files_splitter.setSizes([300, 900])

        # === Layout Central Widget ===
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        layout.addWidget(header_row)
        layout.addWidget(self.ribbon_options_row)
        layout.addWidget(address_bar_container) # Add address bar here
        layout.addWidget(tree_and_files_splitter)
        self.setCentralWidget(central_widget)

        # === Status Bar ===
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #3c3c3c, stop: 1 #5a5a5a);
                color: #ffd700; border-top: 1px solid #555555;
            }
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Clipboard state for Cut/Copy/Paste
        self.clipboard_paths = []
        self.clipboard_mode = None

        # Initial navigation to home directory
        self.navigate_to_directory(str(Path.home()))

    def _create_icons(self):
        """Creates and stores QIcons for the application."""
        # Resolve absolute path to assets directory
        # window.py is in gui/, so we go up one level to find assets
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        assets_dir = os.path.join(base_dir, "assets")

        def get_icon_path(name):
            # Try to find the icon in known subdirectories
            for sub in ["file_icons", "icons"]:
                path = os.path.join(assets_dir, sub, name)
                if os.path.exists(path):
                    return path
            # Return a valid path string even if it doesn't exist, to avoid crashes in QIcon
            return os.path.join(assets_dir, "file_icons", name)

        self.icons = {
            'quick_access': QIcon.fromTheme("folder", QIcon(get_icon_path("quick_access.png"))),
            'favorites': QIcon.fromTheme("emblem-favorite", QIcon(get_icon_path("favourites.png"))),
            'drives': QIcon.fromTheme("drive-harddisk", QIcon(get_icon_path("drives.png"))),
            'documents': QIcon.fromTheme("folder-documents", QIcon(get_icon_path("documents.png"))),
            'downloads': QIcon.fromTheme("folder-download", QIcon(get_icon_path("downloads.png"))),
            'music': QIcon.fromTheme("folder-music", QIcon(get_icon_path("music.png"))),
            'pictures': QIcon.fromTheme("folder-pictures", QIcon(get_icon_path("images.png"))),
            'videos': QIcon.fromTheme("folder-videos", QIcon(get_icon_path("videos.png"))),
            'onedrive': QIcon(get_icon_path("onedrive.png")),
            'drive': QIcon.fromTheme("drive-harddisk", QIcon(get_icon_path("drive.png"))),
            'folder': QIcon.fromTheme("folder", QIcon(get_icon_path("folder.png"))),
            'file': QIcon.fromTheme("text-x-generic", QIcon(get_icon_path("file.png"))),
        }

    def apply_dark_theme(self):
        palette = QPalette()
        # --- FIXED: Clamped invalid RGB values to the valid 0-255 range ---
        palette.setColor(QPalette.Window, QColor(32, 32, 31))
        palette.setColor(QPalette.WindowText, QColor(204, 204, 204))
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(32, 32, 32))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 215, 0))
        palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.Text, QColor(204, 204, 204))
        palette.setColor(QPalette.Button, QColor(42, 42, 42))
        palette.setColor(QPalette.ButtonText, QColor(204, 204, 204))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(255, 215, 0))
        palette.setColor(QPalette.Highlight, QColor(255, 215, 0))
        palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        palette.setColor(QPalette.Light, QColor(60, 60, 60))
        palette.setColor(QPalette.Midlight, QColor(50, 50, 50))
        palette.setColor(QPalette.Dark, QColor(30, 30, 30))
        palette.setColor(QPalette.Mid, QColor(45, 45, 45))
        palette.setColor(QPalette.Shadow, QColor(20, 20, 20))
        palette.setColor(QPalette.Button, QColor(60, 60, 60))
        self.setPalette(palette)

        font = QFont("High Tower Text", 11)
        if sys.platform == "darwin":
             font = QFont("Helvetica Neue", 11)
        QApplication.setFont(font)

    def switch_header_section(self, section):
        for s, btn in self.header_buttons.items():
            btn.setChecked(s == section)

        while self.ribbon_options_layout.count():
            child = self.ribbon_options_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if section == "File":
            file_actions = [
                ("commandprompt", self.open_cmd, "commandprompt.png"),
                ("about", self.show_about, "about.png"),
                ("close", self.close, "close.png"),
            ]
            for action in file_actions:
                self.add_ribbon_button(*action)

        elif section == "Home":
            actions = [
                ("back", self.on_back, "back.png"),
                ("forward", self.on_forward, "forward.png"),
                ("search", self.on_search, "search.png"),
                ("cut", self.on_cut, "cut.png"),
                ("copy", self.on_copy, "copy.png"),
                ("copyaddress", self.on_copy_address, "copyaddress.png"),
                ("paste", self.on_paste, "paste.png"),
                ("move", self.on_move, "move.png"),
                ("compress", self.on_compress, "compress.png"),
                ("rename", self.on_rename, "rename.png"),
                ("favourites", self.on_add_to_favorites, "favourites.png"),
            ]
            for action in actions:
                self.add_ribbon_button(*action)

        elif section == "Settings":
            # 1. Show Ext Toggle
            ext_box = QCheckBox("Show Extensions in Name")
            ext_box.setChecked(self.proxy_model.show_extensions)
            ext_box.setStyleSheet("color: #ffd700; font-size: 10pt;")
            ext_box.toggled.connect(self.proxy_model.set_show_extensions)
            self.ribbon_options_layout.addWidget(ext_box)

            # Separator
            line = QFrame()
            line.setFrameShape(QFrame.VLine)
            line.setFrameShadow(QFrame.Sunken)
            line.setStyleSheet("background-color: #555;")
            self.ribbon_options_layout.addWidget(line)

            # 2. View Mode (List vs Grid)
            mode_group = QGroupBox("View Mode")
            mode_group.setStyleSheet("QGroupBox { border: none; color: #ffd700; }")
            mode_layout = QHBoxLayout()
            mode_layout.setContentsMargins(0,0,0,0)
            
            rb_list = QRadioButton("List")
            rb_grid = QRadioButton("Grid")
            rb_list.setStyleSheet("color: #ccc;")
            rb_grid.setStyleSheet("color: #ccc;")
            
            if self.view_stack.currentIndex() == 0: rb_list.setChecked(True)
            else: rb_grid.setChecked(True)
            
            bg = QButtonGroup(mode_group) # Keep references
            bg.addButton(rb_list)
            bg.addButton(rb_grid)
            
            rb_list.toggled.connect(lambda c: c and self.view_stack.setCurrentIndex(0))
            rb_grid.toggled.connect(lambda c: c and self.view_stack.setCurrentIndex(1))
            
            mode_layout.addWidget(rb_list)
            mode_layout.addWidget(rb_grid)
            mode_group.setLayout(mode_layout)
            self.ribbon_options_layout.addWidget(mode_group)
            
            line2 = QFrame()
            line2.setFrameShape(QFrame.VLine)
            line2.setStyleSheet("background-color: #555;")
            self.ribbon_options_layout.addWidget(line2)

            # 3. Columns (Only for List View)
            col_group = QGroupBox("Columns")
            col_group.setStyleSheet("QGroupBox { border: none; color: #ffd700; }")
            col_layout = QHBoxLayout()
            col_layout.setContentsMargins(0,0,0,0)
            
            # Columns: 1=Size, 2=Type, 3=Date Modified (Name is 0, always shown)
            for name, col_idx in [("Size", 1), ("Type", 2), ("Date", 3)]:
                cb = QCheckBox(name)
                cb.setChecked(not self.file_view.isColumnHidden(col_idx))
                cb.setStyleSheet("color: #ccc;")
                cb.toggled.connect(lambda c, idx=col_idx: self.file_view.setColumnHidden(idx, not c))
                col_layout.addWidget(cb)
            
            col_group.setLayout(col_layout)
            self.ribbon_options_layout.addWidget(col_group)
            
            line3 = QFrame()
            line3.setFrameShape(QFrame.VLine)
            line3.setStyleSheet("background-color: #555;")
            self.ribbon_options_layout.addWidget(line3)

            # 4. Font Settings
            font_group = QGroupBox("Font")
            font_group.setStyleSheet("QGroupBox { border: none; color: #ffd700; }")
            font_layout = QHBoxLayout()
            font_layout.setContentsMargins(0,0,0,0)
            
            self.font_combo = QFontComboBox()
            self.font_combo.setCurrentFont(QApplication.font())
            self.font_combo.currentFontChanged.connect(self.update_app_font)
            # Custom styling for QFontComboBox is tricky, but let's try basic colors
            self.font_combo.setStyleSheet("background: #333; color: #fff; border: 1px solid #555;")
            
            self.font_size = QSpinBox()
            self.font_size.setRange(8, 24)
            self.font_size.setValue(QApplication.font().pointSize())
            self.font_size.valueChanged.connect(self.update_app_font)
            self.font_size.setStyleSheet("background: #333; color: #fff; border: 1px solid #555;")

            font_layout.addWidget(self.font_combo)
            font_layout.addWidget(self.font_size)
            font_group.setLayout(font_layout)
            self.ribbon_options_layout.addWidget(font_group)

        self.ribbon_options_layout.addStretch() # Pushes buttons to the left
        self.header_section = section

    def update_app_font(self):
        font = self.font_combo.currentFont()
        font.setPointSize(self.font_size.value())
        QApplication.setFont(font)
        # Force update of some widgets that might not automatically pick it up immediately
        self.file_view.setFont(font)
        self.nav_tree.setFont(font)
        self.path_edit.setFont(font)


    def add_ribbon_button(self, label, handler, icon_file):
        btn = QPushButton()
        btn.setToolTip(label.replace("_", " ").title())
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "assets", "file_icons", icon_file)

        if os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
            # --- FIXED: Increased icon size to better fit the button ---
            btn.setIconSize(QSize(70, 70))
            btn.setStyleSheet(self.get_button_style())
        else:
            fallback_texts = {"back": "⬅", "forward": "➡", "move": "📂", "commandprompt": "🖥", "about": "ℹ", "close": "❌"}
            btn.setText(fallback_texts.get(label, label[0].upper()))
            btn.setStyleSheet(self.get_button_style() + "QPushButton { font-size: 18px; font-weight: bold; }")

        btn.clicked.connect(handler)
        self.ribbon_options_layout.addWidget(btn)

    def get_button_style(self):
        # Adjusted padding to better center the larger icon
        return """
            QPushButton {
                background-color: #333333; color: #ffd700; border: 1px solid #555555;
                border-radius: 6px; padding: 7px;
                min-width: 50px; min-height: 50px;
                max-width: 50px; max-height: 50px;
                margin: 2px;
            }
            QPushButton:hover { background-color: #444444; border: 1px solid #ffd700; }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ffd700, stop: 1 #b8860b);
                color: #000000;
            }
        """

    def build_navigation_tree(self):
        self.nav_model.removeRows(0, self.nav_model.rowCount())
        root = self.nav_model.invisibleRootItem()

        qa_root = QStandardItem("Quick Access")
        qa_root.setIcon(self.icons['quick_access'])
        qa_root.setEditable(False)
        qa_root.setData("__section__", Qt.UserRole+1)
        root.appendRow(qa_root)

        special_folders = {
            "Documents": self.icons['documents'], "Downloads": self.icons['downloads'],
            "Music": self.icons['music'], "Images": self.icons['pictures'],
            "Videos": self.icons['videos'], "OneDrive": self.icons['onedrive']
        }
        for label, icon in special_folders.items():
            path = resolve_special_folder(label)
            if path and os.path.exists(path):
                item = self.create_tree_item(label, path, icon)
                qa_root.appendRow(item)
                if os.path.isdir(path):
                    item.appendRow(QStandardItem(""))

        favorites_root = QStandardItem("Favorites")
        favorites_root.setIcon(self.icons['favorites'])
        favorites_root.setEditable(False)
        favorites_root.setData("__section__", Qt.UserRole+1)
        root.appendRow(favorites_root)

        for fav in self.favorites_manager.get_favorites():
            icon = self.icons['file'] if fav['type'] == 'file' else self.icons['folder']
            item = QStandardItem(fav['name'])
            item.setIcon(icon)
            item.setEditable(False)
            item.setData(fav['path'], Qt.UserRole)
            item.setData("__favorite__", Qt.UserRole+1)
            favorites_root.appendRow(item)

        drives_root = QStandardItem("This PC")
        drives_root.setIcon(self.icons['drives'])
        drives_root.setEditable(False)
        drives_root.setData("__section__", Qt.UserRole+1)
        root.appendRow(drives_root)

        for drive in self.enumerate_drives():
            d_item = self.create_tree_item(drive, drive, self.icons['drive'])
            drives_root.appendRow(d_item)
            d_item.appendRow(QStandardItem(""))

        self.nav_tree.expand(qa_root.index())
        self.nav_tree.expand(favorites_root.index())
        self.nav_tree.expand(drives_root.index())

    def create_tree_item(self, label: str, path: str, icon: QIcon = None) -> QStandardItem:
        it = QStandardItem(label)
        if icon:
            it.setIcon(icon)
        it.setEditable(False)
        it.setData(path, Qt.UserRole)
        return it

    def enumerate_drives(self):
        import string
        return [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]

    def on_path_entered(self):
        path = self.path_edit.text()
        if os.path.isdir(path):
            self.navigate_to_directory(path)
        else:
            QMessageBox.warning(self, "Invalid Path", f"The path '{path}' does not exist or is not a directory.")
            self.path_edit.setText(self.get_current_dir())

    def on_nav_clicked(self, index):
        item = self.nav_model.itemFromIndex(index)
        path = item.data(Qt.UserRole)
        item_type = item.data(Qt.UserRole+1)

        if item_type == "__favorite__":
            self.on_favorite_clicked(index)
        elif path and os.path.isdir(path):
            self.navigate_to_directory(path)

    def on_nav_double_clicked(self, index):
        item = self.nav_model.itemFromIndex(index)
        path = item.data(Qt.UserRole)
        item_type = item.data(Qt.UserRole+1)

        if item_type == "__favorite__":
            self.on_favorite_double_clicked(index)
        elif path and os.path.exists(path):
            if os.path.isdir(path):
                self.navigate_to_directory(path)
            else:
                os.startfile(path)

    def on_nav_context_menu(self, position):
        index = self.nav_tree.indexAt(position)
        if not index.isValid(): return

        item = self.nav_model.itemFromIndex(index)
        item_type = item.data(Qt.UserRole+1)

        if item_type == "__favorite__":
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu { background-color: #2a2a2a; color: #ccc; border: 1px solid #555; }
                QMenu::item { padding: 8px 20px; }
                QMenu::item:selected { background-color: #ffd700; color: #000; }
            """)
            remove_action = menu.addAction("🗑 Remove from Favorites")
            action = menu.exec_(self.nav_tree.mapToGlobal(position))
            if action == remove_action:
                path = item.data(Qt.UserRole)
                self.remove_favorite(path)
                self.status_bar.showMessage("Removed from favorites", 2000)

    def on_nav_expanded(self, index):
        item = self.nav_model.itemFromIndex(index)
        path = item.data(Qt.UserRole)
        if not path or not os.path.isdir(path): return

        if item.hasChildren() and item.child(0).data(Qt.UserRole) is None and item.child(0).text() == "":
            item.removeRows(0, item.rowCount())
            self.add_children_folders(item, path)

    def add_children_folders(self, parent_item: QStandardItem, directory_path: str, limit: int = 500):
        try:
            entries = sorted([e for e in os.scandir(directory_path) if e.is_dir(follow_symlinks=False)], key=lambda e: e.name.lower())
            for e in entries[:limit]:
                child = self.create_tree_item(e.name, e.path, self.icons['folder'])
                parent_item.appendRow(child)
                try:
                    with os.scandir(e.path) as it:
                        if any(sub.is_dir(follow_symlinks=False) for sub in it):
                            child.appendRow(QStandardItem(""))
                except PermissionError: pass
        except PermissionError: pass

    def open_file(self, index):
        # Allow opening from both list and grid views
        # Map proxy index back to source index
        source_index = self.proxy_model.mapToSource(index)
        path = self.model.filePath(source_index)
        
        if os.path.isdir(path):
            self.navigate_to_directory(path)
        elif os.path.isfile(path):
            try:
                os.startfile(path)
            except Exception as e:
                QMessageBox.warning(self, "Open File Error", f"Could not open the file:\n{e}")

    def open_cmd(self):
        current_dir = self.get_current_dir()
        os.chdir(current_dir)
        os.system('start cmd')

    def show_about(self):
        QMessageBox.information(self, "About", "BrontoSphere File Manager\nVersion 1.0\nPowered by PyQt5")

    def get_selected_paths(self):
        # Determine active view
        if self.view_stack.currentIndex() == 0:
            view = self.file_view
        else:
            view = self.file_grid_view
            
        indexes = view.selectionModel().selectedIndexes()
        if not indexes: return []
        
        # Filter for column 0 (names) to avoid duplicates in list view
        # Grid view is only column 0 effectively, but let's be safe
        paths = []
        for idx in indexes:
            if idx.column() == 0:
                source_idx = self.proxy_model.mapToSource(idx)
                paths.append(self.model.filePath(source_idx))
        return list(set(paths)) # Remove duplicates if any

    def get_current_dir(self):
        # Use proxy model's mapping
        return self.model.filePath(self.proxy_model.mapToSource(self.file_view.rootIndex()))

    def refresh_current_dir(self):
        self.navigate_to_directory(self.get_current_dir(), record_history=False)

    def navigate_to_directory(self, path, record_history=True):
        if not os.path.exists(path): return
        
        # We need to map the source model index for 'path' to the proxy model index
        src_index = self.model.index(path)
        proxy_index = self.proxy_model.mapFromSource(src_index)
        
        self.file_view.setRootIndex(proxy_index)
        self.file_grid_view.setRootIndex(proxy_index)
        
        self.path_edit.setText(path)
        
        if record_history:
            self.navigation_history.add_to_history(path)
            
        # Update window title
        self.setWindowTitle(f"{os.path.basename(path)} - BrontoASPHERE File Manager")

    def on_back(self):
        path = self.navigation_history.go_back()
        if path: self.navigate_to_directory(path, record_history=False)

    def on_forward(self):
        path = self.navigation_history.go_forward()
        if path: self.navigate_to_directory(path, record_history=False)

    def on_search(self):
        search_dialog = SearchDialog(self, self.file_searcher, self.get_current_dir())
        search_dialog.exec_()

    def on_copy(self):
        self.clipboard_paths = self.get_selected_paths()
        if not self.clipboard_paths: return
        self.clipboard_mode = 'copy'
        self.status_bar.showMessage(f"Copied {len(self.clipboard_paths)} item(s)", 3000)

    def on_cut(self):
        self.clipboard_paths = self.get_selected_paths()
        if not self.clipboard_paths: return
        self.clipboard_mode = 'cut'
        self.status_bar.showMessage(f"Cut {len(self.clipboard_paths)} item(s)", 3000)

    def on_copy_address(self):
        from PyQt5.QtGui import QGuiApplication
        paths = self.get_selected_paths()
        if not paths:
            paths = [self.get_current_dir()]
        QGuiApplication.clipboard().setText("\n".join(paths))
        self.status_bar.showMessage("Path(s) copied to clipboard", 3000)

    def on_paste(self):
        if not self.clipboard_paths or self.clipboard_mode not in ('copy', 'cut'):
            QMessageBox.information(self, "Paste", "Clipboard is empty.")
            return
        dest_dir = self.get_current_dir()
        if not os.path.isdir(dest_dir):
            QMessageBox.warning(self, "Paste Error", "Destination is not a folder.")
            return

        errors = []
        for src in self.clipboard_paths:
            try:
                base = os.path.basename(src.rstrip("/\\"))
                dest = os.path.join(dest_dir, base)
                if src == dest or dest.startswith(src + os.path.sep):
                    errors.append(f"Cannot {self.clipboard_mode} '{base}' into a subfolder of itself.")
                    continue
                if self.clipboard_mode == 'copy':
                    self.ps_copy(src, dest)
                else:
                    self.ps_move(src, dest)
            except Exception as e:
                errors.append(f"Failed to {self.clipboard_mode} '{src}': {e}")

        if errors:
            QMessageBox.warning(self, "Paste Error", "Some items failed to paste:\n" + "\n".join(errors))
        if self.clipboard_mode == 'cut':
            self.clipboard_paths = []
            self.clipboard_mode = None
        self.refresh_current_dir()

    def on_move(self):
        paths = self.get_selected_paths()
        if not paths:
            QMessageBox.information(self, "Move", "No items selected.")
            return
        dest_dir = QFileDialog.getExistingDirectory(self, "Select Destination Folder", self.get_current_dir())
        if not dest_dir: return

        errors = []
        for src in paths:
            try:
                self.ps_move(src, os.path.join(dest_dir, os.path.basename(src.rstrip("/\\"))))
            except Exception as e:
                errors.append(f"Failed to move '{src}': {e}")
        if errors:
            QMessageBox.warning(self, "Move Error", "Some items failed to move:\n" + "\n".join(errors))
        self.refresh_current_dir()

    def on_compress(self):
        paths = self.get_selected_paths()
        if not paths:
            QMessageBox.information(self, "Compress", "Select at least one file or folder.")
            return
        dest_dir = self.get_current_dir()
        base_name, ok = QInputDialog.getText(self, "Archive Name", "Enter archive name (without .zip):", text="Archive")
        if not ok or not base_name: return
        archive_path = os.path.join(dest_dir, f"{base_name}.zip")

        import tempfile, shutil
        staging_dir = tempfile.mkdtemp(prefix="bb_zip_")
        try:
            for p in paths:
                self.ps_copy(p, os.path.join(staging_dir, os.path.basename(p.rstrip("/\\"))))
            self.ps_compress(staging_dir, archive_path)
            QMessageBox.information(self, "Compress", f"Successfully created {archive_path}")
        except Exception as e:
            QMessageBox.critical(self, "Compress Error", f"Failed to create archive: {e}")
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)
        self.refresh_current_dir()

    def on_rename(self):
        paths = self.get_selected_paths()
        if len(paths) != 1:
            QMessageBox.information(self, "Rename", "Select exactly one item to rename.")
            return
        src = paths[0]
        new_name, ok = QInputDialog.getText(self, "Rename", "Enter new name:", text=os.path.basename(src))
        if not ok or not new_name: return

        try:
            self.ps_rename(src, os.path.join(os.path.dirname(src), new_name))
        except Exception as e:
            QMessageBox.critical(self, "Rename Error", f"Failed to rename: {e}")
        self.refresh_current_dir()

    def on_add_to_favorites(self):
        paths = self.get_selected_paths()
        if not paths:
            QMessageBox.information(self, "Add to Favorites", "No items selected.")
            return
        added_count = sum(1 for path in paths if self.favorites_manager.add_favorite(path))
        if added_count > 0:
            self.status_bar.showMessage(f"Added {added_count} item(s) to favorites", 3000)
            self.build_navigation_tree()
        else:
            QMessageBox.information(self, "Add to Favorites", "Selected items are already in favorites.")

    def on_favorite_clicked(self, index):
        path = self.nav_model.itemFromIndex(index).data(Qt.UserRole)
        if path and os.path.exists(path):
            parent_dir = os.path.dirname(path) if os.path.isfile(path) else path
            self.navigate_to_directory(parent_dir)

    def on_favorite_double_clicked(self, index):
        path = self.nav_model.itemFromIndex(index).data(Qt.UserRole)
        if path and os.path.exists(path):
            if os.path.isfile(path):
                # --- FIXED: Directly open the file path ---
                try:
                    os.startfile(path)
                except Exception as e:
                    QMessageBox.warning(self, "Open Error", f"Could not open file:\n{e}")
            else:
                self.navigate_to_directory(path)

    def remove_favorite(self, path):
        if self.favorites_manager.remove_favorite(path):
            self.build_navigation_tree()



    def ps_copy(self, src, dest):
        import subprocess
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Copy-Item -LiteralPath '{src}' -Destination '{dest}' -Recurse -Force"], check=True, shell=True)

    def ps_move(self, src, dest):
        import subprocess
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Move-Item -LiteralPath '{src}' -Destination '{dest}' -Force"], check=True, shell=True)

    def ps_rename(self, src, dest):
        import subprocess
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Rename-Item -LiteralPath '{src}' -NewName '{os.path.basename(dest)}' -Force"], check=True, shell=True)

    def ps_compress(self, source_dir, dest_zip):
        import subprocess
        os.makedirs(os.path.dirname(dest_zip), exist_ok=True)
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Compress-Archive -Path '{source_dir}\\*' -DestinationPath '{dest_zip}' -Force"], check=True, shell=True)

    def on_file_context_menu(self, position):
        # Determine sender view
        view = self.sender()
        index = view.indexAt(position)
        if not index.isValid(): return

        # Map to source model to get file path
        source_index = self.proxy_model.mapToSource(index)
        if not source_index.isValid(): return
        
        file_path = self.model.filePath(source_index)
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #2a2a2a; color: #ccc; border: 1px solid #555; }
            QMenu::item { padding: 5px 20px; }
            QMenu::item:selected { background-color: #ffd700; color: #000; }
        """)
        
        open_action = menu.addAction("Open")
        menu.addSeparator()
        properties_action = menu.addAction("Properties")

        action = menu.exec_(view.mapToGlobal(position))
        
        if action == open_action:
            self.open_file(index)
        elif action == properties_action:
            self.show_file_properties(file_path)

    def show_file_properties(self, path):
        dialog = FilePropertiesDialog(self, path)
        dialog.exec_()

class SearchDialog(QDialog):
    """Search dialog for finding files"""

    def __init__(self, parent=None, file_searcher=None, search_directory=""):
        super().__init__(parent)
        self.file_searcher = file_searcher or FileSearcher()
        self.search_directory = search_directory
        self.search_results = []

        self.setWindowTitle("🔍 Search Files")
        self.setGeometry(200, 200, 600, 500)
        self.setup_ui()
        self.apply_dark_theme()

    def setup_ui(self):
        layout = QVBoxLayout()

        options_group = QGroupBox("Search Options")
        options_layout = QVBoxLayout()

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Search Type:"))
        self.search_type = QComboBox()
        self.search_type.addItems(["Windows Style", "File Name", "Content", "Size", "Date"])
        self.search_type.currentTextChanged.connect(self.on_search_type_changed)
        type_layout.addWidget(self.search_type)
        options_layout.addLayout(type_layout)

        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("File Name:"))
        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText("Enter filename to search...")
        text_layout.addWidget(self.search_text)
        options_layout.addLayout(text_layout)

        type_input_layout = QHBoxLayout()
        type_input_layout.addWidget(QLabel("File Type:"))
        self.file_type_input = QLineEdit()
        self.file_type_input.setPlaceholderText("pdf, doc, txt (optional)")
        type_input_layout.addWidget(self.file_type_input)
        options_layout.addLayout(type_input_layout)

        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Directory:"))
        self.dir_combo = QComboBox()
        self.dir_combo.setEditable(True)
        self.dir_combo.setMinimumWidth(300)
        self.populate_directory_dropdown()
        self.dir_combo.setCurrentText(self.search_directory)
        dir_layout.addWidget(self.dir_combo)
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(self.browse_btn)
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setToolTip("Refresh directory list")
        self.refresh_btn.clicked.connect(self.populate_directory_dropdown)
        dir_layout.addWidget(self.refresh_btn)
        options_layout.addLayout(dir_layout)

        self.recursive_check = QCheckBox("Search subdirectories")
        self.recursive_check.setChecked(True)
        options_layout.addWidget(self.recursive_check)

        self.advanced_group = QGroupBox("Advanced Options")
        self.advanced_layout = QVBoxLayout()

        ext_layout = QHBoxLayout()
        ext_layout.addWidget(QLabel("File Extensions:"))
        self.extensions_input = QLineEdit()
        self.extensions_input.setPlaceholderText("txt,doc,pdf (comma separated)")
        ext_layout.addWidget(self.extensions_input)
        self.advanced_layout.addLayout(ext_layout)

        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Size Range (MB):"))
        self.min_size = QLineEdit()
        self.min_size.setPlaceholderText("Min")
        size_layout.addWidget(self.min_size)
        size_layout.addWidget(QLabel("to"))
        self.max_size = QLineEdit()
        self.max_size.setPlaceholderText("Max")
        size_layout.addWidget(self.max_size)
        self.advanced_layout.addLayout(size_layout)

        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Date Range:"))
        self.start_date = QLineEdit()
        self.start_date.setPlaceholderText("YYYY-MM-DD")
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel("to"))
        self.end_date = QLineEdit()
        self.end_date.setPlaceholderText("YYYY-MM-DD")
        date_layout.addWidget(self.end_date)
        self.advanced_layout.addLayout(date_layout)

        self.advanced_group.setLayout(self.advanced_layout)
        self.advanced_group.setVisible(False)
        options_layout.addWidget(self.advanced_group)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        self.search_btn = QPushButton("🔍 Search")
        self.search_btn.clicked.connect(self.perform_search)
        layout.addWidget(self.search_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout()

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)

        actions_layout = QHBoxLayout()
        self.open_btn = QPushButton("Open Selected")
        self.open_btn.clicked.connect(self.open_selected)
        self.open_btn.setEnabled(False)
        actions_layout.addWidget(self.open_btn)

        self.navigate_btn = QPushButton("Navigate to Selected")
        self.navigate_btn.clicked.connect(self.navigate_to_selected)
        self.navigate_btn.setEnabled(False)
        actions_layout.addWidget(self.navigate_btn)

        self.clear_btn = QPushButton("Clear Results")
        self.clear_btn.clicked.connect(self.clear_results)
        actions_layout.addWidget(self.clear_btn)

        results_layout.addLayout(actions_layout)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        self.setLayout(layout)

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QDialog { background-color: #2a2a2a; color: #ccc; }
            QGroupBox {
                background-color: #333333; border: 1px solid #555555;
                border-radius: 5px; margin-top: 10px;
                padding-top: 10px; color: #ffd700; font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px;
            }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #3a3a3a; color: #ccc;
                border: 1px solid #555555; border-radius: 3px; padding: 5px;
            }
            QPushButton {
                background-color: #333333; color: #ffd700;
                border: 1px solid #555555; border-radius: 4px; padding: 8px 15px;
            }
            QPushButton:hover { background-color: #444444; border: 1px solid #ffd700; }
            QPushButton:disabled {
                background-color: #222222; color: #666666; border: 1px solid #444444;
            }
            QProgressBar {
                border: 1px solid #555555; border-radius: 3px;
                text-align: center; background-color: #3a3a3a;
            }
            QProgressBar::chunk { background-color: #ffd700; border-radius: 2px; }
        """)

    def on_search_type_changed(self, search_type):
        is_windows_style = search_type == "Windows Style"
        self.file_type_input.setVisible(is_windows_style)
        self.advanced_group.setVisible(search_type in ["Content", "Size", "Date"])

        if search_type == "Windows Style":
            self.search_text.setPlaceholderText("Enter filename to search...")
            self.file_type_input.setPlaceholderText("pdf, doc, txt (optional)")
        elif search_type == "File Name":
            self.search_text.setPlaceholderText("Enter file pattern (e.g., *.txt)")
        elif search_type == "Content":
            self.search_text.setPlaceholderText("Enter text to search for...")
        else:
            self.search_text.setPlaceholderText("Enter search term...")

    def populate_directory_dropdown(self):
        self.dir_combo.clear()
        common_dirs = []
        home_dir = os.path.expanduser("~")
        if os.path.exists(home_dir):
            common_dirs.append(home_dir)

        if os.name == 'nt':
            special_folders = [
                os.path.join(home_dir, "Documents"), os.path.join(home_dir, "Downloads"),
                os.path.join(home_dir, "Desktop"), os.path.join(home_dir, "Pictures"),
                os.path.join(home_dir, "Music"), os.path.join(home_dir, "Videos"),
                os.path.join(home_dir, "OneDrive"),
            ]
            for folder in special_folders:
                if os.path.exists(folder):
                    common_dirs.append(folder)
            import string
            for drive in string.ascii_uppercase:
                drive_path = f"{drive}:\\"
                if os.path.exists(drive_path):
                    common_dirs.append(drive_path)

        if self.search_directory and self.search_directory not in common_dirs:
            common_dirs.insert(0, self.search_directory)

        for directory in common_dirs:
            self.dir_combo.addItem(directory)

    def browse_directory(self):
        current_dir = self.dir_combo.currentText() or self.search_directory
        directory = QFileDialog.getExistingDirectory(self, "Select Search Directory", current_dir)
        if directory:
            if self.dir_combo.findText(directory) == -1:
                self.dir_combo.addItem(directory)
            self.dir_combo.setCurrentText(directory)

    def perform_search(self):
        search_directory = self.dir_combo.currentText()
        if not search_directory or not os.path.exists(search_directory):
            QMessageBox.warning(self, "Search Error", "Please select a valid directory.")
            return

        search_type = self.search_type.currentText()
        search_text = self.search_text.text().strip()

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.search_btn.setEnabled(False)
        self.results_text.clear()
        QApplication.processEvents() # Update UI

        try:
            results = []
            if search_type == "File Name":
                if not search_text:
                    QMessageBox.warning(self, "Search Error", "Please enter a search term.")
                    return
                results = self.file_searcher.search_files(search_directory, search_text, self.recursive_check.isChecked())
                self.display_results(results)
            # Add other search types here...
        except Exception as e:
            QMessageBox.critical(self, "Search Error", f"An error occurred: {str(e)}")
        finally:
            self.progress_bar.setVisible(False)
            self.search_btn.setEnabled(True)

    def display_results(self, results):
        self.search_results = results
        if not results:
            self.results_text.setText("No results found.")
            self.open_btn.setEnabled(False)
            self.navigate_btn.setEnabled(False)
            return

        result_text = f"Found {len(results)} result(s):\n\n" + "\n".join([f"{i}. {res}" for i, res in enumerate(results, 1)])
        self.results_text.setText(result_text)
        self.open_btn.setEnabled(True)
        self.navigate_btn.setEnabled(True)

    def open_selected(self):
        if not self.search_results: return
        # A real implementation would parse the selected line. This just opens the first result.
        try:
            os.startfile(self.search_results[0])
        except Exception as e:
            QMessageBox.warning(self, "Open Error", f"Could not open file: {e}")

    def navigate_to_selected(self):
        if not self.search_results: return
        # A real implementation would parse the selected line. This navigates to the first result.
        file_path = self.search_results[0]
        if os.path.exists(file_path) and hasattr(self.parent(), 'navigate_to_directory'):
            self.parent().navigate_to_directory(os.path.dirname(file_path))
            self.accept()

    def clear_results(self):
        self.results_text.clear()
        self.search_results = []
        self.open_btn.setEnabled(False)
        self.navigate_btn.setEnabled(False)




class FilePropertiesDialog(QDialog):
    def __init__(self, parent, path):
        super().__init__(parent)
        self.path = path
        self.setWindowTitle(f"{os.path.basename(path)} Properties")
        self.setFixedSize(400, 500)
        
        layout = QVBoxLayout()
        
        # Tabs
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #444; }
            QTabBar::tab { background: #333; color: #ccc; padding: 8px; }
            QTabBar::tab:selected { background: #444; color: #ffd700; }
        """)
        
        # General Tab
        general_tab = QWidget()
        gen_layout = QFormLayout()
        gen_layout.setSpacing(10)
        
        info = QFileInfo(path)
        
        # Icon & Name
        name_label = QLabel(os.path.basename(path))
        name_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #ffd700;")
        gen_layout.addRow(QLabel("Name:"), name_label)
        
        gen_layout.addRow(QLabel("Type:"), QLabel("File folder" if os.path.isdir(path) else "File"))
        gen_layout.addRow(QLabel("Location:"), QLabel(os.path.dirname(path)))
        
        size = info.size()
        size_str = self.format_size(size)
        gen_layout.addRow(QLabel("Size:"), QLabel(size_str))
        
        created = info.created().toString("yyyy-MM-dd HH:mm:ss")
        modified = info.lastModified().toString("yyyy-MM-dd HH:mm:ss")
        accessed = info.lastRead().toString("yyyy-MM-dd HH:mm:ss")
        
        gen_layout.addRow(QLabel("Created:"), QLabel(created))
        gen_layout.addRow(QLabel("Modified:"), QLabel(modified))
        gen_layout.addRow(QLabel("Accessed:"), QLabel(accessed))
        
        # Attributes
        attrs = []
        if info.isReadable(): attrs.append("Readable")
        if info.isWritable(): attrs.append("Writable")
        if info.isHidden(): attrs.append("Hidden")
        gen_layout.addRow(QLabel("Attributes:"), QLabel(", ".join(attrs)))

        general_tab.setLayout(gen_layout)
        tabs.addTab(general_tab, "General")
        
        # Details Tab (Placeholder)
        details_tab = QWidget()
        det_layout = QVBoxLayout()
        det_layout.addWidget(QLabel("Additional details..."))
        details_tab.setLayout(det_layout)
        # tabs.addTab(details_tab, "Details") 
        
        layout.addWidget(tabs)
        
        btn_box = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        btn_box.addStretch()
        btn_box.addWidget(ok_btn)
        
        layout.addLayout(btn_box)
        self.setLayout(layout)
        self.apply_dark_theme()

    def format_size(self, size_bytes):
        if size_bytes < 1024: return f"{size_bytes} bytes"
        elif size_bytes < 1024**2: return f"{size_bytes/1024:.2f} KB"
        elif size_bytes < 1024**3: return f"{size_bytes/1024**2:.2f} MB"
        else: return f"{size_bytes/1024**3:.2f} GB"

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QDialog { background-color: #2a2a2a; color: #ccc; }
            QLabel { color: #ccc; }
            QPushButton {
                background-color: #333; color: #ffd700; border: 1px solid #555;
                border-radius: 4px; padding: 6px 12px;
            }
            QPushButton:hover { background-color: #444; border-color: #ffd700; }
        """)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
