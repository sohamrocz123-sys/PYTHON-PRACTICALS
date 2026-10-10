"""Utility functions for collision handling, file filtering, history logging, and undo."""

from __future__ import annotations

import datetime
import json
import logging
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

HISTORY_FILENAME = ".organizer_history.json"
SYSTEM_FILES: Set[str] = {
    "desktop.ini",
    "thumbs.db",
    ".ds_store",
    "icon\r",
    "$recycle.bin",
    "system volume information",
}


def is_hidden_or_system_file(path: Path) -> bool:
    """
    Check if a file is hidden or an OS system file.

    Args:
        path: Path object to check.

    Returns:
        True if the file is hidden or system-specific, False otherwise.
    """
    name_lower = path.name.lower()

    # Leading dot covers hidden files across POSIX and dotfiles on Windows
    if name_lower.startswith("."):
        return True

    if name_lower in SYSTEM_FILES:
        return True

    # Windows specific hidden or system attribute check
    if sys.platform == "win32":
        try:
            attrs = path.stat().st_file_attributes
            if attrs & (stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM):
                return True
        except (AttributeError, OSError):
            pass

    return False


def resolve_collision(target_path: Path) -> Path:
    """
    Generate a non-colliding path by appending a timestamp (and counter if needed).

    Format: <stem>_<YYYYMMDD_HHMMSS><suffix> or <stem>_<YYYYMMDD_HHMMSS>_<counter><suffix>

    Args:
        target_path: Desired destination file path.

    Returns:
        A unique destination Path that does not currently exist.
    """
    if not target_path.exists():
        return target_path

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    parent = target_path.parent
    stem = target_path.stem
    suffix = target_path.suffix

    candidate = parent / f"{stem}_{timestamp}{suffix}"
    if not candidate.exists():
        return candidate

    counter = 1
    while candidate.exists():
        candidate = parent / f"{stem}_{timestamp}_{counter}{suffix}"
        counter += 1

    return candidate


def setup_logger(verbose: bool = False) -> logging.Logger:
    """
    Set up the application logger.

    Args:
        verbose: If True, log level is DEBUG; otherwise INFO.

    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger("file_organizer")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG if verbose else logging.INFO)
        formatter = logging.Formatter(
            fmt="[%(levelname)s] %(message)s" if not verbose else "[%(levelname)s - %(asctime)s] %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG if verbose else logging.INFO)

    return logger


def save_history_entry(target_dir: Path, moves: List[Dict[str, str]]) -> Path:
    """
    Save the list of performed file moves to the directory's history JSON log.

    Args:
        target_dir: Directory where the history log is stored.
        moves: List of move records, each containing 'source' and 'destination'.

    Returns:
        Path to the history log file.
    """
    history_file = target_dir / HISTORY_FILENAME
    history_data: List[Dict[str, Any]] = []

    if history_file.is_file():
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                content = json.load(f)
                if isinstance(content, list):
                    history_data = content
        except (json.JSONDecodeError, OSError):
            history_data = []

    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "moves": moves,
    }
    history_data.append(entry)

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f, indent=2)

    return history_file


def undo_last_run(target_dir: Path, logger: Optional[logging.Logger] = None) -> Dict[str, Any]:
    """
    Revert the most recent organization run for target_dir using the saved JSON log.

    Args:
        target_dir: The organized directory.
        logger: Optional logger for status messages.

    Returns:
        Summary dict containing counts of reverted files, errors, and missing files.
    """
    history_file = target_dir / HISTORY_FILENAME
    summary = {
        "reverted": 0,
        "missing": 0,
        "errors": 0,
        "details": [],
    }

    if not history_file.is_file():
        if logger:
            logger.warning(f"No history file found at {history_file}. Nothing to undo.")
        return summary

    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        if logger:
            logger.error(f"Failed to read history log: {e}")
        summary["errors"] += 1
        return summary

    if not history_data or not isinstance(history_data, list):
        if logger:
            logger.info("History log is empty. Nothing to undo.")
        return summary

    last_entry = history_data.pop()
    moves: List[Dict[str, str]] = last_entry.get("moves", [])

    if logger:
        logger.info(f"Reverting {len(moves)} move(s) from run at {last_entry.get('timestamp')}...")

    # Revert moves in reverse order
    for item in reversed(moves):
        src_path = Path(item["source"])
        dest_path = Path(item["destination"])

        if not dest_path.exists():
            if logger:
                logger.warning(f"File not found at destination, skipping: {dest_path}")
            summary["missing"] += 1
            continue

        try:
            # Handle collision if the original source path now exists
            final_src_path = resolve_collision(src_path)
            shutil.move(str(dest_path), str(final_src_path))
            summary["reverted"] += 1
            summary["details"].append((str(dest_path), str(final_src_path)))
            if logger:
                logger.debug(f"Restored: {dest_path} -> {final_src_path}")
        except (PermissionError, OSError) as e:
            if logger:
                logger.error(f"Error reverting {dest_path}: {e}")
            summary["errors"] += 1

    # Update or remove history file
    try:
        if history_data:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history_data, f, indent=2)
        else:
            history_file.unlink(missing_ok=True)
    except OSError as e:
        if logger:
            logger.error(f"Error updating history file: {e}")

    return summary
