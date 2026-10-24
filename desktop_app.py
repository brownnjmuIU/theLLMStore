import shutil
import time
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QCheckBox,
    QDialog,
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
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QToolButton,
    QToolTip,
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
from storage.json_store import save_artifact
from chatbot.chunk_loader import load_chunk_artifact
from chatbot.model_connectors import OllamaConnector
from chatbot.rag_service import _build_prompt
from chatbot.retriever import matched_query_terms, retrieve_relevant_chunks
from chatbot.playground import (
    answer_with_trace,
    ask_model,
    build_context,
    chunk_in_memory,
    list_local_models,
)

VISIBLE_SOURCE_CHIP_LIMIT = 2
WORKFLOW_RAIL_EXPANDED_WIDTH = 210
WORKFLOW_RAIL_COLLAPSED_WIDTH = 72

STYLESHEET = """
    QMainWindow, QWidget {
        background: #f4f7f8;
        color: #263241;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 14px;
    }
    QFrame#headerBar {
        background: #fbfcfc;
        border-bottom: 1px solid #d8e2e7;
        border-radius: 0px;
    }
    QFrame#card, QFrame#workflowRail {
        background: #fbfcfc;
        border: 1px solid #d8e2e7;
        border-radius: 16px;
    }
    QFrame#workflowStep {
        background: #f4f7f8;
        border: 1px solid #d8e2e7;
        border-radius: 12px;
    }
    QLabel#stepBadge {
        background: #dbeff2;
        color: #246a73;
        border: 1px solid #b8dce2;
        border-radius: 14px;
        font-weight: 800;
    }
    QLabel#stepTitle {
        color: #263241;
        font-size: 14px;
        font-weight: 800;
    }
    QLabel#stepStatus, QLabel#subtitleLabel, QLabel#helperLabel {
        color: #6a7887;
        font-size: 12px;
    }
    QLabel#iconTipBanner {
        background: #eef8f9;
        color: #246a73;
        border: 1px solid #b8dce2;
        border-radius: 10px;
        padding: 8px 12px;
        font-size: 13px;
        font-weight: 700;
    }
    QFrame#dataSummaryFlow {
        background: #eef8f9;
        border: 1px solid #b8dce2;
        border-radius: 10px;
    }
    QLabel#summaryTitle {
        color: #246a73;
        font-size: 12px;
        font-weight: 850;
    }
    QLabel#summaryChip {
        background: #ffffff;
        color: #246a73;
        border: 1px solid #b8dce2;
        border-radius: 8px;
        padding: 6px 7px;
        font-size: 12px;
        font-weight: 800;
    }
    QLabel#summaryChip[state="pending"] {
        background: #ffffff;
        color: #6a7887;
        border-color: #d8e2e7;
    }
    QLabel#summaryChip[state="active"] {
        background: #2f7f88;
        color: #ffffff;
        border-color: #246a73;
    }
    QLabel#summaryChip[state="done"] {
        background: #e7f3f4;
        color: #246a73;
        border-color: #b8dce2;
    }
    QLabel#summaryArrow {
        color: #2f7f88;
        font-size: 13px;
        font-weight: 900;
    }
    QFrame#chunkVisual {
        background: #eef8f9;
        border: 1px solid #b8dce2;
        border-radius: 10px;
    }
    QLabel#chunkExplainer {
        color: #246a73;
        font-size: 12px;
        font-weight: 750;
    }
    QLabel#documentBlock {
        background: #ffffff;
        color: #246a73;
        border: 1px solid #b8dce2;
        border-radius: 8px;
        padding: 4px 8px;
        font-size: 12px;
        font-weight: 850;
    }
    QLabel#chunkMiniCard {
        background: #ffffff;
        color: #246a73;
        border: 1px solid #b8dce2;
        border-radius: 8px;
        padding: 4px 7px;
        font-size: 12px;
        font-weight: 800;
    }
    QGroupBox {
        font-size: 13px;
        font-weight: 800;
        color: #536475;
        border: 1px solid #d8e2e7;
        border-radius: 14px;
        margin-top: 16px;
        background: #fbfcfc;
        padding: 14px 10px 10px 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: #536475;
    }
    QToolButton#infoButton {
        background: #e7f3f4;
        color: #246a73;
        border: 1px solid #b8dce2;
        border-radius: 10px;
        font-size: 12px;
        font-weight: 900;
        min-width: 20px;
        min-height: 20px;
        max-width: 20px;
        max-height: 20px;
    }
    QToolButton#infoButton:hover {
        background: #d8ecef;
        border-color: #2f7f88;
    }
    QToolTip {
        background: #263241;
        color: #ffffff;
        border: 1px solid #536475;
        padding: 7px;
        font-size: 12px;
    }
    QLineEdit, QSpinBox, QPlainTextEdit {
        border: 1px solid #cddae0;
        border-radius: 10px;
        padding: 8px 10px;
        background: #ffffff;
        font-size: 13px;
        color: #263241;
        selection-background-color: #b8dce2;
    }
    QLineEdit:focus, QSpinBox:focus, QPlainTextEdit:focus {
        border: 1px solid #2f7f88;
        background: #ffffff;
    }
    QPushButton {
        border: 1px solid #cddae0;
        border-radius: 10px;
        background: #eef4f5;
        color: #334252;
        font-weight: 700;
        font-size: 13px;
        padding: 10px 18px;
        min-height: 20px;
    }
    QPushButton:hover {
        background: #e1ecef;
        border-color: #2f7f88;
    }
    QPushButton:disabled {
        background: #edf1f3;
        color: #9aa8b4;
        border-color: #d8e2e7;
    }
    QPushButton#primaryBtn, QPushButton#successBtn {
        background: #2f7f88;
        color: #ffffff;
        border: 1px solid #246a73;
    }
    QPushButton#primaryBtn:hover, QPushButton#successBtn:hover {
        background: #246a73;
    }
    QPushButton#primaryBtn:disabled, QPushButton#successBtn:disabled {
        background: #edf1f3;
        color: #9aa8b4;
        border-color: #d8e2e7;
    }
    QLabel#titleLabel {
        font-size: 26px;
        font-weight: 850;
        color: #243142;
    }
    QLabel#sectionLabel {
        font-size: 13px;
        font-weight: 800;
        color: #536475;
        letter-spacing: 0.7px;
        text-transform: uppercase;
    }
    QLabel#statusBadge {
        border-radius: 14px;
        padding: 5px 14px;
        font-size: 12px;
        font-weight: 800;
    }
    QLabel#privacyBadge {
        background: #e7f3f4;
        color: #246a73;
        border: 1px solid #b8dce2;
        border-radius: 14px;
        padding: 5px 12px;
        font-size: 12px;
        font-weight: 800;
    }
    QScrollArea#chatScrollArea {
        border: 1px solid #d8e2e7;
        border-radius: 12px;
        background: #f8fbfb;
    }
    QWidget#chatMessages {
        background: #f8fbfb;
    }
    QFrame#userMessage {
        background: #2f7f88;
        border: 1px solid #246a73;
        border-radius: 14px;
    }
    QFrame#assistantMessage {
        background: #ffffff;
        border: 1px solid #d8e2e7;
        border-radius: 14px;
    }
    QLabel#messageText {
        background: transparent;
        border: none;
        font-size: 14px;
        line-height: 1.35;
    }
    QFrame#userMessage QLabel#messageText {
        color: #ffffff;
    }
    QFrame#assistantMessage QLabel#messageText {
        color: #263241;
    }
    QLabel#userAvatar {
        background: #2f7f88;
        color: #ffffff;
        border: 1px solid #246a73;
        border-radius: 15px;
        font-size: 12px;
        font-weight: 850;
    }
    QLabel#assistantAvatar {
        background: #e7f3f4;
        color: #246a73;
        border: 1px solid #b8dce2;
        border-radius: 15px;
        font-size: 11px;
        font-weight: 850;
    }
    QPushButton#sourceChip {
        background: #e7f3f4;
        color: #246a73;
        border: 1px solid #b8dce2;
        border-radius: 9px;
        padding: 3px 8px;
        font-size: 12px;
        font-weight: 800;
        min-height: 18px;
    }
    QPushButton#sourceChip:hover {
        background: #d8ecef;
        border-color: #2f7f88;
    }
    QPushButton#stopBtn {
        background: #fff6ed;
        color: #8a4b16;
        border: 1px solid #e6c7a6;
        border-radius: 9px;
        padding: 8px 14px;
        font-weight: 800;
    }
    QPushButton#stopBtn:hover {
        background: #fdebd7;
    }
    QPushButton#stopBtn:disabled {
        background: #f2f4f5;
        color: #9aa7b2;
        border-color: #d8e2e7;
    }
    QLabel#sourceNote {
        color: #66788a;
        background: transparent;
        border: none;
        font-size: 12px;
        padding-top: 2px;
    }
    QFrame#assistantHeader {
        background: #f8fbfb;
        border: 1px solid #d8e2e7;
        border-radius: 12px;
    }
    QLabel#assistantTitle {
        color: #263241;
        font-size: 16px;
        font-weight: 850;
    }
    QLabel#assistantStatus {
        color: #2f7f88;
        font-size: 12px;
        font-weight: 800;
    }
    QDialog#sourcePreviewDialog {
        background: #f4f7f8;
    }
    QLabel#sourcePreviewTitle {
        color: #263241;
        font-size: 18px;
        font-weight: 850;
    }
    QLabel#sourcePreviewMeta {
        color: #246a73;
        font-size: 13px;
        font-weight: 800;
    }
    QLabel#sourcePreviewNote {
        color: #536475;
        font-size: 13px;
    }
    QLabel#sourcePreviewReasonTitle {
        color: #263241;
        font-size: 14px;
        font-weight: 850;
        padding-top: 4px;
    }
    QLabel#sourcePreviewReason {
        color: #536475;
        font-size: 13px;
    }
    QPlainTextEdit#sourcePreviewText {
        background: #ffffff;
        border: 1px solid #b8dce2;
        border-radius: 10px;
        color: #263241;
        font-size: 13px;
        padding: 10px;
    }
    QTabWidget::pane {
        border: 1px solid #d8e2e7;
        border-radius: 12px;
        background: #ffffff;
        top: -1px;
    }
    QTabWidget {
        background: #ffffff;
    }
    QTabBar {
        background: #ffffff;
    }
    QTabBar::base {
        background: #ffffff;
        border-bottom: 1px solid #d8e2e7;
    }
    QTabBar::tab {
        background: #eef4f5;
        border: 1px solid #d8e2e7;
        padding: 8px 16px;
        margin-right: 2px;
        min-width: 92px;
        border-top-left-radius: 9px;
        border-top-right-radius: 9px;
        font-weight: 700;
        font-size: 13px;
        color: #6a7887;
    }
    QTabBar::tab:selected {
        background: #2f7f88;
        color: #ffffff;
        border-color: #2f7f88;
    }
    QProgressBar {
        border: none;
        border-radius: 4px;
        background: #d8e2e7;
        height: 6px;
    }
    QProgressBar::chunk {
        background: #2f7f88;
        border-radius: 4px;
    }
"""

