# File Organizer Desktop GUI 🗂️

A modern, cross-platform desktop application built with **CustomTkinter** and **tkinterdnd2** that automatically sorts messy directories by file extension into categorized subfolders via drag-and-drop.

---

## ✨ Key Features

- **Intuitive Drag & Drop**: Drag any combination of files and folders directly onto the large interactive drop zone.
- **Two Operation Modes**:
  - **Auto-sort on drop**: Instantly organizes dropped files without interrupting your workflow.
  - **Preview first**: Inspect detected categories and target paths in an interactive preview table with per-file checkboxes before committing moves.
- **Collision-Safe Renaming**: Never overwrites existing files. Appends a timestamp (`report_20261010_153012.pdf`) or counter if names collide.
- **Atomic Undo**: Every batch is recorded in `.organizer_history.json`. Revert the last run at any time—even across app restarts.
- **Folder Watcher Automation**: Enable background folder monitoring (e.g. `Downloads`) with `watchdog`. Files are automatically sorted as soon as downloads complete (ignoring `.crdownload`, `.part`, `.tmp`).
- **Customizable Categories**: Built-in visual Settings dialog to create/delete categories, manage extensions, select output folder modes, and configure subfolder recursion.
- **Modern UI & Themes**: Smooth Dark and Light mode toggling with CustomTkinter styling.
- **Clean Architecture**: `core/` contains pure Python logic with zero UI dependencies, fully covered by automated unit tests.

---

## 📁 Default Category Mapping

| Category | File Extensions |
| :--- | :--- |
| **Images** | `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`, `.svg` |
| **Documents** | `.pdf`, `.docx`, `.doc`, `.txt`, `.xlsx`, `.pptx`, `.csv` |
| **Archives** | `.zip`, `.rar`, `.7z`, `.tar`, `.gz` |
| **Installers** | `.exe`, `.msi`, `.dmg`, `.pkg` |
| **Videos** | `.mp4`, `.mkv`, `.mov`, `.avi` |
| **Audio** | `.mp3`, `.wav`, `.flac`, `.aac` |
| **Code** | `.py`, `.js`, `.html`, `.css`, `.json` |
| **Others** | Files with unknown extensions or no extension |

---

## 📂 Project Structure

```text
file_organizer_gui/
├── main.py              # Application entry point
├── config.json          # Persistent settings and category definitions
├── file_organizer.spec  # PyInstaller build specification
├── requirements.txt     # Python package dependencies
├── README.md            # Documentation
├── assets/              # App icons (.ico, .png)
│   ├── icon.ico
│   └── icon.png
├── core/                # Core business logic (Zero UI dependencies)
│   ├── categories.py    # Category mappings & config management
│   ├── organizer.py     # Scanning, classification, collision & moves
│   ├── undo.py          # History log persistence and undo engine
│   └── watcher.py       # Background folder watcher service
├── ui/                  # CustomTkinter GUI components
│   ├── app.py           # Main window & thread orchestration
│   ├── drop_zone.py     # Drag-and-drop target widget
│   ├── preview_table.py # Preview list with selection checkboxes
│   └── settings_window.py # Settings & category editor modal
└── tests/
    └── test_core.py     # Pytest test suite for core logic
```

---

## 🚀 Getting Started

### 1. Requirements & Installation
Python 3.9+ is recommended.

Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Launch the Application
Run the entry point script:
```bash
python main.py
```

---

## 🖥️ User Guide

1. **Drop Zone**:
   - Drag and drop files or folders from Windows Explorer / Finder.
   - Or click **Browse Files...** / **Browse Folder...** to select items via dialog.
2. **Auto-Sort vs. Preview Mode**:
   - Switch between **Auto-sort on drop** and **Preview first** in the header.
   - In Preview mode, uncheck any files you do not wish to move, then click **Organize Selected**.
3. **Undo Last Run**:
   - Click the **Undo Last Run** button in the bottom bar to safely restore files from the previous batch to their original locations.
4. **Settings Dialog**:
   - Click **⚙️ Settings** to configure:
     - Output folder mode: *Sort next to file* vs. *Single destination folder*.
     - Include subfolders (recursive folder search).
     - Category list and extension editor.
     - Reset configuration to defaults.
5. **Watch Folder Mode**:
   - Click **👁️ Watch** to activate real-time automatic sorting for your configured directory (e.g. `Downloads`).

---

## 🧪 Running Tests

Run pytest across all core test cases:
```bash
pytest tests/test_core.py -v
```

---

## 📦 Packaging Standalone Executable (.exe)

Build a single-window executable (without a console window) using the provided `.spec` file:

```bash
pyinstaller file_organizer.spec
```

The compiled standalone executable will be located in the `dist/` directory:
```text
dist/
└── FileOrganizer.exe
```
