#!/usr/bin/env python3
"""File Organizer: A command-line automation script to clean up cluttered directories."""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Enable relative and package imports when run as a standalone script
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from categories import DEFAULT_OTHERS_CATEGORY, build_extension_map, load_categories
from utils import (
    HISTORY_FILENAME,
    is_hidden_or_system_file,
    resolve_collision,
    save_history_entry,
    setup_logger,
    undo_last_run,
)


def scan_directory(directory: Path, ignored_names: Optional[Set[str]] = None) -> List[Path]:
    """
    Scan only the top level of the target directory, excluding directories and ignored files.

    Args:
        directory: The target directory to scan.
        ignored_names: Set of file names (lowercased) to skip.

    Returns:
        List of Path objects for valid files to be categorized.
    """
    if not directory.exists() or not directory.is_dir():
        raise NotADirectoryError(f"Target directory does not exist or is not a directory: {directory}")

    ignored = {n.lower() for n in (ignored_names or set())}
    files_to_organize: List[Path] = []

    try:
        for entry in directory.iterdir():
            # Never process subdirectories (including existing category folders)
            if entry.is_dir():
                continue

            # Skip hidden and system files
            if is_hidden_or_system_file(entry):
                continue

            # Skip script files, logs, or user-ignored files
            if entry.name.lower() in ignored:
                continue

            files_to_organize.append(entry)
    except (PermissionError, OSError) as e:
        logging.getLogger("file_organizer").error(f"Failed scanning directory {directory}: {e}")

    return sorted(files_to_organize, key=lambda p: p.name.lower())


def classify_file(
    file_path: Path,
    ext_to_category: Dict[str, str],
    others_category: str = DEFAULT_OTHERS_CATEGORY,
) -> str:
    """
    Classify a file into a category based on its extension (case-insensitive).

    Args:
        file_path: File path to classify.
        ext_to_category: Mapping of lowercase extension to category name.
        others_category: Default folder for unknown or missing extensions.

    Returns:
        The matched category name.
    """
    ext = file_path.suffix.lower()
    if not ext:
        return others_category
    return ext_to_category.get(ext, others_category)


def move_file(source: Path, destination: Path, dry_run: bool = False) -> Path:
    """
    Move a file to its destination path, creating parent folders and avoiding collisions.

    Args:
        source: Source file path.
        destination: Desired destination file path.
        dry_run: If True, do not execute the physical move.

    Returns:
        The actual destination path used (accounting for collision renaming).
    """
    final_dest = resolve_collision(destination)

    if not dry_run:
        final_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(final_dest))

    return final_dest


