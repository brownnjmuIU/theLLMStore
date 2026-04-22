"""
File Crawler Module

Discovers and traverses local file systems to identify files.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Set, Iterator
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FileInfo:
    """Represents information about a discovered file."""
    path: str
    name: str
    size: int
    extension: str
    modified_time: datetime
    created_time: Optional[datetime] = None
    is_hidden: bool = False
    parent_dir: str = ""


class FileCrawler:
    """
    Crawls local file system to discover files.
    
    Features:
    - Recursive directory traversal
    - Configurable exclusion patterns (hidden files, system directories)
    - Progress tracking
    - Memory-efficient file discovery
    """
    
    # Common system directories to exclude
    DEFAULT_EXCLUDE_DIRS = {
        '.git', '.svn', '.hg', '.bzr',
        '__pycache__', '.pytest_cache', '.mypy_cache',
        'node_modules', '.venv', 'venv', 'env',
        '.DS_Store', 'Thumbs.db',
        'Library/Caches', 'Library/Logs',
        '.Trash', 'Trash', '$Recycle.Bin'
    }
    
    # Common file extensions to exclude
    DEFAULT_EXCLUDE_EXTENSIONS = {
        '.tmp', '.temp', '.log', '.cache',
        '.swp', '.swo', '.bak', '.old'
    }
    
    def __init__(
        self,
        root_path: Optional[str] = None,
        exclude_dirs: Optional[Set[str]] = None,
        exclude_extensions: Optional[Set[str]] = None,
        include_hidden: bool = False,
        max_depth: Optional[int] = None,
        min_file_size: int = 0,
        max_file_size: Optional[int] = None
    ):
        """
        Initialize the file crawler.
        
        Args:
            root_path: Root directory to start crawling from. Defaults to user home.
            exclude_dirs: Set of directory names to exclude
            exclude_extensions: Set of file extensions to exclude
            include_hidden: Whether to include hidden files/directories
            max_depth: Maximum depth to crawl (None = unlimited)
            min_file_size: Minimum file size in bytes to include
            max_file_size: Maximum file size in bytes to include
        """
        self.root_path = Path(root_path) if root_path else Path.home()
        self.exclude_dirs = exclude_dirs or self.DEFAULT_EXCLUDE_DIRS.copy()
        self.exclude_extensions = exclude_extensions or self.DEFAULT_EXCLUDE_EXTENSIONS.copy()
        self.include_hidden = include_hidden
        self.max_depth = max_depth
        self.min_file_size = min_file_size
        self.max_file_size = max_file_size
        
        self.logger = logging.getLogger(__name__)
        self._discovered_files: List[FileInfo] = []
        self._stats = {
            'total_files': 0,
            'total_dirs': 0,
            'skipped_files': 0,
            'skipped_dirs': 0,
            'errors': 0
        }
    
    def crawl(self) -> List[FileInfo]:
        """
        Start crawling the file system.
        
        Returns:
            List of FileInfo objects representing discovered files
        """
        self.logger.info(f"Starting crawl from: {self.root_path}")
        self._discovered_files = []
        self._reset_stats()
        
        try:
            if not self.root_path.exists():
                self.logger.error(f"Root path does not exist: {self.root_path}")
                return []
            
            if not self.root_path.is_dir():
                self.logger.error(f"Root path is not a directory: {self.root_path}")
                return []
            
            self._crawl_directory(self.root_path, depth=0)
            
            self.logger.info(
                f"Crawl completed. Found {self._stats['total_files']} files "
                f"in {self._stats['total_dirs']} directories"
            )
            
        except Exception as e:
            self.logger.error(f"Error during crawl: {e}", exc_info=True)
            self._stats['errors'] += 1
        
        return self._discovered_files
    
    def _crawl_directory(self, directory: Path, depth: int = 0):
        """Recursively crawl a directory."""
        # Check max depth
        if self.max_depth is not None and depth > self.max_depth:
            return
        
        # Check if directory should be excluded
        if self._should_exclude_dir(directory):
            self._stats['skipped_dirs'] += 1
            return
        
        try:
            self._stats['total_dirs'] += 1
            
            # Iterate through directory contents
            for item in directory.iterdir():
                try:
                    # Check if hidden and should be excluded
                    if item.name.startswith('.') and not self.include_hidden:
                        continue
                    
                    if item.is_file():
                        self._process_file(item, directory)
                    elif item.is_dir():
                        self._crawl_directory(item, depth + 1)
                        
                except PermissionError:
                    self.logger.warning(f"Permission denied: {item}")
                    self._stats['errors'] += 1
                    continue
                except Exception as e:
                    self.logger.warning(f"Error processing {item}: {e}")
                    self._stats['errors'] += 1
                    continue
                    
        except PermissionError:
            self.logger.warning(f"Permission denied accessing directory: {directory}")
            self._stats['errors'] += 1
        except Exception as e:
            self.logger.warning(f"Error accessing directory {directory}: {e}")
            self._stats['errors'] += 1
    
    def _process_file(self, file_path: Path, parent_dir: Path):
        """Process a single file and add it to discovered files if it meets criteria."""
        try:
            # Check extension exclusion
            if file_path.suffix.lower() in self.exclude_extensions:
                self._stats['skipped_files'] += 1
                return
            
            # Get file stats
            stat_info = file_path.stat()
            file_size = stat_info.st_size
            
            # Check size constraints
            if file_size < self.min_file_size:
                self._stats['skipped_files'] += 1
                return
            
            if self.max_file_size and file_size > self.max_file_size:
                self._stats['skipped_files'] += 1
                return
            
            # Create FileInfo object
            file_info = FileInfo(
                path=str(file_path.absolute()),
                name=file_path.name,
                size=file_size,
                extension=file_path.suffix.lower(),
                modified_time=datetime.fromtimestamp(stat_info.st_mtime),
                created_time=datetime.fromtimestamp(stat_info.st_ctime) if hasattr(stat_info, 'st_birthtime') else None,
                is_hidden=file_path.name.startswith('.'),
                parent_dir=str(parent_dir.absolute())
            )
            
            self._discovered_files.append(file_info)
            self._stats['total_files'] += 1
            
        except Exception as e:
            self.logger.warning(f"Error processing file {file_path}: {e}")
            self._stats['errors'] += 1
    
    def _should_exclude_dir(self, directory: Path) -> bool:
        """Check if a directory should be excluded."""
        dir_name = directory.name
        
        # Check against exclude list
        if dir_name in self.exclude_dirs:
            return True
        
        # Check if hidden and not including hidden
        if dir_name.startswith('.') and not self.include_hidden:
            return True
        
        return False
    
    def _reset_stats(self):
        """Reset statistics counters."""
        self._stats = {
            'total_files': 0,
            'total_dirs': 0,
            'skipped_files': 0,
            'skipped_dirs': 0,
            'errors': 0
        }
    
    def get_stats(self) -> Dict:
        """Get crawling statistics."""
        return self._stats.copy()
    
    def crawl_generator(self) -> Iterator[FileInfo]:
        """
        Generator version of crawl for memory-efficient processing.
        Yields FileInfo objects as files are discovered.
        """
        self.logger.info(f"Starting generator crawl from: {self.root_path}")
        self._reset_stats()
        
        try:
            if not self.root_path.exists() or not self.root_path.is_dir():
                return
            
            yield from self._crawl_directory_generator(self.root_path, depth=0)
            
        except Exception as e:
            self.logger.error(f"Error during generator crawl: {e}", exc_info=True)
    
    def _crawl_directory_generator(self, directory: Path, depth: int = 0) -> Iterator[FileInfo]:
        """Generator version of directory crawling."""
        if self.max_depth is not None and depth > self.max_depth:
            return
        
        if self._should_exclude_dir(directory):
            self._stats['skipped_dirs'] += 1
            return
        
        try:
            self._stats['total_dirs'] += 1
            
            for item in directory.iterdir():
                try:
                    if item.name.startswith('.') and not self.include_hidden:
                        continue
                    
                    if item.is_file():
                        file_info = self._get_file_info(item, directory)
                        if file_info:
                            yield file_info
                    elif item.is_dir():
                        yield from self._crawl_directory_generator(item, depth + 1)
                        
                except (PermissionError, Exception) as e:
                    self.logger.warning(f"Error processing {item}: {e}")
                    self._stats['errors'] += 1
                    continue
                    
        except (PermissionError, Exception) as e:
            self.logger.warning(f"Error accessing directory {directory}: {e}")
            self._stats['errors'] += 1
    
    def _get_file_info(self, file_path: Path, parent_dir: Path) -> Optional[FileInfo]:
        """Get FileInfo for a file if it meets criteria."""
        try:
            if file_path.suffix.lower() in self.exclude_extensions:
                self._stats['skipped_files'] += 1
                return None
            
            stat_info = file_path.stat()
            file_size = stat_info.st_size
            
            if file_size < self.min_file_size:
                self._stats['skipped_files'] += 1
                return None
            
            if self.max_file_size and file_size > self.max_file_size:
                self._stats['skipped_files'] += 1
                return None
            
            file_info = FileInfo(
                path=str(file_path.absolute()),
                name=file_path.name,
                size=file_size,
                extension=file_path.suffix.lower(),
                modified_time=datetime.fromtimestamp(stat_info.st_mtime),
                created_time=datetime.fromtimestamp(stat_info.st_ctime) if hasattr(stat_info, 'st_birthtime') else None,
                is_hidden=file_path.name.startswith('.'),
                parent_dir=str(parent_dir.absolute())
            )
            
            self._stats['total_files'] += 1
            return file_info
            
        except Exception as e:
            self.logger.warning(f"Error processing file {file_path}: {e}")
            self._stats['errors'] += 1
            return None
