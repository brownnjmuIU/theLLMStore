# File Aggregation Tool - Crawler Module

A Python tool for crawling, identifying, indexing, and aggregating local files to help users understand their file contents before extraction for LLM processing.

## Overview

This crawler module is designed to:
- **Crawl** local file systems to discover files
- **Identify** file types and categories
- **Extract** metadata and content previews
- **Aggregate** files into structured lists
- **Summarize** file contents for user decision-making

## Features

### File Discovery
- Recursive directory traversal
- Configurable exclusion patterns (hidden files, system directories)
- Memory-efficient generator-based crawling
- Progress tracking and statistics

### File Analysis
- Automatic file type detection (documents, images, videos, audio, code, data, archives)
- MIME type identification
- Content preview extraction
- Metadata extraction (size, dates, encoding, etc.)
- Text file analysis (line count, word count, encoding detection)

### Aggregation
- Group files by type or category
- Filter by size, type, readability, tags
- Sort by various criteria
- Export to JSON or CSV
- Generate summary statistics

## GUI Application (Recommended)

A desktop GUI lets you:
- Choose a folder to scan
- View aggregated files grouped by category
- See a 1-line summary/context for each file
- Select only the files you want
- Export selected files to JSON

**Run the GUI:**
```bash
pip install -r requirements.txt
python gui_app.py
```

**Build as .exe (Windows):** See [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) for creating a standalone `FileAggregationTool.exe` that users can run without Python.

---

## Installation

1. Clone or download this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

For basic functionality, Pillow is optional (used for image metadata). PyInstaller is needed only for building the .exe.

## Quick Start

### Basic Usage

```python
from crawler import FileCrawler, FileAnalyzer, FileAggregator
from pathlib import Path

# Initialize crawler
crawler = FileCrawler(
    root_path=str(Path.home() / "Documents"),
    max_depth=3,
    min_file_size=1024  # Only files > 1KB
)

# Discover files
files = crawler.crawl()
print(f"Found {len(files)} files")

# Analyze files
analyzer = FileAnalyzer()
aggregator = FileAggregator()

for file_info in files:
    try:
        analysis = analyzer.analyze(file_info.path)
        aggregator.add_analysis(analysis)
    except Exception as e:
        print(f"Error: {e}")

# Export results
aggregator.export_json("output.json")
aggregator.export_csv("output.csv")

# Print summary
print(aggregator.get_summary_report())
```

### Using Configuration

```python
from crawler.config import get_user_friendly_config

config = get_user_friendly_config()
config.root_path = "/path/to/scan"
config.max_depth = 2
config.filter_file_types = ['document', 'image']

# Use config with crawler...
```

### Filtering and Sorting

```python
# Filter files
filtered = aggregator.filter(
    file_types=['document', 'image'],
    min_size_mb=0.1,
    readable_only=True
)

# Sort by size
sorted_files = aggregator.sort(filtered, key='size_mb', reverse=True)

# Group by type
grouped = aggregator.group_by_type()
```

## Module Structure

```
crawler/
├── __init__.py          # Module exports
├── file_crawler.py      # File discovery and crawling
├── file_analyzer.py     # File type detection and analysis
├── aggregator.py        # File aggregation and export
└── config.py            # Configuration management
```

## Components

### FileCrawler
- Discovers files recursively
- Configurable exclusions
- Memory-efficient generator mode
- Statistics tracking

### FileAnalyzer
- Identifies file types and categories
- Extracts metadata
- Generates content previews
- Creates summaries

### FileAggregator
- Compiles file analyses
- Provides filtering and sorting
- Groups files by type/category
- Exports to JSON/CSV
- Generates statistics

## Configuration Options

### Crawler Settings
- `root_path`: Starting directory (default: user home)
- `exclude_dirs`: Directories to skip
- `exclude_extensions`: File extensions to skip
- `include_hidden`: Include hidden files/directories
- `max_depth`: Maximum crawl depth
- `min_file_size` / `max_file_size`: Size constraints

### Analyzer Settings
- `max_preview_lines`: Lines to extract for preview
- `max_preview_chars`: Characters for preview

### Aggregator Settings
- `output_format`: 'json' or 'csv'
- `include_stats`: Include statistics in output
- Filter and sort options

## File Type Support

### Documents
- PDF, Word (.doc, .docx), Excel (.xls, .xlsx)
- PowerPoint (.ppt, .pptx), Text (.txt, .md)
- OpenDocument formats (.odt, .ods, .odp)

### Images
- JPEG, PNG, GIF, BMP, SVG, WebP
- TIFF, HEIC, RAW formats
- Metadata extraction (dimensions, format)

### Media
- Video: MP4, AVI, MOV, WebM, MKV, etc.
- Audio: MP3, WAV, FLAC, AAC, etc.

### Code
- Python, JavaScript, TypeScript, Java, C/C++
- HTML, CSS, SQL, Shell scripts, and more

### Data
- CSV, JSON, XML, YAML
- Database files (.db, .sqlite)

### Archives
- ZIP, TAR, GZ, 7Z, RAR

## Output Formats

### JSON Export
```json
{
  "exported_at": "2026-02-18T...",
  "statistics": {
    "total_files": 150,
    "total_size_mb": 1250.5,
    "files_by_type": {...},
    "files_by_category": {...}
  },
  "files": [
    {
      "path": "/path/to/file.pdf",
      "file_type": "document",
      "category": "pdf",
      "size_mb": 2.5,
      "content_summary": "...",
      ...
    }
  ]
}
```

### CSV Export
Exports all file information in a tabular format suitable for spreadsheet applications.

## Examples

See `example_usage.py` for comprehensive examples:
- Basic crawling
- Filtered crawling
- Exporting results
- Grouped analysis

Run examples:
```bash
python example_usage.py
```

## Performance Considerations

- Use `crawl_generator()` for memory-efficient processing of large directories
- Set `max_depth` to limit crawl depth
- Use `min_file_size` to skip small files
- Filter results before exporting large datasets

## Error Handling

The crawler handles:
- Permission errors (skips inaccessible files/directories)
- Corrupted files (logs warnings, continues)
- Encoding issues (tries multiple encodings)
- Large files (configurable size limits)

## Future Enhancements

- PDF text extraction
- Office document content extraction
- Image OCR capabilities
- Video/audio metadata extraction
- Database content preview
- GUI interface
- Executable packaging (.exe)

## License

[Add your license here]

## Contributing

[Add contribution guidelines]
