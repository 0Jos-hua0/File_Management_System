import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter,
    QTreeView, QTableView, QPushButton,
    QMessageBox, QInputDialog, QStatusBar, QFileSystemModel, QFrame, QHeaderView, QFileDialog
)
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QSize
from PyQt5.QtGui import QIcon, QPalette, QColor, QLinearGradient, QStandardItemModel, QStandardItem

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
                ("✂ Cut", self.on_cut),
                ("📋 Copy", self.on_copy),
                ("🔗 Copy Address", self.on_copy_address),
                ("📥 Paste", self.on_paste),
                ("📂 Move", self.on_move),
                ("🗜 Compress", self.on_compress),
                ("✏ Rename", self.on_rename),
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
        # Drives
        drives_root = QStandardItem("💽 Drives"); drives_root.setEditable(False); drives_root.setData("__section__", Qt.UserRole+1)
        root.appendRow(drives_root)
        for drive in self.enumerate_drives():
            d_item = self.create_tree_item(drive, drive)
            drives_root.appendRow(d_item)
            d_item.appendRow(QStandardItem(""))  # lazy marker
        self.nav_tree.expand(qa_root.index())
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
        if path and os.path.exists(path):
            self.file_view.setRootIndex(self.model.index(path))
            self.file_view.sortByColumn(3, Qt.DescendingOrder)

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
            self.file_view.setRootIndex(index)
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