"""Category mapping and configuration loader for File Organizer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

# Default category mappings
CATEGORIES: Dict[str, List[str]] = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"],
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".csv"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Installers": [".exe", ".msi", ".dmg", ".pkg"],
    "Videos": [".mp4", ".mkv", ".mov", ".avi"],
    "Audio": [".mp3", ".wav", ".flac", ".aac"],
    "Code": [".py", ".js", ".html", ".css", ".json"],
}

DEFAULT_OTHERS_CATEGORY = "Others"


def load_categories(config_path: Optional[Path] = None) -> Dict[str, List[str]]:
    """
    Load categories from a JSON config file or fall back to default CATEGORIES.

    Extensions in the returned dictionary are normalized to lowercase with a leading dot.

    Args:
        config_path: Optional path to a custom JSON configuration file.

    Returns:
        A dictionary mapping category names to lists of lowercase extensions.
    """
    categories = {cat: [ext.lower() for ext in exts] for cat, exts in CATEGORIES.items()}

    if config_path and config_path.is_file():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            if isinstance(user_config, dict):
                for cat, exts in user_config.items():
                    if isinstance(exts, list):
                        normalized = [
                            ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                            for ext in exts
                            if isinstance(ext, str)
                        ]
                        categories[str(cat)] = normalized
        except (json.JSONDecodeError, OSError) as e:
            # Revert to defaults if config is malformed or unreadable
            pass

    return categories


def build_extension_map(categories: Dict[str, List[str]]) -> Dict[str, str]:
    """
    Create an inverted lookup map from extension to category name.

    Args:
        categories: Mapping of category names to extension lists.

    Returns:
        Mapping of lowercase extension (e.g. '.jpg') to category name (e.g. 'Images').
    """
    ext_map: Dict[str, str] = {}
    for category, extensions in categories.items():
        for ext in extensions:
            ext_map[ext.lower()] = category
    return ext_map
