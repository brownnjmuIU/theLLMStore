# LLM Bundler — PPLLM Local Data Ingestion Tool

A desktop tool that lets you feed your personal files into a local AI assistant — privately and securely. Built for the **Personalized Permissioned LLM (PPLLM)** research project at Indiana University.

All processing happens on your machine. Your files never leave your device.

---

## Quick Start (Windows — Recommended)

> **No Python or coding experience required.**

1. Download `LLM_Bundler_Desktop.exe` from the [Releases](../../releases) page or the [Actions](../../actions) tab
2. Run the installer — Windows may show a security warning, click **More info → Run anyway**
3. The app opens automatically

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

## Research Context

This tool is part of the **PPLLM (Personalized Permissioned LLM)** research project at the Kelley School of Business, Indiana University, supervised by Professor Nick Brown.

It is designed as an educational artifact teaching **responsible AI** principles:
- You decide exactly which files the AI can see
- Every file access is logged by the permission layer
- Data is encrypted before any cloud transfer
- All processing is local — your data stays on your machine

---

## Authors

- **Manas Dani** — Pipeline architecture, extraction modules, desktop UI, encryption layer, aggregator bridge
- **Prabhakaran** — File aggregation tool, permission layer, documentation
- **Professor Nick Brown** — Research direction and supervision, Kelley School of Business, Indiana University
