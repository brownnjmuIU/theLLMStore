# LLM Bundler — PPLLM Local Data Ingestion Tool

A desktop tool that lets you feed your personal files into a local AI assistant — privately and securely. Built for the **Personalized Permissioned LLM (PPLLM)** research project at Indiana University.

All processing happens on your machine. Your files never leave your device.

---

## Quick Start (Windows — Recommended)

> **No Python or coding experience required.**

1. Go to the [Actions](../../actions) tab and open the latest successful workflow run
2. Download the artifact named **LLM_Bundler_Desktop_windows** and unzip it
3. Open the unzipped folder and double-click **LLM_Bundler_Desktop.exe**
4. Windows may show a security warning — click **More info → Run anyway**

That's it. Skip to [Using the App](#using-the-app) below.

---

## What It Does

Think of LLM Bundler as a "file reader" for AI. It:

1. **Reads** your files (PDFs, Word docs, images, videos, browser history, and more)
2. **Extracts** the text content
3. **Breaks it into small pieces** (called chunks) that an AI can search through efficiently
4. **Saves** everything locally on your computer
5. **Optionally locks** the output with encryption before sending it anywhere

Once your files are processed, you load the output into a local AI platform like [AnythingLLM](https://anythingllm.com) and chat with your own data.

```
Your Files → LLM Bundler → Chunks → AnythingLLM → Chat with your data
```

---

## Supported File Types

| Type | Extensions |
|---|---|
| PDF | `.pdf` |
| Word Document | `.docx` |
| PowerPoint | `.pptx` |
| Image (reads text in images) | `.jpg`, `.jpeg`, `.png` |
| Video (transcribes speech) | `.mp4`, `.mov` |
| Platform Data Export | `.json` |
| Browser History | `.sqlite`, `.db` |
| Browser Cookies | `.sqlite`, `.db` (cookie files — safe metadata only) |

---

## Using the App

### Step 1 — Ingest Document
1. Click **Browse…** and select any supported file
2. If the file looks sensitive (e.g. named `passwords.pdf`), the app will ask you to confirm before proceeding
3. Click **Extract + Save Raw JSON**
4. The extracted text appears in the **Preview** tab on the right

### Step 2 — Process & Chunk
1. Leave **Chunk size** and **Chunk overlap** at their defaults (800 / 100) — these work well for most files
2. Click **Process + Save Chunk JSON**
3. The chunked output appears in the **Chunk Preview** tab

Your output files are saved here:
```
Documents/LLM_Bundler/outputs/raw/      ← extracted text
Documents/LLM_Bundler/outputs/chunks/   ← processed chunks ready for AI
```

### Step 3 — Load into AnythingLLM
1. Open [AnythingLLM](https://anythingllm.com) (download and install it separately)
2. Create a workspace
3. Upload the chunk JSON file from `Documents/LLM_Bundler/outputs/chunks/`
4. AnythingLLM will embed it — now you can chat with your file

---

## Encryption (Optional)

If you plan to send your processed data to a cloud server (instead of using it locally), you can encrypt it first so no one can read it in transit.

**How to use it:**
- Check the **Encrypt chunk artifact** box in Step 2 before clicking Process
- An encrypted `.enc` file is saved to `Documents/LLM_Bundler/encrypted/`
- This file is unreadable without the decryption key — safe to transfer

**Note:** For local AnythingLLM use, you do NOT need encryption. Skip this unless you are transferring data to a remote server.

To decrypt a file from the command line:
```bash
python -m encryption.artifact_crypto decrypt path/to/file.enc
```

Keys are stored at `Documents/LLM_Bundler/keys/` and are auto-generated on first use.

---

## Running from Source (Developers)

If you want to run or modify the code directly:

### Prerequisites
- Python 3.10 or higher — [python.org](https://www.python.org/downloads/)
- Tesseract OCR (for image files)
  - Windows: [UB Mannheim installer](https://github.com/UB-Mannheim/tesseract/wiki)
  - Mac: `brew install tesseract`
- ffmpeg (for video files)
  - Windows: [ffmpeg.org](https://ffmpeg.org/download.html)
  - Mac: `brew install ffmpeg`

### Install & Run
```bash
git clone https://github.com/brownnjmuIU/theLLMStore.git
cd theLLMStore

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Mac/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python desktop_app.py
```

---

## Aggregator Bridge (Interoperability)

LLM Bundler connects with the PPLLM File Aggregation Tool (built by Prabhakaran). That tool lets you browse and select files from your computer into a manifest — this bridge then processes all selected files through the full pipeline automatically.

```bash
python integration/process_aggregator_manifest.py path/to/manifest.json
```

Options:
```
--chunk-size     Chunk size in characters (default: 800)
--chunk-overlap  Overlap between chunks (default: 100)
--no-chunk       Save raw artifacts only, skip chunking
```

---

## Folder Structure

```
theLLMStore/
├── desktop_app.py                  Main desktop application
├── requirements.txt                Python dependencies
├── ppllm_architecture.html         Full system architecture diagram
│
├── extractors/                     File-type extraction modules
├── processing/                     Text cleaning and chunking pipeline
├── storage/                        Artifact persistence
├── encryption/                     RSA + AES-256-GCM hybrid encryption
├── integration/                    Aggregator interoperability bridge
└── PPLLM-main/                     File aggregation tool + permission layer
```

---

## System Architecture

To see the full PPLLM system design — all existing components and proposed future layers — open [`ppllm_architecture.html`](ppllm_architecture.html) in any browser.

---

## Codebase Guide (For the Next Dev Team)

This section documents each module so the next team can orient quickly.

### `desktop_app.py`
The main PySide6 desktop UI. All user interactions go through here — file picking, extraction, chunking, and the encrypt checkbox. Start here when debugging UI behavior or adding new file type support.

### `extractors/`
One file per supported format. Each extractor takes `file_bytes: bytes` and returns a dict (e.g. `{"text": "...", "page_count": 4}`).

| File | Handles |
|---|---|
| `pdf_extractor.py` | PDF pages via PyMuPDF |
| `docs_extractor.py` | DOCX files via python-docx |
| `pptx_extractor.py` | PPTX slides via python-pptx |
| `image_extractor.py` | JPG/PNG text via Tesseract OCR |
| `video_extractor.py` | MP4/MOV speech via faster-whisper (local, no API) |
| `browser_extractor.py` | Chrome/Firefox SQLite history and cookie metadata |
| `platform_extractor.py` | JSON exports from platforms (Google Takeout, etc.) |

To add a new file type: create `extractors/yourformat_extractor.py`, implement `extract_text_from_yourformat(file_bytes: bytes) -> dict` (returning at minimum `{"text": "..."}` to match the existing pattern), then wire it into `desktop_app.py` (the file-type dispatch block around line 525) and `integration/process_aggregator_manifest.py` (the equivalent dispatch block there). Note: `processing/pipeline.py` operates on already-saved raw JSON artifacts and does not need to be changed when adding a new extractor.

### `processing/`
Three-stage text pipeline run after extraction.

| File | Role |
|---|---|
| `cleaner.py` | Strips noise: extra whitespace, non-printable characters, boilerplate |
| `chunker.py` | Splits cleaned text into overlapping fixed-size character windows |
| `pipeline.py` | Loads saved raw JSON, then runs cleaner → chunker → storage in one call |

`pipeline.py` accepts an optional `encrypt=True` flag that passes the final chunk artifact through the encryption layer before saving.

### `storage/`
`json_store.py` handles saving and loading raw and chunk artifacts to disk. Output paths:
```
~/Documents/LLM_Bundler/outputs/raw/      ← raw extracted text
~/Documents/LLM_Bundler/outputs/chunks/   ← chunked output
~/Documents/LLM_Bundler/encrypted/        ← encrypted artifacts (if used)
```

### `encryption/`
RSA + AES-256-GCM hybrid encryption for chunk artifacts intended for cloud transfer.

| File | Role |
|---|---|
| `key_manager.py` | Generates and loads a 2048-bit RSA key pair on first run |
| `artifact_crypto.py` | Encrypts/decrypts chunk JSON files; output is a `.enc` binary |

Keys live at `~/Documents/LLM_Bundler/keys/`. The private key never leaves the machine. Encryption is optional and does not affect local AnythingLLM usage.

### `integration/`
`process_aggregator_manifest.py` — the interoperability bridge between this pipeline and Prabhakaran's file aggregation tool. It reads the aggregator's exported JSON manifest (a list of selected file paths) and runs each file through the full pipeline. Optionally loads the permission layer from `PPLLM-main/` if present and logs every access decision to `access_log.db`.

### `PPLLM-main/`
Prabhakaran's teammate repo, copied locally for integration. Contains:
- `file-aggregation-tool/` — GUI for browsing and selecting local files, exports a manifest JSON
- `permission_layer/` — logs file access decisions; loaded optionally by the bridge script

This folder is not part of the core pipeline. It represents the other half of the PPLLM system.

---

## Extending the System

The pipeline was designed to grow. Planned next layers for the NSF grant phase:

- **RAG / Vector Embedding** — embed chunk artifacts into a local vector store (e.g. ChromaDB) for semantic search
- **Conversational Interface** — chat layer on top of the vector store, replacing AnythingLLM dependency
- **Differential Privacy / PII Scrubbing** — strip personally identifiable information before any cloud transfer
- **Audit & Compliance Dashboard** — surface permission logs in a readable UI
- **Cross-Platform Sync** — extend extraction to iOS/Android app exports
- **User Profile & Preference Engine** — build a structured user model from repeated ingestion patterns

See `ppllm_architecture.html` for the full architecture diagram showing existing layers (solid blue) and proposed enhancements (dashed purple/amber).

---

## Educational Purpose

This tool is part of the **PPLLM (Personalized Permissioned LLM)** research project at the Kelley School of Business, Indiana University, supervised by Professor Nick Brown. It is intended as an educational artifact for the NSF grant Integrated Research and Education Plan.

**What it teaches:**

**Responsible AI** — Because users must choose which files the AI can see, they engage directly with the concept of training data. They learn that AI behavior is shaped by what information it is given, and that this choice belongs to the user.

**Information privacy and security** — Users experience firsthand the trade-off between personalization (giving the AI more of your data) and privacy (controlling what it can access). The permission layer and encryption settings make that trade-off visible and actionable rather than invisible and assumed.

**Local-first design** — All processing runs on the user's machine. Nothing is sent to an external server by default. Users learn that AI tools do not have to be cloud-dependent, and that local execution is a valid privacy-preserving alternative.

---

## Authors

- **Manas Dani** — Pipeline architecture, extraction modules, desktop UI, encryption layer, aggregator bridge
- **Prabhakaran** — File aggregation tool, permission layer, documentation
- **Professor Nick Brown** — Research direction and supervision, Kelley School of Business, Indiana University
