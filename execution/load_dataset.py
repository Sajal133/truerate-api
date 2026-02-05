#!/usr/bin/env python3
"""
Dataset Loader Module
=====================
Loads and indexes Amazon review datasets for product-based analysis.

Usage:
    from execution.load_dataset import DatasetLoader
    
    loader = DatasetLoader("data/Cell_Phones_and_Accessories_5.json.gz")
    product = loader.get_product("B00001P4ZH")
    # Returns: {"asin": "...", "reviews": [...], "review_count": 123}

Cost: $0 (local processing)
"""

import gzip
import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Optional
import pickle


class DatasetLoader:
    """
    Load and index Amazon reviews by product ASIN.
    
    Features:
        - Lazy loading (only loads when first accessed)
        - Caching (saves processed index for fast reload)
        - Memory-efficient (streams large files)
    """
    
    def __init__(self, dataset_path: str, cache_dir: str = ".tmp"):
        """
        Initialize the dataset loader.
        
        Args:
            dataset_path: Path to gzipped JSON dataset
            cache_dir: Directory for cached index
        """
        self.dataset_path = Path(dataset_path)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self._product_index = None
        self._review_data = None
        self._loaded = False
        
    @property
    def cache_path(self) -> Path:
        """Path to cached index file."""
        return self.cache_dir / f"{self.dataset_path.stem}_index.pkl"
    
    def _load_from_cache(self) -> bool:
        """Try to load from cache. Returns True if successful."""
        if self.cache_path.exists():
            try:
                cache_mtime = self.cache_path.stat().st_mtime
                data_mtime = self.dataset_path.stat().st_mtime
                
                # Only use cache if it's newer than the data
                if cache_mtime > data_mtime:
                    print(f"Loading from cache: {self.cache_path}")
                    with open(self.cache_path, 'rb') as f:
                        cached = pickle.load(f)
                        self._product_index = cached['index']
                        self._review_data = cached['reviews']
                        self._loaded = True
                        return True
            except Exception as e:
                print(f"Cache load failed: {e}")
        return False
    
    def _save_to_cache(self):
        """Save processed data to cache."""
        try:
            print(f"Saving to cache: {self.cache_path}")
            with open(self.cache_path, 'wb') as f:
                pickle.dump({
                    'index': self._product_index,
                    'reviews': self._review_data
                }, f)
        except Exception as e:
            print(f"Cache save failed: {e}")
    
    def load(self, max_reviews: Optional[int] = None, show_progress: bool = True):
        """
        Load the dataset and build product index.
        
        Args:
            max_reviews: Limit number of reviews to load (None = all)
            show_progress: Print progress updates
        """
        if self._loaded:
            return
        
        # Try cache first
        if max_reviews is None and self._load_from_cache():
            return
        
        if show_progress:
            print(f"Loading dataset: {self.dataset_path}")
        
        self._product_index = defaultdict(list)
        self._review_data = []
        
        # Stream the gzipped file
        with gzip.open(self.dataset_path, 'rt', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if max_reviews and i >= max_reviews:
                    break
                
                if show_progress and i % 50000 == 0:
                    print(f"  Loaded {i:,} reviews...")
                
                try:
                    review = json.loads(line)
                    
                    # Store review with index
                    review_entry = {
                        "id": i,
                        "stars": int(review.get("overall", 3)),
                        "text": review.get("reviewText", ""),
                        "summary": review.get("summary", ""),
                        "verified": review.get("verified", False),
                        "date": review.get("reviewTime", ""),
                        "asin": review.get("asin", "")
                    }
                    
                    self._review_data.append(review_entry)
                    self._product_index[review["asin"]].append(i)
                    
                except (json.JSONDecodeError, KeyError) as e:
                    continue
        
        self._loaded = True
        
        if show_progress:
            print(f"  Total: {len(self._review_data):,} reviews, {len(self._product_index):,} products")
        
        # Cache if we loaded everything
        if max_reviews is None:
            self._save_to_cache()
    
    def get_product(self, asin: str) -> Optional[dict]:
        """
        Get all reviews for a product.
        
        Args:
            asin: Amazon Standard Identification Number
            
        Returns:
            dict with asin, reviews list, review_count, or None if not found
        """
        if not self._loaded:
            self.load()
        
        if asin not in self._product_index:
            return None
        
        review_indices = self._product_index[asin]
        reviews = [self._review_data[i] for i in review_indices]
        
        return {
            "asin": asin,
            "reviews": reviews,
            "review_count": len(reviews),
            "average_stars": sum(r["stars"] for r in reviews) / len(reviews) if reviews else 0
        }
    
    def search_products(self, query: str = "", limit: int = 20) -> list:
        """
        Search for products (returns products with most reviews).
        
        Args:
            query: Optional search term (searches in review text)
            limit: Maximum results to return
            
        Returns:
            List of product info dicts
        """
        if not self._loaded:
            self.load()
        
        # Sort products by review count
        products = []
        for asin, review_indices in self._product_index.items():
            if len(review_indices) >= 5:  # Only products with 5+ reviews
                # Get a sample review for context
                sample = self._review_data[review_indices[0]]
                
                products.append({
                    "asin": asin,
                    "review_count": len(review_indices),
                    "sample_summary": sample.get("summary", "")[:50]
                })
        
        # Sort by review count descending
        products.sort(key=lambda x: x["review_count"], reverse=True)
        
        return products[:limit]
    
    def get_stats(self) -> dict:
        """Get dataset statistics."""
        if not self._loaded:
            self.load()
        
        return {
            "total_reviews": len(self._review_data),
            "total_products": len(self._product_index),
            "avg_reviews_per_product": len(self._review_data) / len(self._product_index) if self._product_index else 0
        }


# ============================================
# CLI Interface
# ============================================

def main():
    """Command-line interface for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Load and query Amazon review dataset")
    parser.add_argument("--data", default="data/Cell_Phones_and_Accessories_5.json.gz",
                        help="Path to dataset")
    parser.add_argument("--max", type=int, help="Max reviews to load")
    parser.add_argument("--asin", help="Get reviews for specific ASIN")
    parser.add_argument("--top", type=int, default=10, help="Show top N products by review count")
    
    args = parser.parse_args()
    
    loader = DatasetLoader(args.data)
    loader.load(max_reviews=args.max)
    
    # Show stats
    stats = loader.get_stats()
    print(f"\nDataset Stats:")
    print(f"  Reviews: {stats['total_reviews']:,}")
    print(f"  Products: {stats['total_products']:,}")
    print(f"  Avg reviews/product: {stats['avg_reviews_per_product']:.1f}")
    
    if args.asin:
        product = loader.get_product(args.asin)
        if product:
            print(f"\nProduct {args.asin}:")
            print(f"  Reviews: {product['review_count']}")
            print(f"  Avg Stars: {product['average_stars']:.2f}")
            print(f"  Sample reviews:")
            for r in product['reviews'][:3]:
                print(f"    {r['stars']}★: {r['text'][:60]}...")
        else:
            print(f"Product {args.asin} not found")
    else:
        # Show top products
        print(f"\nTop {args.top} products by review count:")
        for i, p in enumerate(loader.search_products(limit=args.top), 1):
            print(f"  {i}. {p['asin']}: {p['review_count']} reviews")


if __name__ == "__main__":
    main()
