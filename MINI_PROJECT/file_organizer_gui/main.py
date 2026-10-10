#!/usr/bin/env python3
"""Entry point for the File Organizer Desktop Application."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure application root directory is in sys.path
APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from ui.app import FileOrganizerApp


def main() -> None:
    """Launch File Organizer GUI."""
    app = FileOrganizerApp()

    # Set icon if asset exists
    icon_ico = APP_ROOT / "assets" / "icon.ico"
    if icon_ico.is_file() and sys.platform == "win32":
        try:
            app.iconbitmap(str(icon_ico))
        except Exception:
            pass

    app.mainloop()


if __name__ == "__main__":
    main()
