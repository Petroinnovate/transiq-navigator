import sys, time
sys.path.insert(0, '.')
from app.processors.chunker.adaptive import AdaptiveChunker

# Simulate a medium-sized document with tables
text = '''
# Sales Report Q1

## Overview
Total revenue for Q1 exceeded expectations by 15 percent.

| Month | Revenue | Units | Growth |
|-------|---------|-------|--------|
| Jan   | 120000  | 450   | 12%    |
| Feb   | 145000  | 520   | 21%    |
| Mar   | 168000  | 610   | 16%    |

## Key Findings
Performance was strong across all regions. The eastern division led with 35% growth.
New product lines contributed significantly to overall revenue increase.
Customer retention improved by 8% year over year.

## Recommendations
Focus on western region expansion. Increase marketing budget by 20%.
''' * 100  # Simulate 100-page document

print(f'Input size: {len(text):,} chars')
c = AdaptiveChunker()
t0 = time.time()
chunks = c.chunk_with_metadata(text)
elapsed = time.time() - t0
print(f'Chunks: {len(chunks)}, Time: {elapsed:.3f}s')
print('PASS' if elapsed < 5 else 'SLOW')