SUMMARY_FLOW_STEP_DELAY_MS = 800


class AssistantWorker(QObject):
    token_received = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, question: str, chunks_path: str) -> None:
        super().__init__()
        self.question = question
        self.chunks_path = chunks_path
        self.cancel_requested = False

    def request_cancel(self) -> None:
        self.cancel_requested = True

    @Slot()
    def run(self) -> None:
        try:
            started = time.perf_counter()
            chunks = load_chunk_artifact(self.chunks_path)
            retrieved = retrieve_relevant_chunks(self.question, chunks)
            connector = OllamaConnector()
            trace = {
                "question": self.question,
                "total_chunks": len(chunks),
                "model": getattr(connector, "model", "unknown"),
                "prompt": "",
                "sources": [],
                "seconds": 0.0,
            }
            if not retrieved:
                self.token_received.emit(
                    "I could not find relevant information in the processed chunks."
                )
                trace["seconds"] = time.perf_counter() - started
                self.finished.emit(trace)
                return

            context_blocks = [
                f"[{item.chunk.chunk_id}] {item.chunk.text}" for item in retrieved
            ]
            prompt = _build_prompt(self.question, "\n\n".join(context_blocks))
            trace["prompt"] = prompt
            for token in connector.stream(prompt):
                if self.cancel_requested:
                    break
                self.token_received.emit(token)
            trace["sources"] = [
                {
                    "chunk_id": item.chunk.chunk_id,
                    "chunk_index": item.chunk.chunk_index,
                    "score": item.score,
                    "source_filename": item.chunk.source_filename,
                    "matched_terms": matched_query_terms(
                        self.question, item.chunk.text
                    ),
                    "text": item.chunk.text,
                }
                for item in retrieved
            ]
            trace["seconds"] = time.perf_counter() - started
            self.finished.emit(trace)
       
        except Exception as exc:
            self.failed.emit(str(exc))
