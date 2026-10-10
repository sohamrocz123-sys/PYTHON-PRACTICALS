"""Core organization logic: scanning, classifying, collision resolution, and execution."""

from __future__ import annotations

import datetime
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from core.categories import DEFAULT_OTHERS_CATEGORY, build_extension_map
from core.undo import resolve_collision, save_run

SYSTEM_FILES: Set[str] = {
    "desktop.ini",
    "thumbs.db",
    ".ds_store",
    "$recycle.bin",
    "system volume information",
}


def is_system_or_hidden(path: Path) -> bool:
    """Check if file or directory is hidden or an OS system artifact."""
    name_lower = path.name.lower()
    if name_lower.startswith("."):
        return True
    if name_lower in SYSTEM_FILES:
        return True

    if sys.platform == "win32":
        try:
            attrs = path.stat().st_file_attributes
            if attrs & (stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM):
                return True
        except (AttributeError, OSError):
            pass

    return False


def scan_input_paths(
    input_paths: List[Path],
    include_subfolders: bool = False,
    known_categories: Optional[Set[str]] = None,
) -> List[Path]:
    """
    Collect all valid files from dropped/selected files and directories.

    Args:
        input_paths: List of file and directory paths.
        include_subfolders: If True, recurse through directories.
        known_categories: Set of category folder names to avoid re-sorting.

    Returns:
        Deduplicated list of resolved Path objects.
    """
    found_files: Set[Path] = set()
    category_names = {c.lower() for c in (known_categories or set())}

    for p in input_paths:
        try:
            p_resolved = p.resolve()
        except OSError:
            continue

        if not p_resolved.exists():
            continue

        if is_system_or_hidden(p_resolved):
            continue

        if p_resolved.is_file():
            found_files.add(p_resolved)
        elif p_resolved.is_dir():
            # If directory itself is a known category folder, don't scan its root
            if p_resolved.name.lower() in category_names:
                continue

            try:
                if include_subfolders:
                    for root, dirs, files in os.walk(p_resolved):
                        # Filter out hidden or category dirs in-place
                        dirs[:] = [
                            d for d in dirs
                            if not d.startswith(".") and d.lower() not in category_names
                        ]
                        for f in files:
                            file_p = Path(root) / f
                            if not is_system_or_hidden(file_p):
                                found_files.add(file_p.resolve())
                else:
                    for item in p_resolved.iterdir():
                        if item.is_file() and not is_system_or_hidden(item):
                            found_files.add(item.resolve())
            except (PermissionError, OSError):
                continue

    return sorted(list(found_files), key=lambda x: x.name.lower())


def classify_file(
    file_path: Path,
    ext_map: Dict[str, str],
    others_category: str = DEFAULT_OTHERS_CATEGORY,
) -> str:
    """Classify file into a category based on lowercase suffix."""
    suffix = file_path.suffix.lower()
    if not suffix:
        return others_category
    return ext_map.get(suffix, others_category)


def get_destination_path(
    file_path: Path,
    category: str,
    output_mode: str = "next_to_file",
    single_root_folder: Optional[Path] = None,
) -> Path:
    """Calculate the destination path for a given file and category."""
    if output_mode == "single_root" and single_root_folder:
        dest_dir = single_root_folder / category
    else:
        dest_dir = file_path.parent / category

    return dest_dir / file_path.name


def prepare_organization_plan(
    files: List[Path],
    categories: Dict[str, List[str]],
    output_mode: str = "next_to_file",
    single_root_folder: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Generate an organization plan for each file.

    Returns a list of dicts:
    {
        "source": Path,
        "name": str,
        "category": str,
        "destination": Path,
        "selected": bool,
    }
    """
    ext_map = build_extension_map(categories)
    plan = []

    for file_path in files:
        category = classify_file(file_path, ext_map)
        dest_path = get_destination_path(file_path, category, output_mode, single_root_folder)

        plan.append({
            "source": file_path,
            "name": file_path.name,
            "category": category,
            "destination": dest_path,
            "selected": True,
        })

    return plan


def execute_organization(
    plan: List[Dict[str, Any]],
    dry_run: bool = False,
    history_path: Optional[Path] = None,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
    on_item_result: Optional[Callable[[Dict[str, Any], str, Optional[str]], None]] = None,
) -> Dict[str, Any]:
    """
    Execute organization moves safely in sequential order.

    Args:
        plan: List of plan items (can be filtered by 'selected').
        dry_run: If True, simulate without modifying files on disk.
        history_path: Optional path to save undo log.
        on_progress: Callback (current_index, total_count, current_filename).
        on_item_result: Callback (plan_item, status_code, message). Status: 'moved', 'skipped', 'error'.

    Returns:
        Summary dict containing counts and move records.
    """
    items_to_process = [item for item in plan if item.get("selected", True)]
    total = len(items_to_process)

    summary: Dict[str, Any] = {
        "total": total,
        "moved": 0,
        "skipped": 0,
        "errors": 0,
        "moves": [],
        "categories_count": {},
    }

    for idx, item in enumerate(items_to_process, start=1):
        src: Path = item["source"]
        dest: Path = item["destination"]
        category: str = item["category"]

        if on_progress:
            on_progress(idx, total, src.name)

        if not src.exists():
            summary["skipped"] += 1
            if on_item_result:
                on_item_result(item, "skipped", "Source file no longer exists")
            continue

        # If already at destination
        if src.resolve() == dest.resolve():
            summary["skipped"] += 1
            if on_item_result:
                on_item_result(item, "skipped", "File already in destination category")
            continue

        try:
            final_dest = resolve_collision(dest)

            if not dry_run:
                final_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(final_dest))

            summary["moved"] += 1
            summary["categories_count"][category] = summary["categories_count"].get(category, 0) + 1
            summary["moves"].append({
                "source": str(src.resolve()),
                "destination": str(final_dest.resolve()),
                "category": category,
            })

            if on_item_result:
                status_msg = f"{src.name} -> {category}/{final_dest.name}"
                on_item_result(item, "moved", status_msg)

        except (PermissionError, OSError) as e:
            summary["errors"] += 1
            if on_item_result:
                on_item_result(item, "error", f"Failed to move {src.name}: {e}")

    # Persist history log if not in dry-run
    if not dry_run and summary["moves"]:
        save_run(summary["moves"], history_path=history_path)

    return summary
