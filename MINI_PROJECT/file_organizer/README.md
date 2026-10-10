# File Organizer 🗂️

A cross-platform Python CLI automation script that cleans up cluttered directories (such as `Downloads` or `Desktop`) by automatically sorting files into category subfolders based on file extensions.

---

## ✨ Features

- **Non-Recursive Top-Level Scan**: Only processes files directly inside the target directory. Never touches or traverses existing subdirectories.
- **Case-Insensitive Extension Matching**: Gracefully matches `.JPG`, `.jpg`, `.Jpeg`, `.PNG`, etc. to the same category.
- **Smart Collision Handling**: If a file with the same name already exists in the destination subfolder, it automatically appends a timestamp (e.g. `report_20260504_153012.pdf`) rather than overwriting.
- **"Others" Fallback**: Files with unknown extensions or no extension are safely organized into an `Others/` folder.
- **Safe Filtering**: Skips hidden files (`.env`, `.gitignore`), system files (`desktop.ini`, `thumbs.db`, `.DS_Store`), script files, and active history logs. Handles `PermissionError` and `OSError` per file without stopping the run.
- **`--dry-run` Preview**: Test and preview exactly where files will be routed without modifying disk contents or creating folders.
- **`--undo` Support**: Every run saves a record in `.organizer_history.json`. Use `--undo` to seamlessly revert files to their original locations.
- **Configurable**: Easily override or expand categories with a JSON config file (`config.json`).

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
| **Others** | Any extension not listed above, or files with no extension |

---

## 📂 Project Structure

```text
file_organizer/
├── file_organizer.py       # Main script and CLI entry point
├── categories.py           # Default CATEGORIES mapping and loader
├── utils.py                # Collision handling, filtering, logger, and undo engine
├── config.json             # Optional custom categories template
├── requirements.txt        # Development dependencies
├── README.md               # Documentation and usage guide
└── tests/
    └── test_organizer.py   # Comprehensive pytest test suite
```

---

## 🚀 Quick Start

### 1. Requirements & Setup
Python 3.9 or newer is required.

Install test dependencies (optional):
```bash
pip install -r requirements.txt
```

### 2. Basic Usage

By default, executing the script with no arguments targets your user **Downloads** directory:

```bash
python file_organizer.py
```

Organize a specific folder (e.g., your Desktop or a custom folder):
```bash
python file_organizer.py "C:\Users\Username\Desktop"
# or on macOS / Linux:
python file_organizer.py ~/Desktop
```

---

## 🛠️ CLI Options

```text
usage: file_organizer [-h] [--dry-run] [--undo] [--verbose] [--config CONFIG] [path]

Clean up cluttered directories by sorting files into category subfolders.

positional arguments:
  path                  Target directory path to organize (default: current user's Downloads folder)

options:
  -h, --help            Show this help message and exit
  --dry-run             Preview what would be moved without changing anything on disk.
  --undo                Revert the last organization run using the saved history log.
  --verbose, -v         Enable detailed logging output (DEBUG level).
  --config CONFIG, -c CONFIG
                        Optional path to a custom config.json file to override categories.
```

### Examples

#### Preview with Dry-Run
```bash
python file_organizer.py "D:\MyFolder" --dry-run
```

#### Detailed Output (Verbose)
```bash
python file_organizer.py "D:\MyFolder" --verbose
```

#### Reverting the Last Run (Undo)
```bash
python file_organizer.py "D:\MyFolder" --undo
```

#### Using a Custom Configuration
```bash
python file_organizer.py "D:\MyFolder" --config custom_config.json
```

---

## ⚙️ Customizing Categories

You can override or extend categories by editing `config.json` or passing `--config path/to/config.json`:

```json
{
  "Images": [".jpg", ".jpeg", ".png", ".webp"],
  "Ebooks": [".epub", ".mobi", ".azw3"],
  "Datasets": [".csv", ".tsv", ".parquet", ".arrow"]
}
```

Extensions can be written with or without the leading dot and are always treated case-insensitively.

---

## 🧪 Running Tests

Execute the test suite using `pytest`:

```bash
pytest tests/test_organizer.py -v
```