class PlaygroundWorker(QObject):
    result_ready = Signal(object)
    failed = Signal(str)
    done = Signal()

    def __init__(self, question: str, raw_path: str, sizes: list[int]) -> None:
        super().__init__()
        self.question = question
        self.raw_path = raw_path
        self.sizes = sizes

    @Slot()
    def run(self) -> None:
        try:
            for slot, size in enumerate(self.sizes):
                chunks = chunk_in_memory(self.raw_path, size, size // 8)
                trace = answer_with_trace(self.question, chunks)
                trace["chunk_size"] = size
                trace["slot"] = slot
                self.result_ready.emit(trace)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.done.emit()
class CompareWorker(QObject):
    context_ready = Signal(object)
    result_ready = Signal(object)
    failed = Signal(str)
    done = Signal()

    def __init__(self, question: str, chunks_path: str, models: list[str]) -> None:
        super().__init__()
        self.question = question
        self.chunks_path = chunks_path
        self.models = models

    @Slot()
    def run(self) -> None:
        try:
            chunks = load_chunk_artifact(self.chunks_path)
            context = build_context(self.question, chunks)
            self.context_ready.emit(context)
            if not context["prompt"]:
                return
            for slot, model in enumerate(self.models):
                result = ask_model(context["prompt"], model)
                result["slot"] = slot
                self.result_ready.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.done.emit()
class ImmediateTooltipButton(QToolButton):
    def enterEvent(self, event) -> None:
        tooltip = self.toolTip()
        if tooltip:
            QToolTip.showText(self.mapToGlobal(self.rect().bottomRight()), tooltip, self)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        QToolTip.hideText()
        super().leaveEvent(event)


class LLMBundlerDesktop(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PPLLM Studio")
        self.resize(1320, 860)
        self.setMinimumSize(1180, 760)

        self.selected_file: Path | None = None
        self.raw_doc_id: str | None = None
        self.raw_artifact_path: str | None = None
        self.latest_chunks_path: str | None = None
        self.chat_request_in_flight = False
        self.chat_thread: QThread | None = None
        self.chat_worker: AssistantWorker | None = None
        self.current_assistant_label: QLabel | None = None
        self.current_assistant_layout: QVBoxLayout | None = None
        self.assistant_placeholder_visible = False
        self.workflow_sidebar_collapsed = False
        self.latest_saved_path: str | None = None

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

        self.icon_tip_label = QLabel(
            "Tip: hover the i icons before each step to see what PPLLM will do."
        )
        self.icon_tip_label.setObjectName("iconTipBanner")
        self.icon_tip_label.setWordWrap(True)
        content_layout.addWidget(self.icon_tip_label)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_workflow_rail())
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        self.main_splitter = splitter
        splitter.setSizes([WORKFLOW_RAIL_EXPANDED_WIDTH, 480, 770])
        splitter.setHandleWidth(6)
        content_layout.addWidget(splitter, stretch=1)

        root_layout.addWidget(content, stretch=1)

        self.setStyleSheet(STYLESHEET)
        self.setCentralWidget(root)
        self._sync_workflow_state()

    def _sync_workflow_state(self) -> None:
        ingest_done = bool(self.raw_artifact_path)
        chunks_done = bool(self.latest_chunks_path)
        self._set_step_status("ingest", "Done" if ingest_done else "Ready")
        self._set_step_status("process", "Done" if chunks_done else ("Ready" if ingest_done else "Locked"))
        self._set_step_status("assistant", "Ready" if chunks_done else "Needs chunks")
        self._set_step_status("export", "Ready" if chunks_done else "Locked")

    def _set_step_status(self, key: str, status: str) -> None:
        step = self.workflow_steps[key]
        step["status"].setText(status)
        step["frame"].setToolTip(f"{step['title'].text()} - {status}")
        step["frame"].setProperty("state", status.lower().replace(" ", "-"))
        step["frame"].style().unpolish(step["frame"])
        step["frame"].style().polish(step["frame"])

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("headerBar")
        header.setFixedHeight(64)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)

        self.app_title = QLabel("PPLLM Studio")
        self.app_title.setObjectName("titleLabel")
        self.app_subtitle = QLabel("Private local AI workspace")
        self.app_subtitle.setObjectName("subtitleLabel")
        title_stack = QVBoxLayout()
        title_stack.setSpacing(1)
        title_stack.addWidget(self.app_title)
        title_stack.addWidget(self.app_subtitle)
        layout.addLayout(title_stack, stretch=1)

        layout.addSpacing(20)

        self.privacy_badge = QLabel("Local only: nothing sent to cloud")
        self.privacy_badge.setObjectName("privacyBadge")
        self.privacy_badge.setAlignment(Qt.AlignCenter)
        self.privacy_badge.setFixedHeight(34)
        layout.addWidget(self.privacy_badge)

        layout.addSpacing(8)

        # Status badge
        self.status_badge = QLabel("● Idle")
        self.status_badge.setObjectName("statusBadge")
        self.status_badge.setAlignment(Qt.AlignCenter)
        self.status_badge.setMinimumWidth(180)
        self.status_badge.setFixedHeight(44)
        self._set_status("● Idle", "info")
        layout.addWidget(self.status_badge)

        return header

    def _build_workflow_rail(self) -> QFrame:
        self.workflow_rail = QFrame()
        self.workflow_rail.setObjectName("workflowRail")
        self.workflow_rail.setMinimumWidth(WORKFLOW_RAIL_EXPANDED_WIDTH)
        self.workflow_rail.setMaximumWidth(WORKFLOW_RAIL_EXPANDED_WIDTH)
        layout = QVBoxLayout(self.workflow_rail)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        toggle_row = QHBoxLayout()
        toggle_row.addStretch(1)
        self.workflow_toggle_btn = QToolButton()
        self.workflow_toggle_btn.setObjectName("infoButton")
        self.workflow_toggle_btn.setText("<")
        self.workflow_toggle_btn.setToolTip("Collapse workflow sidebar")
        self.workflow_toggle_btn.clicked.connect(self._toggle_workflow_sidebar)
        toggle_row.addWidget(self.workflow_toggle_btn)
        layout.addLayout(toggle_row)

        self.workflow_steps = {}
        for key, number, title, status in [
            ("ingest", "1", "Ingest", "Ready"),
            ("process", "2", "Process", "Locked"),
            ("assistant", "3", "Assistant", "Needs chunks"),
            ("export", "4", "Export", "Locked"),
        ]:
            row = self._build_workflow_step(number, title, status)
            self.workflow_steps[key] = row
            layout.addWidget(row["frame"])
        layout.addStretch(1)
        return self.workflow_rail

    def _build_workflow_step(self, number: str, title: str, status: str) -> dict:
        frame = QFrame()
        frame.setObjectName("workflowStep")
        row = QHBoxLayout(frame)
        row.setContentsMargins(10, 10, 10, 10)
        row.setSpacing(10)
        badge = QLabel(number)
        badge.setObjectName("stepBadge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(28, 28)
        title_label = QLabel(title)
        title_label.setObjectName("stepTitle")
        status_label = QLabel(status)
        status_label.setObjectName("stepStatus")
        text_stack = QVBoxLayout()
        text_stack.setSpacing(1)
        text_stack.addWidget(title_label)
        text_stack.addWidget(status_label)
        row.addWidget(badge)
        row.addLayout(text_stack, stretch=1)
        return {"frame": frame, "badge": badge, "title": title_label, "status": status_label}

    def _toggle_workflow_sidebar(self) -> None:
        self.workflow_sidebar_collapsed = not self.workflow_sidebar_collapsed
        width = (
            WORKFLOW_RAIL_COLLAPSED_WIDTH
            if self.workflow_sidebar_collapsed
            else WORKFLOW_RAIL_EXPANDED_WIDTH
        )
        self.workflow_rail.setMinimumWidth(width)
        self.workflow_rail.setMaximumWidth(width)
        self.workflow_toggle_btn.setText(">" if self.workflow_sidebar_collapsed else "<")
        self.workflow_toggle_btn.setToolTip(
            "Expand workflow sidebar"
            if self.workflow_sidebar_collapsed
            else "Collapse workflow sidebar"
        )
        for step in self.workflow_steps.values():
            step["title"].setVisible(not self.workflow_sidebar_collapsed)
            step["status"].setVisible(not self.workflow_sidebar_collapsed)
            step["frame"].setToolTip(
                f"{step['title'].text()} - {step['status'].text()}"
            )

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
        self.preview_tabs.setDocumentMode(False)
        self.preview_tabs.tabBar().setDrawBase(False)

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

        assistant_tab = QWidget()
        assistant_layout = QVBoxLayout(assistant_tab)
        assistant_layout.setContentsMargins(12, 12, 12, 12)
        assistant_layout.setSpacing(10)
        self.chat_header = QFrame()
        self.chat_header.setObjectName("assistantHeader")
        chat_header_layout = QHBoxLayout(self.chat_header)
        chat_header_layout.setContentsMargins(12, 10, 12, 10)
        chat_header_layout.setSpacing(12)
        chat_title_stack = QVBoxLayout()
        chat_title_stack.setSpacing(1)
        self.chat_title_label = QLabel("Assistant")
        self.chat_title_label.setObjectName("assistantTitle")
        self.chat_model_label = QLabel("Local model: llama3.1:8b")
        self.chat_model_label.setObjectName("helperLabel")
        self.chat_grounding_label = QLabel(
            "Answers are grounded in retrieved chunks from your processed file."
        )
        self.chat_grounding_label.setObjectName("helperLabel")
        chat_title_stack.addWidget(self.chat_title_label)
        chat_title_stack.addWidget(self.chat_model_label)
        chat_title_stack.addWidget(self.chat_grounding_label)
        self.chat_status_label = QLabel("Ready after chunks")
        self.chat_status_label.setObjectName("assistantStatus")
        self.chat_status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        chat_header_layout.addLayout(chat_title_stack, stretch=1)
        chat_header_layout.addWidget(self.chat_status_label)
        assistant_layout.addWidget(self.chat_header)
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setObjectName("chatScrollArea")
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setMinimumHeight(300)
        self.chat_messages = QWidget()
        self.chat_messages.setObjectName("chatMessages")
        self.chat_messages_layout = QVBoxLayout(self.chat_messages)
        self.chat_messages_layout.setContentsMargins(14, 14, 14, 14)
        self.chat_messages_layout.setSpacing(10)
        self.chat_messages_layout.setAlignment(Qt.AlignTop)
        self.chat_scroll.setWidget(self.chat_messages)
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask about the processed chunks...")
        self.chat_input.returnPressed.connect(self._submit_chatbot_question)
        self.chat_ask_btn = QPushButton("Ask")
        self.chat_ask_btn.clicked.connect(self._submit_chatbot_question)
        self.chat_ask_btn.setEnabled(False)
        self.chat_stop_btn = QPushButton("Stop")
        self.chat_stop_btn.setObjectName("stopBtn")
        self.chat_stop_btn.clicked.connect(self.stop_chatbot_generation)
        self.chat_stop_btn.setVisible(False)
        self.chat_stop_btn.setEnabled(False)
        chat_row = QHBoxLayout()
        chat_row.setSpacing(8)
        chat_row.addWidget(self.chat_input, stretch=1)
        chat_row.addWidget(self.chat_stop_btn)
        chat_row.addWidget(self.chat_ask_btn)
        assistant_layout.addWidget(self.chat_scroll, stretch=1)
        assistant_layout.addLayout(chat_row)

        self.preview_tabs.addTab(self.preview, "Text")
        self.preview_tabs.addTab(self.chunk_preview, "Chunks")
        self.preview_tabs.addTab(assistant_tab, "Assistant")
        layout.addWidget(self.preview_tabs, stretch=2)

        log_header = QHBoxLayout()
        log_header.setSpacing(8)
        self.log_label = QLabel("ACTIVITY LOG")
        self.log_label.setObjectName("sectionLabel")
        self.log_placeholder_line = QLabel("Recent local processing events")
        self.log_placeholder_line.setObjectName("helperLabel")
        log_header.addWidget(self.log_label)
        log_header.addWidget(self.log_placeholder_line, stretch=1)
        layout.addLayout(log_header)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Status updates will appear here...")
        self.log.setMinimumHeight(96)
        self.log.setMaximumHeight(130)
        layout.addWidget(self.log)

        saved_path_row = QHBoxLayout()
        saved_path_row.setSpacing(8)
        self.saved_path_label = QLabel("No saved file yet")
        self.saved_path_label.setObjectName("helperLabel")
        self.copy_saved_path_btn = QPushButton("Copy Path")
        self.copy_saved_path_btn.clicked.connect(self.copy_latest_saved_path)
        self.copy_saved_path_btn.setEnabled(False)
        self.open_saved_folder_btn = QPushButton("Open Folder")
        self.open_saved_folder_btn.clicked.connect(self.open_latest_saved_folder)
        self.open_saved_folder_btn.setEnabled(False)
        saved_path_row.addWidget(self.saved_path_label, stretch=1)
        saved_path_row.addWidget(self.copy_saved_path_btn)
        saved_path_row.addWidget(self.open_saved_folder_btn)
        layout.addLayout(saved_path_row)
        return panel

    def _build_ingest_box(self) -> QGroupBox:
        box = QGroupBox("Step 1 - Ingest Document")
        layout = QVBoxLayout(box)
        layout.setSpacing(10)

        row = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("Select a PDF, DOCX, or PPTX file...")
        self.file_path_input.setReadOnly(True)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.select_file)
        row.addWidget(self.file_path_input, stretch=1)
        row.addWidget(browse_btn)
        self.ingest_info_btn = ImmediateTooltipButton()
        self.ingest_info_btn.setObjectName("infoButton")
        self.ingest_info_btn.setText("i")
        self.ingest_info_btn.setToolTip(
            "Choose only files you want to use with AI.\n"
            "Originals stay unchanged.\n\n"
            "PPLLM creates a clean text copy that AI tools can search."
        )
        row.addWidget(self.ingest_info_btn)
        layout.addLayout(row)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.extract_btn = QPushButton("Extract + Save Raw JSON")
        self.extract_btn.setObjectName("primaryBtn")
        self.extract_btn.clicked.connect(self.extract_and_save_raw)
        self.save_raw_copy_btn = QPushButton("Save Raw JSON As...")
        self.save_raw_copy_btn.clicked.connect(self.save_raw_copy_as)
        self.save_raw_copy_btn.setEnabled(False)
        action_row.addWidget(self.extract_btn, stretch=2)
        action_row.addWidget(self.save_raw_copy_btn, stretch=1)
        layout.addLayout(action_row)

        return box

    def _build_chunk_box(self) -> QGroupBox:
        self.chunk_box = QGroupBox("Step 2 - Process && Chunk")
        layout = QVBoxLayout(self.chunk_box)
        layout.setSpacing(10)

        chunk_info_row = QHBoxLayout()
        chunk_info_row.setSpacing(6)
        self.chunk_explainer_label = QLabel(
            "Large files are split into searchable chunks so the Assistant can find the right evidence."
        )
        self.chunk_explainer_label.setObjectName("chunkExplainer")
        self.chunk_explainer_label.setWordWrap(True)
        chunk_info_row.addWidget(self.chunk_explainer_label, stretch=1)
        self.chunk_info_btn = ImmediateTooltipButton()
        self.chunk_info_btn.setObjectName("infoButton")
        self.chunk_info_btn.setText("i")
        self.chunk_info_btn.setToolTip(
            "Large files are split into smaller searchable pieces called chunks.\n\n"
            "This helps local AI tools search long documents more reliably.\n"
            "The Assistant retrieves the most relevant chunks before answering."
        )
        chunk_info_row.addWidget(self.chunk_info_btn)
        layout.addLayout(chunk_info_row)
        layout.addWidget(self._build_chunk_visual())

        self.chunk_form = QFormLayout()
        self.chunk_form.setSpacing(8)
        self.chunk_form.setLabelAlignment(Qt.AlignLeft)
        self.chunk_form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.chunk_size = QSpinBox()
        self.chunk_size.setRange(100, 4000)
        self.chunk_size.setValue(800)
        self.chunk_overlap = QSpinBox()
        self.chunk_overlap.setRange(0, 1000)
        self.chunk_overlap.setValue(100)
        self.chunk_form.addRow("Chunk size (chars):", self.chunk_size)
        self.chunk_form.addRow("Chunk overlap (chars):", self.chunk_overlap)
        layout.addLayout(self.chunk_form)

        self.encrypt_checkbox = QCheckBox("Encrypt chunk artifact after saving")
        self.encrypt_checkbox.setToolTip(
            "Encrypts the chunk JSON using RSA + AES-256 hybrid encryption before transfer."
        )
        encryption_row = QHBoxLayout()
        encryption_row.setSpacing(6)
        encryption_row.addWidget(self.encrypt_checkbox, stretch=1)
        self.encryption_info_btn = ImmediateTooltipButton()
        self.encryption_info_btn.setObjectName("infoButton")
        self.encryption_info_btn.setText("i")
        self.encryption_info_btn.setToolTip(
            "Encryption protects the processed chunk file if you plan to move it outside this computer.\n\n"
            "Use it when:\n"
            "- emailing the chunk file\n"
            "- uploading it to another tool\n"
            "- storing it in shared cloud folders\n"
            "- working with sensitive documents\n\n"
            "You may leave it off when:\n"
            "- staying fully local\n"
            "- only using the built-in PPLLM Assistant"
        )
        encryption_row.addWidget(self.encryption_info_btn)
        layout.addLayout(encryption_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.process_btn = QPushButton("Process + Save Chunk JSON")
        self.process_btn.setObjectName("successBtn")
        self.process_btn.clicked.connect(self.process_and_save_chunks)
        self.process_btn.setEnabled(False)
        self.save_chunk_copy_btn = QPushButton("Save Chunk JSON As...")
        self.save_chunk_copy_btn.clicked.connect(self.save_chunk_copy_as)
        self.save_chunk_copy_btn.setEnabled(False)
        action_row.addWidget(self.process_btn, stretch=2)
        action_row.addWidget(self.save_chunk_copy_btn, stretch=1)
        layout.addLayout(action_row)

        self.playground_btn = QPushButton("Open Chunk Playground")
        self.playground_btn.setToolTip(
            "Try two chunk sizes on the same question and compare what the AI finds. "
            "Nothing is saved."
        )
        self.playground_btn.clicked.connect(self.open_chunk_playground)
        self.compare_btn = QPushButton("Open Model Comparison")
        self.compare_btn.setToolTip(
            "Ask a small and a large model the same question and compare speed and answers."
        )
        self.compare_btn.clicked.connect(self.open_model_comparison)
        lab_row = QHBoxLayout()
        lab_row.setSpacing(8)
        lab_row.addWidget(self.playground_btn, stretch=1)
        lab_row.addWidget(self.compare_btn, stretch=1)
        layout.addLayout(lab_row)

        self.data_summary_frame = QFrame()
        self.data_summary_frame.setObjectName("dataSummaryFlow")
        self.data_summary_frame.setMaximumHeight(116)
        data_summary_layout = QVBoxLayout(self.data_summary_frame)
        data_summary_layout.setContentsMargins(9, 6, 9, 7)
        data_summary_layout.setSpacing(5)
        self.summary_title_label = QLabel("Data journey")
        self.summary_title_label.setObjectName("summaryTitle")
        data_summary_layout.addWidget(self.summary_title_label)

        flow_row = QHBoxLayout()
        flow_row.setSpacing(6)
        self.summary_file_label = self._build_summary_chip()
        self.summary_chunks_label = self._build_summary_chip()
        self.summary_save_label = self._build_summary_chip()
        self.summary_encryption_label = self._build_summary_chip()
        for index, chip in enumerate(
            [
                self.summary_file_label,
                self.summary_chunks_label,
                self.summary_save_label,
                self.summary_encryption_label,
            ]
        ):
            flow_row.addWidget(chip, stretch=1)
            if index < 3:
                arrow = QLabel(">")
                arrow.setObjectName("summaryArrow")
                arrow.setAlignment(Qt.AlignCenter)
                flow_row.addWidget(arrow)
        data_summary_layout.addLayout(flow_row)
        self.data_summary_frame.setVisible(False)
        layout.addWidget(self.data_summary_frame)

        return self.chunk_box

    def _build_chunk_visual(self) -> QFrame:
        self.chunk_visual_frame = QFrame()
        self.chunk_visual_frame.setObjectName("chunkVisual")
        self.chunk_visual_frame.setMaximumHeight(46)
        visual_layout = QHBoxLayout(self.chunk_visual_frame)
        visual_layout.setContentsMargins(8, 5, 8, 5)
        visual_layout.setSpacing(6)

        self.long_document_label = QLabel("Long document")
        self.long_document_label.setObjectName("documentBlock")
        self.long_document_label.setAlignment(Qt.AlignCenter)
        self.long_document_label.setMinimumHeight(30)
        visual_layout.addWidget(self.long_document_label, stretch=2)

        arrow = QLabel(">")
        arrow.setObjectName("summaryArrow")
        arrow.setAlignment(Qt.AlignCenter)
        visual_layout.addWidget(arrow)

        self.chunk_visual_chips = []
        for label in ("Chunk 1", "Chunk 2", "Chunk 3"):
            chip = QLabel(label)
            chip.setObjectName("chunkMiniCard")
            chip.setAlignment(Qt.AlignCenter)
            chip.setMinimumHeight(30)
            self.chunk_visual_chips.append(chip)
            visual_layout.addWidget(chip, stretch=1)
        return self.chunk_visual_frame

    def _build_summary_chip(self) -> QLabel:
        chip = QLabel()
        chip.setObjectName("summaryChip")
        chip.setAlignment(Qt.AlignCenter)
        chip.setWordWrap(True)
        chip.setMinimumHeight(42)
        return chip

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
        self.file_path_input.setText(self.selected_file.name)
        self.file_path_input.setToolTip(str(self.selected_file))
        self._log(f"Selected: {self.selected_file.name}")

        self._warn_if_sensitive(self.selected_file.name)

    _SENSITIVE_KEYWORDS = {
        "bank",
        "confidential",
        "financial",
        "grades",
        "health",
        "id",
        "license",
        "medical",
        "passport",
        "password",
        "payroll",
        "private",
        "secret",
        "ssn",
        "student",
        "tax",
        "transcript",
    }

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
                self._sync_workflow_state()
                self._log(f"Cancelled - sensitive file not processed: {filename}")
            else:
                self._log(f"Sensitive file warning accepted: {filename}")

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
        if not self._confirm_permission_review(file_type):
            self._log(f"Permission review cancelled: {self.selected_file.name}")
            return

        self._set_status("● Working...", "working")
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
                    self._log("Cookie extraction mode: safe metadata only (values excluded).")
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
            self._set_latest_saved_path(output_path)
            self.process_btn.setEnabled(True)
            self.save_raw_copy_btn.setEnabled(True)
            self._sync_workflow_state()
            self._set_status("● Raw Saved", "success")
            self.progress.setVisible(False)

            chars = len(result["text"])
            pages = result.get("page_count")
            page_info = f", {pages} pages" if pages else ""
            self._log(f"Raw artifact saved - {chars:,} chars{page_info}")
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

        self._set_status("● Chunking...", "working")
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
            self._set_latest_saved_path(self.latest_chunks_path)
            self.save_chunk_copy_btn.setEnabled(True)
            self.chat_ask_btn.setEnabled(True)
            self._sync_workflow_state()
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

            chunk_path = Path(self.latest_chunks_path)
            self._log(f"Chunking complete - {result['total_chunks']} chunks created")
            self._log(f"Saved file: {chunk_path.name}")
            self._log(f"Folder: {chunk_path.parent}")
            if should_encrypt and "encrypted_path" in result:
                encrypted_path = Path(result["encrypted_path"])
                self._log(f"Encrypted file: {encrypted_path.name}")

            summary = self._show_processing_summary(result, should_encrypt)
            QMessageBox.information(self, "Data Journey Summary", summary)
        except Exception as exc:
            self._set_status("● Error", "warn")
            self.progress.setVisible(False)
            self._warn(f"Failed to process chunks.\n\n{exc}")

    def _show_processing_summary(self, result: dict, encrypted: bool) -> str:
        summary = self._build_processing_summary(result, encrypted)
        source_filename = result.get("source_filename") or "selected file"
        total_chunks = result.get("total_chunks", 0)
        output_path = result.get("output_path", "")
        output_name = Path(output_path).name if output_path else "local JSON"
        self.summary_file_label.setText(f"Input file\n{source_filename}")
        self.summary_chunks_label.setText(f"Chunks\n{total_chunks} pieces")
        self.summary_save_label.setText(f"Local save\n{output_name}")
        self.summary_encryption_label.setText(f"Encryption\n{'On' if encrypted else 'Off'}")
        self.data_summary_frame.setToolTip(summary)
        self.data_summary_frame.setVisible(True)
        self._reset_summary_flow()
        self._start_summary_flow_animation()
        return summary

    def _summary_chips(self) -> list[QLabel]:
        return [
            self.summary_file_label,
            self.summary_chunks_label,
            self.summary_save_label,
            self.summary_encryption_label,
        ]

    def _reset_summary_flow(self) -> None:
        for chip in self._summary_chips():
            self._set_summary_chip_state(chip, "pending")

    def _activate_summary_step(self, active_index: int) -> None:
        for index, chip in enumerate(self._summary_chips()):
            if index < active_index:
                self._set_summary_chip_state(chip, "done")
            elif index == active_index:
                self._set_summary_chip_state(chip, "active")
            else:
                self._set_summary_chip_state(chip, "pending")

    def _set_summary_chip_state(self, chip: QLabel, state: str) -> None:
        chip.setProperty("state", state)
        chip.style().unpolish(chip)
        chip.style().polish(chip)

    def _start_summary_flow_animation(self) -> None:
        for index in range(len(self._summary_chips())):
            QTimer.singleShot(
                SUMMARY_FLOW_STEP_DELAY_MS * (index + 1),
                lambda step=index: self._activate_summary_step(step),
            )

    def _build_processing_summary(self, result: dict, encrypted: bool) -> str:
        source_filename = result.get("source_filename") or "selected file"
        total_chunks = result.get("total_chunks", 0)
        output_path = result.get("output_path", "local chunk file")
        output_name = Path(output_path).name if output_path else "local chunk file"
        lines = [
            "Data journey",
            f"File: {source_filename}",
            f"Chunks created: {total_chunks} searchable pieces",
            f"Saved locally: {output_name}",
            f"Encryption: {'On' if encrypted else 'Off'}",
            "Original file: Unchanged",
        ]
        encrypted_path = result.get("encrypted_path")
        if encrypted and encrypted_path:
            lines.append(f"Encrypted copy: {Path(encrypted_path).name}")
        return "\n".join(lines)

    def _submit_chatbot_question(self) -> None:
        self.ask_chatbot()

    def ask_chatbot(self) -> None:
        if self.chat_request_in_flight:
            return
        if not self.latest_chunks_path:
            self._warn("Process a document into chunks before asking the assistant.")
            return
        question = self.chat_input.text().strip()
        if not question:
            self._warn("Enter a question first.")
            return
        self.chat_request_in_flight = True
        self.chat_ask_btn.setEnabled(False)
        self.chat_stop_btn.setVisible(True)
        self.chat_stop_btn.setEnabled(True)
        self.chat_input.setEnabled(False)
        self.chat_status_label.setText("Thinking")
        self._add_user_message(question)
        self._start_assistant_message()
        self.chat_input.clear()
        self.chat_thread = QThread(self)
        self.chat_worker = AssistantWorker(question, self.latest_chunks_path)
        self.chat_worker.moveToThread(self.chat_thread)
        self.chat_thread.started.connect(self.chat_worker.run)
        self.chat_worker.token_received.connect(self._append_chat_token)
        self.chat_worker.finished.connect(self._finish_chat_response)
        self.chat_worker.failed.connect(self._handle_chat_error)
        self.chat_worker.finished.connect(self.chat_thread.quit)
        self.chat_worker.failed.connect(self.chat_thread.quit)
        self.chat_thread.finished.connect(self.chat_worker.deleteLater)
        self.chat_thread.finished.connect(self.chat_thread.deleteLater)
        self.chat_thread.finished.connect(self._clear_chat_worker_refs)
        self.chat_thread.start()

    def stop_chatbot_generation(self) -> None:
        if self.chat_worker is not None:
            self.chat_worker.request_cancel()
        self.chat_stop_btn.setEnabled(False)
        self.chat_status_label.setText("Stopping")

    def _add_user_message(self, text: str) -> None:
        self._add_message_bubble("user", text)
        self._scroll_chat_to_bottom()

    def _start_assistant_message(self) -> None:
        self.current_assistant_label, self.current_assistant_layout = (
            self._add_message_bubble("assistant", "Thinking...")
        )
        self.assistant_placeholder_visible = True
        self._scroll_chat_to_bottom()

    def _add_message_bubble(self, role: str, text: str) -> tuple[QLabel, QVBoxLayout]:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        bubble = QFrame()
        bubble.setObjectName("userMessage" if role == "user" else "assistantMessage")
        bubble.setMaximumWidth(620)
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(14, 10, 14, 10)
        bubble_layout.setSpacing(8)

        label = QLabel(text)
        label.setObjectName("messageText")
        label.setTextFormat(Qt.PlainText)
        label.setWordWrap(True)
        bubble_layout.addWidget(label)

        avatar = self._build_chat_avatar(role)
        if role == "user":
            row_layout.addStretch(1)
            row_layout.addWidget(bubble)
            row_layout.addWidget(avatar, alignment=Qt.AlignTop)
        else:
            row_layout.addWidget(avatar, alignment=Qt.AlignTop)
            row_layout.addWidget(bubble)
            row_layout.addStretch(1)

        self.chat_messages_layout.addWidget(row)
        return label, bubble_layout

    def _build_chat_avatar(self, role: str) -> QLabel:
        avatar = QLabel("U" if role == "user" else "AI")
        avatar.setObjectName("userAvatar" if role == "user" else "assistantAvatar")
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(30, 30)
        avatar.setToolTip("You" if role == "user" else "PPLLM Assistant")
        return avatar

    def _append_chat_token(self, token: str) -> None:
        if self.current_assistant_label is None:
            self._start_assistant_message()
        assert self.current_assistant_label is not None
        if self.assistant_placeholder_visible:
            self.current_assistant_label.setText(token)
            self.assistant_placeholder_visible = False
        else:
            self.current_assistant_label.setText(
                self.current_assistant_label.text() + token
            )
        self._scroll_chat_to_bottom()

    def _finish_chat_response(self, trace: dict) -> None:
        sources = trace.get("sources", [])
        self.last_trace = trace
        print("TRACE", trace.get("total_chunks"), trace.get("model"),
              round(trace.get("seconds", 0), 1),
              [(s["chunk_id"], s["score"]) for s in sources])
        source_items = self._normalize_source_items(sources)
        if source_items and self.current_assistant_layout is not None:
            visible_sources = source_items[:VISIBLE_SOURCE_CHIP_LIMIT]
            source_row = QHBoxLayout()
            source_row.setSpacing(6)
            for source in visible_sources:
                chunk_id = source["chunk_id"]
                chip = QPushButton(f"Source {chunk_id}")
                chip.setObjectName("sourceChip")
                chip.setToolTip("Click to preview the chunk used for this answer.")
                chip.clicked.connect(
                    lambda checked=False, item=source: self._show_source_preview(item)
                )
                source_row.addWidget(chip)
            source_row.addStretch(1)
            self.current_assistant_layout.addLayout(source_row)
            if len(source_items) > len(visible_sources):
                source_note = QLabel(
                    f"Used {len(source_items)} chunks, showing strongest sources."
                )
                source_note.setObjectName("sourceNote")
                self.current_assistant_layout.addWidget(source_note)
        if self.current_assistant_layout is not None:
            explain_btn = QPushButton("Explain this answer")
            explain_btn.setObjectName("sourceChip")
            explain_btn.setToolTip(
                "See which parts of your document the AI read and the exact text it was sent."
            )
            explain_btn.clicked.connect(
                lambda checked=False, t=trace: self._build_explain_dialog(t).exec()
            )
            self.current_assistant_layout.addWidget(explain_btn, 0, Qt.AlignLeft)
        self.current_assistant_label = None
        self.current_assistant_layout = None
        self.assistant_placeholder_visible = False
        self._scroll_chat_to_bottom()
        self._reset_chat_request_state()

    def _normalize_source_items(self, sources: list) -> list[dict]:
        source_items = []
        for source in sources:
            if isinstance(source, dict):
                source_items.append(
                    {
                        "chunk_id": str(source.get("chunk_id", "")),
                        "source_filename": str(source.get("source_filename", "")),
                        "matched_terms": [
                            str(term) for term in source.get("matched_terms", [])
                        ],
                        "text": str(source.get("text", "")),
                        "chunk_index": int(source.get("chunk_index", -1)),
                        "score": int(source.get("score", 0)),
                    }
                )
            else:
                source_items.append(
                    {
                        "chunk_id": str(source),
                        "source_filename": "",
                        "matched_terms": [],
                        "text": "",
                        "chunk_index": -1,
                        "score": 0,
                    }
                )
        return [item for item in source_items if item["chunk_id"]]

    def _show_source_preview(self, source: dict) -> None:
        self._build_source_preview_dialog(source).exec()

    def _build_source_preview_dialog(self, source: dict) -> QDialog:
        chunk_id = source.get("chunk_id", "unknown")
        filename = source.get("source_filename") or "processed file"
        text = (source.get("text") or "").strip()
        preview = text[:600]
        if len(text) > len(preview):
            preview += "..."
        if not preview:
            preview = "Preview text is not available for this source chip."

        dialog = QDialog(self)
        dialog.setObjectName("sourcePreviewDialog")
        dialog.setWindowTitle("Source Chunk")
        dialog.setMinimumSize(640, 460)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("Source Chunk")
        title.setObjectName("sourcePreviewTitle")
        layout.addWidget(title)

        meta = QLabel(f"Chunk {chunk_id} · {filename}")
        meta.setObjectName("sourcePreviewMeta")
        meta.setWordWrap(True)
        layout.addWidget(meta)

        note = QLabel("This is the context the Assistant used to answer.")
        note.setObjectName("sourcePreviewNote")
        note.setWordWrap(True)
        layout.addWidget(note)

        matched_terms = source.get("matched_terms", [])
        reason_title = QLabel("Why this source was used")
        reason_title.setObjectName("sourcePreviewReasonTitle")
        layout.addWidget(reason_title)

        if matched_terms:
            reason_text = f"Matched question terms: {', '.join(matched_terms)}"
        else:
            reason_text = (
                "Selected as one of the strongest nearby chunks for this question. "
                "Exact keyword matches were limited."
            )
        reason = QLabel(reason_text)
        reason.setObjectName("sourcePreviewReason")
        reason.setWordWrap(True)
        layout.addWidget(reason)

        preview_box = QPlainTextEdit()
        preview_box.setObjectName("sourcePreviewText")
        preview_box.setReadOnly(True)
        preview_box.setPlainText(preview)
        preview_box.setMinimumHeight(260)
        layout.addWidget(preview_box, stretch=1)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)
        return dialog
    def _build_explain_dialog(self, trace: dict) -> QDialog:
        sources = self._normalize_source_items(trace.get("sources", []))
        total = trace.get("total_chunks", 0)
        used = len(sources)

        dialog = QDialog(self)
        dialog.setObjectName("sourcePreviewDialog")
        dialog.setWindowTitle("Explain This Answer")
        dialog.setMinimumSize(720, 560)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("Explain This Answer")
        title.setObjectName("sourcePreviewTitle")
        layout.addWidget(title)

        if used:
            percent = round(100 * used / total) if total else 0
            headline_text = (
                f"The AI read {used} of {total} pieces of your document "
                f"(about {percent}%). It never sees the whole file, only these pieces."
            )
        else:
            headline_text = (
                "No part of your document matched this question, so nothing was sent "
                "to the AI. 'Not found in the document' is an honest answer, not a failure."
            )
        headline = QLabel(headline_text)
        headline.setObjectName("sourcePreviewReason")
        headline.setWordWrap(True)
        layout.addWidget(headline)

        meta = QLabel(
            f"Model: {trace.get('model', 'unknown')} · "
            f"Time: {trace.get('seconds', 0):.1f} s"
        )
        meta.setObjectName("sourcePreviewMeta")
        layout.addWidget(meta)

        tabs = QTabWidget()
        tabs.setElideMode(Qt.ElideNone)
        tabs.tabBar().setExpanding(False)

        read_box = QPlainTextEdit()
        read_box.setReadOnly(True)
        read_box.setPlainText(
            "\n\n".join(
                f"Piece {s['chunk_index']} of {total} "
                f"(id {s['chunk_id']}, score {s['score']})\n{s['text']}"
                for s in sources
            )
            or "No pieces were read."
        )
        tabs.addTab(read_box, "What the AI read")

        why_lines = [
            "PPLLM gives every piece a score by counting how often the keywords "
            "in your question appear in it. It then keeps up to 4 of the highest "
            "scoring pieces and ignores the rest.",
            "",
        ]
        for s in sources:
            terms = ", ".join(s["matched_terms"]) or "no exact keyword match"
            why_lines.append(
                f"Piece {s['chunk_index']}: score {s['score']}, matched words: {terms}"
            )
        why_box = QPlainTextEdit()
        why_box.setReadOnly(True)
        why_box.setPlainText("\n".join(why_lines))
        tabs.addTab(why_box, "Why these pieces")

        prompt_text = trace.get("prompt") or "Nothing was sent to the AI for this question."
        prompt_box = QPlainTextEdit()
        prompt_box.setReadOnly(True)
        prompt_box.setPlainText(prompt_text)
        tabs.addTab(prompt_box, "Exact text sent to the AI")

        layout.addWidget(tabs, stretch=1)

        button_row = QHBoxLayout()
        copy_btn = QPushButton("Copy prompt")
        copy_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(prompt_text)
        )
        button_row.addWidget(copy_btn)
        button_row.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_row.addWidget(close_btn)
        layout.addLayout(button_row)
        return dialog
    def open_chunk_playground(self) -> None:
        if not self.raw_artifact_path:
            self._warn("Please ingest a document first (Step 1).")
            return
        if getattr(self, "playground_dialog", None) is None:
            self.playground_dialog = self._build_playground_dialog()
        self.playground_dialog.show()
        self.playground_dialog.raise_()

    def _build_playground_dialog(self) -> QDialog:
        dialog = QDialog(self)
        dialog.setObjectName("sourcePreviewDialog")
        dialog.setWindowTitle("Chunk Playground")
        dialog.setMinimumSize(1000, 680)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("Chunk Playground")
        title.setObjectName("sourcePreviewTitle")
        layout.addWidget(title)

        intro = QLabel(
            "Ask the same question with two chunk sizes. Small pieces can cut a fact in half; "
            "large pieces can bury it in unrelated text. Watch how the pieces the AI reads, "
            "and its answer, change. Nothing here is saved."
        )
        intro.setObjectName("sourcePreviewNote")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        controls = QHBoxLayout()
        self.pg_question = QLineEdit()
        self.pg_question.setPlaceholderText("Ask a question about your document...")
        controls.addWidget(self.pg_question, stretch=3)
        self.pg_size_a = QSpinBox()
        self.pg_size_a.setRange(100, 4000)
        self.pg_size_a.setValue(200)
        self.pg_size_b = QSpinBox()
        self.pg_size_b.setRange(100, 4000)
        self.pg_size_b.setValue(1500)
        controls.addWidget(QLabel("Size A:"))
        controls.addWidget(self.pg_size_a)
        controls.addWidget(QLabel("Size B:"))
        controls.addWidget(self.pg_size_b)
        self.pg_run_btn = QPushButton("Run both")
        self.pg_run_btn.setObjectName("successBtn")
        self.pg_run_btn.clicked.connect(self._run_chunk_playground)
        controls.addWidget(self.pg_run_btn)
        layout.addLayout(controls)

        columns = QHBoxLayout()
        self.pg_outputs = []
        for _ in range(2):
            box = QPlainTextEdit()
            box.setReadOnly(True)
            box.setPlainText("Results will appear here.")
            columns.addWidget(box, stretch=1)
            self.pg_outputs.append(box)
        layout.addLayout(columns, stretch=1)
        return dialog

    def _run_chunk_playground(self) -> None:
        question = self.pg_question.text().strip()
        if not question:
            self._warn("Type a question first.")
            return
        sizes = [self.pg_size_a.value(), self.pg_size_b.value()]
        for box, size in zip(self.pg_outputs, sizes):
            box.setPlainText(f"Chunk size {size}: splitting and asking the AI...")
        self.pg_run_btn.setEnabled(False)

        self.pg_thread = QThread(self)
        self.pg_worker = PlaygroundWorker(question, self.raw_artifact_path, sizes)
        self.pg_worker.moveToThread(self.pg_thread)
        self.pg_thread.started.connect(self.pg_worker.run)
        self.pg_worker.result_ready.connect(self._show_playground_result)
        self.pg_worker.failed.connect(self._warn)
        self.pg_worker.done.connect(self._playground_done)
        self.pg_worker.done.connect(self.pg_thread.quit)
        self.pg_thread.finished.connect(self.pg_worker.deleteLater)
        self.pg_thread.finished.connect(self.pg_thread.deleteLater)
        self.pg_thread.start()

    def _show_playground_result(self, trace: dict) -> None:
        sources = self._normalize_source_items(trace.get("sources", []))
        total = trace.get("total_chunks", 0)
        lines = [
            f"CHUNK SIZE: {trace.get('chunk_size')} characters",
            f"Document split into {total} pieces. The AI read {len(sources)} of them.",
            f"Time: {trace.get('seconds', 0):.1f} s",
            "",
            "ANSWER",
            trace.get("answer") or "(no answer)",
            "",
            "PIECES THE AI READ",
        ]
        for s in sources:
            terms = ", ".join(s["matched_terms"]) or "none"
            lines.append(f"Piece {s['chunk_index']} (score {s['score']}, matched: {terms})")
            lines.append(s["text"])
            lines.append("")
        self.pg_outputs[trace["slot"]].setPlainText("\n".join(lines))

    def _playground_done(self) -> None:
        self.pg_run_btn.setEnabled(True)
    def open_model_comparison(self) -> None:
        if not getattr(self, "latest_chunks_path", None):
            self._warn("Please process your document first (Step 2).")
            return
        try:
            models = list_local_models()
        except Exception:
            self._warn("Could not reach Ollama. Start Ollama and try again.")
            return
        if len(models) < 2:
            self._warn(
                "Model Comparison needs at least two local models.\n\n"
                "Install a small one in Terminal:  ollama pull llama3.2:1b"
            )
            return
        if getattr(self, "compare_dialog", None) is None:
            self.compare_dialog = self._build_compare_dialog()
        self._fill_model_choices(models)
        self.compare_dialog.show()
        self.compare_dialog.raise_()

    def _build_compare_dialog(self) -> QDialog:
        dialog = QDialog(self)
        dialog.setObjectName("sourcePreviewDialog")
        dialog.setWindowTitle("Model Comparison")
        dialog.setMinimumSize(1000, 680)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("Model Comparison")
        title.setObjectName("sourcePreviewTitle")
        layout.addWidget(title)

        intro = QLabel(
            "Both models receive exactly the same pieces of your document, so only the model "
            "changes. Bigger models usually answer better but are slower and need a stronger "
            "computer. The first run of each model includes time to load it into memory."
        )
        intro.setObjectName("sourcePreviewNote")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        controls = QHBoxLayout()
        self.cmp_question = QLineEdit()
        self.cmp_question.setPlaceholderText("Ask a question about your document...")
        controls.addWidget(self.cmp_question, stretch=3)
        self.cmp_model_a = QComboBox()
        self.cmp_model_b = QComboBox()
        controls.addWidget(QLabel("Model A:"))
        controls.addWidget(self.cmp_model_a)
        controls.addWidget(QLabel("Model B:"))
        controls.addWidget(self.cmp_model_b)
        self.cmp_run_btn = QPushButton("Compare")
        self.cmp_run_btn.setObjectName("successBtn")
        self.cmp_run_btn.clicked.connect(self._run_model_comparison)
        controls.addWidget(self.cmp_run_btn)
        layout.addLayout(controls)

        self.cmp_context_label = QLabel("")
        self.cmp_context_label.setObjectName("sourcePreviewReason")
        self.cmp_context_label.setWordWrap(True)
        layout.addWidget(self.cmp_context_label)

        columns = QHBoxLayout()
        self.cmp_outputs = []
        for _ in range(2):
            box = QPlainTextEdit()
            box.setReadOnly(True)
            box.setPlainText("Results will appear here.")
            columns.addWidget(box, stretch=1)
            self.cmp_outputs.append(box)
        layout.addLayout(columns, stretch=1)
        return dialog

    def _fill_model_choices(self, models: list[dict]) -> None:
        ordered = sorted(models, key=lambda item: item["size_gb"])
        self.cmp_sizes = {item["name"]: item["size_gb"] for item in ordered}
        for combo in (self.cmp_model_a, self.cmp_model_b):
            combo.clear()
            combo.addItems([item["name"] for item in ordered])
        self.cmp_model_a.setCurrentIndex(0)
        self.cmp_model_b.setCurrentIndex(len(ordered) - 1)

    def _run_model_comparison(self) -> None:
        question = self.cmp_question.text().strip()
        if not question:
            self._warn("Type a question first.")
            return
        models = [self.cmp_model_a.currentText(), self.cmp_model_b.currentText()]
        for box, model in zip(self.cmp_outputs, models):
            box.setPlainText(f"{model}: waiting for its turn...")
        self.cmp_context_label.setText("Finding the relevant pieces of your document...")
        self.cmp_run_btn.setEnabled(False)

        self.cmp_thread = QThread(self)
        self.cmp_worker = CompareWorker(question, self.latest_chunks_path, models)
        self.cmp_worker.moveToThread(self.cmp_thread)
        self.cmp_thread.started.connect(self.cmp_worker.run)
        self.cmp_worker.context_ready.connect(self._show_compare_context)
        self.cmp_worker.result_ready.connect(self._show_compare_result)
        self.cmp_worker.failed.connect(self._warn)
        self.cmp_worker.done.connect(self._compare_done)
        self.cmp_worker.done.connect(self.cmp_thread.quit)
        self.cmp_thread.finished.connect(self.cmp_worker.deleteLater)
        self.cmp_thread.finished.connect(self.cmp_thread.deleteLater)
        self.cmp_thread.start()

    def _show_compare_context(self, context: dict) -> None:
        used = len(context.get("sources", []))
        total = context.get("total_chunks", 0)
        if context.get("prompt"):
            self.cmp_context_label.setText(
                f"Both models receive the exact same text: {used} of {total} pieces "
                "of your document plus your question."
            )
        else:
            self.cmp_context_label.setText(
                "No part of your document matched this question, so nothing was sent "
                "to either model. Try a different question."
            )
            for box in self.cmp_outputs:
                box.setPlainText("Nothing was sent to this model.")

    def _show_compare_result(self, result: dict) -> None:
        model = result.get("model", "")
        size_gb = getattr(self, "cmp_sizes", {}).get(model, 0)
        lines = [
            f"MODEL: {model}  ({size_gb:.1f} GB on disk)",
            f"Total time: {result.get('seconds', 0):.1f} s "
            f"(of which {result.get('load_seconds', 0):.1f} s loading the model)",
            f"Writing speed: {result.get('tokens_per_second', 0):.1f} tokens per second "
            f"({result.get('tokens', 0)} tokens written)",
            "",
            "ANSWER",
            result.get("answer") or "(no answer)",
        ]
        self.cmp_outputs[result["slot"]].setPlainText("\n".join(lines))
        next_slot = result["slot"] + 1
        if next_slot < len(self.cmp_outputs):
            self.cmp_outputs[next_slot].setPlainText(
                f"{self.cmp_model_b.currentText()}: running now..."
            )

    def _compare_done(self) -> None:
        self.cmp_run_btn.setEnabled(True)
    def _handle_chat_error(self, error_message: str) -> None:
        message = error_message
        if "Could not reach local Ollama" in message:
            message = (
                "Local Ollama is not reachable. Start Ollama, confirm "
                "llama3.1:8b is installed, then try again."
            )
        if self.current_assistant_label is None:
            self._start_assistant_message()
        assert self.current_assistant_label is not None
        self.current_assistant_label.setText(f"Assistant failed: {message}")
        self._warn(f"Assistant failed.\n\n{message}")
        self.current_assistant_label = None
        self.current_assistant_layout = None
        self.assistant_placeholder_visible = False
        self._reset_chat_request_state()

    def _reset_chat_request_state(self) -> None:
        self.chat_request_in_flight = False
        self.chat_input.setEnabled(True)
        self.chat_ask_btn.setEnabled(True)
        self.chat_stop_btn.setVisible(False)
        self.chat_stop_btn.setEnabled(False)
        self.chat_status_label.setText("Ready after chunks")

    def _clear_chat_worker_refs(self) -> None:
        self.chat_worker = None
        self.chat_thread = None

    def _scroll_chat_to_bottom(self) -> None:
        QApplication.processEvents()
        scrollbar = self.chat_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _confirm_permission_review(self, file_type: str) -> bool:
        assert self.selected_file is not None
        result = QMessageBox.question(
            self,
            "Review Local Permission",
            (
                f"PPLLM is about to read this local file:\n\n"
                f"File: {self.selected_file.name}\n"
                f"Type: {file_type.upper()}\n\n"
                "PPLLM will extract text and save a local JSON copy.\n"
                "The original file stays unchanged.\n"
                "Nothing is sent to the cloud."
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if result == QMessageBox.Yes:
            self._log(f"Permission review accepted: {self.selected_file.name}")
            return True
        return False

    def _set_latest_saved_path(self, path: str) -> None:
        self.latest_saved_path = path
        saved_name = Path(path).name
        self.saved_path_label.setText(f"Saved locally: {saved_name}")
        self.saved_path_label.setToolTip(path)
        self.copy_saved_path_btn.setEnabled(True)
        self.open_saved_folder_btn.setEnabled(True)

    def copy_latest_saved_path(self) -> None:
        if not self.latest_saved_path:
            self._warn("No saved file path is available yet.")
            return
        QApplication.clipboard().setText(self.latest_saved_path)
        self._log(f"Copied saved path: {self.latest_saved_path}")

    def open_latest_saved_folder(self) -> None:
        if not self.latest_saved_path:
            self._warn("No saved folder is available yet.")
            return
        folder = Path(self.latest_saved_path).parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        self._log(f"Opened saved folder: {folder}")

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
        self._set_latest_saved_path(target_path)
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
        self._set_latest_saved_path(target_path)
        self._log(f"💾 Chunk JSON saved to: {target_path}")

    def _warn(self, text: str) -> None:
        QMessageBox.warning(self, "LLM Bundler", text)
        self._log(f"⚠️  {text}")
        self._set_status("● Warning", "warn")

    def _log(self, message: str) -> None:
        self.log.appendPlainText(message)

    def _set_status(self, text: str, kind: str = "info") -> None:
        styles = {
            "info": ("#eef4f5", "#536475", "#cddae0"),
            "success": ("#e2f5ea", "#2d6b4f", "#b6dfc8"),
            "warn": ("#fff3dc", "#8a5a12", "#ead19a"),
            "working": ("#ece8fb", "#5e4e91", "#d2c8f0"),
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
