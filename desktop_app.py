import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QFrame,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QProgressBar,
)

from extractors.docs_extractor import extract_text_from_docx
from extractors.image_extractor import extract_text_from_image
from extractors.browser_extractor import (
    extract_text_from_browser_cookies,
    extract_text_from_browser_history,
)
from extractors.pdf_extractor import extract_text_from_pdf
from extractors.pptx_extractor import extract_text_from_pptx
from extractors.platform_extractor import extract_text_from_platform_export
from extractors.video_extractor import extract_text_from_video
from processing.pipeline import process_document
from storage.json_store import get_output_root, save_artifact

STYLESHEET = """
    QMainWindow, QWidget {
        background: #0f1117;
        color: #e2e8f0;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 14px;
    }
    QGroupBox {
        font-size: 13px;
        font-weight: 700;
        color: #94a3b8;
        border: 1px solid #1e293b;
        border-radius: 12px;
        margin-top: 16px;
        background: #141920;
        padding: 14px 10px 10px 10px;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: #64748b;
    }
    QLineEdit, QSpinBox, QPlainTextEdit {
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 8px 10px;
        background: #0d1117;
        font-size: 13px;
        color: #e2e8f0;
        selection-background-color: #3b82f6;
    }
    QLineEdit:focus, QSpinBox:focus, QPlainTextEdit:focus {
        border: 1px solid #3b82f6;
        background: #0d1117;
    }
    QLineEdit:read-only {
        color: #64748b;
    }
    QSpinBox::up-button, QSpinBox::down-button {
        background: #1e293b;
        border: none;
        border-radius: 4px;
        width: 18px;
    }
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {
        background: #3b82f6;
    }
    QPushButton {
        border: 1px solid #1e293b;
        border-radius: 8px;
        background: #1e293b;
        color: #cbd5e1;
        font-weight: 600;
        font-size: 13px;
        padding: 10px 18px;
        min-height: 20px;
    }
    QPushButton:hover {
        background: #263548;
        border-color: #3b82f6;
        color: #f1f5f9;
    }
    QPushButton:disabled {
        background: #0d1117;
        color: #334155;
        border-color: #1e293b;
    }
    QPushButton#primaryBtn {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #2563eb, stop:1 #1d4ed8);
        color: #ffffff;
        border: none;
        font-size: 13px;
        font-weight: 700;
    }
    QPushButton#primaryBtn:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #1d4ed8, stop:1 #1e40af);
        border: none;
    }
    QPushButton#primaryBtn:disabled {
        background: #1e293b;
        color: #475569;
        border: none;
    }
    QPushButton#successBtn {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #059669, stop:1 #047857);
        color: #ffffff;
        border: none;
        font-size: 13px;
        font-weight: 700;
    }
    QPushButton#successBtn:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #047857, stop:1 #065f46);
        border: none;
    }
    QPushButton#successBtn:disabled {
        background: #1e293b;
        color: #475569;
        border: none;
    }
    QLabel#titleLabel {
        font-size: 28px;
        font-weight: 800;
        color: #f8fafc;
        letter-spacing: -0.5px;
    }
    QLabel#titleAccent {
        font-size: 28px;
        font-weight: 800;
        color: #3b82f6;
        letter-spacing: -0.5px;
    }
    QLabel#subtitleLabel {
        color: #475569;
        font-size: 13px;
    }
    QLabel#statusBadge {
        border-radius: 14px;
        padding: 5px 14px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    QLabel#sectionLabel {
        font-size: 13px;
        font-weight: 700;
        color: #64748b;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    QLabel#helperLabel {
        color: #475569;
        font-size: 12px;
    }
    QFrame#card {
        background: #141920;
        border: 1px solid #1e293b;
        border-radius: 14px;
    }
    QFrame#headerBar {
        background: #0d1117;
        border-bottom: 1px solid #1e293b;
        border-radius: 0px;
    }
    QTabWidget::pane {
        border: 1px solid #1e293b;
        border-radius: 10px;
        background: #0d1117;
        top: -1px;
    }
    QTabBar::tab {
        background: #141920;
        border: 1px solid #1e293b;
        padding: 8px 18px;
        margin-right: 3px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        font-weight: 600;
        font-size: 13px;
        color: #64748b;
    }
    QTabBar::tab:selected {
        background: #1d4ed8;
        color: #ffffff;
        border-color: #1d4ed8;
    }
    QTabBar::tab:hover:!selected {
        background: #1e293b;
        color: #94a3b8;
    }
    QProgressBar {
        border: none;
        border-radius: 4px;
        background: #1e293b;
        height: 6px;
        text-align: center;
    }
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #3b82f6, stop:1 #8b5cf6);
        border-radius: 4px;
    }
    QScrollBar:vertical {
        background: #0d1117;
        width: 8px;
        border-radius: 4px;
    }
    QScrollBar::handle:vertical {
        background: #1e293b;
        border-radius: 4px;
        min-height: 20px;
    }
    QScrollBar::handle:vertical:hover {
        background: #3b82f6;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
"""


