"""
File Aggregation Tool - GUI Application

A desktop app that crawls a directory, shows aggregated files by category with
1-line summaries, and lets users select which files to export as JSON.
"""

import json
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import threading

from crawler import FileCrawler, FileAnalyzer, FileAggregator
from crawler.file_analyzer import FileAnalysis

# Reduce logging noise in GUI
logging.getLogger("crawler").setLevel(logging.WARNING)


def get_one_line_summary(analysis: FileAnalysis, max_length: int = 80) -> str:
    """Get a concise 1-line summary for display."""
    summary = (
        analysis.content_summary
        or analysis.content_preview
        or f"{analysis.file_type} file ({analysis.size_mb:.2f} MB)"
    )
    # Take first line and truncate
    first_line = summary.replace("\n", " ").strip()
    if len(first_line) > max_length:
        return first_line[: max_length - 3] + "..."
    return first_line or f"{analysis.category} - {analysis.size_mb:.2f} MB"


class FileAggregationGUI:
    """Main GUI application for file aggregation with selective export."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("File Aggregation Tool")
        self.root.geometry("900x650")
        self.root.minsize(700, 500)

        # State
        self.aggregator = FileAggregator()
        self.file_vars: Dict[str, tk.BooleanVar] = {}
        self.analyses_by_path: Dict[str, FileAnalysis] = {}
        self.is_scanning = False

        self._build_ui()

    def _build_ui(self):
        """Build the main UI layout."""
        # Top panel: scan button only (no folder selection - scans all user paths)
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        self.scan_btn = ttk.Button(
            top_frame, text="Scan & Aggregate", command=self._start_scan
        )
        self.scan_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(
            top_frame,
            text="(Scans your home directory, excluding system/cache folders)",
            foreground="gray",
        ).pack(side=tk.LEFT, padx=10)

        # Options row
        options_frame = ttk.Frame(self.root, padding=(10, 0))
        options_frame.pack(fill=tk.X)

        ttk.Label(options_frame, text="Max depth (0=unlimited):").pack(
            side=tk.LEFT, padx=(0, 5)
        )
        self.depth_var = tk.StringVar(value="0")
        depth_spin = ttk.Spinbox(
            options_frame, from_=0, to=20, textvariable=self.depth_var, width=4
        )
        depth_spin.pack(side=tk.LEFT, padx=5)
        ttk.Label(options_frame, text="Min size (KB):").pack(side=tk.LEFT, padx=(15, 5))
        self.min_size_var = tk.IntVar(value=0)
        min_size_spin = ttk.Spinbox(
            options_frame, from_=0, to=10240, textvariable=self.min_size_var, width=6
        )
        min_size_spin.pack(side=tk.LEFT, padx=5)

        # Progress / status
        self.status_var = tk.StringVar(
            value="Click Scan & Aggregate to discover and analyze files. Then select the files you want and export to JSON."
        )
        status_label = ttk.Label(
            self.root, textvariable=self.status_var, foreground="gray"
        )
        status_label.pack(anchor=tk.W, padx=15, pady=(5, 0))

        # Main content: notebook with file list
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # File list frame (scrollable)
        list_frame = ttk.Frame(self.notebook)
        self.notebook.add(list_frame, text="Files by Category")

        # Treeview with checkboxes (using tags and bind)
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("select", "summary", "size")
        self.tree = ttk.Treeview(
            tree_frame, columns=columns, show="tree headings", height=20, selectmode="extended"
        )
        self.tree.heading("#0", text="Category / File")
        self.tree.column("#0", width=280, minwidth=150)
        self.tree.heading("select", text="✓")
        self.tree.column("select", width=40, minwidth=40)
        self.tree.heading("summary", text="Summary / Context")
        self.tree.column("summary", width=380, minwidth=200)
        self.tree.heading("size", text="Size")
        self.tree.column("size", width=70, minwidth=60)

        scroll_y = ttk.Scrollbar(tree_frame)
        scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)

        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.configure(command=self.tree.yview)
        scroll_x.configure(command=self.tree.xview)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind("<ButtonRelease-1>", self._toggle_selection)  # Single-click to toggle
        self.tree.bind("<space>", self._toggle_selection)

        # Selection controls
        sel_frame = ttk.Frame(list_frame)
        sel_frame.pack(fill=tk.X, pady=5)

        ttk.Button(sel_frame, text="Select All", command=self._select_all).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(sel_frame, text="Deselect All", command=self._deselect_all).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(sel_frame, text="Select by Category", command=self._select_by_category).pack(
            side=tk.LEFT, padx=5
        )

        # Export button
        export_frame = ttk.Frame(self.root, padding=10)
        export_frame.pack(fill=tk.X)

        self.export_btn = ttk.Button(
            export_frame,
            text="Export Selected to JSON",
            command=self._export_selected,
            state=tk.DISABLED,
        )
        self.export_btn.pack(side=tk.LEFT, padx=5)

        self.export_status_var = tk.StringVar(value="")
        ttk.Label(export_frame, textvariable=self.export_status_var).pack(
            side=tk.LEFT, padx=10
        )

    def _start_scan(self):
        if self.is_scanning:
            return
        root_path = Path.home()

        self.is_scanning = True
        self.scan_btn.config(state=tk.DISABLED)
        self.export_btn.config(state=tk.DISABLED)
        self.status_var.set("Scanning... Please wait.")
        self.aggregator.clear()
        self.file_vars.clear()
        self.analyses_by_path.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            depth_val = int(self.depth_var.get())
            max_depth = None if depth_val == 0 else depth_val
        except (ValueError, TypeError):
            max_depth = 0
        min_size = 0
        try:
            min_size = int(self.min_size_var.get()) * 1024
        except (ValueError, TypeError):
            pass

        thread = threading.Thread(
            target=self._do_scan,
            args=(str(root_path), max_depth, min_size),
        )
        thread.daemon = True
        thread.start()
        self.root.after(100, self._check_scan_complete)

    def _do_scan(self, root_path: str, max_depth: int, min_file_size: int):
        # Extended exclusions for system/cache folders (scans all user paths)
        extra_exclude_dirs = {
            "Library",  # macOS: caches, app support, preferences
            "Cache", "Caches",
            "AppData",  # Windows: Roaming/Local/Temp
            "LocalLow",
            "Application Data",
            "System Volume Information",
            "$Recycle.Bin",
            "Thumbs.db",
        }
        exclude_dirs = set(FileCrawler.DEFAULT_EXCLUDE_DIRS) | extra_exclude_dirs

        try:
            crawler = FileCrawler(
                root_path=root_path,
                max_depth=max_depth,
                min_file_size=max(0, min_file_size),
                exclude_dirs=exclude_dirs,
            )
            analyzer = FileAnalyzer(max_preview_lines=5, max_preview_chars=200)

            files = crawler.crawl()
            for file_info in files:
                try:
                    analysis = analyzer.analyze(file_info.path)
                    self.aggregator.add_analysis(analysis)
                except Exception:
                    continue
        except Exception as e:
            self._scan_error = str(e)
        else:
            self._scan_error = None
        self._scan_done = True

    def _check_scan_complete(self):
        if not hasattr(self, "_scan_done") or not self._scan_done:
            self.root.after(200, self._check_scan_complete)
            return

        self.is_scanning = False
        self.scan_btn.config(state=tk.NORMAL)

        if hasattr(self, "_scan_error") and self._scan_error:
            messagebox.showerror("Scan Error", self._scan_error)
            self.status_var.set("Scan failed.")
            return

        self._populate_tree()
        count = len(self.aggregator.analyses)
        self.status_var.set(
            f"Found {count} files. Click each file to select it (✓), then Export Selected to JSON."
        )
        self.export_btn.config(state=tk.NORMAL)

    def _populate_tree(self):
        """Populate the tree with files grouped by category."""
        grouped = self.aggregator.group_by_category()

        for category in sorted(grouped.keys(), key=lambda c: (-len(grouped[c]), c)):
            analyses = grouped[category]
            parent = self.tree.insert("", tk.END, text=category, open=True)

            for analysis in sorted(analyses, key=lambda a: a.path):
                var = tk.BooleanVar(value=False)
                self.file_vars[analysis.path] = var
                self.analyses_by_path[analysis.path] = analysis

                summary = get_one_line_summary(analysis)
                filename = Path(analysis.path).name
                size_str = f"{analysis.size_mb:.2f} MB"

                iid = self.tree.insert(
                    parent,
                    tk.END,
                    text=filename,
                    values=("☐", summary, size_str),
                    tags=(analysis.path,),
                )
                self.tree.set(iid, "select", "☐")

    def _toggle_selection(self, event):
        """Toggle selection on double-click or space."""
        selection = self.tree.selection()
        for item in selection:
            vals = self.tree.item(item, "values")
            if not vals:
                continue
            tags = self.tree.item(item, "tags")
            if tags:
                path = tags[0]
                if path in self.file_vars:
                    var = self.file_vars[path]
                    var.set(not var.get())
                    self.tree.set(item, "select", "☑" if var.get() else "☐")

    def _select_all(self):
        for path, var in self.file_vars.items():
            var.set(True)
        self._refresh_tree_checks()

    def _deselect_all(self):
        for var in self.file_vars.values():
            var.set(False)
        self._refresh_tree_checks()

    def _select_by_category(self):
        """Select all files in the selected category/categories."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo(
                "Select by Category",
                "Select one or more category headers (or files), then click this button.",
            )
            return
        items_to_select = []
        for item in selection:
            parent = self.tree.parent(item)
            # If this is a category row (parent is root), get its file children
            if parent == "":
                items_to_select.extend(self.tree.get_children(item))
            else:
                # File row: select all siblings in same category
                items_to_select.extend(self.tree.get_children(parent))
        for child in items_to_select:
            tags = self.tree.item(child, "tags")
            if tags and tags[0] in self.file_vars:
                self.file_vars[tags[0]].set(True)
        self._refresh_tree_checks()

    def _refresh_tree_checks(self):
        for item in self.tree.get_children():
            self._refresh_checks_recursive(item)

    def _refresh_checks_recursive(self, item):
        tags = self.tree.item(item, "tags")
        if tags and tags[0] in self.file_vars:
            var = self.file_vars[tags[0]]
            self.tree.set(item, "select", "☑" if var.get() else "☐")
        for child in self.tree.get_children(item):
            self._refresh_checks_recursive(child)

    def _get_selected_analyses(self) -> List[FileAnalysis]:
        return [
            a for path, a in self.analyses_by_path.items()
            if path in self.file_vars and self.file_vars[path].get()
        ]

    def _export_selected(self):
        selected = self._get_selected_analyses()
        if not selected:
            messagebox.showwarning(
                "No Selection",
                "Please select at least one file to export.",
            )
            return

        # Bring window to front so save dialog is visible (macOS fix)
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.update_idletasks()

        output_path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save JSON As",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="selected_files.json",
            initialdir=str(Path.home() / "Desktop"),
        )

        self.root.attributes("-topmost", False)
        if not output_path:
            return

        try:
            self.aggregator.export_json(
                output_path,
                analyses=selected,
                include_stats=True,
            )
            self.export_status_var.set(f"Exported {len(selected)} files to {output_path}")
            messagebox.showinfo("Export Complete", f"Exported {len(selected)} files to:\n{output_path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
            self.export_status_var.set("Export failed.")

    def run(self):
        self.root.mainloop()


def main():
    app = FileAggregationGUI()
    app.run()


if __name__ == "__main__":
    main()
