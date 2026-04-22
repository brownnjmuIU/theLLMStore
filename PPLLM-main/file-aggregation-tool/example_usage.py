"""
Example usage script for the file aggregation crawler.

This demonstrates how to use the crawler module to discover, analyze,
and aggregate local files.
"""

import logging
import sys
from pathlib import Path

from crawler import FileCrawler, FileAnalyzer, FileAggregator
from crawler.config import CrawlerConfig, get_user_friendly_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def example_basic_crawl():
    """Basic example: crawl and analyze files."""
    print("=" * 60)
    print("Example 1: Basic File Crawling")
    print("=" * 60)
    
    # Initialize crawler
    crawler = FileCrawler(
        root_path=str(Path.home() / "Documents"),  # Start from Documents folder
        max_depth=2,  # Limit depth to 2 levels
        min_file_size=1024  # Only files larger than 1KB
    )
    
    # Crawl files
    print("\nCrawling files...")
    files = crawler.crawl()
    
    print(f"\nFound {len(files)} files")
    print(f"Crawl statistics: {crawler.get_stats()}")
    
    # Analyze files
    print("\nAnalyzing files...")
    analyzer = FileAnalyzer()
    aggregator = FileAggregator()
    
    # Analyze first 10 files as example
    for file_info in files[:10]:
        try:
            analysis = analyzer.analyze(file_info.path)
            aggregator.add_analysis(analysis)
            print(f"  Analyzed: {file_info.name} ({analysis.file_type})")
        except Exception as e:
            print(f"  Error analyzing {file_info.name}: {e}")
    
    # Get summary
    print("\n" + aggregator.get_summary_report())


def example_filtered_crawl():
    """Example: crawl with filtering."""
    print("\n" + "=" * 60)
    print("Example 2: Filtered Crawling (Documents Only)")
    print("=" * 60)
    
    # Use configuration
    config = get_user_friendly_config()
    config.root_path = str(Path.home() / "Documents")
    config.max_depth = 3
    config.filter_file_types = ['document']
    
    # Initialize components
    crawler = FileCrawler(
        root_path=config.root_path,
        max_depth=config.max_depth,
        exclude_dirs=config.exclude_dirs,
        exclude_extensions=config.exclude_extensions
    )
    
    analyzer = FileAnalyzer(
        max_preview_lines=config.max_preview_lines,
        max_preview_chars=config.max_preview_chars
    )
    
    aggregator = FileAggregator()
    
    # Crawl and analyze
    print("\nCrawling and analyzing documents...")
    files = crawler.crawl()
    
    for file_info in files:
        try:
            analysis = analyzer.analyze(file_info.path)
            aggregator.add_analysis(analysis)
        except Exception as e:
            print(f"  Error: {e}")
            continue
    
    # Filter results
    filtered = aggregator.filter(
        file_types=config.filter_file_types,
        min_size_mb=0.01  # At least 10KB
    )
    
    # Sort by size
    sorted_files = aggregator.sort(filtered, key='size_mb', reverse=True)
    
    print(f"\nFound {len(sorted_files)} document files")
    print("\nTop 5 largest documents:")
    for analysis in sorted_files[:5]:
        print(f"  {analysis.path}")
        print(f"    Type: {analysis.category}, Size: {analysis.size_mb} MB")
        if analysis.content_summary:
            print(f"    Summary: {analysis.content_summary[:100]}")
        print()


def example_export_results():
    """Example: crawl and export results."""
    print("\n" + "=" * 60)
    print("Example 3: Export Results to JSON/CSV")
    print("=" * 60)
    
    # Use a small test directory
    test_dir = Path.home() / "Documents"
    if not test_dir.exists():
        print(f"Test directory not found: {test_dir}")
        return
    
    crawler = FileCrawler(
        root_path=str(test_dir),
        max_depth=2,
        min_file_size=100  # At least 100 bytes
    )
    
    analyzer = FileAnalyzer()
    aggregator = FileAggregator()
    
    print("\nCrawling files...")
    files = crawler.crawl()
    print(f"Found {len(files)} files")
    
    # Analyze files (limit to first 50 for demo)
    print("\nAnalyzing files...")
    analyzed_count = 0
    for file_info in files[:50]:
        try:
            analysis = analyzer.analyze(file_info.path)
            aggregator.add_analysis(analysis)
            analyzed_count += 1
            if analyzed_count % 10 == 0:
                print(f"  Analyzed {analyzed_count} files...")
        except Exception as e:
            continue
    
    print(f"\nAnalyzed {analyzed_count} files")
    
    # Export to JSON
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    json_path = output_dir / "file_aggregation.json"
    print(f"\nExporting to JSON: {json_path}")
    aggregator.export_json(str(json_path), include_stats=True)
    
    # Export to CSV
    csv_path = output_dir / "file_aggregation.csv"
    print(f"Exporting to CSV: {csv_path}")
    aggregator.export_csv(str(csv_path))
    
    # Print summary
    print("\n" + aggregator.get_summary_report())


def example_grouped_analysis():
    """Example: group files by type."""
    print("\n" + "=" * 60)
    print("Example 4: Grouped Analysis")
    print("=" * 60)
    
    crawler = FileCrawler(
        root_path=str(Path.home() / "Documents"),
        max_depth=2
    )
    
    analyzer = FileAnalyzer()
    aggregator = FileAggregator()
    
    print("\nCrawling and analyzing...")
    files = crawler.crawl()
    
    for file_info in files[:30]:  # Limit for demo
        try:
            analysis = analyzer.analyze(file_info.path)
            aggregator.add_analysis(analysis)
        except Exception:
            continue
    
    # Group by type
    grouped = aggregator.group_by_type()
    
    print("\nFiles grouped by type:")
    for file_type, analyses in sorted(grouped.items()):
        total_size = sum(a.size_mb for a in analyses)
        print(f"\n{file_type.upper()}: {len(analyses)} files ({total_size:.2f} MB)")
        for analysis in analyses[:3]:  # Show first 3
            print(f"  - {Path(analysis.path).name} ({analysis.size_mb} MB)")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("FILE AGGREGATION CRAWLER - EXAMPLES")
    print("=" * 60)
    
    try:
        # Run examples
        example_basic_crawl()
        example_filtered_crawl()
        example_export_results()
        example_grouped_analysis()
        
        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
