"""
Simple test script to verify the crawler module works correctly.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from crawler import FileCrawler, FileAnalyzer, FileAggregator

def test_basic_functionality():
    """Test basic crawler functionality."""
    print("Testing File Crawler Module...")
    print("=" * 60)
    
    # Test 1: Initialize crawler
    print("\n1. Testing crawler initialization...")
    try:
        crawler = FileCrawler(root_path=str(Path.home() / "Documents"), max_depth=1)
        print("   ✓ Crawler initialized successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Test 2: Crawl files
    print("\n2. Testing file discovery...")
    try:
        files = crawler.crawl()
        print(f"   ✓ Found {len(files)} files")
        print(f"   Statistics: {crawler.get_stats()}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Test 3: Analyze a file
    print("\n3. Testing file analysis...")
    if files:
        try:
            analyzer = FileAnalyzer()
            test_file = files[0]
            analysis = analyzer.analyze(test_file.path)
            print(f"   ✓ Analyzed: {test_file.name}")
            print(f"     Type: {analysis.file_type}, Category: {analysis.category}")
            print(f"     Size: {analysis.size_mb} MB")
        except Exception as e:
            print(f"   ✗ Error analyzing file: {e}")
            return False
    else:
        print("   ⚠ No files found to analyze")
    
    # Test 4: Aggregate files
    print("\n4. Testing file aggregation...")
    try:
        aggregator = FileAggregator()
        analyzer = FileAnalyzer()
        
        # Analyze first 5 files
        for file_info in files[:5]:
            try:
                analysis = analyzer.analyze(file_info.path)
                aggregator.add_analysis(analysis)
            except Exception:
                continue
        
        stats = aggregator.get_statistics()
        print(f"   ✓ Aggregated {stats.total_files} files")
        print(f"     Total size: {stats.total_size_mb} MB")
        print(f"     Files by type: {stats.files_by_type}")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Test 5: Export functionality
    print("\n5. Testing export functionality...")
    try:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        aggregator.export_json(str(output_dir / "test_output.json"))
        aggregator.export_csv(str(output_dir / "test_output.csv"))
        print("   ✓ Exported to JSON and CSV")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1)
