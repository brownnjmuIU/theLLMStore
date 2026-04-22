"""
Configuration module for the file crawler.

Provides default configurations and settings management.
"""

from typing import Set, Optional, List
from dataclasses import dataclass, field


@dataclass
class CrawlerConfig:
    """Configuration for the file crawler."""
    
    # Path settings
    root_path: Optional[str] = None  # None = user home directory
    
    # Exclusion settings
    exclude_dirs: Set[str] = field(default_factory=lambda: {
        '.git', '.svn', '.hg', '.bzr',
        '__pycache__', '.pytest_cache', '.mypy_cache',
        'node_modules', '.venv', 'venv', 'env',
        '.DS_Store', 'Thumbs.db',
        'Library/Caches', 'Library/Logs',
        '.Trash', 'Trash', '$Recycle.Bin',
        'System Volume Information', 'Windows', 'Program Files',
        'Program Files (x86)', 'ProgramData'
    })
    
    exclude_extensions: Set[str] = field(default_factory=lambda: {
        '.tmp', '.temp', '.log', '.cache',
        '.swp', '.swo', '.bak', '.old',
        '.pyc', '.pyo', '.pyd', '.so', '.dll'
    })
    
    # File filtering
    include_hidden: bool = False
    max_depth: Optional[int] = None  # None = unlimited
    min_file_size: int = 0  # bytes
    max_file_size: Optional[int] = None  # bytes
    
    # Analysis settings
    max_preview_lines: int = 10
    max_preview_chars: int = 500
    
    # Output settings
    output_format: str = 'json'  # 'json' or 'csv'
    output_path: Optional[str] = None
    include_stats: bool = True
    
    # Filtering options for aggregation
    filter_file_types: Optional[List[str]] = None
    filter_categories: Optional[List[str]] = None
    filter_min_size_mb: Optional[float] = None
    filter_max_size_mb: Optional[float] = None
    filter_readable_only: Optional[bool] = None
    
    # Sorting
    sort_key: str = 'path'  # 'path', 'size_mb', 'file_type', 'category'
    sort_reverse: bool = False
    
    def add_exclude_dir(self, dir_name: str):
        """Add a directory to exclusion list."""
        self.exclude_dirs.add(dir_name)
    
    def add_exclude_extension(self, ext: str):
        """Add an extension to exclusion list."""
        if not ext.startswith('.'):
            ext = '.' + ext
        self.exclude_extensions.add(ext.lower())
    
    def remove_exclude_dir(self, dir_name: str):
        """Remove a directory from exclusion list."""
        self.exclude_dirs.discard(dir_name)
    
    def remove_exclude_extension(self, ext: str):
        """Remove an extension from exclusion list."""
        if not ext.startswith('.'):
            ext = '.' + ext
        self.exclude_extensions.discard(ext.lower())


# Predefined configurations
def get_default_config() -> CrawlerConfig:
    """Get default configuration."""
    return CrawlerConfig()


def get_documents_only_config() -> CrawlerConfig:
    """Configuration for crawling documents only."""
    config = CrawlerConfig()
    config.filter_file_types = ['document']
    return config


def get_media_only_config() -> CrawlerConfig:
    """Configuration for crawling media files only."""
    config = CrawlerConfig()
    config.filter_file_types = ['image', 'video', 'audio']
    return config


def get_code_only_config() -> CrawlerConfig:
    """Configuration for crawling code files only."""
    config = CrawlerConfig()
    config.filter_file_types = ['code']
    return config


def get_user_friendly_config() -> CrawlerConfig:
    """Configuration optimized for end users (excludes system files)."""
    config = CrawlerConfig()
    # Add more exclusions for user-friendly mode
    config.exclude_dirs.update({
        'Library', 'System', 'Applications',
        'Windows', 'Program Files', 'Program Files (x86)'
    })
    config.include_hidden = False
    config.min_file_size = 1024  # At least 1KB
    return config
