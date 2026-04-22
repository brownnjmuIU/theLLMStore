"""
File Aggregation Tool - Crawler Module

This module provides functionality to crawl, identify, index, and aggregate
local files for users to understand their file contents before extraction.
"""

from .file_crawler import FileCrawler
from .file_analyzer import FileAnalyzer
from .aggregator import FileAggregator

__all__ = ['FileCrawler', 'FileAnalyzer', 'FileAggregator']
