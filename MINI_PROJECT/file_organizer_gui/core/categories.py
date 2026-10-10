"""Core categories and settings manager for File Organizer GUI."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Default category mappings
DEFAULT_CATEGORIES: Dict[str, List[str]] = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"],
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".csv"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Installers": [".exe", ".msi", ".dmg", ".pkg"],
    "Videos": [".mp4", ".mkv", ".mov", ".avi"],
    "Audio": [".mp3", ".wav", ".flac", ".aac"],
    "Code": [".py", ".js", ".html", ".css", ".json"],
}

DEFAULT_OTHERS_CATEGORY = "Others"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "categories": copy.deepcopy(DEFAULT_CATEGORIES),
    "output_mode": "next_to_file",  # Options: 'next_to_file' or 'single_root'
    "single_root_folder": str(Path.home() / "Downloads" / "Sorted"),
    "include_subfolders": False,
    "auto_sort_on_drop": True,
    "watch_folder_path": str(Path.home() / "Downloads"),
    "watch_enabled": False,
    "theme_mode": "Dark",  # 'Dark' or 'Light'
}

CONFIG_FILE_NAME = "config.json"


def get_default_config_path() -> Path:
    """Return the default configuration file path relative to the app root."""
    return Path(__file__).resolve().parent.parent / CONFIG_FILE_NAME


def normalize_extension(ext: str) -> str:
    """Ensure extension is lowercased and prefixed with a dot."""
    ext = ext.strip().lower()
    if not ext:
        return ""
    return ext if ext.startswith(".") else f".{ext}"


def build_extension_map(categories: Dict[str, List[str]]) -> Dict[str, str]:
    """
    Build an inverted lookup mapping from lowercased extension to category name.

    Args:
        categories: Mapping of category names to lists of extensions.

    Returns:
        Mapping of extension (e.g. '.jpg') to category name (e.g. 'Images').
    """
    ext_map: Dict[str, str] = {}
    for category, extensions in categories.items():
        for ext in extensions:
            cleaned = normalize_extension(ext)
            if cleaned:
                ext_map[cleaned] = category
    return ext_map


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load configuration and user settings from config.json.
    Merges missing keys with defaults to guarantee valid settings.
    """
    path = config_path or get_default_config_path()
    config = copy.deepcopy(DEFAULT_SETTINGS)

    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_data = json.load(f)

            if isinstance(user_data, dict):
                # If the json has top-level "categories", merge settings dictionary
                if "categories" in user_data and isinstance(user_data["categories"], dict):
                    # Clean and normalize extensions
                    cleaned_cats: Dict[str, List[str]] = {}
                    for cat, exts in user_data["categories"].items():
                        if isinstance(exts, list):
                            cleaned_cats[str(cat)] = [
                                normalize_extension(e) for e in exts if isinstance(e, str) and normalize_extension(e)
                            ]
                    user_data["categories"] = cleaned_cats
                    config.update(user_data)
                else:
                    # Legacy or simple categories-only config format
                    cleaned_cats = {}
                    for cat, exts in user_data.items():
                        if isinstance(exts, list):
                            cleaned_cats[str(cat)] = [
                                normalize_extension(e) for e in exts if isinstance(e, str) and normalize_extension(e)
                            ]
                    if cleaned_cats:
                        config["categories"] = cleaned_cats
        except (json.JSONDecodeError, OSError):
            pass

    return config


def save_config(config_data: Dict[str, Any], config_path: Optional[Path] = None) -> Path:
    """Save configuration dictionary to config.json."""
    path = config_path or get_default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)

    return path


def reset_config_to_defaults(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Reset configuration to default settings and persist to file."""
    config = copy.deepcopy(DEFAULT_SETTINGS)
    save_config(config, config_path)
    return config
