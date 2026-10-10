"""Unit tests for the File Organizer core logic (zero UI dependencies)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure application root directory is in sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import pytest

from core.categories import (
    DEFAULT_CATEGORIES,
    DEFAULT_OTHERS_CATEGORY,
    build_extension_map,
    load_config,
    normalize_extension,
)
from core.organizer import (
    classify_file,
    execute_organization,
    prepare_organization_plan,
    scan_input_paths,
)
from core.undo import load_history, resolve_collision, undo_last_run


@pytest.fixture
def ext_map():
    return build_extension_map(DEFAULT_CATEGORIES)


# 1. Extension matching
def test_extension_matching(ext_map):
    """Test classification for standard extensions."""
    assert classify_file(Path("vacation.png"), ext_map) == "Images"
    assert classify_file(Path("contract.pdf"), ext_map) == "Documents"
    assert classify_file(Path("archive.zip"), ext_map) == "Archives"
    assert classify_file(Path("setup.exe"), ext_map) == "Installers"
    assert classify_file(Path("video.mp4"), ext_map) == "Videos"
    assert classify_file(Path("audio.mp3"), ext_map) == "Audio"
    assert classify_file(Path("script.py"), ext_map) == "Code"


# 2. Case-insensitivity
def test_case_insensitivity(ext_map):
    """Test case-insensitive extension classification."""
    assert classify_file(Path("PHOTO.JPG"), ext_map) == "Images"
    assert classify_file(Path("DOCUMENT.Docx"), ext_map) == "Documents"
    assert classify_file(Path("MUSIC.MP3"), ext_map) == "Audio"
    assert classify_file(Path("PROJECT.JSON"), ext_map) == "Code"


# 3. Unknown and missing extensions
def test_unknown_and_missing_extensions(ext_map):
    """Test files with unknown or missing extensions route to Others."""
    assert classify_file(Path("file.xyz_unknown"), ext_map) == DEFAULT_OTHERS_CATEGORY
    assert classify_file(Path("README"), ext_map) == DEFAULT_OTHERS_CATEGORY
    assert classify_file(Path("Makefile"), ext_map) == DEFAULT_OTHERS_CATEGORY


# 4. Collision renaming
def test_collision_renaming(tmp_path):
    """Test destination collision resolution by appending timestamp/counter."""
    dest_dir = tmp_path / "Documents"
    dest_dir.mkdir(parents=True)
    existing_file = dest_dir / "report.pdf"
    existing_file.write_text("v1")

    resolved = resolve_collision(existing_file)

    assert resolved != existing_file
    assert resolved.parent == dest_dir
    assert resolved.suffix == ".pdf"
    assert resolved.stem.startswith("report_")
    assert not resolved.exists()


# 5. Dry-run mode
def test_dry_run_mode(tmp_path):
    """Test that dry-run mode does not move files or alter directories on disk."""
    f1 = tmp_path / "dry_pic.png"
    f2 = tmp_path / "dry_notes.txt"
    f1.write_text("png")
    f2.write_text("txt")

    files = [f1, f2]
    plan = prepare_organization_plan(files, DEFAULT_CATEGORIES, output_mode="next_to_file")

    summary = execute_organization(plan, dry_run=True)

    assert summary["moved"] == 2
    assert summary["errors"] == 0

    # Files must still exist in their original locations
    assert f1.exists()
    assert f2.exists()
    assert not (tmp_path / "Images").exists()
    assert not (tmp_path / "Documents").exists()


# 6. Full execution and Undo
def test_execution_and_undo(tmp_path):
    """Test full execution followed by atomic undo restoration."""
    f1 = tmp_path / "pic.jpg"
    f2 = tmp_path / "sheet.xlsx"
    f3 = tmp_path / "mystery.bin"
    f1.write_text("jpg data")
    f2.write_text("sheet data")
    f3.write_text("bin data")

    history_log = tmp_path / ".test_history.json"

    files = [f1, f2, f3]
    plan = prepare_organization_plan(files, DEFAULT_CATEGORIES, output_mode="next_to_file")

    # Organize
    summary = execute_organization(plan, dry_run=False, history_path=history_log)
    assert summary["moved"] == 3
    assert not f1.exists()
    assert not f2.exists()
    assert not f3.exists()

    dest1 = tmp_path / "Images" / "pic.jpg"
    dest2 = tmp_path / "Documents" / "sheet.xlsx"
    dest3 = tmp_path / DEFAULT_OTHERS_CATEGORY / "mystery.bin"
    assert dest1.exists()
    assert dest2.exists()
    assert dest3.exists()

    # Revert via undo
    undo_summary = undo_last_run(history_path=history_log)
    assert undo_summary["reverted"] == 3
    assert undo_summary["errors"] == 0

    # Original files are restored
    assert f1.exists()
    assert f2.exists()
    assert f3.exists()
    assert not dest1.exists()
    assert not dest2.exists()
    assert not dest3.exists()


# 7. Subfolder scanning vs single-level
def test_subfolder_scanning(tmp_path):
    """Test scanning with and without recursion."""
    top_file = tmp_path / "top.txt"
    top_file.write_text("top")

    sub_dir = tmp_path / "Sub"
    sub_dir.mkdir()
    sub_file = sub_dir / "nested.txt"
    sub_file.write_text("nested")

    # Non-recursive scan
    scanned_non_rec = scan_input_paths([tmp_path], include_subfolders=False)
    assert top_file in scanned_non_rec
    assert sub_file not in scanned_non_rec

    # Recursive scan
    scanned_rec = scan_input_paths([tmp_path], include_subfolders=True)
    assert top_file in scanned_rec
    assert sub_file in scanned_rec
