"""
Main orchestrator for ICLR data collection
"""
from tqdm import tqdm
import time
from typing import List, Dict
from .api_client import OpenReviewClient
from .processor import PaperProcessor
from .storage import Storage

class ICLRCollector:
    """Orchestrate the collection of ICLR papers"""
    
    def __init__(self, username: str = None, password: str = None):
        """
        Initialize collector with API client, processor, and storage
        
        Args:
            username: OpenReview username (optional)
            password: OpenReview password (optional)
        """
        self.client = OpenReviewClient(username, password)
        self.processor = PaperProcessor()
        self.storage = Storage()
    
    def collect_year(self, year: int, append_mode: bool = True) -> List[Dict]:
        """
        Collect all papers for a specific year
        
        Args:
            year: Conference year to collect
            append_mode: If True, append to existing file. If False, clear file first.
            
        Returns:
            List of collected paper dictionaries
        """
        print(f"\n📚 Collecting ICLR {year}...")
        
        # Get submissions from API
        submissions = self.client.get_submissions(year)
        
        if not submissions:
            print(f"⚠️  No submissions found for {year}")
            return []
        
        print(f"📄 Found {len(submissions)} papers")
        
        # Process each paper
        papers = []
        for submission in tqdm(submissions, desc=f"Processing {year}"):
            try:
                # Build paper record
                paper = self.processor.build_paper_record(submission, year)
                
                # Save immediately (incremental save)
                self.storage.save_paper(paper)
                papers.append(paper)
                
                # Rate limiting
                self.client.add_delay(0.1)
                
            except Exception as e:
                print(f"\n⚠️  Error processing paper: {e}")
                continue
        
        print(f"✅ Collected {len(papers)} papers from ICLR {year}")
        return papers
    
    def collect_all(self, start_year: int = 2016, end_year: int = 2025):
        """
        Collect papers for all years in range
        
        Args:
            start_year: First year to collect
            end_year: Last year to collect
        """
        print(f"🚀 Starting ICLR data collection ({start_year}-{end_year})")
        print("=" * 50)
        
        # Clear output file for fresh start (only for collect_all)
        self.storage.clear_file()
        
        # Collect each year
        summary = {}
        for year in range(start_year, end_year + 1):
            try:
                papers = self.collect_year(year, append_mode=True)
                summary[year] = {
                    'success': True,
                    'count': len(papers)
                }
                
                # Delay between years to be respectful
                if year < end_year:
                    print("⏳ Waiting before next year...")
                    time.sleep(5)
                    
            except Exception as e:
                print(f"❌ Failed to collect {year}: {e}")
                summary[year] = {
                    'success': False,
                    'error': str(e)
                }
        
        # Print final summary
        self._print_summary(summary)
        
        # Generate README
        self._generate_readme()
    
    def _print_summary(self, summary: Dict):
        """Print collection summary"""
        print("\n" + "=" * 50)
        print("📊 COLLECTION SUMMARY")
        print("=" * 50)
        
        total = 0
        for year, result in sorted(summary.items()):
            if result['success']:
                print(f"  ✅ {year}: {result['count']} papers")
                total += result['count']
            else:
                print(f"  ❌ {year}: Failed")
        
        print(f"\n📈 Total papers collected: {total}")
        print(f"📁 Data saved to: {self.storage.output_file}")
    
    def _generate_readme(self):
        """Generate README with dataset documentation"""
        stats = self.storage.get_statistics()
        
        readme = f"""# ICLR Dataset (2016-2025)

## Overview
- **Total papers**: {stats['total_papers']}
- **Total reviews**: {stats['total_reviews']}
- **Papers with meta-reviews**: {stats['papers_with_meta_review']}
- **File**: iclr2016-2025_main.jsonl

## Papers by Year
"""
        for year in sorted(stats['papers_by_year'].keys()):
            readme += f"- {year}: {stats['papers_by_year'][year]} papers\n"
        
        readme += """
## Usage
```python
import json

papers = []
with open('data/output/iclr2016-2025_main.jsonl', 'r') as f:
    for line in f:
        papers.append(json.loads(line))
```
"""
        
        with open('README.md', 'w') as f:
            f.write(readme)
        
        print("📝 README.md generated")