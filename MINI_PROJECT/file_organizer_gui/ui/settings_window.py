"""Settings dialog for categories, output folder modes, and application preferences."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Callable, Dict, List
import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.categories import DEFAULT_CATEGORIES, DEFAULT_SETTINGS, normalize_extension, reset_config_to_defaults, save_config


class SettingsWindow(ctk.CTkToplevel):
    """Configuration and category management modal window."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        config: Dict[str, Any],
        on_save_callback: Callable[[Dict[str, Any]], None],
    ):
        super().__init__(master)
        self.title("File Organizer - Settings")
        self.geometry("680x620")
        self.minsize(640, 560)
        self.grab_set()  # Make modal

        self.config_data = copy.deepcopy(config)
        self.on_save_callback = on_save_callback

        self._build_ui()
        self._populate_fields()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Tabview for organizing settings
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=16, pady=(12, 8))

        self.tab_general = self.tabview.add("General & Output")
        self.tab_categories = self.tabview.add("Categories & Extensions")

        self._build_general_tab()
        self._build_categories_tab()

        # Bottom actions
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 16))

        self.reset_btn = ctk.CTkButton(
            self.bottom_frame,
            text="Reset to Defaults",
            fg_color=("#EF4444", "#DC2626"),
            hover_color=("#DC2626", "#B91C1C"),
            width=130,
            command=self._on_reset_defaults,
        )
        self.reset_btn.pack(side="left")

        self.save_btn = ctk.CTkButton(
            self.bottom_frame,
            text="Save & Apply",
            width=130,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_save,
        )
        self.save_btn.pack(side="right", padx=(8, 0))

        self.cancel_btn = ctk.CTkButton(
            self.bottom_frame,
            text="Cancel",
            width=90,
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#1E293B", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            command=self.destroy,
        )
        self.cancel_btn.pack(side="right")

    def _build_general_tab(self) -> None:
        tab = self.tab_general
        tab.grid_columnconfigure(0, weight=1)

        # Output Mode Section
        lbl_out = ctk.CTkLabel(
            tab,
            text="Destination Output Mode",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        lbl_out.pack(fill="x", padx=12, pady=(12, 6))

        self.output_mode_var = ctk.StringVar(value="next_to_file")

        self.radio_next_to_file = ctk.CTkRadioButton(
            tab,
            text="Sort into subfolders next to each file's current location",
            variable=self.output_mode_var,
            value="next_to_file",
            command=self._on_output_mode_changed,
        )
        self.radio_next_to_file.pack(anchor="w", padx=20, pady=4)

        self.radio_single_root = ctk.CTkRadioButton(
            tab,
            text="Sort everything into a single designated root folder",
            variable=self.output_mode_var,
            value="single_root",
            command=self._on_output_mode_changed,
        )
        self.radio_single_root.pack(anchor="w", padx=20, pady=4)

        # Single Root Folder Picker Frame
        self.single_root_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.single_root_frame.pack(fill="x", padx=36, pady=(4, 12))

        self.root_folder_entry = ctk.CTkEntry(
            self.single_root_frame,
            placeholder_text="Select destination root directory...",
            width=360,
        )
        self.root_folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.browse_root_btn = ctk.CTkButton(
            self.single_root_frame,
            text="Browse...",
            width=80,
            command=self._browse_single_root,
        )
        self.browse_root_btn.pack(side="left")

        # Behavior Section
        lbl_beh = ctk.CTkLabel(
            tab,
            text="Behavior & Scanning",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        lbl_beh.pack(fill="x", padx=12, pady=(16, 6))

        self.auto_sort_var = ctk.BooleanVar(value=True)
        self.chk_auto_sort = ctk.CTkCheckBox(
            tab,
            text="Auto-sort immediately on drop (disables Preview mode by default)",
            variable=self.auto_sort_var,
        )
        self.chk_auto_sort.pack(anchor="w", padx=20, pady=4)

        self.include_subfolders_var = ctk.BooleanVar(value=False)
        self.chk_include_sub = ctk.CTkCheckBox(
            tab,
            text="Include subfolders when dropping folders (recursive scan)",
            variable=self.include_subfolders_var,
        )
        self.chk_include_sub.pack(anchor="w", padx=20, pady=4)

    def _build_categories_tab(self) -> None:
        tab = self.tab_categories
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Instructions
        lbl_info = ctk.CTkLabel(
            tab,
            text="Select a category to view and modify associated file extensions.",
            font=ctk.CTkFont(size=12),
            text_color=("#64748B", "#94A3B8"),
            anchor="w",
        )
        lbl_info.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 4))

        # Categories list frame (left)
        left_frame = ctk.CTkFrame(tab, corner_radius=8)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=6)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(1, weight=1)

        lbl_cat_head = ctk.CTkLabel(left_frame, text="Categories", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_cat_head.grid(row=0, column=0, sticky="w", padx=8, pady=6)

        self.categories_scroll = ctk.CTkScrollableFrame(left_frame, fg_color="transparent")
        self.categories_scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        # Category input & buttons
        cat_input_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        cat_input_frame.grid(row=2, column=0, sticky="ew", padx=6, pady=6)

        self.new_cat_entry = ctk.CTkEntry(cat_input_frame, placeholder_text="New Category Name", height=28)
        self.new_cat_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.add_cat_btn = ctk.CTkButton(
            cat_input_frame,
            text="+ Add",
            width=60,
            height=28,
            command=self._on_add_category,
        )
        self.add_cat_btn.pack(side="left")

        # Extensions frame (right)
        right_frame = ctk.CTkFrame(tab, corner_radius=8)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=6)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)

        self.lbl_selected_cat = ctk.CTkLabel(
            right_frame,
            text="Extensions for: (None)",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.lbl_selected_cat.grid(row=0, column=0, sticky="w", padx=8, pady=6)

        self.ext_scroll = ctk.CTkScrollableFrame(right_frame, fg_color="transparent")
        self.ext_scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        ext_input_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        ext_input_frame.grid(row=2, column=0, sticky="ew", padx=6, pady=6)

        self.new_ext_entry = ctk.CTkEntry(ext_input_frame, placeholder_text=".ext (e.g. .epub)", height=28)
        self.new_ext_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.add_ext_btn = ctk.CTkButton(
            ext_input_frame,
            text="+ Add",
            width=60,
            height=28,
            command=self._on_add_extension,
        )
        self.add_ext_btn.pack(side="left")

        self.selected_category_name: str = ""

    def _populate_fields(self) -> None:
        out_mode = self.config_data.get("output_mode", "next_to_file")
        self.output_mode_var.set(out_mode)
        self.root_folder_entry.insert(0, self.config_data.get("single_root_folder", ""))
        self._on_output_mode_changed()

        self.auto_sort_var.set(self.config_data.get("auto_sort_on_drop", True))
        self.include_subfolders_var.set(self.config_data.get("include_subfolders", False))

        self._refresh_categories_list()

    def _on_output_mode_changed(self) -> None:
        is_single = self.output_mode_var.get() == "single_root"
        state = "normal" if is_single else "disabled"
        self.root_folder_entry.configure(state=state)
        self.browse_root_btn.configure(state=state)

    def _browse_single_root(self) -> None:
        folder = filedialog.askdirectory(title="Choose Single Output Root Folder")
        if folder:
            self.root_folder_entry.delete(0, "end")
            self.root_folder_entry.insert(0, folder)

    def _refresh_categories_list(self) -> None:
        for child in self.categories_scroll.winfo_children():
            child.destroy()

        categories = self.config_data.get("categories", {})
        cat_names = sorted(categories.keys())

        if not self.selected_category_name and cat_names:
            self.selected_category_name = cat_names[0]
        elif self.selected_category_name not in categories and cat_names:
            self.selected_category_name = cat_names[0]

        for cat in cat_names:
            row = ctk.CTkFrame(
                self.categories_scroll,
                fg_color=("#2563EB", "#1D4ED8") if cat == self.selected_category_name else "transparent",
                corner_radius=6,
                height=30,
            )
            row.pack(fill="x", pady=2)

            btn_select = ctk.CTkButton(
                row,
                text=cat,
                fg_color="transparent",
                text_color="#FFFFFF" if cat == self.selected_category_name else ("#1E293B", "#F8FAFC"),
                hover_color=("#3B82F6", "#2563EB"),
                anchor="w",
                command=lambda c=cat: self._select_category(c),
            )
            btn_select.pack(side="left", fill="x", expand=True)

            del_btn = ctk.CTkButton(
                row,
                text="✕",
                width=24,
                height=24,
                fg_color="transparent",
                hover_color=("#EF4444", "#DC2626"),
                command=lambda c=cat: self._delete_category(c),
            )
            del_btn.pack(side="right", padx=4)

        self._refresh_extensions_list()

    def _select_category(self, cat_name: str) -> None:
        self.selected_category_name = cat_name
        self._refresh_categories_list()

    def _refresh_extensions_list(self) -> None:
        for child in self.ext_scroll.winfo_children():
            child.destroy()

        if not self.selected_category_name:
            self.lbl_selected_cat.configure(text="Extensions for: (None)")
            return

        self.lbl_selected_cat.configure(text=f"Extensions for: {self.selected_category_name}")
        exts = self.config_data.get("categories", {}).get(self.selected_category_name, [])

        for ext in sorted(exts):
            row = ctk.CTkFrame(self.ext_scroll, fg_color=("#E2E8F0", "#334155"), corner_radius=6, height=28)
            row.pack(fill="x", pady=2)

            lbl_ext = ctk.CTkLabel(row, text=ext, font=ctk.CTkFont(size=12, weight="bold"))
            lbl_ext.pack(side="left", padx=8)

            del_btn = ctk.CTkButton(
                row,
                text="✕",
                width=20,
                height=20,
                fg_color="transparent",
                hover_color=("#EF4444", "#DC2626"),
                command=lambda e=ext: self._delete_extension(e),
            )
            del_btn.pack(side="right", padx=4)

    def _on_add_category(self) -> None:
        new_cat = self.new_cat_entry.get().strip()
        if not new_cat:
            return

        if "categories" not in self.config_data:
            self.config_data["categories"] = {}

        if new_cat in self.config_data["categories"]:
            messagebox.showwarning("Duplicate Category", f"Category '{new_cat}' already exists.", parent=self)
            return

        self.config_data["categories"][new_cat] = []
        self.new_cat_entry.delete(0, "end")
        self.selected_category_name = new_cat
        self._refresh_categories_list()

    def _delete_category(self, cat_name: str) -> None:
        if cat_name in self.config_data.get("categories", {}):
            del self.config_data["categories"][cat_name]
            if self.selected_category_name == cat_name:
                self.selected_category_name = ""
            self._refresh_categories_list()

    def _on_add_extension(self) -> None:
        if not self.selected_category_name:
            return

        new_ext = normalize_extension(self.new_ext_entry.get())
        if not new_ext:
            return

        ext_list = self.config_data["categories"].setdefault(self.selected_category_name, [])
        if new_ext not in ext_list:
            ext_list.append(new_ext)

        self.new_ext_entry.delete(0, "end")
        self._refresh_extensions_list()

    def _delete_extension(self, ext: str) -> None:
        if self.selected_category_name:
            ext_list = self.config_data["categories"].get(self.selected_category_name, [])
            if ext in ext_list:
                ext_list.remove(ext)
            self._refresh_extensions_list()

    def _on_reset_defaults(self) -> None:
        confirm = messagebox.askyesno(
            "Reset Defaults",
            "Are you sure you want to restore all settings and category mappings to default?",
            parent=self,
        )
        if confirm:
            self.config_data = reset_config_to_defaults()
            self.selected_category_name = ""
            self._populate_fields()

    def _on_save(self) -> None:
        # Collect values
        out_mode = self.output_mode_var.get()
        single_root = self.root_folder_entry.get().strip()

        if out_mode == "single_root" and not single_root:
            messagebox.showwarning("Missing Root Folder", "Please specify a destination root directory.", parent=self)
            return

        self.config_data["output_mode"] = out_mode
        self.config_data["single_root_folder"] = single_root
        self.config_data["auto_sort_on_drop"] = self.auto_sort_var.get()
        self.config_data["include_subfolders"] = self.include_subfolders_var.get()

        save_config(self.config_data)
        self.on_save_callback(self.config_data)
        self.destroy()
