"""Preview table widget displaying pending files, categories, and target destinations."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List
import customtkinter as ctk


class PreviewTable(ctk.CTkFrame):
    """Scrollable table showing files to organize with checkboxes and action controls."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_organize_selected: Callable[[List[Dict[str, Any]]], None],
        on_clear: Callable[[], None],
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=12,
            fg_color=("#F8FAFC", "#0F172A"),
            border_width=1,
            border_color=("#CBD5E1", "#334155"),
            **kwargs,
        )
        self.on_organize_selected = on_organize_selected
        self.on_clear = on_clear

        self._plan_items: List[Dict[str, Any]] = []
        self._checkbox_vars: List[ctk.BooleanVar] = []

        self._build_ui()

    def _build_ui(self) -> None:
        # Top toolbar
        self.toolbar = ctk.CTkFrame(self, fg_color="transparent", height=42)
        self.toolbar.pack(fill="x", padx=12, pady=(10, 6))

        self.count_badge = ctk.CTkLabel(
            self.toolbar,
            text="Pending Files: 0",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        )
        self.count_badge.pack(side="left")

        # Right-side action buttons
        self.organize_btn = ctk.CTkButton(
            self.toolbar,
            text="Organize Selected",
            width=140,
            height=32,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#16A34A", "#15803D"),
            hover_color=("#15803D", "#166534"),
            command=self._on_organize_clicked,
        )
        self.organize_btn.pack(side="right", padx=(6, 0))

        self.clear_btn = ctk.CTkButton(
            self.toolbar,
            text="Clear",
            width=80,
            height=32,
            corner_radius=8,
            fg_color=("#EF4444", "#DC2626"),
            hover_color=("#DC2626", "#B91C1C"),
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_clear_clicked,
        )
        self.clear_btn.pack(side="right", padx=6)

        self.deselect_all_btn = ctk.CTkButton(
            self.toolbar,
            text="Deselect All",
            width=90,
            height=32,
            corner_radius=8,
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#1E293B", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            font=ctk.CTkFont(size=11),
            command=self._deselect_all,
        )
        self.deselect_all_btn.pack(side="right", padx=4)

        self.select_all_btn = ctk.CTkButton(
            self.toolbar,
            text="Select All",
            width=80,
            height=32,
            corner_radius=8,
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#1E293B", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            font=ctk.CTkFont(size=11),
            command=self._select_all,
        )
        self.select_all_btn.pack(side="right", padx=4)

        # Header bar
        self.header_frame = ctk.CTkFrame(
            self,
            fg_color=("#E2E8F0", "#1E293B"),
            height=32,
            corner_radius=6,
        )
        self.header_frame.pack(fill="x", padx=12, pady=(0, 4))

        self.h_check = ctk.CTkLabel(self.header_frame, text="", width=36)
        self.h_check.pack(side="left")

        self.h_name = ctk.CTkLabel(
            self.header_frame,
            text="File Name",
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
            width=220,
        )
        self.h_name.pack(side="left", padx=6)

        self.h_cat = ctk.CTkLabel(
            self.header_frame,
            text="Category",
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
            width=110,
        )
        self.h_cat.pack(side="left", padx=6)

        self.h_dest = ctk.CTkLabel(
            self.header_frame,
            text="Destination Path",
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
        )
        self.h_dest.pack(side="left", fill="x", expand=True, padx=6)

        # Scrollable items list
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def load_plan(self, plan: List[Dict[str, Any]]) -> None:
        """Populate the table with plan items."""
        self.clear()
        self._plan_items = plan
        self.count_badge.configure(text=f"Pending Files: {len(plan)}")

        # Badge color palette for categories
        cat_colors = {
            "Images": ("#DBEAFE", "#1E40AF"),
            "Documents": ("#FEF3C7", "#92400E"),
            "Archives": ("#F3E8FF", "#6B21A8"),
            "Installers": ("#FCE7F3", "#9D174D"),
            "Videos": ("#DCFCE7", "#166534"),
            "Audio": ("#FFEDD5", "#9A3412"),
            "Code": ("#E0E7FF", "#3730A3"),
            "Others": ("#F1F5F9", "#475569"),
        }

        for idx, item in enumerate(plan):
            row = ctk.CTkFrame(
                self.scroll_frame,
                fg_color=("#FFFFFF", "#1E293B") if idx % 2 == 0 else ("#F8FAFC", "#0F172A"),
                height=34,
                corner_radius=6,
            )
            row.pack(fill="x", pady=2)

            # Checkbox
            var = ctk.BooleanVar(value=item.get("selected", True))
            self._checkbox_vars.append(var)

            chk = ctk.CTkCheckBox(
                row,
                text="",
                variable=var,
                width=24,
                checkbox_width=18,
                checkbox_height=18,
                command=lambda i=idx, v=var: self._update_item_selected(i, v.get()),
            )
            chk.pack(side="left", padx=(8, 4))

            # File Name
            name = item.get("name", "")
            display_name = (name[:30] + "...") if len(name) > 33 else name
            lbl_name = ctk.CTkLabel(
                row,
                text=display_name,
                font=ctk.CTkFont(size=12),
                anchor="w",
                width=220,
            )
            lbl_name.pack(side="left", padx=6)

            # Category badge
            cat = item.get("category", "Others")
            bg_c, text_c = cat_colors.get(cat, ("#F1F5F9", "#475569"))

            cat_badge = ctk.CTkLabel(
                row,
                text=f" {cat} ",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=bg_c,
                text_color=text_c,
                corner_radius=6,
                width=90,
            )
            cat_badge.pack(side="left", padx=6)

            # Destination
            dest = str(item.get("destination", ""))
            display_dest = (dest[:50] + "...") if len(dest) > 53 else dest
            lbl_dest = ctk.CTkLabel(
                row,
                text=display_dest,
                font=ctk.CTkFont(size=11),
                text_color=("#64748B", "#94A3B8"),
                anchor="w",
            )
            lbl_dest.pack(side="left", fill="x", expand=True, padx=6)

    def _update_item_selected(self, index: int, value: bool) -> None:
        if 0 <= index < len(self._plan_items):
            self._plan_items[index]["selected"] = value

    def _select_all(self) -> None:
        for var in self._checkbox_vars:
            var.set(True)
        for item in self._plan_items:
            item["selected"] = True

    def _deselect_all(self) -> None:
        for var in self._checkbox_vars:
            var.set(False)
        for item in self._plan_items:
            item["selected"] = False

    def _on_organize_clicked(self) -> None:
        selected_items = [item for item in self._plan_items if item.get("selected", True)]
        self.on_organize_selected(selected_items)

    def _on_clear_clicked(self) -> None:
        self.clear()
        self.on_clear()

    def clear(self) -> None:
        """Clear all entries in the preview table."""
        self._plan_items = []
        self._checkbox_vars = []
        for child in self.scroll_frame.winfo_children():
            child.destroy()
        self.count_badge.configure(text="Pending Files: 0")
