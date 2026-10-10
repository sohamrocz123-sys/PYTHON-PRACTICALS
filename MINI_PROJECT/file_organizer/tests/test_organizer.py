"""Unit and integration tests for File Organizer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure file_organizer directory is in sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import pytest

from categories import DEFAULT_OTHERS_CATEGORY, build_extension_map, load_categories
from file_organizer import classify_file, organize_directory, scan_directory
from utils import HISTORY_FILENAME, resolve_collision, undo_last_run


@pytest.fixture
def sample_categories():
    return {
        "Images": [".jpg", ".jpeg", ".png", ".gif"],
        "Documents": [".pdf", ".docx", ".txt"],
        "Code": [".py", ".json"],
    }


@pytest.fixture
def ext_map(sample_categories):
    return build_extension_map(sample_categories)


def test_extension_matching(ext_map):
    """Test standard extension classification."""
    assert classify_file(Path("photo.jpg"), ext_map) == "Images"
    assert classify_file(Path("notes.txt"), ext_map) == "Documents"
    assert classify_file(Path("script.py"), ext_map) == "Code"


def test_case_insensitivity(ext_map):
    """Test that uppercase or mixed-case extensions match properly."""
    assert classify_file(Path("PHOTO.JPG"), ext_map) == "Images"
    assert classify_file(Path("IMAGE.PnG"), ext_map) == "Images"
    assert classify_file(Path("REPORT.PDF"), ext_map) == "Documents"
    assert classify_file(Path("SCRIPT.PY"), ext_map) == "Code"


def test_unknown_and_missing_extensions(ext_map):
    """Test files with unknown or missing extensions go to Others."""
    # Unknown extension
    assert classify_file(Path("archive.unknown_xyz"), ext_map) == DEFAULT_OTHERS_CATEGORY
    # No extension
    assert classify_file(Path("README"), ext_map) == DEFAULT_OTHERS_CATEGORY
    assert classify_file(Path("LICENSE"), ext_map) == DEFAULT_OTHERS_CATEGORY


def test_collision_renaming(tmp_path):
    """Test that collision resolution generates a unique name without overwriting."""
    dest_dir = tmp_path / "Documents"
    dest_dir.mkdir(parents=True)
    existing_file = dest_dir / "report.pdf"
    existing_file.write_text("original content")

    # Destination already exists
    resolved = resolve_collision(existing_file)

    assert resolved != existing_file
    assert resolved.parent == dest_dir
    assert resolved.suffix == ".pdf"
    assert resolved.stem.startswith("report_")
    assert not resolved.exists()


def test_dry_run_mode(tmp_path, sample_categories):
    """Test that dry-run mode previews operations without moving files."""
    f1 = tmp_path / "pic.png"
    f2 = tmp_path / "notes.txt"
    f1.write_text("image bytes")
    f2.write_text("text content")

    summary = organize_directory(
        directory=tmp_path,
        categories=sample_categories,
        dry_run=True,
    )

    assert summary["total_scanned"] == 2
    assert summary["total_moved"] == 2
    assert summary["moved_by_category"]["Images"] == 1
    assert summary["moved_by_category"]["Documents"] == 1

    # Files must still exist in root
    assert f1.exists()
    assert f2.exists()

    # Category directories should not have been created
    assert not (tmp_path / "Images").exists()
    assert not (tmp_path / "Documents").exists()

    # History file should not be created
    assert not (tmp_path / HISTORY_FILENAME).exists()


def test_full_organize_and_undo(tmp_path, sample_categories):
    """Test real organization and subsequent undo operation."""
    f1 = tmp_path / "pic.PNG"
    f2 = tmp_path / "notes.txt"
    f3 = tmp_path / "unknown.random"
    f1.write_text("png data")
    f2.write_text("doc data")
    f3.write_text("random data")

    # Organize
    summary = organize_directory(
        directory=tmp_path,
        categories=sample_categories,
        dry_run=False,
    )

    assert summary["total_moved"] == 3
    assert not f1.exists()
    assert not f2.exists()
    assert not f3.exists()

    # Verify moved locations
    dest1 = tmp_path / "Images" / "pic.PNG"
    dest2 = tmp_path / "Documents" / "notes.txt"
    dest3 = tmp_path / DEFAULT_OTHERS_CATEGORY / "unknown.random"

    assert dest1.exists()
    assert dest2.exists()
    assert dest3.exists()

    # History file should exist
    assert (tmp_path / HISTORY_FILENAME).exists()

    # Undo
    undo_summary = undo_last_run(tmp_path)
    assert undo_summary["reverted"] == 3
    assert undo_summary["errors"] == 0

    # Files are back in their root positions
    assert f1.exists()
    assert f2.exists()
    assert f3.exists()
    assert not dest1.exists()
    assert not dest2.exists()
    assert not dest3.exists()


def test_ignore_subdirectories_and_hidden(tmp_path, sample_categories):
    """Test that subfolders and hidden/system files are ignored."""
    subfolder = tmp_path / "ExistingFolder"
    subfolder.mkdir()
    (subfolder / "nested.txt").write_text("nested")

    hidden_file = tmp_path / ".hidden_file.txt"
    hidden_file.write_text("hidden")

    desktop_ini = tmp_path / "desktop.ini"
    desktop_ini.write_text("system")

    valid_file = tmp_path / "doc.pdf"
    valid_file.write_text("valid")

    scanned = scan_directory(tmp_path)
    scanned_names = [p.name for p in scanned]

    assert "doc.pdf" in scanned_names
    assert "ExistingFolder" not in scanned_names
    assert ".hidden_file.txt" not in scanned_names
    assert "desktop.ini" not in scanned_names


def test_custom_config_override(tmp_path):
    """Test loading custom config from JSON."""
    custom_cfg = tmp_path / "custom_config.json"
    custom_cfg.write_text(
        json.dumps({
            "Music": ["mp3", ".wav"],
            "Ebooks": [".EPUB", ".mobi"],
        })
    )

    cats = load_categories(custom_cfg)
    assert "Music" in cats
    assert ".mp3" in cats["Music"]
    assert ".wav" in cats["Music"]
    assert "Ebooks" in cats
    assert ".epub" in cats["Ebooks"]
    assert ".mobi" in cats["Ebooks"]
