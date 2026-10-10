"""Folder watcher service using watchdog for automatic background organization."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Set

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from core.organizer import execute_organization, is_system_or_hidden, prepare_organization_plan

LOGGER = logging.getLogger("file_organizer_watcher")

# Temporary download extensions to ignore until completed
INCOMPLETE_EXTENSIONS: Set[str] = {
    ".crdownload",  # Chrome / Chromium
    ".part",        # Firefox
    ".tmp",         # Generic temp
    ".download",    # Safari
    ".opdownload",  # Opera
}


def wait_until_file_stable(file_path: Path, max_wait_seconds: int = 15, interval: float = 1.0) -> bool:
    """
    Check if a file has finished writing by verifying stable file size and read access.

    Args:
        file_path: Target path to monitor.
        max_wait_seconds: Maximum time to wait for completion.
        interval: Delay between consecutive size checks.

    Returns:
        True if the file size is non-zero and stable; False if timed out or inaccessible.
    """
    if not file_path.is_file():
        return False

    elapsed = 0.0
    last_size = -1

    while elapsed < max_wait_seconds:
        if not file_path.exists():
            return False

        # If extension is still a known download temp extension, keep waiting
        if file_path.suffix.lower() in INCOMPLETE_EXTENSIONS:
            time.sleep(interval)
            elapsed += interval
            continue

        try:
            current_size = file_path.stat().st_size
            # If size hasn't changed since last check and size > 0
            if current_size == last_size and current_size > 0:
                # Attempt to open file to ensure write lock released
                try:
                    with open(file_path, "rb") as _:
                        return True
                except (PermissionError, OSError):
                    pass
            last_size = current_size
        except OSError:
            pass

        time.sleep(interval)
        elapsed += interval

    return False


class WatcherEventHandler(FileSystemEventHandler):
    """Event handler that detects new or modified files and organizes them."""

    def __init__(
        self,
        watch_dir: Path,
        config_provider: Callable[[], Dict[str, Any]],
        on_event: Optional[Callable[[str, str], None]] = None,
    ):
        super().__init__()
        self.watch_dir = watch_dir.resolve()
        self.config_provider = config_provider
        self.on_event = on_event
        self._processing_paths: Set[Path] = set()
        self._lock = threading.Lock()

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle_file(Path(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        if hasattr(event, "dest_path"):
            self._handle_file(Path(event.dest_path))

    def _handle_file(self, path: Path) -> None:
        if path.is_dir():
            return

        resolved = path.resolve()
        if is_system_or_hidden(resolved):
            return

        if resolved.suffix.lower() in INCOMPLETE_EXTENSIONS:
            return

        with self._lock:
            if resolved in self._processing_paths:
                return
            self._processing_paths.add(resolved)

        # Process in separate background thread to avoid blocking the watchdog observer loop
        threading.Thread(
            target=self._process_file_thread,
            args=(resolved,),
            daemon=True,
        ).start()

    def _process_file_thread(self, file_path: Path) -> None:
        try:
            # Wait until write finishes
            is_ready = wait_until_file_stable(file_path)
            if not is_ready:
                return

            config = self.config_provider()
            categories = config.get("categories", {})
            output_mode = config.get("output_mode", "next_to_file")
            single_root = Path(config.get("single_root_folder", "")) if config.get("single_root_folder") else None

            plan = prepare_organization_plan(
                files=[file_path],
                categories=categories,
                output_mode=output_mode,
                single_root_folder=single_root,
            )

            if plan:
                result = execute_organization(plan, dry_run=False)
                if result["moved"] > 0 and self.on_event:
                    first_move = result["moves"][0]
                    self.on_event("moved", f"{file_path.name} -> {first_move['category']}")

        except Exception as e:
            LOGGER.error(f"Error organizing watched file {file_path}: {e}")
            if self.on_event:
                self.on_event("error", f"{file_path.name}: {e}")
        finally:
            with self._lock:
                self._processing_paths.discard(file_path)


class FolderWatcher:
    """Manages the background watchdog observer thread."""

    def __init__(
        self,
        watch_dir: Path,
        config_provider: Callable[[], Dict[str, Any]],
        on_event: Optional[Callable[[str, str], None]] = None,
    ):
        self.watch_dir = watch_dir
        self.config_provider = config_provider
        self.on_event = on_event
        self._observer: Optional[Observer] = None
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> bool:
        if self._is_running:
            return True

        if not self.watch_dir.is_dir():
            return False

        try:
            handler = WatcherEventHandler(
                watch_dir=self.watch_dir,
                config_provider=self.config_provider,
                on_event=self.on_event,
            )
            self._observer = Observer()
            self._observer.schedule(handler, str(self.watch_dir), recursive=False)
            self._observer.start()
            self._is_running = True
            return True
        except Exception as e:
            LOGGER.error(f"Failed starting FolderWatcher: {e}")
            self._is_running = False
            return False

    def stop(self) -> None:
        if self._observer and self._is_running:
            try:
                self._observer.stop()
                self._observer.join(timeout=2.0)
            except Exception:
                pass
            self._observer = None
        self._is_running = False
