import os
import json
import pickle
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter,
    QTreeView, QTableView, QPushButton,
    QMessageBox, QInputDialog, QStatusBar, QFileSystemModel, QFrame, QHeaderView, QFileDialog,
    QMenu, QDialog, QLineEdit, QComboBox, QCheckBox, QTextEdit, QProgressBar, QGroupBox
)
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QSize
from PyQt5.QtGui import QIcon, QPalette, QColor, QLinearGradient, QStandardItemModel, QStandardItem

# Import core modules
from core import NavigationHistory, FavoritesManager, FileSearcher

# ---- add imports for ctypes known folders ----
import sys
import ctypes
from ctypes import wintypes


class DirsOnlyProxyModel(QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row, source_parent):
        index = self.sourceModel().index(source_row, 0, source_parent)
        return self.sourceModel().isDir(index)

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
        self.setWindowTitle("BrontoBase File Manager")
        self.setGeometry(100, 100, 1200, 750)
        
        # Initialize core modules first
        self.navigation_history = NavigationHistory()
        self.favorites_manager = FavoritesManager()
        self.file_searcher = FileSearcher()
        
        # Apply dark theme
        self.apply_dark_theme()

        # === Header Section (Row 1) ===
        header_row = QWidget()
        header_row.setStyleSheet("background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #2c2c2c, stop: 1 #4a4a4a);")
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
                    background-color: #333333;
                    color: #ffd700;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 5px 15px;
                }
                QPushButton:hover {
                    background-color: #444444;
                    border: 1px solid #ffd700;
                }
                QPushButton:checked {
                    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ffd700, stop: 1 #b8860b);
                    color: #000000;
                    font-weight: bold;
                }
            """)
            btn.clicked.connect(lambda checked, s=section: self.switch_header_section(s))
            header_layout.addWidget(btn)
            self.header_buttons[section] = btn
        header_row.setLayout(header_layout)

        # === Ribbon Options Row (Row 2) ===
        self.ribbon_options_row = QWidget()
        self.ribbon_options_row.setStyleSheet("background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #3c3c3c, stop: 1 #5a5a5a);")
        self.ribbon_options_layout = QHBoxLayout()
        self.ribbon_options_layout.setContentsMargins(10, 5, 10, 5)
        self.ribbon_options_layout.setSpacing(15)
        self.ribbon_options_row.setFixedHeight(60)
        self.ribbon_options_row.setLayout(self.ribbon_options_layout)

        # Set initial section
        self.header_section = "File"
        self.switch_header_section("File")

        # === File System Model ===
        self.model = QFileSystemModel()
        self.model.setRootPath('')

        # === Combined Navigation Tree (Quick Access + Drives) ===
        self.nav_model = QStandardItemModel()
        self.nav_model.setHorizontalHeaderLabels(["Navigation"]) 
        self.nav_tree = QTreeView()
        self.nav_tree.setModel(self.nav_model)
        self.nav_tree.setHeaderHidden(False)
        self.nav_tree.setStyleSheet("""
            QTreeView { 
                background:#2a2a2a; 
                color:#ccc; 
                border:none; 
                alternate-background-color:#333333;
                outline: 0;
            }
            QTreeView::item { 
                padding:5px; 
                border-bottom:1px solid #333; 
                border: none;
            }
            QTreeView::item:selected { 
                background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #ffd700, stop:1 #b8860b); 
                color:#000; 
                font-weight:bold; 
                border: none;
            }
            QTreeView::item:hover { 
                background-color:#444; 
                border: none;
            }
            QTreeView::branch:has-siblings:!adjoins-item {
                border-image: url(none.png);
            }
            QTreeView::branch:has-siblings:adjoins-item {
                border-image: url(none.png);
            }
            QTreeView::branch:!has-children:!has-siblings:adjoins-item {
                border-image: url(none.png);
            }
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {
                border-image: none;
                image: url(none.png);
            }
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {
                border-image: none;
                image: url(none.png);
            }
        """)
        
        # Style the tree view header specifically
        self.nav_tree.header().setStyleSheet("""
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3c3c3c, stop:1 #2a2a2a);
                color: #ffd700;
                padding: 5px;
                border: 1px solid #555;
                font-weight: bold;
                border-bottom: 2px solid #555;
            }
            QHeaderView {
                background: #2a2a2a;
                border: none;
            }
        """)
        
        self.build_navigation_tree()
        self.nav_tree.expanded.connect(self.on_nav_expanded)
        self.nav_tree.clicked.connect(self.on_nav_clicked)
        self.nav_tree.doubleClicked.connect(self.on_nav_double_clicked)
        self.nav_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.nav_tree.customContextMenuRequested.connect(self.on_nav_context_menu)

        # File view
        self.file_view = QTableView()
        self.file_view.setModel(self.model)
        self.file_view.setRootIndex(self.model.index(self.model.rootPath()))
        self.file_view.setSelectionBehavior(QTableView.SelectRows)
        self.file_view.setAlternatingRowColors(True)
        
        # Style the file view header
        self.file_view.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3c3c3c, stop:1 #2a2a2a);
                color: #ffd700;
                padding: 5px;
                border: 1px solid #555;
                font-weight: bold;
                border-bottom: 2px solid #555;
            }
            QHeaderView {
                background: #2a2a2a;
                border: none;
            }
        """)
        
        self.file_view.verticalHeader().setStyleSheet("""
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3c3c3c, stop:1 #2a2a2a);
                color: #ffd700;
                padding: 5px;
                border: 1px solid #555;
                font-weight: bold;
                border-right: 2px solid #555;
            }
            QHeaderView {
                background: #2a2a2a;
                border: none;
            }
        """)
        
        self.file_view.setStyleSheet("""
            QTableView { 
                background:#2a2a2a; 
                color:#ccc; 
                alternate-background-color:#333333; 
                gridline-color:#444444; 
                border:none;
                outline: 0;
            }
            QTableView::item { 
                padding:5px; 
                border-bottom:1px solid #333; 
                border: none;
            }
            QTableView::item:selected { 
                background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #ffd700, stop:1 #b8860b); 
                color:#000; 
                font-weight:bold; 
                border: none;
            }
            QTableView::item:hover { 
                background-color:#444; 
                border: none;
            }
        """)
        
        # Ensure important columns are visible and sized
        header = self.file_view.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.Interactive)
        # Columns: 0 Name, 1 Size, 2 Type, 3 Date Modified
        self.file_view.setColumnHidden(0, False)
        self.file_view.setColumnHidden(1, False)
        self.file_view.setColumnHidden(2, False)
        self.file_view.setColumnHidden(3, False)
        self.file_view.setColumnWidth(0, 320)
        self.file_view.setColumnWidth(1, 120)
        self.file_view.setColumnWidth(2, 140)
        self.file_view.setColumnWidth(3, 170)
        
        self.file_view.setColumnWidth(0, 280)
        self.file_view.doubleClicked.connect(self.open_file)
        self.file_view.setSortingEnabled(True)
        self.file_view.sortByColumn(3, Qt.DescendingOrder)

        # Splitter
        tree_and_files_splitter = QSplitter(Qt.Horizontal)
        tree_and_files_splitter.setStyleSheet("""
            QSplitter::handle { 
                background-color:#555; 
                width: 3px;
            }
            QSplitter::handle:hover {
                background-color:#666;
            }
            QSplitter {
                background: #2a2a2a;
                border: none;
            }
        """)
        tree_and_files_splitter.addWidget(self.nav_tree)
        tree_and_files_splitter.addWidget(self.file_view)
        tree_and_files_splitter.setSizes([300, 900])

        # Layout central
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        layout.addWidget(header_row)
        layout.addWidget(self.ribbon_options_row)
        layout.addWidget(tree_and_files_splitter)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # === Status Bar ===
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #3c3c3c, stop: 1 #5a5a5a);
                color: #ffd700;
                border-top: 1px solid #555555;
            }
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Clipboard state for Cut/Copy/Paste
        self.clipboard_paths = []
        self.clipboard_mode = None  # 'cut' | 'copy'

    def apply_dark_theme(self):
        # Set application palette for dark theme
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(42, 42, 42))
        palette.setColor(QPalette.WindowText, QColor(204, 204, 204))
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.AlternateBase, QColor(42, 42, 42))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 215, 0))
        palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.Text, QColor(204, 204, 204))
        palette.setColor(QPalette.Button, QColor(42, 42, 42))
        palette.setColor(QPalette.ButtonText, QColor(204, 204, 204))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(255, 215, 0))
        palette.setColor(QPalette.Highlight, QColor(255, 215, 0))
        palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        
        # Additional palette settings to remove white elements
        palette.setColor(QPalette.Light, QColor(60, 60, 60))
        palette.setColor(QPalette.Midlight, QColor(50, 50, 50))
        palette.setColor(QPalette.Dark, QColor(30, 30, 30))
        palette.setColor(QPalette.Mid, QColor(45, 45, 45))
        palette.setColor(QPalette.Shadow, QColor(20, 20, 20))
        
        # Fix for header and other white areas
        palette.setColor(QPalette.Button, QColor(60, 60, 60))
        palette.setColor(QPalette.Window, QColor(42, 42, 42))
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        
        self.setPalette(palette)

    # ---------------------------
    # Ribbon Section Switch
    # ---------------------------
    def switch_header_section(self, section):
        for s, btn in self.header_buttons.items():
            btn.setChecked(s == section)

        # Clear old buttons
        while self.ribbon_options_layout.count():
            child = self.ribbon_options_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if section == "File":
            for text, cb in [("🖥 Command Prompt", self.open_cmd), ("ℹ About", self.show_about), ("❌ Close", self.close)]:
                btn = QPushButton(text); btn.setStyleSheet(self.get_button_style()); btn.clicked.connect(cb)
                self.ribbon_options_layout.addWidget(btn)

        elif section == "Home":
            actions = [
                ("⬅ Back", self.on_back),
                ("➡ Forward", self.on_forward),
                ("🔍 Search", self.on_search),
                ("✂ Cut", self.on_cut),
                ("📋 Copy", self.on_copy),
                ("🔗 Copy Address", self.on_copy_address),
                ("📥 Paste", self.on_paste),
                ("📂 Move", self.on_move),
                ("🗜 Compress", self.on_compress),
                ("✏ Rename", self.on_rename),
                ("⭐ Add to Favorites", self.on_add_to_favorites),
            ]
            for label, handler in actions:
                btn = QPushButton(label)
                btn.setStyleSheet(self.get_button_style())
                btn.clicked.connect(handler)
                self.ribbon_options_layout.addWidget(btn)

        elif section == "Settings":
            lbl = QLabel("⚙ Settings panel (coming soon)"); lbl.setStyleSheet("color:#ffd700;"); self.ribbon_options_layout.addWidget(lbl)
        self.header_section = section

    def get_button_style(self):
        return """
            QPushButton {
                background-color: #333333;
                color: #ffd700;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #444444;
                border: 1px solid #ffd700;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ffd700, stop: 1 #b8860b);
                color: #000000;
            }
        """

    # -------- Navigation tree construction --------
    def build_navigation_tree(self):
        self.nav_model.removeRows(0, self.nav_model.rowCount())
        root = self.nav_model.invisibleRootItem()
        
        # Quick Access
        qa_root = QStandardItem("📁 Quick Access"); qa_root.setEditable(False); qa_root.setData("__section__", Qt.UserRole+1)
        root.appendRow(qa_root)
        for label in ["Documents", "Downloads", "Music", "Images", "Videos", "OneDrive"]:
            path = resolve_special_folder(label)
            item = self.create_tree_item(label, path)
            qa_root.appendRow(item)
            # lazy child marker
            if os.path.isdir(path):
                item.appendRow(QStandardItem(""))
        
        # Favorites
        favorites_root = QStandardItem("⭐ Favorites"); favorites_root.setEditable(False); favorites_root.setData("__section__", Qt.UserRole+1)
        root.appendRow(favorites_root)
        
        # Load and display favorites
        favorites = self.favorites_manager.get_favorites()
        for fav in favorites:
            # Create favorite item with special icon
            icon = "📄" if fav['type'] == 'file' else "📁"
            item = QStandardItem(f"{icon} {fav['name']}")
            item.setEditable(False)
            item.setData(fav['path'], Qt.UserRole)
            item.setData("__favorite__", Qt.UserRole+1)  # Mark as favorite
            favorites_root.appendRow(item)
        
        # Drives
        drives_root = QStandardItem("💽 Drives"); drives_root.setEditable(False); drives_root.setData("__section__", Qt.UserRole+1)
        root.appendRow(drives_root)
        for drive in self.enumerate_drives():
            d_item = self.create_tree_item(drive, drive)
            drives_root.appendRow(d_item)
            d_item.appendRow(QStandardItem(""))  # lazy marker
        
        self.nav_tree.expand(qa_root.index())
        self.nav_tree.expand(favorites_root.index())
        self.nav_tree.expand(drives_root.index())

    def create_tree_item(self, label: str, path: str) -> QStandardItem:
        it = QStandardItem(label)
        it.setEditable(False)
        it.setData(path, Qt.UserRole)  # store absolute path
        return it

    def enumerate_drives(self):
        import string
        return [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]

    def on_nav_clicked(self, index):
        item = self.nav_model.itemFromIndex(index)
        path = item.data(Qt.UserRole)
        item_type = item.data(Qt.UserRole+1)
        
        if item_type == "__favorite__":
            # Handle favorite item click - navigate to parent directory
            self.on_favorite_clicked(index)
        elif path and os.path.exists(path):
            self.navigate_to_directory(path)

    def on_nav_double_clicked(self, index):
        item = self.nav_model.itemFromIndex(index)
        path = item.data(Qt.UserRole)
        item_type = item.data(Qt.UserRole+1)
        
        if item_type == "__favorite__":
            # Handle favorite item double-click - open the file/folder
            self.on_favorite_double_clicked(index)
        elif path and os.path.exists(path):
            # For regular items, navigate to them
            self.navigate_to_directory(path)

    def on_nav_context_menu(self, position):
        """Handle right-click context menu for navigation tree"""
        index = self.nav_tree.indexAt(position)
        if not index.isValid():
            return
            
        item = self.nav_model.itemFromIndex(index)
        item_type = item.data(Qt.UserRole+1)
        
        if item_type == "__favorite__":
            # Context menu for favorite items
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #2a2a2a;
                    color: #ccc;
                    border: 1px solid #555;
                }
                QMenu::item {
                    padding: 8px 20px;
                }
                QMenu::item:selected {
                    background-color: #ffd700;
                    color: #000;
                }
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
        if not path or not os.path.isdir(path):
            return
        # If first child is a dummy, clear and populate real children
        if item.hasChildren() and item.child(0).data(Qt.UserRole) is None and item.child(0).text() == "":
            item.removeRows(0, item.rowCount())
            self.add_children_folders(item, path)

    def add_children_folders(self, parent_item: QStandardItem, directory_path: str, limit: int = 500):
        try:
            entries = [e for e in os.scandir(directory_path) if e.is_dir(follow_symlinks=False)]
            # optional: sort by name
            entries.sort(key=lambda e: e.name.lower())
            for e in entries[:limit]:
                child = self.create_tree_item(e.name, e.path)
                parent_item.appendRow(child)
                # add lazy marker if subdirs exist
                try:
                    with os.scandir(e.path) as it:
                        if any(sub.is_dir(follow_symlinks=False) for sub in it):
                            child.appendRow(QStandardItem(""))
                except PermissionError:
                    pass
        except PermissionError:
            pass

    # ---------------------------
    # File / Navigation Functions
    # ---------------------------
    def open_file(self, index):
        path = self.model.filePath(index)
        if os.path.isdir(path):
            self.navigate_to_directory(path)
        elif os.path.isfile(path):
            os.startfile(path)

    def open_cmd(self):
        os.system('start cmd')

    def show_about(self):
        QMessageBox.information(self, "About", "BrontoBase File Manager\nPowered by PyQt5")

    # ---------------------------
    # Helpers for selection and refresh
    # ---------------------------
    def get_selected_paths(self):
        indexes = self.file_view.selectionModel().selectedRows(0)
        paths = []
        for idx in indexes:
            src_index = idx
            paths.append(self.model.filePath(src_index))
        return paths

    def get_current_dir(self):
        root_idx = self.file_view.rootIndex()
        return self.model.filePath(root_idx)

    def refresh_current_dir(self):
        current_dir = self.get_current_dir()
        self.file_view.setRootIndex(self.model.index(current_dir))
        self.file_view.sortByColumn(3, Qt.DescendingOrder)

    # ---------------------------
    # File operation handlers
    # ---------------------------
    def on_copy(self):
        self.clipboard_paths = self.get_selected_paths()
        self.clipboard_mode = 'copy'
        self.status_bar.showMessage(f"Copied {len(self.clipboard_paths)} item(s)", 3000)

    def on_cut(self):
        self.clipboard_paths = self.get_selected_paths()
        self.clipboard_mode = 'cut'
        self.status_bar.showMessage(f"Cut {len(self.clipboard_paths)} item(s)", 3000)

    def on_copy_address(self):
        from PyQt5.QtGui import QGuiApplication
        paths = self.get_selected_paths()
        if not paths:
            QMessageBox.information(self, "Copy Address", "No items selected.")
            return
        QGuiApplication.clipboard().setText("\n".join(paths))
        self.status_bar.showMessage("Paths copied to clipboard", 3000)

    def on_paste(self):
        if not self.clipboard_paths or self.clipboard_mode not in ('copy', 'cut'):
            QMessageBox.information(self, "Paste", "Clipboard is empty.")
            return
        dest_dir = self.get_current_dir()
        if not os.path.isdir(dest_dir):
            QMessageBox.warning(self, "Paste", "Destination is not a folder.")
            return
        errors = []
        for src in self.clipboard_paths:
            try:
                base = os.path.basename(src.rstrip("/\\"))
                dest = os.path.join(dest_dir, base)
                if self.clipboard_mode == 'copy':
                    self.ps_copy(src, dest)
                else:
                    self.ps_move(src, dest)
            except Exception as e:
                errors.append(f"{src} → {dest_dir}: {e}")
        if errors:
            QMessageBox.warning(self, "Paste", "Some items failed to paste:\n" + "\n".join(errors))
        if self.clipboard_mode == 'cut':
            # Clear after move
            self.clipboard_paths = []
            self.clipboard_mode = None
        self.refresh_current_dir()

    def on_move(self):
        paths = self.get_selected_paths()
        if not paths:
            QMessageBox.information(self, "Move", "No items selected.")
            return
        dest_dir = QFileDialog.getExistingDirectory(self, "Select Destination Folder", self.get_current_dir())
        if not dest_dir:
            return
        errors = []
        for src in paths:
            try:
                base = os.path.basename(src.rstrip("/\\"))
                dest = os.path.join(dest_dir, base)
                self.ps_move(src, dest)
            except Exception as e:
                errors.append(f"{src} → {dest_dir}: {e}")
        if errors:
            QMessageBox.warning(self, "Move", "Some items failed to move:\n" + "\n".join(errors))
        self.refresh_current_dir()

    def on_compress(self):
        paths = self.get_selected_paths()
        if not paths:
            QMessageBox.information(self, "Compress", "Select at least one file or folder.")
            return
        dest_dir = self.get_current_dir()
        # Name archive
        base_name, ok = QInputDialog.getText(self, "Archive Name", "Enter archive name (without .zip):", text="Archive")
        if not ok or not base_name:
            return
        archive_path = os.path.join(dest_dir, f"{base_name}.zip")
        # Build a temp staging folder to zip multiple items
        import tempfile, shutil
        staging_dir = tempfile.mkdtemp(prefix="bb_zip_")
        try:
            for p in paths:
                name = os.path.basename(p.rstrip("/\\"))
                target = os.path.join(staging_dir, name)
                if os.path.isdir(p):
                    self.ps_copy(p, target)
                else:
                    # ensure parent exists
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    self.ps_copy(p, target)
            # Use PowerShell Compress-Archive
            self.ps_compress(staging_dir, archive_path)
            QMessageBox.information(self, "Compress", f"Created {archive_path}")
        except Exception as e:
            QMessageBox.critical(self, "Compress", f"Failed to create archive: {e}")
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
        if not ok or not new_name:
            return
        dest = os.path.join(os.path.dirname(src), new_name)
        try:
            self.ps_rename(src, dest)
        except Exception as e:
            QMessageBox.critical(self, "Rename", f"Failed: {e}")
        self.refresh_current_dir()

    # ---------------------------
    # Favorites functionality
    # ---------------------------
    def on_add_to_favorites(self):
        """Add selected files/folders to favorites"""
        paths = self.get_selected_paths()
        if not paths:
            QMessageBox.information(self, "Add to Favorites", "No items selected.")
            return
        
        added_count = 0
        
        for path in paths:
            if self.favorites_manager.add_favorite(path):
                added_count += 1
        
        if added_count > 0:
            self.status_bar.showMessage(f"Added {added_count} item(s) to favorites", 3000)
            # Refresh the navigation tree to show new favorites
            self.build_navigation_tree()
        else:
            QMessageBox.information(self, "Add to Favorites", "Selected items are already in favorites or don't exist.")

    def on_favorite_clicked(self, index):
        """Handle single click on favorite item - navigate to file location"""
        item = self.nav_model.itemFromIndex(index)
        path = item.data(Qt.UserRole)
        if path and os.path.exists(path):
            # Navigate to the parent directory of the favorite
            parent_dir = os.path.dirname(path)
            self.navigate_to_directory(parent_dir)
            self.status_bar.showMessage(f"Navigated to: {parent_dir}")

    def on_favorite_double_clicked(self, index):
        """Handle double click on favorite item - open the file"""
        item = self.nav_model.itemFromIndex(index)
        path = item.data(Qt.UserRole)
        if path and os.path.exists(path):
            if os.path.isfile(path):
                os.startfile(path)
                self.status_bar.showMessage(f"Opened: {path}")
            else:
                # For folders, navigate to them
                self.navigate_to_directory(path)
                self.status_bar.showMessage(f"Navigated to: {path}")

    def remove_favorite(self, path):
        """Remove a favorite item"""
        if self.favorites_manager.remove_favorite(path):
            self.build_navigation_tree()

    # ---------------------------
    # Navigation helpers
    # ---------------------------
    def navigate_to_directory(self, path):
        """Navigate to a directory and update history"""
        if not os.path.exists(path) or not os.path.isdir(path):
            return
            
        # Add current location to history before navigating
        current_path = self.get_current_dir()
        if current_path and current_path != path:
            self.navigation_history.add_to_history(current_path)
            
        # Navigate to new location
        self.file_view.setRootIndex(self.model.index(path))
        self.file_view.sortByColumn(3, Qt.DescendingOrder)
        
    def on_back(self):
        """Navigate back to previous directory"""
        previous_path = self.navigation_history.go_back()
        
        if previous_path:
            self.file_view.setRootIndex(self.model.index(previous_path))
            self.file_view.sortByColumn(3, Qt.DescendingOrder)
            self.status_bar.showMessage(f"Back to: {previous_path}", 2000)
        else:
            self.status_bar.showMessage("No more history to go back", 2000)
            
    def on_forward(self):
        """Navigate forward to next directory"""
        next_path = self.navigation_history.go_forward()
        
        if next_path:
            self.file_view.setRootIndex(self.model.index(next_path))
            self.file_view.sortByColumn(3, Qt.DescendingOrder)
            self.status_bar.showMessage(f"Forward to: {next_path}", 2000)
        else:
            self.status_bar.showMessage("No more history to go forward", 2000)

    # ---------------------------
    # Search functionality
    # ---------------------------
    def on_search(self):
        """Open search dialog"""
        search_dialog = SearchDialog(self, self.file_searcher, self.get_current_dir())
        search_dialog.exec_()


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
        
        # Search options group
        options_group = QGroupBox("Search Options")
        options_layout = QVBoxLayout()
        
        # Search type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Search Type:"))
        self.search_type = QComboBox()
        self.search_type.addItems(["Windows Style", "File Name", "Content", "Size", "Date"])
        self.search_type.currentTextChanged.connect(self.on_search_type_changed)
        type_layout.addWidget(self.search_type)
        options_layout.addLayout(type_layout)
        
        # Search text
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("File Name:"))
        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText("Enter filename to search...")
        text_layout.addWidget(self.search_text)
        options_layout.addLayout(text_layout)
        
        # File type
        type_input_layout = QHBoxLayout()
        type_input_layout.addWidget(QLabel("File Type:"))
        self.file_type_input = QLineEdit()
        self.file_type_input.setPlaceholderText("pdf, doc, txt (optional)")
        type_input_layout.addWidget(self.file_type_input)
        options_layout.addLayout(type_input_layout)
        
        # Directory
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
        
        # Recursive search
        self.recursive_check = QCheckBox("Search subdirectories")
        self.recursive_check.setChecked(True)
        options_layout.addWidget(self.recursive_check)
        
        # Advanced options (initially hidden)
        self.advanced_group = QGroupBox("Advanced Options")
        self.advanced_layout = QVBoxLayout()
        
        # File extensions for content search
        ext_layout = QHBoxLayout()
        ext_layout.addWidget(QLabel("File Extensions:"))
        self.extensions_input = QLineEdit()
        self.extensions_input.setPlaceholderText("txt,doc,pdf (comma separated)")
        ext_layout.addWidget(self.extensions_input)
        self.advanced_layout.addLayout(ext_layout)
        
        # Size range
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
        
        # Date range
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
        
        # Search button
        self.search_btn = QPushButton("🔍 Search")
        self.search_btn.clicked.connect(self.perform_search)
        layout.addWidget(self.search_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Results
        results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        
        # Results actions
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
        """Apply dark theme to the dialog"""
        self.setStyleSheet("""
            QDialog {
                background-color: #2a2a2a;
                color: #ccc;
            }
            QGroupBox {
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffd700;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #3a3a3a;
                color: #ccc;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton {
                background-color: #333333;
                color: #ffd700;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #444444;
                border: 1px solid #ffd700;
            }
            QPushButton:disabled {
                background-color: #222222;
                color: #666666;
                border: 1px solid #444444;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
                background-color: #3a3a3a;
            }
            QProgressBar::chunk {
                background-color: #ffd700;
                border-radius: 2px;
            }
        """)
    
    def on_search_type_changed(self, search_type):
        """Handle search type change"""
        is_windows_style = search_type == "Windows Style"
        self.file_type_input.setVisible(is_windows_style)
        self.advanced_group.setVisible(search_type in ["Content", "Size", "Date"])
        
        # Update placeholders based on search type
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
        """Populate the directory dropdown with available directories"""
        self.dir_combo.clear()
        
        # Add common directories
        common_dirs = []
        
        # User's home directory
        home_dir = os.path.expanduser("~")
        if os.path.exists(home_dir):
            common_dirs.append(home_dir)
        
        # Windows special folders
        if os.name == 'nt':  # Windows
            special_folders = [
                os.path.join(home_dir, "Documents"),
                os.path.join(home_dir, "Downloads"),
                os.path.join(home_dir, "Desktop"),
                os.path.join(home_dir, "Pictures"),
                os.path.join(home_dir, "Music"),
                os.path.join(home_dir, "Videos"),
                os.path.join(home_dir, "OneDrive"),
                os.path.join(home_dir, "AppData", "Local"),
                os.path.join(home_dir, "AppData", "Roaming"),
            ]
            
            for folder in special_folders:
                if os.path.exists(folder):
                    common_dirs.append(folder)
        
        # Add drives (Windows)
        if os.name == 'nt':
            import string
            for drive in string.ascii_uppercase:
                drive_path = f"{drive}:\\"
                if os.path.exists(drive_path):
                    common_dirs.append(drive_path)
        
        # Add current search directory if not already in list
        if self.search_directory and self.search_directory not in common_dirs:
            common_dirs.insert(0, self.search_directory)
        
        # Add directories to combo box
        for directory in common_dirs:
            self.dir_combo.addItem(directory)
    
    def browse_directory(self):
        """Browse for search directory"""
        current_dir = self.dir_combo.currentText() if self.dir_combo.currentText() else self.search_directory
        directory = QFileDialog.getExistingDirectory(self, "Select Search Directory", current_dir)
        if directory:
            # Add to combo box if not already present
            if self.dir_combo.findText(directory) == -1:
                self.dir_combo.addItem(directory)
            self.dir_combo.setCurrentText(directory)
    
    def perform_search(self):
        """Perform the search based on selected options"""
        search_directory = self.dir_combo.currentText()
        if not search_directory or not os.path.exists(search_directory):
            QMessageBox.warning(self, "Search Error", "Please select a valid directory.")
            return
        
        search_type = self.search_type.currentText()
        search_text = self.search_text.text().strip()
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.search_btn.setEnabled(False)
        self.results_text.clear()
        
        try:
            if search_type == "Windows Style":
                if not search_text:
                    QMessageBox.warning(self, "Search Error", "Please enter a filename to search for.")
                    return
                file_type = self.file_type_input.text().strip()
                results = self.file_searcher.search_files_windows_style(
                    search_text, 
                    file_type, 
                    search_directory
                )
                self.display_windows_style_results(results)
                
            elif search_type == "File Name":
                if not search_text:
                    QMessageBox.warning(self, "Search Error", "Please enter a search term.")
                    return
                results = self.file_searcher.search_files(
                    search_directory, 
                    search_text, 
                    self.recursive_check.isChecked()
                )
                self.display_results(results)
                
            elif search_type == "Content":
                if not search_text:
                    QMessageBox.warning(self, "Search Error", "Please enter text to search for.")
                    return
                extensions = None
                if self.extensions_input.text().strip():
                    extensions = [ext.strip() for ext in self.extensions_input.text().split(",")]
                results = self.file_searcher.search_by_content(search_directory, search_text, extensions)
                self.display_results(results)
                
            elif search_type == "Size":
                min_size = None
                max_size = None
                if self.min_size.text().strip():
                    try:
                        min_size = int(float(self.min_size.text()) * 1024 * 1024)  # Convert MB to bytes
                    except ValueError:
                        pass
                if self.max_size.text().strip():
                    try:
                        max_size = int(float(self.max_size.text()) * 1024 * 1024)  # Convert MB to bytes
                    except ValueError:
                        pass
                results = self.file_searcher.search_by_size(search_directory, min_size, max_size)
                self.display_size_results(results)
                
            elif search_type == "Date":
                start_date = self.start_date.text().strip() or None
                end_date = self.end_date.text().strip() or None
                results = self.file_searcher.search_by_date(search_directory, start_date, end_date)
                self.display_size_results(results)
                
        except Exception as e:
            QMessageBox.critical(self, "Search Error", f"An error occurred during search: {str(e)}")
        finally:
            self.progress_bar.setVisible(False)
            self.search_btn.setEnabled(True)
    
    def display_results(self, results):
        """Display search results"""
        self.search_results = results
        if not results:
            self.results_text.setText("No results found.")
            self.open_btn.setEnabled(False)
            self.navigate_btn.setEnabled(False)
            return
        
        result_text = f"Found {len(results)} result(s):\n\n"
        for i, result in enumerate(results, 1):
            result_text += f"{i}. {result}\n"
        
        self.results_text.setText(result_text)
        self.open_btn.setEnabled(True)
        self.navigate_btn.setEnabled(True)
    
    def display_windows_style_results(self, results):
        """Display Windows-style search results with similarity scores"""
        self.search_results = [result['path'] for result in results]
        if not results:
            self.results_text.setText("No results found.")
            self.open_btn.setEnabled(False)
            self.navigate_btn.setEnabled(False)
            return
        
        result_text = f"Found {len(results)} result(s):\n\n"
        for i, result in enumerate(results, 1):
            size_str = self.file_searcher.format_size(result['size'])
            similarity_percent = int(result['similarity'] * 100)
            result_text += f"{i}. {result['name']} ({result['extension']}) - {size_str}\n"
            result_text += f"   Path: {result['path']}\n"
            result_text += f"   Relevance: {similarity_percent}% | Modified: {result['modified']}\n\n"
        
        self.results_text.setText(result_text)
        self.open_btn.setEnabled(True)
        self.navigate_btn.setEnabled(True)
    
    def display_size_results(self, results):
        """Display size/date search results"""
        self.search_results = [result['path'] for result in results]
        if not results:
            self.results_text.setText("No results found.")
            self.open_btn.setEnabled(False)
            self.navigate_btn.setEnabled(False)
            return
        
        result_text = f"Found {len(results)} result(s):\n\n"
        for i, result in enumerate(results, 1):
            size_str = self.file_searcher.format_size(result['size'])
            result_text += f"{i}. {result['path']} ({size_str}, {result['modified']})\n"
        
        self.results_text.setText(result_text)
        self.open_btn.setEnabled(True)
        self.navigate_btn.setEnabled(True)
    
    def open_selected(self):
        """Open the selected file"""
        if not self.search_results:
            return
        
        # For simplicity, open the first result
        # In a real implementation, you'd want to get the selected line
        if self.search_results:
            file_path = self.search_results[0]
            if os.path.exists(file_path):
                os.startfile(file_path)
    
    def navigate_to_selected(self):
        """Navigate to the selected file's directory"""
        if not self.search_results:
            return
        
        # For simplicity, navigate to the first result
        if self.search_results:
            file_path = self.search_results[0]
            if os.path.exists(file_path):
                parent_dir = os.path.dirname(file_path)
                # Navigate in the parent window
                if hasattr(self.parent(), 'navigate_to_directory'):
                    self.parent().navigate_to_directory(parent_dir)
                    self.accept()  # Close the dialog
    
    def clear_results(self):
        """Clear search results"""
        self.results_text.clear()
        self.search_results = []
        self.open_btn.setEnabled(False)
        self.navigate_btn.setEnabled(False)

    # ---------------------------
    # PowerShell-backed helpers
    # ---------------------------
    def ps_copy(self, src, dest):
        import subprocess
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Copy-Item -LiteralPath \"{src}\" -Destination \"{dest}\" -Recurse -Force"], check=True)

    def ps_move(self, src, dest):
        import subprocess
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Move-Item -LiteralPath \"{src}\" -Destination \"{dest}\" -Force"], check=True)

    def ps_rename(self, src, dest):
        import subprocess
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Rename-Item -LiteralPath \"{src}\" -NewName \"{os.path.basename(dest)}\" -Force"], check=True)

    def ps_compress(self, source_dir, dest_zip):
        import subprocess
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(dest_zip), exist_ok=True)
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Compress-Archive -Path \"{source_dir}\\*\" -DestinationPath \"{dest_zip}\" -Force"], check=True)