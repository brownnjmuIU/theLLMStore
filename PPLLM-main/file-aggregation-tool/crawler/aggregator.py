"""
File Aggregator Module

Aggregates analyzed files into structured lists and provides filtering/sorting capabilities.
"""

import json
import csv
import logging
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime
from dataclasses import asdict, dataclass

from .file_analyzer import FileAnalysis


@dataclass
class AggregationStats:
    """Statistics about aggregated files."""
    total_files: int = 0
    files_by_type: Dict[str, int] = None
    total_size_mb: float = 0.0
    files_by_category: Dict[str, int] = None
    
    def __post_init__(self):
        if self.files_by_type is None:
            self.files_by_type = {}
        if self.files_by_category is None:
            self.files_by_category = {}


class FileAggregator:
    """
    Aggregates file analyses into structured lists.
    
    Features:
    - Group files by type/category
    - Filter by various criteria
    - Sort files
    - Export to JSON/CSV
    - Generate statistics
    """
    
    def __init__(self):
        """Initialize the aggregator."""
        self.logger = logging.getLogger(__name__)
        self.analyses: List[FileAnalysis] = []
    
    def add_analysis(self, analysis: FileAnalysis):
        """Add a file analysis to the aggregation."""
        self.analyses.append(analysis)
    
    def add_analyses(self, analyses: List[FileAnalysis]):
        """Add multiple file analyses."""
        self.analyses.extend(analyses)
    
    def clear(self):
        """Clear all aggregated analyses."""
        self.analyses = []
    
    def filter(
        self,
        file_types: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        min_size_mb: Optional[float] = None,
        max_size_mb: Optional[float] = None,
        tags: Optional[List[str]] = None,
        readable_only: Optional[bool] = None,
        custom_filter: Optional[Callable[[FileAnalysis], bool]] = None
    ) -> List[FileAnalysis]:
        """
        Filter analyses based on criteria.
        
        Args:
            file_types: List of file types to include (e.g., ['document', 'image'])
            categories: List of categories to include
            min_size_mb: Minimum file size in MB
            max_size_mb: Maximum file size in MB
            tags: Files must have at least one of these tags
            readable_only: Only include readable files
            custom_filter: Custom filter function
            
        Returns:
            Filtered list of FileAnalysis objects
        """
        filtered = self.analyses.copy()
        
        if file_types:
            filtered = [a for a in filtered if a.file_type in file_types]
        
        if categories:
            filtered = [a for a in filtered if a.category in categories]
        
        if min_size_mb is not None:
            filtered = [a for a in filtered if a.size_mb >= min_size_mb]
        
        if max_size_mb is not None:
            filtered = [a for a in filtered if a.size_mb <= max_size_mb]
        
        if tags:
            filtered = [a for a in filtered if any(tag in a.tags for tag in tags)]
        
        if readable_only is not None:
            filtered = [a for a in filtered if a.is_readable == readable_only]
        
        if custom_filter:
            filtered = [a for a in filtered if custom_filter(a)]
        
        return filtered
    
    def sort(
        self,
        analyses: Optional[List[FileAnalysis]] = None,
        key: str = 'path',
        reverse: bool = False
    ) -> List[FileAnalysis]:
        """
        Sort analyses.
        
        Args:
            analyses: List to sort (defaults to all analyses)
            key: Sort key ('path', 'size_mb', 'file_type', 'modified_time')
            reverse: Reverse sort order
            
        Returns:
            Sorted list
        """
        if analyses is None:
            analyses = self.analyses
        
        if key == 'path':
            return sorted(analyses, key=lambda x: x.path, reverse=reverse)
        elif key == 'size_mb':
            return sorted(analyses, key=lambda x: x.size_mb, reverse=reverse)
        elif key == 'file_type':
            return sorted(analyses, key=lambda x: (x.file_type, x.path), reverse=reverse)
        elif key == 'category':
            return sorted(analyses, key=lambda x: (x.category, x.path), reverse=reverse)
        else:
            return sorted(analyses, key=lambda x: getattr(x, key, ''), reverse=reverse)
    
    def group_by_type(self, analyses: Optional[List[FileAnalysis]] = None) -> Dict[str, List[FileAnalysis]]:
        """Group analyses by file type."""
        if analyses is None:
            analyses = self.analyses
        
        grouped = {}
        for analysis in analyses:
            if analysis.file_type not in grouped:
                grouped[analysis.file_type] = []
            grouped[analysis.file_type].append(analysis)
        
        return grouped
    
    def group_by_category(self, analyses: Optional[List[FileAnalysis]] = None) -> Dict[str, List[FileAnalysis]]:
        """Group analyses by category."""
        if analyses is None:
            analyses = self.analyses
        
        grouped = {}
        for analysis in analyses:
            category = analysis.category or 'unknown'
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(analysis)
        
        return grouped
    
    def get_statistics(self, analyses: Optional[List[FileAnalysis]] = None) -> AggregationStats:
        """Generate statistics about aggregated files."""
        if analyses is None:
            analyses = self.analyses
        
        stats = AggregationStats()
        stats.total_files = len(analyses)
        
        for analysis in analyses:
            # Count by type
            stats.files_by_type[analysis.file_type] = stats.files_by_type.get(analysis.file_type, 0) + 1
            
            # Count by category
            category = analysis.category or 'unknown'
            stats.files_by_category[category] = stats.files_by_category.get(category, 0) + 1
            
            # Total size
            stats.total_size_mb += analysis.size_mb
        
        stats.total_size_mb = round(stats.total_size_mb, 2)
        
        return stats
    
    def to_dict_list(self, analyses: Optional[List[FileAnalysis]] = None) -> List[Dict]:
        """Convert analyses to list of dictionaries."""
        if analyses is None:
            analyses = self.analyses
        
        result = []
        for analysis in analyses:
            data = asdict(analysis)
            # Convert datetime objects to strings
            if 'modified_time' in data and isinstance(data['modified_time'], datetime):
                data['modified_time'] = data['modified_time'].isoformat()
            if 'created_time' in data and isinstance(data['created_time'], datetime):
                data['created_time'] = data['created_time'].isoformat()
            result.append(data)
        
        return result
    
    def export_json(
        self,
        output_path: str,
        analyses: Optional[List[FileAnalysis]] = None,
        indent: int = 2,
        include_stats: bool = True
    ):
        """
        Export analyses to JSON file.
        
        Args:
            output_path: Path to output JSON file
            analyses: Analyses to export (defaults to all)
            indent: JSON indentation
            include_stats: Whether to include statistics in output
        """
        if analyses is None:
            analyses = self.analyses
        
        output_data = {
            'exported_at': datetime.now().isoformat(),
            'files': self.to_dict_list(analyses)
        }
        
        if include_stats:
            stats = self.get_statistics(analyses)
            output_data['statistics'] = {
                'total_files': stats.total_files,
                'total_size_mb': stats.total_size_mb,
                'files_by_type': stats.files_by_type,
                'files_by_category': stats.files_by_category
            }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=indent, ensure_ascii=False)
        
        self.logger.info(f"Exported {len(analyses)} files to {output_path}")
    
    def export_csv(
        self,
        output_path: str,
        analyses: Optional[List[FileAnalysis]] = None
    ):
        """
        Export analyses to CSV file.
        
        Args:
            output_path: Path to output CSV file
            analyses: Analyses to export (defaults to all)
        """
        if analyses is None:
            analyses = self.analyses
        
        if not analyses:
            self.logger.warning("No analyses to export")
            return
        
        # Get all unique keys from analyses
        all_keys = set()
        for analysis in analyses:
            all_keys.update(asdict(analysis).keys())
        
        # Define column order
        columns = [
            'path', 'file_type', 'category', 'size_mb', 'mime_type',
            'is_readable', 'encoding', 'line_count', 'word_count',
            'content_summary', 'tags'
        ]
        
        # Add any additional keys
        for key in sorted(all_keys):
            if key not in columns:
                columns.append(key)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()
            
            for analysis in analyses:
                row = asdict(analysis)
                # Convert lists/dicts to strings
                if 'tags' in row and isinstance(row['tags'], list):
                    row['tags'] = ', '.join(row['tags'])
                if 'metadata' in row and isinstance(row['metadata'], dict):
                    row['metadata'] = json.dumps(row['metadata'])
                # Convert datetime
                if 'modified_time' in row and isinstance(row['modified_time'], datetime):
                    row['modified_time'] = row['modified_time'].isoformat()
                if 'created_time' in row and isinstance(row['created_time'], datetime):
                    row['created_time'] = row['created_time'].isoformat()
                
                writer.writerow(row)
        
        self.logger.info(f"Exported {len(analyses)} files to {output_path}")
    
    def get_summary_report(self, analyses: Optional[List[FileAnalysis]] = None) -> str:
        """
        Generate a human-readable summary report.
        
        Args:
            analyses: Analyses to summarize (defaults to all)
            
        Returns:
            Formatted summary string
        """
        if analyses is None:
            analyses = self.analyses
        
        stats = self.get_statistics(analyses)
        
        report = []
        report.append("=" * 60)
        report.append("FILE AGGREGATION SUMMARY")
        report.append("=" * 60)
        report.append(f"\nTotal Files: {stats.total_files}")
        report.append(f"Total Size: {stats.total_size_mb:.2f} MB")
        report.append("\nFiles by Type:")
        
        for file_type, count in sorted(stats.files_by_type.items()):
            report.append(f"  {file_type:15s}: {count:5d} files")
        
        report.append("\nFiles by Category (Top 10):")
        sorted_categories = sorted(
            stats.files_by_category.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        for category, count in sorted_categories:
            report.append(f"  {category:15s}: {count:5d} files")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)
