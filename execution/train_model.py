#!/usr/bin/env python3
"""
Model Training Pipeline
=======================
Fine-tune a sentiment model on Amazon review data.

This script uses the star ratings as pseudo-labels for sentiment:
- 1-2 stars = Negative
- 3 stars = Neutral  
- 4-5 stars = Positive

Usage:
    python execution/train_model.py --max-samples 10000 --epochs 3

Output: Saves trained model to models/sentiment_finetuned/

Cost: $0 (runs locally, but requires ~4GB RAM for DistilBERT)
"""

import sys
import os
import json
import gzip
import random
import argparse
from pathlib import Path
from typing import List, Tuple
import pickle

# Check for required dependencies
try:
    import torch
    from torch.utils.data import Dataset, DataLoader
    from transformers import (
        DistilBertTokenizer, 
        DistilBertForSequenceClassification,
        Trainer, 
        TrainingArguments,
        EarlyStoppingCallback
    )
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support
    import numpy as np
    TRAINING_AVAILABLE = True
except ImportError as e:
    TRAINING_AVAILABLE = False
    MISSING_DEP = str(e)


# ============================================
# Dataset Class
# ============================================

class ReviewDataset(Dataset):
    """PyTorch Dataset for review sentiment classification."""
    
    def __init__(self, texts: List[str], labels: List[int], tokenizer, max_length: int = 128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]
        
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'labels': torch.tensor(label, dtype=torch.long)
        }


# ============================================
# Data Loading
# ============================================

def load_training_data(
    data_path: str,
    max_samples: int = 10000,
    min_text_length: int = 20
) -> Tuple[List[str], List[int]]:
    """
    Load Amazon reviews and convert to sentiment labels.
    
    Star to sentiment mapping:
        1-2 stars → 0 (Negative)
        3 stars   → 1 (Neutral)
        4-5 stars → 2 (Positive)
    """
    print(f"Loading data from: {data_path}")
    
    texts = []
    labels = []
    
    # Read samples from all star levels to ensure balance
    samples_by_label = {0: [], 1: [], 2: []}
    samples_per_class = max_samples // 3
    
    with gzip.open(data_path, 'rt', encoding='utf-8') as f:
        for line in f:
            try:
                review = json.loads(line)
                text = review.get('reviewText', '').strip()
                stars = int(review.get('overall', 3))
                
                # Skip short/empty reviews
                if len(text) < min_text_length:
                    continue
                
                # Map stars to labels
                if stars <= 2:
                    label = 0  # Negative
                elif stars == 3:
                    label = 1  # Neutral
                else:
                    label = 2  # Positive
                
                # Add if we need more of this class
                if len(samples_by_label[label]) < samples_per_class:
                    samples_by_label[label].append((text, label))
                
                # Check if we have enough
                if all(len(v) >= samples_per_class for v in samples_by_label.values()):
                    break
                    
            except (json.JSONDecodeError, KeyError):
                continue
    
    # Combine and shuffle
    all_samples = []
    for samples in samples_by_label.values():
        all_samples.extend(samples)
    
    random.shuffle(all_samples)
    
    texts = [s[0] for s in all_samples]
    labels = [s[1] for s in all_samples]
    
    print(f"Loaded {len(texts)} samples")
    print(f"  Negative (1-2★): {labels.count(0)}")
    print(f"  Neutral (3★): {labels.count(1)}")
    print(f"  Positive (4-5★): {labels.count(2)}")
    
    return texts, labels


# ============================================
# Training Functions
# ============================================

def compute_metrics(eval_pred):
    """Compute accuracy, precision, recall, F1."""
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)
    
    accuracy = accuracy_score(labels, predictions)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average='weighted'
    )
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1
    }


def train_model(
    train_texts: List[str],
    train_labels: List[int],
    output_dir: str = "models/sentiment_finetuned",
    epochs: int = 3,
    batch_size: int = 16,
    learning_rate: float = 2e-5
):
    """
    Fine-tune DistilBERT on review sentiment data.
    """
    print("\n" + "="*50)
    print("Starting Model Training")
    print("="*50)
    
    # Check device
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Load tokenizer and model
    print("Loading DistilBERT...")
    model_name = "distilbert-base-uncased"
    tokenizer = DistilBertTokenizer.from_pretrained(model_name)
    model = DistilBertForSequenceClassification.from_pretrained(
        model_name,
        num_labels=3,  # Negative, Neutral, Positive
        problem_type="single_label_classification"
    )
    
    # Split data
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        train_texts, train_labels, test_size=0.15, stratify=train_labels, random_state=42
    )
    
    print(f"Training samples: {len(train_texts)}")
    print(f"Validation samples: {len(val_texts)}")
    
    # Create datasets
    train_dataset = ReviewDataset(train_texts, train_labels, tokenizer)
    val_dataset = ReviewDataset(val_texts, val_labels, tokenizer)
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        warmup_steps=100,
        weight_decay=0.01,
        learning_rate=learning_rate,
        logging_dir=f"{output_dir}/logs",
        logging_steps=50,
        eval_strategy="steps",
        eval_steps=200,
        save_strategy="steps",
        save_steps=200,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        report_to="none",  # Disable wandb/tensorboard
        fp16=device == "cuda",  # Use mixed precision on CUDA
    )
    
    # Initialize trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)]
    )
    
    # Train!
    print("\nTraining started...")
    trainer.train()
    
    # Evaluate
    print("\nEvaluating...")
    results = trainer.evaluate()
    print(f"\nFinal Results:")
    print(f"  Accuracy: {results['eval_accuracy']:.4f}")
    print(f"  F1 Score: {results['eval_f1']:.4f}")
    print(f"  Precision: {results['eval_precision']:.4f}")
    print(f"  Recall: {results['eval_recall']:.4f}")
    
    # Save model
    print(f"\nSaving model to: {output_dir}")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    # Save training info
    info = {
        "model_name": model_name,
        "num_labels": 3,
        "label_map": {0: "negative", 1: "neutral", 2: "positive"},
        "training_samples": len(train_texts),
        "validation_samples": len(val_texts),
        "epochs": epochs,
        "final_accuracy": results['eval_accuracy'],
        "final_f1": results['eval_f1']
    }
    
    with open(f"{output_dir}/training_info.json", 'w') as f:
        json.dump(info, f, indent=2)
    
    print("\n✅ Training complete!")
    return results


# ============================================
# CLI
# ============================================

def main():
    parser = argparse.ArgumentParser(description="Train sentiment model on Amazon reviews")
    parser.add_argument("--data", default="data/Cell_Phones_and_Accessories_5.json.gz",
                        help="Path to training data")
    parser.add_argument("--output", default="models/sentiment_finetuned",
                        help="Output directory for trained model")
    parser.add_argument("--max-samples", type=int, default=9000,
                        help="Maximum training samples (balanced across classes)")
    parser.add_argument("--epochs", type=int, default=3,
                        help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16,
                        help="Training batch size")
    parser.add_argument("--lr", type=float, default=2e-5,
                        help="Learning rate")
    
    args = parser.parse_args()
    
    if not TRAINING_AVAILABLE:
        print(f"❌ Missing dependencies: {MISSING_DEP}")
        print("\nInstall with: pip install torch transformers scikit-learn")
        sys.exit(1)
    
    # Create output directory
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load data
    texts, labels = load_training_data(
        args.data,
        max_samples=args.max_samples
    )
    
    # Train model
    train_model(
        train_texts=texts,
        train_labels=labels,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr
    )


if __name__ == "__main__":
    main()
