#!/usr/bin/env python3
"""
Combined Training Script
========================
Train on multiple Amazon review datasets for improved accuracy.

Combines:
- Cell Phones and Accessories (169MB)
- Electronics (80MB)

Usage:
    python execution/train_combined.py
"""

import sys
import os
import json
import gzip
import random
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from execution.train_model import (
    load_training_data, 
    train_model, 
    TRAINING_AVAILABLE
)


def load_multiple_datasets(data_paths: list, max_per_dataset: int = 5000) -> tuple:
    """Load and combine samples from multiple datasets."""
    all_texts = []
    all_labels = []
    
    for path in data_paths:
        if not Path(path).exists():
            print(f"⚠️  Skipping missing: {path}")
            continue
        
        print(f"\n📦 Loading: {path}")
        texts, labels = load_training_data(path, max_samples=max_per_dataset)
        all_texts.extend(texts)
        all_labels.extend(labels)
    
    # Shuffle combined data
    combined = list(zip(all_texts, all_labels))
    random.shuffle(combined)
    all_texts, all_labels = zip(*combined)
    
    print(f"\n📊 Combined Dataset:")
    print(f"  Total samples: {len(all_texts)}")
    print(f"  Negative: {all_labels.count(0)}")
    print(f"  Neutral: {all_labels.count(1)}")
    print(f"  Positive: {all_labels.count(2)}")
    
    return list(all_texts), list(all_labels)


def main():
    if not TRAINING_AVAILABLE:
        print("❌ Missing dependencies. Install with: pip install torch transformers scikit-learn")
        sys.exit(1)
    
    # Datasets to combine
    datasets = [
        "data/Cell_Phones_and_Accessories_5.json.gz",
        "data/Electronics_5.json.gz",
    ]
    
    # Load combined data (5000 per dataset = 10000 total, balanced)
    texts, labels = load_multiple_datasets(datasets, max_per_dataset=6000)
    
    # Train with more epochs
    train_model(
        train_texts=texts,
        train_labels=labels,
        output_dir="models/sentiment_finetuned",
        epochs=4,  # More epochs for better accuracy
        batch_size=16,
        learning_rate=2e-5
    )
    
    print("\n🎉 Enhanced training complete!")


if __name__ == "__main__":
    main()