class LLMBundlerDesktop(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LLM Bundler")
        self.resize(1320, 860)
        self.setMinimumSize(1180, 760)

        self.selected_file: Path | None = None
        self.raw_doc_id: str | None = None
        self.raw_artifact_path: str | None = None
        self.latest_chunks_path: str | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setSpacing(0)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Header bar
        root_layout.addWidget(self._build_header())

        # Progress bar (thin, below header)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(4)
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)
        root_layout.addWidget(self.progress)

        # Main content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 16, 20, 16)
        content_layout.setSpacing(12)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([440, 820])
        splitter.setHandleWidth(8)
        content_layout.addWidget(splitter, stretch=1)

        root_layout.addWidget(content, stretch=1)

        self.setStyleSheet(STYLESHEET)
        self.setCentralWidget(root)

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("headerBar")
        header.setFixedHeight(64)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)

        # Logo + title
        title_row = QHBoxLayout()
        title_row.setSpacing(0)
        title1 = QLabel("LLM")
        title1.setObjectName("titleLabel")
        title2 = QLabel(" Bundler")
        title2.setObjectName("titleAccent")
        title_row.addWidget(title1)
        title_row.addWidget(title2)
        title_row.addStretch()

        layout.addLayout(title_row, stretch=1)

        # Subtitle
        subtitle = QLabel(f"Output → {get_output_root()}")
        subtitle.setObjectName("subtitleLabel")
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Status badge
        self.status_badge = QLabel("● Idle")
        self.status_badge.setObjectName("statusBadge")
        self.status_badge.setAlignment(Qt.AlignCenter)
        self.status_badge.setFixedWidth(120)
        self._set_status("● Idle", "info")
        layout.addWidget(self.status_badge)

        return header

    def _build_left_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        layout.addWidget(self._build_ingest_box())
        layout.addWidget(self._build_chunk_box())
        layout.addStretch(1)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        preview_label = QLabel("PREVIEW")
        preview_label.setObjectName("sectionLabel")
        layout.addWidget(preview_label)

        self.preview_tabs = QTabWidget()
        self.preview_tabs.setDocumentMode(True)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("Extracted text will appear here after ingestion...")
        self.preview.setMinimumHeight(310)

        self.chunk_preview = QPlainTextEdit()
        self.chunk_preview.setReadOnly(True)
        self.chunk_preview.setPlaceholderText(
            "Chunk preview will appear here after processing..."
        )
        self.chunk_preview.setMinimumHeight(310)

        self.preview_tabs.addTab(self.preview, "📄  Extracted Text")
        self.preview_tabs.addTab(self.chunk_preview, "🧩  Chunk Preview")
        layout.addWidget(self.preview_tabs, stretch=2)

        log_label = QLabel("ACTIVITY LOG")
        log_label.setObjectName("sectionLabel")
        layout.addWidget(log_label)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Status updates will appear here...")
        self.log.setMinimumHeight(160)
        layout.addWidget(self.log, stretch=1)
        return panel

    def _build_ingest_box(self) -> QGroupBox:
        box = QGroupBox("Step 1 — Ingest Document")
        layout = QVBoxLayout(box)
        layout.setSpacing(10)

        row = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("Select a PDF, DOCX, or PPTX file...")
        self.file_path_input.setReadOnly(True)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self.select_file)
        row.addWidget(self.file_path_input, stretch=1)
        row.addWidget(browse_btn)
        layout.addLayout(row)

        helper = QLabel("Supported: PDF · DOCX · PPTX")
        helper.setObjectName("helperLabel")
        layout.addWidget(helper)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.extract_btn = QPushButton("⬆  Extract + Save Raw JSON")
        self.extract_btn.setObjectName("primaryBtn")
        self.extract_btn.clicked.connect(self.extract_and_save_raw)
        self.save_raw_copy_btn = QPushButton("Save Raw JSON As…")
        self.save_raw_copy_btn.clicked.connect(self.save_raw_copy_as)
        self.save_raw_copy_btn.setEnabled(False)
        action_row.addWidget(self.extract_btn, stretch=2)
        action_row.addWidget(self.save_raw_copy_btn, stretch=1)
        layout.addLayout(action_row)

        return box

    def _build_chunk_box(self) -> QGroupBox:
        box = QGroupBox("Step 2 — Process & Chunk")
        layout = QVBoxLayout(box)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)
        self.chunk_size = QSpinBox()
        self.chunk_size.setRange(100, 4000)
        self.chunk_size.setValue(800)
        self.chunk_overlap = QSpinBox()
        self.chunk_overlap.setRange(0, 1000)
        self.chunk_overlap.setValue(100)
        form.addRow("Chunk size (chars):", self.chunk_size)
        form.addRow("Chunk overlap (chars):", self.chunk_overlap)
        layout.addLayout(form)

        self.encrypt_checkbox = QCheckBox("🔒  Encrypt chunk artifact after saving")
        self.encrypt_checkbox.setToolTip(
            "Encrypts the chunk JSON using RSA + AES-256 hybrid encryption before transfer."
        )
        layout.addWidget(self.encrypt_checkbox)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.process_btn = QPushButton("🧩  Process + Save Chunk JSON")
        self.process_btn.setObjectName("successBtn")
        self.process_btn.clicked.connect(self.process_and_save_chunks)
        self.process_btn.setEnabled(False)
        self.save_chunk_copy_btn = QPushButton("Save Chunk JSON As…")
        self.save_chunk_copy_btn.clicked.connect(self.save_chunk_copy_as)
        self.save_chunk_copy_btn.setEnabled(False)
        action_row.addWidget(self.process_btn, stretch=2)
        action_row.addWidget(self.save_chunk_copy_btn, stretch=1)
        layout.addLayout(action_row)

        return box

    def select_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose file",
            "",
            (
                "Supported Files (*.pdf *.docx *.pptx *.jpg *.jpeg *.png *.mp4 *.mov *.json *.sqlite *.db);;"
                "Documents (*.pdf *.docx *.pptx);;"
                "Images (*.jpg *.jpeg *.png);;"
                "Videos (*.mp4 *.mov);;"
                "Platform Exports (*.json);;"
                "Browser DBs (*.sqlite *.db);;"
                "All Files (*)"
            ),
        )
        if not file_path:
            return

        self.selected_file = Path(file_path)
        self.file_path_input.setText(str(self.selected_file))
        self._log(f"📂 Selected: {self.selected_file.name}")

        self._warn_if_sensitive(self.selected_file.name)

    _SENSITIVE_KEYWORDS = {"private", "secret", "password", "bank", "ssn", "confidential"}

    def _warn_if_sensitive(self, filename: str) -> None:
        name_lower = filename.lower()
        if any(kw in name_lower for kw in self._SENSITIVE_KEYWORDS):
            result = QMessageBox.warning(
                self,
                "Sensitive File Detected",
                f"'{filename}' may contain sensitive personal data.\n\n"
                "Are you sure you want to extract and process this file?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if result == QMessageBox.No:
                self.selected_file = None
                self.file_path_input.clear()
                self._log(f"🚫 Cancelled — sensitive file not processed: {filename}")

    def extract_and_save_raw(self) -> None:
        if self.selected_file is None:
            self._warn("Please choose a file first.")
            return

        file_type = self.selected_file.suffix.lower().lstrip(".")
        supported_types = {
            "pdf", "docx", "pptx",
            "jpg", "jpeg", "png",
            "mp4", "mov",
            "json",
            "sqlite", "db",
        }
        if file_type not in supported_types:
            self._warn(
                "Unsupported file type. Choose a document, image, video, platform export JSON, "
                "or browser history/cookie DB file."
            )
            return

        self._set_status("● Working…", "working")
        self.progress.setVisible(True)
        QApplication.processEvents()

        try:
            file_bytes = self.selected_file.read_bytes()
            if file_type == "pdf":
                result = extract_text_from_pdf(file_bytes)
            elif file_type == "docx":
                result = extract_text_from_docx(file_bytes)
            elif file_type == "pptx":
                result = extract_text_from_pptx(file_bytes)
            elif file_type in {"jpg", "jpeg", "png"}:
                result = extract_text_from_image(file_bytes)
            elif file_type in {"mp4", "mov"}:
                result = extract_text_from_video(file_bytes)
            elif file_type == "json":
                result = extract_text_from_platform_export(file_bytes)
            else:  # sqlite/db
                db_name = self.selected_file.name.lower()
                is_cookie_db = "cookie" in db_name
                if is_cookie_db:
                    self._log("🔐 Cookie extraction mode: safe metadata only (values excluded).")
                    result = extract_text_from_browser_cookies(file_bytes)
                else:
                    result = extract_text_from_browser_history(file_bytes)

            self.preview.setPlainText(result["text"][:6000])
            self.chunk_preview.clear()
            self.preview_tabs.setCurrentIndex(0)

            doc_id, output_path = save_artifact(
                filename=self.selected_file.name,
                file_type=file_type,
                text=result["text"],
                page_count=result["page_count"],
            )
            self.raw_doc_id = doc_id
            self.raw_artifact_path = output_path
            self.process_btn.setEnabled(True)
            self.save_raw_copy_btn.setEnabled(True)
            self._set_status("● Raw Saved", "success")
            self.progress.setVisible(False)

            chars = len(result["text"])
            pages = result.get("page_count")
            page_info = f" · {pages} pages" if pages else ""
            self._log(f"✅ Raw artifact saved — {chars:,} chars{page_info}")
            self._log(f"   ID: {doc_id}")
            QMessageBox.information(self, "Success", "Raw JSON artifact saved successfully.")
        except Exception as exc:
            self._set_status("● Error", "warn")
            self.progress.setVisible(False)
            self._warn(f"Failed to extract/save raw artifact.\n\n{exc}")

    def process_and_save_chunks(self) -> None:
        if not self.raw_artifact_path:
            self._warn("Please save a raw artifact first.")
            return

        self._set_status("● Chunking…", "working")
        self.progress.setVisible(True)
        QApplication.processEvents()

        try:
            should_encrypt = self.encrypt_checkbox.isChecked()
            result = process_document(
                file_path=self.raw_artifact_path,
                chunk_size=self.chunk_size.value(),
                chunk_overlap=self.chunk_overlap.value(),
                encrypt=should_encrypt,
            )
            self.latest_chunks_path = result["output_path"]
            self.save_chunk_copy_btn.setEnabled(True)
            self._set_status("● Chunks Ready", "success")
            self.progress.setVisible(False)

            preview_chunks = result["chunks"][:8]
            preview_text = []
            for chunk in preview_chunks:
                preview_text.append(
                    f"[{chunk['chunk_id']}] (#{chunk['chunk_index']})\n{chunk['text']}\n"
                )
            if result["total_chunks"] > len(preview_chunks):
                preview_text.append(
                    f"... {result['total_chunks'] - len(preview_chunks)} more chunks not shown."
                )
            self.chunk_preview.setPlainText("\n" + ("\n" + ("-" * 70) + "\n").join(preview_text))
            self.preview_tabs.setCurrentIndex(1)

            self._log(f"✅ Chunking complete — {result['total_chunks']} chunks created")
            self._log(f"   Saved to: {self.latest_chunks_path}")
            if should_encrypt and "encrypted_path" in result:
                self._log(f"🔒 Encrypted artifact: {result['encrypted_path']}")

            success_msg = f"Chunking complete.\n{result['total_chunks']} chunks created."
            if should_encrypt and "encrypted_path" in result:
                success_msg += f"\n\nEncrypted file saved to:\n{result['encrypted_path']}"
            QMessageBox.information(self, "Success", success_msg)
        except Exception as exc:
            self._set_status("● Error", "warn")
            self.progress.setVisible(False)
            self._warn(f"Failed to process chunks.\n\n{exc}")

    def save_raw_copy_as(self) -> None:
        if not self.raw_artifact_path or not self.raw_doc_id:
            self._warn("No raw artifact is available yet.")
            return

        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Raw JSON As",
            f"doc_{self.raw_doc_id}.json",
            "JSON Files (*.json)",
        )
        if not target_path:
            return
        shutil.copyfile(self.raw_artifact_path, target_path)
        self._log(f"💾 Raw JSON saved to: {target_path}")

    def save_chunk_copy_as(self) -> None:
        if not self.latest_chunks_path or not self.raw_doc_id:
            self._warn("No chunk artifact is available yet.")
            return

        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Chunk JSON As",
            f"doc_{self.raw_doc_id}_chunks.json",
            "JSON Files (*.json)",
        )
        if not target_path:
            return
        shutil.copyfile(self.latest_chunks_path, target_path)
        self._log(f"💾 Chunk JSON saved to: {target_path}")

    def _warn(self, text: str) -> None:
        QMessageBox.warning(self, "LLM Bundler", text)
        self._log(f"⚠️  {text}")
        self._set_status("● Warning", "warn")

    def _log(self, message: str) -> None:
        self.log.appendPlainText(message)

    def _set_status(self, text: str, kind: str = "info") -> None:
        styles = {
            "info":    ("#1e293b", "#64748b", "#334155"),
            "success": ("#052e16", "#4ade80", "#166534"),
            "warn":    ("#431407", "#fb923c", "#9a3412"),
            "working": ("#1e1b4b", "#818cf8", "#3730a3"),
        }
        bg, fg, border = styles.get(kind, styles["info"])
        self.status_badge.setText(text)
        self.status_badge.setStyleSheet(
            f"background: {bg}; color: {fg}; border: 1px solid {border};"
            "border-radius: 14px; padding: 5px 14px; font-size: 12px; font-weight: 700;"
        )


def main() -> None:
    app = QApplication([])
    app.setApplicationName("LLM Bundler")
    window = LLMBundlerDesktop()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
