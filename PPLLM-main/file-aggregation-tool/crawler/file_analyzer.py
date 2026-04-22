"""
File Analyzer Module

Identifies file types, extracts metadata, and generates content summaries.
"""

import os
import mimetypes
import logging
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class FileAnalysis:
    """Comprehensive analysis of a file."""
    path: str
    file_type: str  # e.g., 'document', 'image', 'video', 'audio', 'code', 'data', 'archive', 'other'
    mime_type: Optional[str] = None
    category: str = ""  # More specific category
    size_mb: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_preview: Optional[str] = None  # First few lines or summary
    content_summary: Optional[str] = None  # Brief description of content
    tags: List[str] = field(default_factory=list)
    is_readable: bool = False
    encoding: Optional[str] = None
    line_count: Optional[int] = None
    word_count: Optional[int] = None


class FileAnalyzer:
    """
    Analyzes files to identify type, extract metadata, and generate summaries.
    
    Supports:
    - Text files (code, documents, logs)
    - Images (metadata extraction)
    - Documents (PDF, Word, Excel, etc.)
    - Media files (video, audio)
    - Archives
    - Data files (CSV, JSON, etc.)
    """
    
    # File type mappings
    DOCUMENT_EXTENSIONS = {
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.odt', '.ods', '.odp', '.rtf', '.txt', '.md', '.tex'
    }
    
    IMAGE_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
        '.tiff', '.tif', '.ico', '.heic', '.heif', '.raw', '.cr2', '.nef'
    }
    
    VIDEO_EXTENSIONS = {
        '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv',
        '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv'
    }
    
    AUDIO_EXTENSIONS = {
        '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a',
        '.opus', '.amr', '.aiff'
    }
    
    CODE_EXTENSIONS = {
        '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.hpp',
        '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt',
        '.html', '.css', '.scss', '.sass', '.xml', '.json', '.yaml', '.yml',
        '.sh', '.bash', '.zsh', '.ps1', '.bat', '.sql', '.r', '.m',
        '.vue', '.jsx', '.tsx', '.dart', '.lua', '.pl', '.pm'
    }
    
    DATA_EXTENSIONS = {
        '.csv', '.json', '.xml', '.yaml', '.yml', '.toml',
        '.db', '.sqlite', '.sqlite3', '.xlsx', '.xls'
    }
    
    ARCHIVE_EXTENSIONS = {
        '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar',
        '.tar.gz', '.tgz', '.tar.bz2', '.tar.xz'
    }
    
    # Text file encodings to try
    TEXT_ENCODINGS = ['utf-8', 'utf-16', 'latin-1', 'cp1252', 'ascii']
    
    def __init__(self, max_preview_lines: int = 10, max_preview_chars: int = 500):
        """
        Initialize the file analyzer.
        
        Args:
            max_preview_lines: Maximum lines to extract for preview
            max_preview_chars: Maximum characters for content preview
        """
        self.max_preview_lines = max_preview_lines
        self.max_preview_chars = max_preview_chars
        self.logger = logging.getLogger(__name__)
        
        # Initialize mimetypes
        mimetypes.init()
    
    def analyze(self, file_path: str) -> FileAnalysis:
        """
        Analyze a file and return comprehensive analysis.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            FileAnalysis object with all extracted information
        """
        path = Path(file_path)
        
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Basic file info
        stat_info = path.stat()
        size_mb = stat_info.st_size / (1024 * 1024)
        
        # Determine file type
        file_type, category = self._classify_file(path)
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        
        # Initialize analysis
        analysis = FileAnalysis(
            path=str(path.absolute()),
            file_type=file_type,
            mime_type=mime_type,
            category=category,
            size_mb=round(size_mb, 2)
        )
        
        # Extract metadata and content based on file type
        try:
            if file_type == 'text' or file_type == 'code' or file_type == 'document':
                self._analyze_text_file(path, analysis)
            elif file_type == 'image':
                self._analyze_image_file(path, analysis)
            elif file_type == 'data':
                self._analyze_data_file(path, analysis)
            elif file_type == 'archive':
                self._analyze_archive_file(path, analysis)
            else:
                self._analyze_generic_file(path, analysis)
                
        except Exception as e:
            self.logger.warning(f"Error analyzing file {file_path}: {e}")
            analysis.metadata['error'] = str(e)
        
        # Add tags
        analysis.tags = self._generate_tags(analysis)
        
        return analysis
    
    def _classify_file(self, path: Path) -> tuple[str, str]:
        """
        Classify file into type and category.
        
        Returns:
            Tuple of (file_type, category)
        """
        ext = path.suffix.lower()
        name_lower = path.name.lower()
        
        # Check specific extensions
        if ext in self.DOCUMENT_EXTENSIONS:
            if ext in {'.pdf'}:
                return ('document', 'pdf')
            elif ext in {'.doc', '.docx'}:
                return ('document', 'word')
            elif ext in {'.xls', '.xlsx'}:
                return ('document', 'excel')
            elif ext in {'.ppt', '.pptx'}:
                return ('document', 'presentation')
            elif ext in {'.txt', '.md'}:
                return ('document', 'text')
            else:
                return ('document', 'other')
        
        elif ext in self.IMAGE_EXTENSIONS:
            return ('image', ext[1:])  # Remove the dot
        
        elif ext in self.VIDEO_EXTENSIONS:
            return ('video', ext[1:])
        
        elif ext in self.AUDIO_EXTENSIONS:
            return ('audio', ext[1:])
        
        elif ext in self.CODE_EXTENSIONS:
            return ('code', ext[1:])
        
        elif ext in self.DATA_EXTENSIONS:
            return ('data', ext[1:])
        
        elif ext in self.ARCHIVE_EXTENSIONS:
            return ('archive', ext[1:])
        
        # Fallback: check MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type:
            if mime_type.startswith('text/'):
                return ('text', 'plain')
            elif mime_type.startswith('image/'):
                return ('image', mime_type.split('/')[1])
            elif mime_type.startswith('video/'):
                return ('video', mime_type.split('/')[1])
            elif mime_type.startswith('audio/'):
                return ('audio', mime_type.split('/')[1])
        
        return ('other', 'unknown')
    
    def _analyze_text_file(self, path: Path, analysis: FileAnalysis):
        """Analyze text-based files."""
        try:
            # Try to read the file
            content = None
            encoding = None
            
            for enc in self.TEXT_ENCODINGS:
                try:
                    with open(path, 'r', encoding=enc) as f:
                        content = f.read()
                    encoding = enc
                    analysis.is_readable = True
                    analysis.encoding = enc
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    self.logger.debug(f"Error reading with {enc}: {e}")
                    continue
            
            if content:
                lines = content.split('\n')
                analysis.line_count = len(lines)
                analysis.word_count = len(content.split())
                
                # Extract preview
                preview_lines = lines[:self.max_preview_lines]
                preview_text = '\n'.join(preview_lines)
                
                if len(preview_text) > self.max_preview_chars:
                    preview_text = preview_text[:self.max_preview_chars] + '...'
                
                analysis.content_preview = preview_text
                
                # Generate summary
                analysis.content_summary = self._summarize_text(content, analysis.category)
                
                # Add metadata
                analysis.metadata.update({
                    'encoding': encoding,
                    'line_count': analysis.line_count,
                    'word_count': analysis.word_count,
                    'char_count': len(content)
                })
            else:
                analysis.metadata['note'] = 'Could not decode as text'
                
        except Exception as e:
            self.logger.warning(f"Error analyzing text file {path}: {e}")
            analysis.metadata['error'] = str(e)
    
    def _analyze_image_file(self, path: Path, analysis: FileAnalysis):
        """Analyze image files."""
        try:
            # Try to get basic image info using PIL if available
            try:
                from PIL import Image
                with Image.open(path) as img:
                    analysis.metadata.update({
                        'width': img.width,
                        'height': img.height,
                        'format': img.format,
                        'mode': img.mode
                    })
                    analysis.content_summary = f"Image: {img.width}x{img.height} pixels, {img.format} format"
            except ImportError:
                analysis.metadata['note'] = 'PIL not available for detailed image analysis'
                analysis.content_summary = f"Image file: {analysis.category.upper()}"
            except Exception as e:
                self.logger.debug(f"PIL error: {e}")
                analysis.content_summary = f"Image file: {analysis.category.upper()}"
                
        except Exception as e:
            self.logger.warning(f"Error analyzing image {path}: {e}")
            analysis.metadata['error'] = str(e)
    
    def _analyze_data_file(self, path: Path, analysis: FileAnalysis):
        """Analyze data files (CSV, JSON, etc.)."""
        try:
            ext = path.suffix.lower()
            
            if ext == '.json':
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    analysis.is_readable = True
                    analysis.encoding = 'utf-8'
                    
                    if isinstance(data, dict):
                        analysis.content_summary = f"JSON object with {len(data)} keys"
                        analysis.metadata['keys'] = list(data.keys())[:10]  # First 10 keys
                    elif isinstance(data, list):
                        analysis.content_summary = f"JSON array with {len(data)} items"
                        analysis.metadata['item_count'] = len(data)
                    
                    # Preview
                    preview = json.dumps(data, indent=2)[:self.max_preview_chars]
                    analysis.content_preview = preview + ('...' if len(str(data)) > self.max_preview_chars else '')
                    
                except Exception as e:
                    analysis.metadata['error'] = f"Invalid JSON: {e}"
            
            elif ext == '.csv':
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()[:self.max_preview_lines]
                    analysis.is_readable = True
                    analysis.encoding = 'utf-8'
                    analysis.line_count = len(lines)
                    analysis.content_preview = ''.join(lines)
                    analysis.content_summary = f"CSV file with {len(lines)} rows (preview)"
                except Exception as e:
                    analysis.metadata['error'] = str(e)
            
            else:
                # Try as text
                self._analyze_text_file(path, analysis)
                
        except Exception as e:
            self.logger.warning(f"Error analyzing data file {path}: {e}")
            analysis.metadata['error'] = str(e)
    
    def _analyze_archive_file(self, path: Path, analysis: FileAnalysis):
        """Analyze archive files."""
        analysis.content_summary = f"Archive file: {analysis.category.upper()}"
        analysis.metadata['note'] = 'Archive contents not extracted'
    
    def _analyze_generic_file(self, path: Path, analysis: FileAnalysis):
        """Analyze generic/unknown files."""
        analysis.content_summary = f"File type: {analysis.category or 'unknown'}"
    
    def _summarize_text(self, content: str, category: str) -> str:
        """Generate a brief summary of text content."""
        if not content:
            return "Empty file"
        
        # Remove excessive whitespace
        content_clean = ' '.join(content.split())
        
        # For code files, try to identify language/type
        if category in ['py', 'js', 'ts', 'java', 'cpp', 'c']:
            # Count common code patterns
            lines = content.split('\n')
            non_empty = [l for l in lines if l.strip()]
            return f"Code file with {len(non_empty)} non-empty lines"
        
        # For documents, use first sentence or first 100 chars
        if len(content_clean) > 100:
            summary = content_clean[:100] + '...'
        else:
            summary = content_clean
        
        return summary
    
    def _generate_tags(self, analysis: FileAnalysis) -> List[str]:
        """Generate tags for the file based on analysis."""
        tags = []
        
        # File type tag
        tags.append(analysis.file_type)
        
        # Category tag
        if analysis.category:
            tags.append(analysis.category)
        
        # Size-based tags
        if analysis.size_mb > 100:
            tags.append('large')
        elif analysis.size_mb < 1:
            tags.append('small')
        
        # Content-based tags
        if analysis.is_readable:
            tags.append('readable')
        
        if analysis.line_count and analysis.line_count > 1000:
            tags.append('long')
        
        return tags
