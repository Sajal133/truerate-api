#!/usr/bin/env python3
"""
Batch Review Processor
======================
Orchestrates the full analysis pipeline for batch review processing.

Usage:
    from execution.process_batch import ReviewProcessor
    
    processor = ReviewProcessor()
    results = processor.process_csv("reviews.csv")
    processor.save_results(results, "output.json")

Cost: $0 (all local processing)
"""

import json
import csv
import gzip
from pathlib import Path
from typing import Optional, Generator
from datetime import datetime

# Import execution modules
from analyze_sentiment import SentimentAnalyzer
from score_credibility import CredibilityScorer
from detect_sarcasm import SarcasmDetector
from calculate_weighted_rating import WeightedRatingCalculator


class ReviewProcessor:
    """
    Full pipeline processor for batch review analysis.
    
    Pipeline:
        1. Load reviews (CSV, JSON, JSONL)
        2. Analyze sentiment
        3. Score credibility
        4. Detect sarcasm
        5. Calculate weighted rating
        6. Aggregate product-level statistics
    """
    
    def __init__(self,
                 sentiment_mode: str = "hybrid",
                 star_weight: float = 0.2,
                 sentiment_weight: float = 0.8):
        """
        Initialize all processing modules.
        
        Args:
            sentiment_mode: "vader", "transformer", or "hybrid"
            star_weight: Weight for star rating (default 0.2)
            sentiment_weight: Weight for sentiment (default 0.8)
        """
        self.sentiment_analyzer = SentimentAnalyzer(mode=sentiment_mode)
        self.credibility_scorer = CredibilityScorer()
        self.sarcasm_detector = SarcasmDetector()
        self.rating_calculator = WeightedRatingCalculator(star_weight, sentiment_weight)
    
    def process_review(self, review: dict) -> dict:
        """
        Process a single review through the full pipeline.
        
        Args:
            review: Dict with 'text' and 'stars' keys
            
        Returns:
            Complete analysis result
        """
        text = review.get("text", "")
        stars = review.get("stars", 3)
        
        # Step 1: Sentiment Analysis
        sentiment_result = self.sentiment_analyzer.analyze(text)
        sentiment_score = sentiment_result.get("sentiment_score", 0.0)
        
        # Step 2: Credibility Scoring
        credibility_result = self.credibility_scorer.score(
            text=text,
            stars=stars,
            sentiment_score=sentiment_score
        )
        credibility = credibility_result.get("score", 1.0)
        
        # Step 3: Sarcasm Detection
        sarcasm_result = self.sarcasm_detector.detect(
            text=text,
            stars=stars,
            sentiment_score=sentiment_score
        )
        is_sarcastic = sarcasm_result.get("is_sarcastic", False)
        sarcasm_confidence = sarcasm_result.get("confidence", 0.0)
        
        # Step 4: Weighted Rating Calculation
        rating_result = self.rating_calculator.calculate(
            stars=stars,
            sentiment_score=sentiment_score,
            credibility=credibility,
            is_sarcastic=is_sarcastic,
            sarcasm_confidence=sarcasm_confidence
        )
        
        return {
            "original": {
                "text": text,
                "stars": stars,
                "verified": review.get("verified", False),
                "product_id": review.get("product_id", review.get("asin", "")),
                "date": review.get("date", review.get("reviewTime", ""))
            },
            "analysis": {
                "sentiment": sentiment_result,
                "credibility": credibility_result,
                "sarcasm": sarcasm_result
            },
            "result": {
                "adjusted_rating": rating_result["adjusted_rating"],
                "original_stars": stars,
                "rating_delta": round(rating_result["adjusted_rating"] - stars, 2),
                "classification": credibility_result["classification"],
                "is_sarcastic": is_sarcastic
            }
        }
    
    def process_batch(self, reviews: list[dict], show_progress: bool = True) -> list[dict]:
        """
        Process multiple reviews.
        
        Args:
            reviews: List of review dicts
            show_progress: Print progress updates
            
        Returns:
            List of processed results
        """
        results = []
        total = len(reviews)
        
        for i, review in enumerate(reviews):
            if show_progress and i % 100 == 0:
                print(f"Processing {i}/{total} reviews...")
            
            results.append(self.process_review(review))
        
        if show_progress:
            print(f"✓ Completed {total} reviews")
        
        return results
    
    def load_csv(self, filepath: str, 
                 text_column: str = "text",
                 stars_column: str = "stars",
                 max_rows: Optional[int] = None) -> list[dict]:
        """
        Load reviews from CSV file.
        
        Args:
            filepath: Path to CSV file
            text_column: Column name for review text
            stars_column: Column name for star rating
            max_rows: Maximum rows to load (None = all)
        """
        reviews = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if max_rows and i >= max_rows:
                    break
                
                reviews.append({
                    "text": row.get(text_column, ""),
                    "stars": int(float(row.get(stars_column, 3))),
                    **{k: v for k, v in row.items() if k not in [text_column, stars_column]}
                })
        
        print(f"Loaded {len(reviews)} reviews from {filepath}")
        return reviews
    
    def load_json(self, filepath: str, max_rows: Optional[int] = None) -> list[dict]:
        """
        Load reviews from JSON file (array or JSONL).
        """
        reviews = []
        
        # Handle gzipped files
        opener = gzip.open if filepath.endswith('.gz') else open
        
        with opener(filepath, 'rt', encoding='utf-8') as f:
            first_char = f.read(1)
            f.seek(0)
            
            if first_char == '[':
                # JSON array
                data = json.load(f)
                for i, item in enumerate(data):
                    if max_rows and i >= max_rows:
                        break
                    reviews.append(self._normalize_review(item))
            else:
                # JSONL (one JSON per line)
                for i, line in enumerate(f):
                    if max_rows and i >= max_rows:
                        break
                    reviews.append(self._normalize_review(json.loads(line)))
        
        print(f"Loaded {len(reviews)} reviews from {filepath}")
        return reviews
    
    def _normalize_review(self, item: dict) -> dict:
        """Normalize review dict to standard format."""
        return {
            "text": item.get("text", item.get("reviewText", "")),
            "stars": int(item.get("stars", item.get("overall", 3))),
            "verified": item.get("verified", False),
            "product_id": item.get("product_id", item.get("asin", "")),
            "date": item.get("date", item.get("reviewTime", ""))
        }
    
    def aggregate_product(self, results: list[dict]) -> dict:
        """
        Aggregate results by product for product-level statistics.
        
        Returns:
            Dict of product_id → aggregated stats
        """
        from collections import defaultdict
        
        products = defaultdict(list)
        
        for result in results:
            product_id = result["original"]["product_id"]
            products[product_id].append(result)
        
        aggregated = {}
        
        for product_id, product_results in products.items():
            n = len(product_results)
            
            # Calculate averages
            original_ratings = [r["original"]["stars"] for r in product_results]
            adjusted_ratings = [r["result"]["adjusted_rating"] for r in product_results]
            
            # Count classifications
            classifications = [r["result"]["classification"] for r in product_results]
            bot_count = classifications.count("bot")
            low_effort_count = classifications.count("low_effort")
            human_count = classifications.count("human")
            
            sarcastic_count = sum(1 for r in product_results if r["result"]["is_sarcastic"])
            
            aggregated[product_id] = {
                "product_id": product_id,
                "total_reviews": n,
                "original_average": round(sum(original_ratings) / n, 2),
                "adjusted_average": round(sum(adjusted_ratings) / n, 2),
                "rating_difference": round(sum(adjusted_ratings) / n - sum(original_ratings) / n, 2),
                "review_breakdown": {
                    "bot": bot_count,
                    "low_effort": low_effort_count,
                    "human": human_count,
                    "sarcastic": sarcastic_count
                },
                "bot_percentage": round(bot_count / n * 100, 1),
                "credibility_score": round(human_count / n, 2)
            }
        
        return aggregated
    
    def save_results(self, results: list[dict], filepath: str):
        """Save results to JSON file."""
        output = {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "total_reviews": len(results),
                "config": {
                    "star_weight": self.rating_calculator.star_weight,
                    "sentiment_weight": self.rating_calculator.sentiment_weight
                }
            },
            "results": results
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
        
        print(f"✓ Saved results to {filepath}")
    
    def process_csv(self, input_path: str, 
                    output_path: Optional[str] = None,
                    max_rows: Optional[int] = None) -> list[dict]:
        """
        Convenience method: Load CSV, process, save results.
        """
        reviews = self.load_csv(input_path, max_rows=max_rows)
        results = self.process_batch(reviews)
        
        if output_path:
            self.save_results(results, output_path)
        
        return results
    
    def process_json(self, input_path: str,
                     output_path: Optional[str] = None,
                     max_rows: Optional[int] = None) -> list[dict]:
        """
        Convenience method: Load JSON/JSONL, process, save results.
        """
        reviews = self.load_json(input_path, max_rows=max_rows)
        results = self.process_batch(reviews)
        
        if output_path:
            self.save_results(results, output_path)
        
        return results


