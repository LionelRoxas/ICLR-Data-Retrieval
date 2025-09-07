# ICLR Dataset (2016-2025)

## Overview
A comprehensive dataset of ICLR (International Conference on Learning Representations) papers from 2016 to 2025, including both accepted and rejected submissions along with their reviews, meta-reviews, and decision outcomes.

## Dataset Format
- **File**: `iclr2016-2025_main.jsonl`
- **Format**: JSON Lines (one JSON object per line)
- **Encoding**: UTF-8
- **Total Papers**: 33,772

## Schema Description

Each line in the JSONL file represents a single paper submission with the following structure:

### Core Fields
- **`paper_id`** (string): Unique OpenReview identifier for the submission
- **`year`** (integer): Conference year (2016-2025)
- **`title`** (string): Paper title
- **`authors`** (list[string]): List of author names
- **`affiliations`** (list): Author affiliations (Note: Often empty due to API limitations)
- **`abstract`** (string): Full paper abstract
- **`url`** (string): OpenReview forum URL for the submission
- **`pdf_url`** (string): Direct link to the paper PDF
- **`crawl_timestamp`** (string): ISO format timestamp of when the data was collected

### Metadata
- **`page_metadata`** (object):
  - `venue` (string): Conference venue identifier (e.g., "ICLR.cc/2020/Conference")
  - `keywords` (list[string]): Paper keywords/tags
  - `number` (integer/null): Submission number (may be null for some years)

### Reviews
- **`official_reviews`** (list[object]): List of reviewer assessments
  - `reviewer_id` (string): Anonymized reviewer identifier
  - `score` (string): Review score/rating
  - `confidence` (string): Reviewer confidence level
  - `text` (string): Main review text
  - `date` (string): Review submission date (ISO format)
  - `strengths` (string): Listed strengths (empty for some years)
  - `weaknesses` (string): Listed weaknesses (empty for some years)  
  - `questions` (string): Reviewer questions (empty for some years)

### Decision Information
- **`meta_review`** (object): Area chair/meta-reviewer assessment
  - `text` (string): Meta-review content
  - `decision_rationale` (string): Rationale for the decision
- **`decision`** (string): Final decision (accept/reject/poster/oral/spotlight)

## Data Collection Methodology

### API Approach
We chose to use the OpenReview API rather than web scraping for several reasons:
1. **Reliability**: APIs provide structured, consistent data without HTML parsing complexities
2. **Efficiency**: Bulk data retrieval with proper pagination support
3. **Compliance**: Respectful of server resources with built-in rate limiting
4. **Completeness**: Direct access to all reviews and metadata

### API Version Strategy
- **OpenReview API v2** (primary): Used for years 2023-2025
  - Endpoint: `https://api2.openreview.net`
  - Features nested JSON structure with `value` keys
  - Better support for recent conference formats

- **OpenReview API v1** (fallback): Used for years 2016-2022, and as fallback for 2023+
  - Endpoint: `https://api.openreview.net`
  - Direct field access without nested structures
  - Required for older conference data

### Fallback Mechanism
For years 2023-2025, the collector first attempts API v2 with various invitation patterns:
- `ICLR.cc/{year}/Conference/-/Submission`
- `ICLR.cc/{year}/Conference/-/Blind_Submission`

If v2 returns no results, it automatically falls back to v1 to ensure complete data coverage.

## Field Variations by Year

### Consistent Fields (All Years)
- Core identification fields (paper_id, year, title, authors)
- Basic content (abstract, URLs)
- Decision information

### Year-Specific Variations
- **2016-2017**: Limited review structure, missing some detailed fields
- **2018-2022**: Standardized review format with strengths/weaknesses fields
- **2023-2025**: Enhanced metadata, but may require API fallback for complete data

### Known Limitations
1. **Affiliations**: Often empty due to API privacy restrictions
2. **Review Details**: Early years (2016-2017) have less structured review data
3. **PDF URLs**: Format varies slightly between years
4. **Submission Numbers**: Not consistently available across all years

## Dataset Statistics
- **Total Papers**: 33,772 (includes both accepted and rejected submissions)
- **Review Coverage**: Most papers include 3-4 official reviews
- **Decision Types**: Primarily accept/reject, with additional categories (poster/oral/spotlight) in later years
- **Year Range**: 2016-2025 (10 years of conference data)

## Usage Example
```python
import json

papers = []
with open('iclr2016-2025_main.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        papers.append(json.loads(line))

# Filter for accepted papers
accepted = [p for p in papers if p['decision'] == 'accept']

# Access reviews for a paper
reviews = papers[0]['official_reviews']

# Get papers from a specific year
papers_2024 = [p for p in papers if p['year'] == 2024]