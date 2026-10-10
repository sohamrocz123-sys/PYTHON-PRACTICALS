"""Main application window for File Organizer GUI."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
import customtkinter as ctk
from tkinter import messagebox
from tkinterdnd2 import TkinterDnD

from core.categories import DEFAULT_SETTINGS, load_config, save_config
from core.organizer import execute_organization, prepare_organization_plan, scan_input_paths
from core.undo import get_history_count, undo_last_run
from core.watcher import FolderWatcher
from ui.drop_zone import DropZone
from ui.preview_table import PreviewTable
from ui.settings_window import SettingsWindow


class FileOrganizerApp(ctk.CTk, TkinterDnD.DnDWrapper):
    """File Organizer Desktop Application."""

    def __init__(self):
        super().__init__()
        # Initialize tkdnd extension
        self.TkdndVersion = TkinterDnD._require(self)

        # App Configuration
        self.config = load_config()
        self.appearance_mode = self.config.get("theme_mode", "Dark")
        ctk.set_appearance_mode(self.appearance_mode)
        ctk.set_default_color_theme("blue")

        # Window settings
        self.title("File Organizer")
        self.geometry("940x700")
        self.minsize(720, 520)

        # State
        self.is_processing = False
        self.folder_watcher: Optional[FolderWatcher] = None
        self.pending_plan: List[Dict[str, Any]] = []

        self._build_ui()
        self._init_watcher()

    def _build_ui(self) -> None:
        self.grid_rowconfigure(2, weight=1)  # Center area expands
        self.grid_columnconfigure(0, weight=1)

        # 1. Header Frame
        self._build_header()

        # 2. Progress & Status bar
        self._build_status_bar()

        # 3. Center workspace (DropZone and PreviewTable switcher)
        self._build_center_workspace()

        # 4. Results / Activity Log
        self._build_results_log()

        # 5. Bottom Action Bar
        self._build_bottom_bar()

    def _build_header(self) -> None:
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent", height=50)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(12, 4))
        self.header_frame.grid_columnconfigure(1, weight=1)

        # Title & Logo
        title_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_frame.pack(side="left")

        self.title_label = ctk.CTkLabel(
            title_frame,
            text="🗂️ File Organizer",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.title_label.pack(side="left", padx=(0, 10))

        # Mode Selector
        self.mode_var = ctk.StringVar(
            value="auto" if self.config.get("auto_sort_on_drop", True) else "preview"
        )
        self.mode_selector = ctk.CTkSegmentedButton(
            self.header_frame,
            values=["Auto-sort on drop", "Preview first"],
            command=self._on_mode_switched,
        )
        self.mode_selector.set(
            "Auto-sort on drop" if self.mode_var.get() == "auto" else "Preview first"
        )
        self.mode_selector.pack(side="left", padx=16)

        # Theme toggle switch
        self.theme_switch = ctk.CTkSwitch(
            self.header_frame,
            text="Dark Mode",
            command=self._toggle_theme,
        )
        if self.appearance_mode == "Dark":
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()
            self.theme_switch.configure(text="Light Mode")
        self.theme_switch.pack(side="right", padx=(8, 0))

    def _build_status_bar(self) -> None:
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent", height=32)
        self.status_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(2, 6))
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Ready. Drop files or folders below.",
            font=ctk.CTkFont(size=12),
            text_color=("#64748B", "#94A3B8"),
            anchor="w",
        )
        self.status_label.pack(side="left")

        self.progress_bar = ctk.CTkProgressBar(self.status_frame, width=220, height=10)
        self.progress_bar.set(0)
        self.progress_bar.pack(side="right")

    def _build_center_workspace(self) -> None:
        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=4)
        self.center_frame.grid_columnconfigure(0, weight=1)
        self.center_frame.grid_rowconfigure(0, weight=1)

        # Drop Zone
        self.drop_zone = DropZone(
            self.center_frame,
            on_paths_received=self._handle_input_paths,
        )

        # Preview Table
        self.preview_table = PreviewTable(
            self.center_frame,
            on_organize_selected=self._execute_preview_batch,
            on_clear=self._clear_preview_mode,
        )

        # Initially show drop zone
        self.drop_zone.grid(row=0, column=0, sticky="nsew")

    def _build_results_log(self) -> None:
        self.log_frame = ctk.CTkFrame(self, corner_radius=10, height=130)
        self.log_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(6, 8))
        self.log_frame.grid_columnconfigure(0, weight=1)

        lbl_log = ctk.CTkLabel(
            self.log_frame,
            text="Activity Log",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#64748B", "#94A3B8"),
            anchor="w",
        )
        lbl_log.pack(anchor="w", padx=10, pady=(4, 0))

        self.log_text = ctk.CTkTextbox(
            self.log_frame,
            height=90,
            font=ctk.CTkFont(family="Consolas", size=11),
            activate_scrollbars=True,
        )
        self.log_text.pack(fill="x", padx=8, pady=(2, 6))

    def _build_bottom_bar(self) -> None:
        self.bottom_bar = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent", height=44)
        self.bottom_bar.grid(row=4, column=0, sticky="ew", padx=20, pady=(4, 16))

        # Watch folder toggle and status
        self.watch_btn = ctk.CTkButton(
            self.bottom_bar,
            text="👁️ Watch: Off",
            width=130,
            height=34,
            corner_radius=8,
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#1E293B", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._toggle_watch_folder,
        )
        self.watch_btn.pack(side="left", padx=(0, 8))

        self.settings_btn = ctk.CTkButton(
            self.bottom_bar,
            text="⚙️ Settings",
            width=110,
            height=34,
            corner_radius=8,
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#1E293B", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            command=self._open_settings,
        )
        self.settings_btn.pack(side="left", padx=4)

        self.open_output_btn = ctk.CTkButton(
            self.bottom_bar,
            text="📂 Open Output Folder",
            width=160,
            height=34,
            corner_radius=8,
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#1E293B", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            command=self._open_output_folder,
        )
        self.open_output_btn.pack(side="left", padx=4)

        # Undo Button
        self.undo_btn = ctk.CTkButton(
            self.bottom_bar,
            text="↩️ Undo Last Run",
            width=140,
            height=34,
            corner_radius=8,
            fg_color=("#475569", "#475569"),
            hover_color=("#334155", "#334155"),
            command=self._handle_undo,
        )
        self.undo_btn.pack(side="right")
        self._update_undo_button_state()

    # --- Mode & Theme Logic ---
    def _toggle_theme(self) -> None:
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("Dark")
            self.theme_switch.configure(text="Dark Mode")
            self.config["theme_mode"] = "Dark"
        else:
            ctk.set_appearance_mode("Light")
            self.theme_switch.configure(text="Light Mode")
            self.config["theme_mode"] = "Light"
        save_config(self.config)

    def _on_mode_switched(self, selected_mode: str) -> None:
        if selected_mode == "Auto-sort on drop":
            self.mode_var.set("auto")
            self.config["auto_sort_on_drop"] = True
            self.drop_zone.grid(row=0, column=0, sticky="nsew")
            self.preview_table.grid_forget()
        else:
            self.mode_var.set("preview")
            self.config["auto_sort_on_drop"] = False
            if self.pending_plan:
                self.preview_table.grid(row=0, column=0, sticky="nsew")
                self.drop_zone.grid_forget()
        save_config(self.config)

    def _open_settings(self) -> None:
        SettingsWindow(self, config=self.config, on_save_callback=self._on_settings_saved)

    def _on_settings_saved(self, new_config: Dict[str, Any]) -> None:
        self.config = new_config
        self.mode_var.set("auto" if new_config.get("auto_sort_on_drop", True) else "preview")
        self.mode_selector.set("Auto-sort on drop" if self.mode_var.get() == "auto" else "Preview first")
        self._log_message("Settings updated and saved successfully.")

    def _open_output_folder(self) -> None:
        output_mode = self.config.get("output_mode", "next_to_file")
        if output_mode == "single_root" and self.config.get("single_root_folder"):
            target_dir = Path(self.config["single_root_folder"])
        else:
            target_dir = Path.home() / "Downloads"

        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(target_dir))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(target_dir)])
            else:
                subprocess.Popen(["xdg-open", str(target_dir)])
        except Exception as e:
            messagebox.showerror("Error Opening Folder", f"Could not open {target_dir}: {e}")

    # --- Watch Folder Support ---
    def _init_watcher(self) -> None:
        watch_path_str = self.config.get("watch_folder_path") or str(Path.home() / "Downloads")
        self.config["watch_folder_path"] = watch_path_str
        watch_path = Path(watch_path_str)

        self.folder_watcher = FolderWatcher(
            watch_dir=watch_path,
            config_provider=lambda: self.config,
            on_event=self._on_watcher_event,
        )

        if self.config.get("watch_enabled", False):
            self._start_watcher()

    def _start_watcher(self) -> None:
        if self.folder_watcher and self.folder_watcher.start():
            watch_dir_name = Path(self.config["watch_folder_path"]).name
            self.watch_btn.configure(
                text=f"🟢 Watching: {watch_dir_name}",
                fg_color=("#16A34A", "#15803D"),
                hover_color=("#15803D", "#166534"),
            )
            self._log_message(f"Folder watcher active on: {self.config['watch_folder_path']}")

    def _stop_watcher(self) -> None:
        if self.folder_watcher:
            self.folder_watcher.stop()
            self.watch_btn.configure(
                text="👁️ Watch: Off",
                fg_color=("#E2E8F0", "#334155"),
                hover_color=("#CBD5E1", "#475569"),
            )
            self._log_message("Folder watcher stopped.")

    def _toggle_watch_folder(self) -> None:
        if self.folder_watcher and self.folder_watcher.is_running:
            self._stop_watcher()
            self.config["watch_enabled"] = False
        else:
            self._start_watcher()
            self.config["watch_enabled"] = True
        save_config(self.config)

    def _on_watcher_event(self, event_type: str, message: str) -> None:
        prefix = "[Watch Move]" if event_type == "moved" else "[Watch Error]"
        self.after(0, lambda: self._log_message(f"{prefix} {message}"))
        self.after(0, self._update_undo_button_state)

    # --- File Organization Workflow ---
    def _handle_input_paths(self, input_paths: List[Path]) -> None:
        if self.is_processing:
            messagebox.showwarning("Busy", "An organization task is already running.")
            return

        # Scan files in background
        threading.Thread(
            target=self._scan_and_dispatch,
            args=(input_paths,),
            daemon=True,
        ).start()

    def _scan_and_dispatch(self, input_paths: List[Path]) -> None:
        self.after(0, lambda: self.status_label.configure(text="Scanning items..."))
        categories = self.config.get("categories", {})
        include_subfolders = self.config.get("include_subfolders", False)

        files = scan_input_paths(
            input_paths=input_paths,
            include_subfolders=include_subfolders,
            known_categories=set(categories.keys()),
        )

        if not files:
            self.after(0, lambda: self._log_message("No eligible files found to organize."))
            self.after(0, lambda: self.status_label.configure(text="Ready. No files to process."))
            return

        # Prepare plan
        output_mode = self.config.get("output_mode", "next_to_file")
        single_root = Path(self.config.get("single_root_folder", "")) if self.config.get("single_root_folder") else None

        plan = prepare_organization_plan(
            files=files,
            categories=categories,
            output_mode=output_mode,
            single_root_folder=single_root,
        )

        if self.mode_var.get() == "auto":
            # Check large batch confirmation (> 200 files)
            if len(plan) > 200:
                proceed = messagebox.askyesno(
                    "Large Batch Confirmation",
                    f"You dropped {len(plan)} files. Proceed with organizing?",
                    parent=self,
                )
                if not proceed:
                    self.after(0, lambda: self.status_label.configure(text="Organization canceled by user."))
                    return
            self._execute_moves_async(plan)
        else:
            # Preview first mode
            self.pending_plan = plan
            self.after(0, lambda: self._show_preview_table(plan))

    def _show_preview_table(self, plan: List[Dict[str, Any]]) -> None:
        self.preview_table.load_plan(plan)
        self.drop_zone.grid_forget()
        self.preview_table.grid(row=0, column=0, sticky="nsew")
        self.status_label.configure(text=f"Loaded {len(plan)} file(s) for preview.")

    def _clear_preview_mode(self) -> None:
        self.pending_plan = []
        self.preview_table.grid_forget()
        self.drop_zone.grid(row=0, column=0, sticky="nsew")
        self.status_label.configure(text="Ready.")

    def _execute_preview_batch(self, selected_items: List[Dict[str, Any]]) -> None:
        if not selected_items:
            messagebox.showinfo("No Files Selected", "Please select at least one file to organize.", parent=self)
            return

        if len(selected_items) > 200:
            proceed = messagebox.askyesno(
                "Large Batch Confirmation",
                f"You selected {len(selected_items)} files. Proceed with organizing?",
                parent=self,
            )
            if not proceed:
                return

        self._execute_moves_async(selected_items)

    def _execute_moves_async(self, plan_items: List[Dict[str, Any]]) -> None:
        self.is_processing = True
        self.progress_bar.set(0)
        self.status_label.configure(text=f"Organizing {len(plan_items)} files...")

        threading.Thread(
            target=self._run_move_task,
            args=(plan_items,),
            daemon=True,
        ).start()

    def _run_move_task(self, plan_items: List[Dict[str, Any]]) -> None:
        total = len(plan_items)

        def on_progress(idx: int, tot: int, name: str) -> None:
            pct = idx / tot
            self.after(0, lambda i=idx, t=tot, n=name, p=pct: self._update_progress(i, t, n, p))

        def on_result(item: Dict[str, Any], status: str, msg: Optional[str]) -> None:
            if status == "moved":
                self.after(0, lambda: self._log_message(f"[Moved] {msg}"))
            elif status == "skipped":
                self.after(0, lambda: self._log_message(f"[Skipped] {item['name']}: {msg}"))
            elif status == "error":
                self.after(0, lambda: self._log_message(f"[Error] {msg}"))

        summary = execute_organization(
            plan=plan_items,
            dry_run=False,
            on_progress=on_progress,
            on_item_result=on_result,
        )

        self.after(0, lambda: self._on_organization_finished(summary))

    def _update_progress(self, current: int, total: int, filename: str, pct: float) -> None:
        self.progress_bar.set(pct)
        self.status_label.configure(text=f"Organizing ({current}/{total}): {filename}")

    def _on_organization_finished(self, summary: Dict[str, Any]) -> None:
        self.is_processing = False
        self.progress_bar.set(1.0)
        self.status_label.configure(text="Finished.")

        # Revert to drop zone if in preview mode
        self._clear_preview_mode()
        self._update_undo_button_state()

        # Toast / Alert Summary
        summary_msg = f"{summary['moved']} moved, {summary['skipped']} skipped, {summary['errors']} errors"
        self._log_message(f"--- Summary: {summary_msg} ---")
        messagebox.showinfo(
            "Organization Complete",
            f"Run Finished:\n\n• Moved: {summary['moved']}\n• Skipped: {summary['skipped']}\n• Errors: {summary['errors']}",
            parent=self,
        )

    # --- Undo Support ---
    def _update_undo_button_state(self) -> None:
        history_cnt = get_history_count()
        if history_cnt > 0:
            self.undo_btn.configure(
                state="normal",
                text=f"↩️ Undo Last Run ({history_cnt})",
                fg_color=("#2563EB", "#1D4ED8"),
                hover_color=("#1D4ED8", "#1E40AF"),
            )
        else:
            self.undo_btn.configure(
                state="disabled",
                text="↩️ Undo Last Run",
                fg_color=("#94A3B8", "#475569"),
            )

    def _handle_undo(self) -> None:
        if self.is_processing:
            return

        confirm = messagebox.askyesno(
            "Confirm Undo",
            "Are you sure you want to revert the most recent organization run?",
            parent=self,
        )
        if not confirm:
            return

        self.status_label.configure(text="Reverting previous run...")

        def on_step(src: str, dest: str) -> None:
            self.after(0, lambda: self._log_message(f"[Undo] Restored: {Path(src).name} -> {Path(dest).parent.name}"))

        summary = undo_last_run(on_step=on_step)
        self._update_undo_button_state()
        self.status_label.configure(text="Undo completed.")

        undo_msg = f"Undo finished: {summary['reverted']} reverted, {summary['missing']} missing, {summary['errors']} errors"
        self._log_message(f"--- {undo_msg} ---")
        messagebox.showinfo(
            "Undo Complete",
            f"Undo Result:\n\n• Reverted: {summary['reverted']}\n• Missing: {summary['missing']}\n• Errors: {summary['errors']}",
            parent=self,
        )

    def _log_message(self, message: str) -> None:
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