# ============================================
# CLI Interface
# ============================================

def main():
    """Command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process batch reviews")
    parser.add_argument("input", help="Input file (CSV, JSON, or JSONL)")
    parser.add_argument("-o", "--output", help="Output JSON file")
    parser.add_argument("--max-rows", type=int, help="Max reviews to process")
    parser.add_argument("--mode", choices=["vader", "transformer", "hybrid"], default="hybrid")
    parser.add_argument("--star-weight", type=float, default=0.2)
    
    args = parser.parse_args()
    
    processor = ReviewProcessor(
        sentiment_mode=args.mode,
        star_weight=args.star_weight,
        sentiment_weight=1.0 - args.star_weight
    )
    
    input_path = Path(args.input)
    
    if input_path.suffix == '.csv':
        results = processor.process_csv(args.input, args.output, args.max_rows)
    else:
        results = processor.process_json(args.input, args.output, args.max_rows)
    
    # Print summary
    aggregated = processor.aggregate_product(results)
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    for product_id, stats in list(aggregated.items())[:5]:
        print(f"\nProduct: {product_id}")
        print(f"  Reviews: {stats['total_reviews']}")
        print(f"  Original: {stats['original_average']} → Adjusted: {stats['adjusted_average']}")
        print(f"  Bot %: {stats['bot_percentage']}%")


if __name__ == "__main__":
    main()
