"""Drop zone widget with drag-and-drop support, visual feedback, and fallback file picker."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional
import customtkinter as ctk
from tkinter import filedialog
from tkinterdnd2 import DND_FILES


class DropZone(ctk.CTkFrame):
    """Interactive drag and drop zone with hover highlights and file browse fallback."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_paths_received: Callable[[List[Path]], None],
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=16,
            border_width=2,
            border_color=("#94A3B8", "#475569"),
            fg_color=("#F1F5F9", "#1E293B"),
            **kwargs,
        )
        self.on_paths_received = on_paths_received
        self._is_dragging = False

        self._build_ui()
        self._setup_dnd()

    def _build_ui(self) -> None:
        self.grid_rowconfigure((0, 1, 2, 3), weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Center content frame
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Icon Label
        self.icon_label = ctk.CTkLabel(
            self.content_frame,
            text="📥",
            font=("Segoe UI Emoji", 48),
        )
        self.icon_label.pack(pady=(0, 6))

        # Main Title
        self.title_label = ctk.CTkLabel(
            self.content_frame,
            text="Drop files or folders here",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        )
        self.title_label.pack(pady=(0, 4))

        # Subtitle
        self.subtitle_label = ctk.CTkLabel(
            self.content_frame,
            text="They will be instantly sorted into category subfolders",
            font=ctk.CTkFont(size=13),
            text_color=("#64748B", "#94A3B8"),
        )
        self.subtitle_label.pack(pady=(0, 18))

        # Action Buttons frame
        self.btn_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.btn_frame.pack()

        self.browse_files_btn = ctk.CTkButton(
            self.btn_frame,
            text="Browse Files...",
            width=130,
            height=34,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_browse_files,
        )
        self.browse_files_btn.pack(side="left", padx=6)

        self.browse_folder_btn = ctk.CTkButton(
            self.btn_frame,
            text="Browse Folder...",
            width=130,
            height=34,
            corner_radius=8,
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#1E293B", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_browse_folder,
        )
        self.browse_folder_btn.pack(side="left", padx=6)

    def _setup_dnd(self) -> None:
        """Register drag and drop listeners on the frame and inner elements."""
        widgets = [
            self,
            self.content_frame,
            self.icon_label,
            self.title_label,
            self.subtitle_label,
            self.btn_frame,
        ]

        for w in widgets:
            try:
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<DropEnter>>", self._on_drag_enter)
                w.dnd_bind("<<DropLeave>>", self._on_drag_leave)
                w.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass

    def _on_drag_enter(self, event) -> None:
        self.configure(
            border_color=("#2563EB", "#38BDF8"),
            fg_color=("#EFF6FF", "#1E3A8A"),
        )
        self.title_label.configure(text="Release to drop files here!")

    def _on_drag_leave(self, event) -> None:
        self.configure(
            border_color=("#94A3B8", "#475569"),
            fg_color=("#F1F5F9", "#1E293B"),
        )
        self.title_label.configure(text="Drop files or folders here")

    def _on_drop(self, event) -> None:
        self._on_drag_leave(event)
        raw_data = event.data
        if not raw_data:
            return

        # Split tricky paths containing spaces and curly brackets
        try:
            raw_paths = self.tk.splitlist(raw_data)
        except Exception:
            raw_paths = [raw_data]

        paths: List[Path] = []
        for p_str in raw_paths:
            cleaned = p_str.strip().strip('"').strip("'")
            if cleaned:
                paths.append(Path(cleaned))

        if paths:
            self.on_paths_received(paths)

    def _on_browse_files(self) -> None:
        selected = filedialog.askopenfilenames(title="Select Files to Organize")
        if selected:
            self.on_paths_received([Path(p) for p in selected])

    def _on_browse_folder(self) -> None:
        selected = filedialog.askdirectory(title="Select Folder to Organize")
        if selected:
            self.on_paths_received([Path(selected)])
