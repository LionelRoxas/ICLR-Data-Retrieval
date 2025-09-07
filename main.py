#!/usr/bin/env python3
"""
Entry point for ICLR data collection
Usage:
    python main.py              # Collect all years (2016-2025)
    python main.py 2024         # Collect specific year
    python main.py 2020 2024    # Collect range of years
    python main.py --resume     # Resume from last incomplete year
    python main.py --resume 2023  # Resume from specific year
"""
import sys
import os
import json
from dotenv import load_dotenv
from src.collector import ICLRCollector
from src.storage import Storage

def get_last_collected_year():
    """Find the last successfully collected year from the JSONL file"""
    storage = Storage()
    try:
        papers = storage.read_papers()
        if papers:
            years = [p.get('year', 0) for p in papers]
            return max(years) if years else None
    except:
        return None

def main():
    """Main execution function"""
    # Load environment variables
    load_dotenv()
    
    # Optional credentials from .env
    username = os.getenv('OPENREVIEW_USERNAME')
    password = os.getenv('OPENREVIEW_PASSWORD')
    
    # Initialize collector
    collector = ICLRCollector(username, password)
    
    # Check for resume flag
    if '--resume' in sys.argv:
        # Remove the flag from args
        sys.argv.remove('--resume')
        
        # Check if a specific year is provided after --resume
        if len(sys.argv) > 1:
            start_year = int(sys.argv[1])
            print(f"📂 Resuming from year {start_year}...")
        else:
            # Auto-detect last year
            last_year = get_last_collected_year()
            if last_year:
                start_year = last_year + 1
                print(f"📂 Detected last collected year: {last_year}")
                print(f"📂 Resuming from year {start_year}...")
            else:
                start_year = 2016
                print(f"📂 No existing data found, starting from {start_year}...")
        
        # Don't clear the file when resuming
        for year in range(start_year, 2026):
            try:
                papers = collector.collect_year(year)
                if year < 2025:
                    print("⏳ Waiting before next year...")
                    import time
                    time.sleep(5)
            except Exception as e:
                print(f"❌ Failed to collect {year}: {e}")
                break
        
        # Print statistics
        stats = collector.storage.get_statistics()
        print(f"\n📊 Total papers in dataset: {stats['total_papers']}")
        
    # Parse command line arguments normally
    elif len(sys.argv) == 1:
        # No arguments: collect all years
        collector.collect_all()
        
    elif len(sys.argv) == 2:
        # Single argument: collect specific year
        year = int(sys.argv[1])
        papers = collector.collect_year(year)
        print(f"\n📊 Collected {len(papers)} papers from {year}")
        print(f"📁 Appended to: {collector.storage.output_file}")
        
    elif len(sys.argv) == 3:
        # Two arguments: collect range
        start_year = int(sys.argv[1])
        end_year = int(sys.argv[2])
        
        # Don't clear file for custom ranges - append instead
        for year in range(start_year, end_year + 1):
            try:
                papers = collector.collect_year(year)
                if year < end_year:
                    print("⏳ Waiting before next year...")
                    import time
                    time.sleep(5)
            except Exception as e:
                print(f"❌ Failed to collect {year}: {e}")
        
        # Print statistics
        stats = collector.storage.get_statistics()
        print(f"\n📊 Total papers in dataset: {stats['total_papers']}")
        
    else:
        print("Usage:")
        print("  python main.py              # Collect all years (2016-2025)")
        print("  python main.py 2024         # Collect specific year")
        print("  python main.py 2020 2024    # Collect range of years")
        print("  python main.py --resume     # Resume from last incomplete year")
        print("  python main.py --resume 2023  # Resume from specific year")
        sys.exit(1)

if __name__ == "__main__":
    main()