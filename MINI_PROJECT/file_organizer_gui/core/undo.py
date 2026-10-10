"""Move history logging and undo manager for File Organizer GUI."""

from __future__ import annotations

import datetime
import json
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

HISTORY_FILE_NAME = ".organizer_history.json"


def get_default_history_path() -> Path:
    """Return default history log path in the app root."""
    return Path(__file__).resolve().parent.parent / HISTORY_FILE_NAME


def resolve_collision(target_path: Path) -> Path:
    """
    Generate a non-colliding path by appending timestamp and counter if target exists.
    Format: <stem>_<YYYYMMDD_HHMMSS><suffix>
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


def load_history(history_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load the full history log from JSON."""
    path = history_path or get_default_history_path()
    if not path.is_file():
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_run(moves: List[Dict[str, str]], history_path: Optional[Path] = None) -> None:
    """
    Record a successful batch of moves to the history file.

    Args:
        moves: List of move records with 'source', 'destination', and optional 'category'.
        history_path: Optional custom path to history file.
    """
    if not moves:
        return

    path = history_path or get_default_history_path()
    history = load_history(path)

    run_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "moves": moves,
    }
    history.append(run_entry)

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except OSError:
        pass


def get_history_count(history_path: Optional[Path] = None) -> int:
    """Get number of runs available in history."""
    return len(load_history(history_path))


def get_last_run_info(history_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Get details for the most recent run."""
    history = load_history(history_path)
    return history[-1] if history else None


def undo_last_run(
    history_path: Optional[Path] = None,
    on_step: Optional[Callable[[str, str], None]] = None,
) -> Dict[str, Any]:
    """
    Revert the moves from the most recent run.

    Args:
        history_path: Optional path to history file.
        on_step: Optional callback called on each file reverted (source, dest).

    Returns:
        Summary dict containing counts of reverted, missing, and error files.
    """
    path = history_path or get_default_history_path()
    history = load_history(path)

    summary: Dict[str, Any] = {
        "reverted": 0,
        "missing": 0,
        "errors": 0,
        "details": [],
    }

    if not history:
        return summary

    last_run = history.pop()
    moves: List[Dict[str, str]] = last_run.get("moves", [])

    for item in reversed(moves):
        src_path = Path(item["source"])
        dest_path = Path(item["destination"])

        if not dest_path.exists():
            summary["missing"] += 1
            continue

        try:
            # If the original location has a new file, avoid overwriting
            safe_src = resolve_collision(src_path)
            safe_src.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dest_path), str(safe_src))

            summary["reverted"] += 1
            summary["details"].append((str(dest_path), str(safe_src)))

            if on_step:
                on_step(str(dest_path), str(safe_src))

            # Attempt to clean up empty destination category folder
            parent_dir = dest_path.parent
            if parent_dir.exists() and not any(parent_dir.iterdir()):
                try:
                    parent_dir.rmdir()
                except OSError:
                    pass

        except (PermissionError, OSError) as e:
            summary["errors"] += 1

    # Save updated history (with last run removed)
    try:
        if history:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        else:
            path.unlink(missing_ok=True)
    except OSError:
        pass

    return summary