def organize_directory(
    directory: Path,
    categories: Optional[Dict[str, List[str]]] = None,
    dry_run: bool = False,
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """
    Organize top-level files in the specified directory into category subfolders.

    Args:
        directory: Path to the directory to organize.
        categories: Category to extensions map.
        dry_run: If True, preview moves without applying changes.
        logger: Optional logger instance.

    Returns:
        Summary dictionary of the organization run.
    """
    if logger is None:
        logger = logging.getLogger("file_organizer")

    if categories is None:
        categories = load_categories()

    ext_map = build_extension_map(categories)

    # Names to ignore (scripts, history log, etc.)
    ignored_names: Set[str] = {
        HISTORY_FILENAME.lower(),
        "file_organizer.py",
        "categories.py",
        "utils.py",
        "config.json",
        Path(__file__).name.lower(),
    }

    files = scan_directory(directory, ignored_names=ignored_names)

    summary: Dict[str, Any] = {
        "total_scanned": len(files),
        "moved_by_category": defaultdict(int),
        "total_moved": 0,
        "skipped": 0,
        "errors": 0,
        "moves": [],  # List of {source, destination, category}
    }

    logger.info(f"Scanning target directory: {directory.resolve()}")
    logger.info(f"Found {len(files)} file(s) to process.")

    for file_path in files:
        category = classify_file(file_path, ext_map)
        target_subfolder = directory / category

        # Target file destination path before collision resolution
        target_path = target_subfolder / file_path.name

        try:
            actual_dest = move_file(file_path, target_path, dry_run=dry_run)
            summary["moved_by_category"][category] += 1
            summary["total_moved"] += 1
            summary["moves"].append(
                {
                    "source": str(file_path.resolve()),
                    "destination": str(actual_dest.resolve()),
                    "category": category,
                }
            )

            action_prefix = "[DRY-RUN] Would move" if dry_run else "Moved"
            logger.debug(f"{action_prefix}: '{file_path.name}' -> '{category}/{actual_dest.name}'")

        except (PermissionError, OSError) as e:
            logger.error(f"Error processing file '{file_path.name}': {e}")
            summary["errors"] += 1

    # Save move log for undo if real moves were made
    if not dry_run and summary["moves"]:
        history_path = save_history_entry(directory, summary["moves"])
        logger.debug(f"Saved run history to: {history_path}")

    return summary


def print_summary(summary: Dict[str, Any], dry_run: bool = False) -> None:
    """Print a clean tabular summary of the organization run."""
    title = "ORGANIZATION SUMMARY (DRY RUN)" if dry_run else "ORGANIZATION SUMMARY"
    print("\n" + "=" * 45)
    print(f" {title}")
    print("=" * 45)
    print(f"Total files processed : {summary['total_scanned']}")
    print(f"Total files moved     : {summary['total_moved']}")
    print(f"Skipped / unchanged   : {summary['skipped']}")
    print(f"Errors encountered    : {summary['errors']}")
    print("-" * 45)
    print("Breakdown by category:")

    moved_by_cat = summary.get("moved_by_category", {})
    if moved_by_cat:
        for cat in sorted(moved_by_cat.keys()):
            count = moved_by_cat[cat]
            print(f"  - {cat:<15}: {count} file(s)")
    else:
        print("  (No files were moved)")
    print("=" * 45 + "\n")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="file_organizer",
        description="Clean up cluttered directories by sorting files into category subfolders.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path.home() / "Downloads",
        help="Target directory path to organize (default: current user's Downloads folder)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be moved without changing anything on disk.",
    )
    parser.add_argument(
        "--undo",
        action="store_true",
        help="Revert the last organization run using the saved history log.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable detailed logging output (DEBUG level).",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=None,
        help="Optional path to a custom config.json file to override categories.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for File Organizer."""
    args = parse_args(argv)
    logger = setup_logger(verbose=args.verbose)

    target_dir: Path = args.path.resolve()

    if not target_dir.exists():
        logger.error(f"Target directory does not exist: {target_dir}")
        return 1

    if not target_dir.is_dir():
        logger.error(f"Target path is not a directory: {target_dir}")
        return 1

    # Undo Mode
    if args.undo:
        logger.info(f"Attempting to revert previous run in: {target_dir}")
        undo_summary = undo_last_run(target_dir, logger=logger)
        print("\n" + "=" * 40)
        print(" UNDO SUMMARY")
        print("=" * 40)
        print(f"Files reverted : {undo_summary['reverted']}")
        print(f"Files missing  : {undo_summary['missing']}")
        print(f"Errors         : {undo_summary['errors']}")
        print("=" * 40 + "\n")
        return 0 if undo_summary["errors"] == 0 else 1

    # Load custom or default config
    config_file = args.config
    if config_file is None:
        local_config = CURRENT_DIR / "config.json"
        if local_config.is_file():
            config_file = local_config

    categories = load_categories(config_file)
    if args.verbose:
        logger.debug(f"Loaded {len(categories)} categories: {', '.join(categories.keys())}")

    if args.dry_run:
        logger.info("Running in DRY-RUN mode. No files will be modified or moved.")

    summary = organize_directory(
        directory=target_dir,
        categories=categories,
        dry_run=args.dry_run,
        logger=logger,
    )

    print_summary(summary, dry_run=args.dry_run)
    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
