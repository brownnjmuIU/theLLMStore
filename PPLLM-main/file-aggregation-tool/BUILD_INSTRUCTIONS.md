# Building the File Aggregation Tool as .exe

This guide explains how to build a standalone Windows executable (`.exe`) so users can run the tool without installing Python.

## Prerequisites

- Python 3.9+ installed
- Run from the project directory

## Step 1: Install Dependencies

```bash
cd file-aggregation-tool
pip install -r requirements.txt
```

This installs PyInstaller and Pillow (for image analysis).

## Step 2: Build the Executable

**Windows (creates .exe):**

```bash
pyinstaller build_exe.spec
```

**Output:** `dist/FileAggregationTool.exe`

**macOS / Linux (creates a binary, no .exe extension):**

```bash
pyinstaller build_exe.spec
```

**Output:** `dist/FileAggregationTool`

## Step 3: Distribute

- **Windows:** Share the `FileAggregationTool.exe` file. Users can double-click to run.
- **macOS/Linux:** Share the `FileAggregationTool` binary. Users may need to run `chmod +x FileAggregationTool` and then `./FileAggregationTool`.

## Notes

- The first run may take a few seconds while the app unpacks.
- The `.exe` is self-contained; no Python installation is required on the target machine.
- To reduce size, you can add `excludes` in the spec (e.g., exclude unused modules).
- For a smaller build, consider using `--onefile` (already used in the spec) vs `--onedir` for a folder with the executable and libraries.

## Running from Source (Development)

```bash
python gui_app.py
```

Or use the GUI as the main entry point during development.
