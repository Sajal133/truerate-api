# Truth Gap Analyser - API & Data Sources Reference

> **Purpose:** Central reference for all FREE APIs, data sources, NLP models, and training datasets.
> **Cost:** $0 for development and training phase
>
> **Last Updated:** 2026-01-31

---

## 📋 Table of Contents

1. [Free NLP Tools](#-free-nlp-tools)
2. [Free Training Datasets](#-free-training-datasets)
3. [Local Model Setup](#-local-model-setup)
4. [Environment Configuration](#-environment-configuration)
5. [Future Paid Options](#-future-paid-options-post-mvp)

---

## 🧠 Free NLP Tools

### Overview: Zero-Cost Stack

| Tool | Type | Accuracy | Speed | Use Case |
|------|------|----------|-------|----------|
| **VADER** | Rule-based | ~75% | ⚡ Instant | Primary sentiment |
| **DistilBERT** | Transformer | ~85% | 🚀 Fast | Higher accuracy |
| **RoBERTa** | Transformer | ~91% | 🐢 Medium | Best accuracy |
| **spaCy** | NLP toolkit | N/A | ⚡ Fast | Text preprocessing |
| **langdetect** | Detection | ~98% | ⚡ Instant | Language detection |

**Total Cost: $0** — All run locally on your machine.

---

### 1. VADER Sentiment Analyzer

**Best for:** Fast baseline processing, real-time analysis

| Attribute | Value |
|-----------|-------|
| **Library** | `vaderSentiment` |
| **Install** | `pip install vaderSentiment` |
| **Accuracy** | ~75% on product reviews |
| **Speed** | <1ms per review |
| **Memory** | <50MB |
| **Network** | Not required |

**Usage:**
```python
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def analyze_sentiment_vader(text: str) -> dict:
    """
    Analyze sentiment using VADER (free, instant, offline).
    
    Returns:
        sentiment_score: -1.0 (negative) to +1.0 (positive)
        confidence: Based on magnitude of compound score
    """
    if not text or len(text.strip()) < 3:
        return {"sentiment_score": 0.0, "confidence": 0.0}
    
    scores = analyzer.polarity_scores(text)
    
    return {
        "sentiment_score": scores["compound"],  # -1 to +1
        "positive": scores["pos"],
        "negative": scores["neg"],
        "neutral": scores["neu"],
        "confidence": abs(scores["compound"])  # Higher = more confident
    }

# Example
result = analyze_sentiment_vader("This product is amazing!")
# {'sentiment_score': 0.5859, 'positive': 0.535, 'negative': 0.0, 'neutral': 0.465, 'confidence': 0.5859}
```

**Strengths:**
- ✅ Instant processing (1000s of reviews per second)
- ✅ No API costs ever
- ✅ Works offline
- ✅ Good with social media text, emojis, slang

**Weaknesses:**
- ❌ Struggles with sarcasm
- ❌ No context understanding
- ❌ English only

---

### 2. HuggingFace Transformers (Local)

**Best for:** Higher accuracy when VADER confidence is low

#### Recommended Models (All Free)

| Model | Accuracy | Size | Speed | Languages |
|-------|----------|------|-------|-----------|
| `distilbert-base-uncased-finetuned-sst-2-english` | 85% | 250MB | Fast | English |
| `cardiffnlp/twitter-roberta-base-sentiment-latest` | 91% | 500MB | Medium | English |
| `nlptown/bert-base-multilingual-uncased-sentiment` | 88% | 700MB | Medium | 6 languages |
| `tabularisai/multilingual-sentiment-analysis` | 85% | 1.1GB | Slow | 17 languages |

**Installation:**
```bash
pip install transformers torch

# For CPU-only (smaller install)
pip install transformers
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

**Usage:**
```python
from transformers import pipeline

# Load once at startup (downloads model on first run)
sentiment_pipeline = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english"
)

def analyze_sentiment_transformer(text: str) -> dict:
    """
    Analyze sentiment using DistilBERT (free, local, higher accuracy).
    
    Returns:
        sentiment_score: -1.0 to +1.0
        confidence: Model confidence
    """
    if not text or len(text.strip()) < 3:
        return {"sentiment_score": 0.0, "confidence": 0.0}
    
    # Truncate to 512 tokens (BERT limit)
    text = text[:512]
    
    result = sentiment_pipeline(text)[0]
    
    # Convert to -1 to +1 scale
    if result["label"] == "POSITIVE":
        score = result["score"]
    else:
        score = -result["score"]
    
    return {
        "sentiment_score": score,
        "confidence": result["score"],
        "label": result["label"]
    }

# Example
result = analyze_sentiment_transformer("This product is terrible!")
# {'sentiment_score': -0.9987, 'confidence': 0.9987, 'label': 'NEGATIVE'}
```

**Hybrid Approach (Recommended):**
```python
def analyze_sentiment_hybrid(text: str) -> dict:
    """
    Use VADER first, escalate to transformer if low confidence.
    Cost: $0 | Accuracy: ~88%
    """
    # Step 1: Fast VADER check
    vader_result = analyze_sentiment_vader(text)
    
    # Step 2: If high confidence, use VADER result
    if vader_result["confidence"] > 0.6:
        return {
            "sentiment_score": vader_result["sentiment_score"],
            "confidence": vader_result["confidence"],
            "model_used": "vader"
        }
    
    # Step 3: Low confidence → use transformer
    transformer_result = analyze_sentiment_transformer(text)
    return {
        "sentiment_score": transformer_result["sentiment_score"],
        "confidence": transformer_result["confidence"],
        "model_used": "distilbert"
    }
```

---

### 3. spaCy (Text Preprocessing)

**Best for:** Tokenization, lemmatization, entity extraction

| Attribute | Value |
|-----------|-------|
| **Library** | `spacy` |
| **Install** | `pip install spacy` |
| **Model** | `en_core_web_sm` (small, fast) |
| **Memory** | ~50MB |

**Installation:**
```bash
pip install spacy
python -m spacy download en_core_web_sm
```

**Usage:**
```python
import spacy

nlp = spacy.load("en_core_web_sm")

def preprocess_text(text: str) -> dict:
    """Clean and analyze text structure."""
    doc = nlp(text)
    
    return {
        "tokens": [token.text for token in doc],
        "lemmas": [token.lemma_ for token in doc if not token.is_stop],
        "entities": [(ent.text, ent.label_) for ent in doc.ents],
        "word_count": len([t for t in doc if not t.is_punct]),
        "sentence_count": len(list(doc.sents))
    }

# Example
result = preprocess_text("The iPhone 15 has a great screen but terrible battery.")
# {'tokens': [...], 'lemmas': ['iPhone', 'great', 'screen', 'terrible', 'battery'], ...}
```

---

### 4. langdetect (Language Detection)

**Best for:** Filtering non-English reviews for English-only models

| Attribute | Value |
|-----------|-------|
| **Library** | `langdetect` |
| **Install** | `pip install langdetect` |
| **Accuracy** | ~98% |
| **Speed** | Instant |

**Usage:**
```python
from langdetect import detect, DetectorFactory

# Make results deterministic
DetectorFactory.seed = 0

def detect_language(text: str) -> str:
    """Detect language of text. Returns ISO 639-1 code (e.g., 'en', 'es', 'fr')."""
    try:
        if not text or len(text.strip()) < 10:
            return "unknown"
        return detect(text)
    except:
        return "unknown"

# Example
detect_language("This is a great product!")  # 'en'
detect_language("C'est un excellent produit!")  # 'fr'
```

---

## 📊 Free Training Datasets

### Overview: Academic & Open Datasets

| Dataset | Reviews | Categories | Size | Best For |
|---------|---------|------------|------|----------|
| **Amazon Reviews (UCSD)** | 233M+ | 29 categories | 34GB | Product reviews |
| **Yelp Open Dataset** | 8M+ | Restaurants | 9GB | Business reviews |
| **IMDB Reviews** | 50K | Movies | 80MB | Sentiment baseline |
| **SST-2** | 67K | Sentences | 10MB | Fine-tuning |
| **Sarcasm Headlines** | 28K | News | 5MB | Sarcasm detection |

**Total Cost: $0** — All freely available for research/development.

---

### 1. Amazon Product Reviews Dataset (UCSD)

**The primary dataset for this project.**

| Attribute | Value |
|-----------|-------|
| **Source** | UC San Diego / Julian McAuley |
| **Size** | 233M+ reviews (1996-2018) |
| **Categories** | 29 product categories |
| **Format** | JSON (gzipped) |
| **License** | Research/academic use |

**Download Links:**
```bash
# Small samples (5-core: users with 5+ reviews)
# Electronics - 1.7GB
wget https://jmcauley.ucsd.edu/data/amazon_v2/categoryFilesSmall/Electronics_5.json.gz

# Home & Kitchen - 800MB
wget https://jmcauley.ucsd.edu/data/amazon_v2/categoryFilesSmall/Home_and_Kitchen_5.json.gz

# Cell Phones - 200MB
wget https://jmcauley.ucsd.edu/data/amazon_v2/categoryFilesSmall/Cell_Phones_and_Accessories_5.json.gz

# Full dataset (ALL reviews) - much larger
wget https://jmcauley.ucsd.edu/data/amazon_v2/categoryFiles/Electronics.json.gz
```

**Data Schema:**
```json
{
  "overall": 5.0,
  "verified": true,
  "reviewTime": "01 1, 2018",
  "reviewerID": "A1234EXAMPLE",
  "asin": "B00001P4ZH",
  "reviewerName": "Customer Name",
  "reviewText": "This is an excellent product. The quality is amazing and it arrived quickly.",
  "summary": "Five Stars",
  "unixReviewTime": 1514764800
}
```

**Loading Script:**
```python
import gzip
import json

def load_amazon_reviews(filepath: str, max_reviews: int = None):
    """Load Amazon reviews from gzipped JSON file."""
    reviews = []
    
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if max_reviews and i >= max_reviews:
                break
            
            review = json.loads(line)
            reviews.append({
                "stars": review["overall"],
                "text": review.get("reviewText", ""),
                "verified": review.get("verified", False),
                "date": review.get("reviewTime", ""),
                "product_id": review["asin"]
            })
    
    return reviews

# Load 1000 reviews for testing
reviews = load_amazon_reviews("Electronics_5.json.gz", max_reviews=1000)
```

---

### 2. Yelp Open Dataset

| Attribute | Value |
|-----------|-------|
| **Source** | Yelp |
| **Size** | 8M+ reviews, 160K businesses |
| **Format** | JSON |
| **License** | Academic (requires agreement) |
| **Sign Up** | [yelp.com/dataset](https://www.yelp.com/dataset) |

**Data Schema:**
```json
{
  "review_id": "abc123",
  "user_id": "user456",
  "business_id": "biz789",
  "stars": 4,
  "date": "2018-01-01",
  "text": "Great food, but slow service...",
  "useful": 2,
  "funny": 0,
  "cool": 1
}
```

---

### 3. IMDB Movie Reviews (Stanford)

**Good for baseline sentiment model validation.**

| Attribute | Value |
|-----------|-------|
| **Source** | Stanford AI Lab |
| **Size** | 50,000 reviews (balanced 25K pos / 25K neg) |
| **Format** | Text files |
| **License** | Research use |

**Download & Load:**
```bash
wget https://ai.stanford.edu/~amaas/data/sentiment/aclImdb_v1.tar.gz
tar -xzf aclImdb_v1.tar.gz
```

```python
import os
from pathlib import Path

def load_imdb_reviews(data_dir: str):
    """Load IMDB reviews for sentiment analysis."""
    reviews = []
    
    for split in ["train", "test"]:
        for sentiment in ["pos", "neg"]:
            folder = Path(data_dir) / split / sentiment
            for filepath in folder.glob("*.txt"):
                with open(filepath, 'r', encoding='utf-8') as f:
                    reviews.append({
                        "text": f.read(),
                        "sentiment": 1 if sentiment == "pos" else -1,
                        "split": split
                    })
    
    return reviews

reviews = load_imdb_reviews("aclImdb")
```

---

### 4. Sarcasm Headlines Dataset (Kaggle)

**For training/testing sarcasm detection.**

| Attribute | Value |
|-----------|-------|
| **Source** | Kaggle / Rishabh Misra |
| **Size** | 28,619 headlines |
| **Format** | JSON |
| **License** | CC0 (Public Domain) |
| **Download** | [kaggle.com/rmisra/news-headlines-dataset-for-sarcasm-detection](https://www.kaggle.com/datasets/rmisra/news-headlines-dataset-for-sarcasm-detection) |

**Data Schema:**
```json
{
  "article_link": "https://...",
  "headline": "thirtysomething scientists unveil doomsday clock of hair loss",
  "is_sarcastic": 1
}
```

**Loading:**
```python
import json

def load_sarcasm_data(filepath: str):
    """Load sarcasm dataset for training."""
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            item = json.loads(line)
            data.append({
                "text": item["headline"],
                "is_sarcastic": bool(item["is_sarcastic"])
            })
    return data
```

---

### 5. Kaggle Amazon Reviews (Alternative)

**Pre-formatted, easier to use than UCSD.**

| Attribute | Value |
|-----------|-------|
| **Source** | Kaggle |
| **Size** | 34M reviews |
| **Format** | CSV |
| **License** | Public |
| **Download** | [kaggle.com/bittlingmayer/amazonreviews](https://www.kaggle.com/datasets/bittlingmayer/amazonreviews) |

---

## 🔧 Local Model Setup

### One-Time Installation Script

```bash
#!/bin/bash
# setup_nlp_models.sh
# Run this once to download all required models

echo "Installing Python dependencies..."
pip install vaderSentiment transformers torch spacy langdetect pandas numpy

echo "Downloading spaCy English model..."
python -m spacy download en_core_web_sm

echo "Pre-downloading HuggingFace models..."
python -c "
from transformers import pipeline
print('Downloading DistilBERT sentiment model...')
pipeline('sentiment-analysis', model='distilbert-base-uncased-finetuned-sst-2-english')
print('Done!')
"

echo "Testing VADER..."
python -c "
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
analyzer = SentimentIntensityAnalyzer()
result = analyzer.polarity_scores('This is a great test!')
print(f'VADER test: {result}')
"

echo "✅ All models installed and ready!"
```

### Model Storage Location

```bash
# HuggingFace models are cached here:
~/.cache/huggingface/hub/

# spaCy models:
# macOS: ~/Library/Application Support/spacy/
# Linux: ~/.local/share/spacy/

# To check disk usage:
du -sh ~/.cache/huggingface/
```

### Offline Mode

```python
# Set these before importing transformers for fully offline operation:
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

from transformers import pipeline
# Now uses only cached models, no network requests
```

---

## ⚙️ Environment Configuration

### Minimal .env for Zero-Cost Setup

```bash
# .env file - Zero-cost configuration

# ============================================
# Model Configuration (All Free/Local)
# ============================================

# Primary sentiment model
SENTIMENT_MODEL=hybrid  # Options: vader, distilbert, roberta, hybrid

# Sarcasm detection
SARCASM_MODEL=rule-based  # Options: rule-based (only free option)

# ============================================
# Processing Configuration
# ============================================

# Ratio weights (from research findings)
STAR_WEIGHT=0.2
SENTIMENT_WEIGHT=0.8

# VADER confidence threshold for hybrid mode
# Below this → escalate to transformer
VADER_CONFIDENCE_THRESHOLD=0.6

# Processing limits
BATCH_SIZE=100
MAX_REVIEWS_PER_PRODUCT=5000

# ============================================
# Data Paths
# ============================================

# Training data directory
DATA_DIR=./data

# Model cache (HuggingFace)
TRANSFORMERS_CACHE=~/.cache/huggingface/hub

# ============================================
# Logging
# ============================================
LOG_LEVEL=INFO
```

### requirements.txt (Free Tools Only)

```txt
# Core NLP (all free, local)
vaderSentiment>=3.3.2
transformers>=4.30.0
torch>=2.0.0
spacy>=3.7.0
langdetect>=1.0.9

# Data processing
pandas>=2.0.0
numpy>=1.24.0

# Utilities
python-dotenv>=1.0.0
tqdm>=4.65.0

# API (for later - currently not used)
# fastapi>=0.100.0
# uvicorn>=0.22.0
```

---

## 💡 Development Workflow (Zero Cost)

### Recommended Approach

```
┌─────────────────────────────────────────────────────────────┐
│  DEVELOPMENT PHASE (Current - $0)                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Load Amazon/Yelp academic datasets                      │
│  2. Process with VADER (instant, free)                      │
│  3. Escalate low-confidence to DistilBERT (local, free)     │
│  4. Validate against ground truth test cases                │
│  5. Tune credibility scoring algorithm                      │
│  6. Achieve target MAE < 0.75                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼ (After MVP validated)
┌─────────────────────────────────────────────────────────────┐
│  PRODUCTION PHASE (Future - Optional paid upgrades)         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  • Add OpenAI/Claude for edge cases (optional)              │
│  • Add RapidAPI for live Amazon scraping (optional)         │
│  • Deploy API with caching                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📈 Future Paid Options (Post-MVP)

> [!NOTE]
> These are **not required** for development. Document here for future reference only.

### When to Consider Paid APIs

| Scenario | Free Solution Works? | Paid Upgrade Benefit |
|----------|---------------------|---------------------|
| Processing 10K reviews | ✅ Yes (local models) | Slightly faster |
| Sarcasm in edge cases | ⚠️ 70% accuracy | 95% with GPT-4 |
| Live Amazon scraping | ❌ Not possible | RapidAPI enables it |
| Multi-language (rare) | ✅ mBERT works | Better with Claude |

### Cost If Needed Later

| Service | Free Tier | When to Pay |
|---------|-----------|-------------|
| OpenAI | $5 credit | Edge case escalation |
| RapidAPI | 100 req/mo | Live data collection |
| Google Places | Very limited | If analyzing Google reviews |

---

## 📝 Quick Reference

### Install Everything

```bash
pip install vaderSentiment transformers torch spacy langdetect pandas numpy python-dotenv tqdm
python -m spacy download en_core_web_sm
```

### Test Everything Works

```python
# test_nlp_setup.py
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from transformers import pipeline
import spacy
from langdetect import detect

# Test VADER
vader = SentimentIntensityAnalyzer()
print("VADER:", vader.polarity_scores("This is great!"))

# Test Transformer
sentiment = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
print("DistilBERT:", sentiment("This is terrible!"))

# Test spaCy
nlp = spacy.load("en_core_web_sm")
doc = nlp("The iPhone has a great screen.")
print("spaCy entities:", [(ent.text, ent.label_) for ent in doc.ents])

# Test langdetect
print("Language:", detect("Bonjour le monde"))

print("\n✅ All NLP tools working!")
```

### Dataset Quick Download

```bash
# Create data directory
mkdir -p data

# Download small Amazon sample (200MB)
cd data
wget https://jmcauley.ucsd.edu/data/amazon_v2/categoryFilesSmall/Cell_Phones_and_Accessories_5.json.gz

# Or Electronics (1.7GB)
wget https://jmcauley.ucsd.edu/data/amazon_v2/categoryFilesSmall/Electronics_5.json.gz
```

---

**Total Development Cost: $0** 🎉

*This document will be updated when paid integrations are added post-MVP.*
