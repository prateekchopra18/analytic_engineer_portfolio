# Project 03 — Semantic Model Matching (Python)

> **Stack**: Python · YAML · Workato Custom Actions  
> **Status**: Production  
> **Context**: Data Genie semantic layer automation

## Overview

Python script deployed as a **Workato custom action** that automatically matches natural language query intent to the correct semantic model columns. Eliminates manual YAML parsing and improves SQL generation accuracy for the Data Genie MCP tool.

## Problem Statement

The `yaml_function` MCP tool returned non-deterministic results, consistently omitting business-critical columns:

| Missing Column | Impact |
|----------------|--------|
| `ACCOUNT_TO_LEAD_CONVERSION` | Lead funnel queries broken |
| `CONTRACT_NAME` / `CONTRACT_STATUS` | Contract analysis failed |
| `OPPORTUNITY_FROM_ACCOUNT_TYPE` | Segmentation queries wrong |
| `OPPORTUNITY_FROM_LEAD_TYPE` | Source attribution broken |

The fix: a deterministic Python matcher that uses the full 27-column schema from `extract_yaml_file` as ground truth.

## Architecture

```
User Query (natural language)
        │
        ▼
┌───────────────────────────┐
│  execute(params)          │  Workato entry point
│  params['yaml_object']    │  Pre-parsed YAML (dict)
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│  extract_columns()        │  Pull all column names
│  + descriptions           │  from semantic model
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│  score_relevance()        │  TF-IDF cosine similarity
│                           │  against query tokens
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│  return top_k columns     │  Ranked by match score
│  with metadata            │  + data types + verified SQL
└───────────────────────────┘
```

## Key Implementation Details

### Entry Point (Workato Custom Action)
```python
def execute(params):
    """
    Workato pre-parses the YAML object — no manual parsing needed.
    params['yaml_object'] is already a Python dict.
    """
    yaml_data = params['yaml_object']       # dict, not string
    query     = params['user_query']
    top_k     = params.get('top_k', 10)

    columns   = extract_columns(yaml_data)
    scored    = score_relevance(columns, query)

    return {
        'matched_columns': scored[:top_k],
        'total_columns':   len(columns),
        'query_tokens':    tokenize(query)
    }
```

### Scoring Logic
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def score_relevance(columns, query):
    corpus    = [query] + [c['description'] for c in columns]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    tfidf     = vectorizer.fit_transform(corpus)
    scores    = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()

    for i, col in enumerate(columns):
        col['match_score'] = round(float(scores[i]), 4)

    return sorted(columns, key=lambda x: x['match_score'], reverse=True)
```

## Results

| Metric | Before | After |
|--------|--------|-------|
| Column coverage | ~22/27 cols | 27/27 cols |
| Missing business columns | 5 | 0 |
| SQL generation accuracy | ~72% | ~94% |
| Determinism | Non-deterministic | Deterministic |

## Files

```
python-engineering/
├── README.md
├── src/
│   ├── semantic_matcher.py      # Core matching logic
│   ├── column_extractor.py      # YAML schema parser
│   └── utils.py                 # Tokenization helpers
├── tests/
│   ├── test_matcher.py          # Unit tests
│   └── fixtures/
│       └── sample_schema.yaml   # Test YAML schema
└── notebooks/
    └── matching_analysis.ipynb  # Accuracy benchmarking
```
