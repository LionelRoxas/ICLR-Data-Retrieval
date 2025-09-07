"""
Handle data storage to JSONL format
"""
import json
import os
from typing import Dict, List
from pathlib import Path

class Storage:
    """Handle JSONL file operations"""
    
    def __init__(self, output_file: str = 'data/output/iclr2016-2025_main.jsonl'):
        """
        Initialize storage with output file path
        
        Args:
            output_file: Path to output JSONL file
        """
        self.output_file = output_file
        self._ensure_directory()
    
    def _ensure_directory(self):
        """Create output directory if it doesn't exist"""
        Path(self.output_file).parent.mkdir(parents=True, exist_ok=True)
    
    def save_paper(self, paper_data: Dict):
        """
        Append single paper to JSONL file
        
        Args:
            paper_data: Paper dictionary to save
        """
        with open(self.output_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(paper_data, ensure_ascii=False) + '\n')
    
    def save_papers(self, papers: List[Dict]):
        """
        Save multiple papers to JSONL file
        
        Args:
            papers: List of paper dictionaries
        """
        for paper in papers:
            self.save_paper(paper)
    
    def clear_file(self):
        """Clear/create empty output file"""
        open(self.output_file, 'w').close()
    
    def read_papers(self) -> List[Dict]:
        """
        Read all papers from JSONL file
        
        Returns:
            List of paper dictionaries
        """
        papers = []
        if os.path.exists(self.output_file):
            with open(self.output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        papers.append(json.loads(line))
        return papers
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about collected data
        
        Returns:
            Dictionary with statistics
        """
        papers = self.read_papers()
        
        stats = {
            'total_papers': len(papers),
            'papers_by_year': {},
            'total_reviews': 0,
            'papers_with_meta_review': 0
        }
        
        for paper in papers:
            year = paper.get('year', 'unknown')
            stats['papers_by_year'][year] = stats['papers_by_year'].get(year, 0) + 1
            stats['total_reviews'] += len(paper.get('official_reviews', []))
            if paper.get('meta_review', {}).get('text'):
                stats['papers_with_meta_review'] += 1
        
        return stats