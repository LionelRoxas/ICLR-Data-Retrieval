# ICLR Dataset (2016-2025)

## Overview
- **Total papers**: 33772
- **Total reviews**: 179277
- **Papers with meta-reviews**: 28893
- **File**: iclr2016-2025_main.jsonl

## Papers by Year
- 2016: 125 papers
- 2017: 651 papers
- 2018: 1284 papers
- 2019: 1419 papers
- 2020: 2213 papers
- 2021: 2594 papers
- 2022: 2617 papers
- 2023: 3793 papers
- 2024: 7404 papers
- 2025: 11672 papers

## Usage
```python
import json

papers = []
with open('data/output/iclr2016-2025_main.jsonl', 'r') as f:
    for line in f:
        papers.append(json.loads(line))
```
