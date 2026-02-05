#!/usr/bin/env python3
"""
Weighted Rating Calculator
==========================
Applies the 20/80 star-sentiment fusion to calculate adjusted ratings.

Usage:
    from execution.calculate_weighted_rating import WeightedRatingCalculator
    
    calculator = WeightedRatingCalculator()
    result = calculator.calculate(stars=5, sentiment_score=-0.7, credibility=0.85, is_sarcastic=True)
    # {'adjusted_rating': 1.6, 'components': {...}}

Cost: $0 (all local processing)
"""

from typing import Optional


class WeightedRatingCalculator:
    """
    Calculates integrity-weighted rating using 20/80 star-sentiment fusion.
    
    Formula:
        1. Convert sentiment (-1 to +1) → rating scale (1 to 5)
        2. Apply ratio: (stars × 0.2) + (sentiment_rating × 0.8)
        3. Adjust based on credibility
        4. Handle sarcasm (invert if detected)
    """
    
    def __init__(self, 
                 star_weight: float = 0.2, 
                 sentiment_weight: float = 0.8):
        """
        Initialize with configurable weights.
        
        Args:
            star_weight: Weight for star rating (default 0.2 = 20%)
            sentiment_weight: Weight for sentiment (default 0.8 = 80%)
        """
        if abs((star_weight + sentiment_weight) - 1.0) > 0.001:
            raise ValueError("star_weight + sentiment_weight must equal 1.0")
        
        self.star_weight = star_weight
        self.sentiment_weight = sentiment_weight
    
    def sentiment_to_rating(self, sentiment_score: float) -> float:
        """
        Convert sentiment score (-1 to +1) to rating scale (1 to 5).
        
        Mapping:
            -1.0 → 1.0 (very negative)
             0.0 → 3.0 (neutral)
            +1.0 → 5.0 (very positive)
        """
        # Formula: ((sentiment + 1) / 2) * 4 + 1
        # Clamp sentiment to valid range first
        sentiment_clamped = max(-1.0, min(1.0, sentiment_score))
        return ((sentiment_clamped + 1) / 2) * 4 + 1
    
    def calculate(self,
                  stars: int,
                  sentiment_score: float,
                  credibility: float = 1.0,
                  is_sarcastic: bool = False,
                  sarcasm_confidence: float = 0.0) -> dict:
        """
        Calculate the weighted adjusted rating.
        
        Args:
            stars: Original star rating (1-5)
            sentiment_score: Sentiment from analyzer (-1 to +1)
            credibility: Credibility score (0-1)
            is_sarcastic: Whether sarcasm was detected
            sarcasm_confidence: Confidence of sarcasm detection (0-1)
            
        Returns:
            adjusted_rating: Final calculated rating (1.0-5.0)
            components: Breakdown of calculation
        """
        # Validate inputs
        stars = max(1, min(5, stars))
        sentiment_score = max(-1.0, min(1.0, sentiment_score))
        credibility = max(0.0, min(1.0, credibility))
        
        # ============================================
        # Step 1: Convert sentiment to rating scale
        # ============================================
        
        sentiment_rating = self.sentiment_to_rating(sentiment_score)
        
        # ============================================
        # Step 2: Handle sarcasm (invert sentiment)
        # ============================================
        
        effective_sentiment_rating = sentiment_rating
        sarcasm_adjustment = 0.0
        
        if is_sarcastic and sarcasm_confidence >= 0.5:
            # Invert sentiment: 5 → 1, 4 → 2, 3 → 3, 2 → 4, 1 → 5
            effective_sentiment_rating = 6 - sentiment_rating
            sarcasm_adjustment = effective_sentiment_rating - sentiment_rating
        
        # ============================================
        # Step 3: Apply 20/80 weighted fusion
        # ============================================
        
        base_rating = (stars * self.star_weight) + (effective_sentiment_rating * self.sentiment_weight)
        
        # ============================================
        # Step 4: Apply credibility adjustment
        # ============================================
        
        # Low credibility reviews get pushed toward neutral (3.0)
        if credibility < 0.4:
            # Blend toward neutral based on how low credibility is
            neutrality_factor = 1 - (credibility / 0.4)
            adjusted_rating = base_rating * (1 - neutrality_factor * 0.5) + 3.0 * (neutrality_factor * 0.5)
        else:
            adjusted_rating = base_rating
        
        # ============================================
        # Step 5: Clamp to valid range
        # ============================================
        
        adjusted_rating = max(1.0, min(5.0, adjusted_rating))
        
        return {
            "adjusted_rating": round(adjusted_rating, 2),
            "components": {
                "original_stars": stars,
                "sentiment_score": sentiment_score,
                "sentiment_as_rating": round(sentiment_rating, 2),
                "sarcasm_detected": is_sarcastic,
                "sarcasm_confidence": sarcasm_confidence,
                "effective_sentiment_rating": round(effective_sentiment_rating, 2),
                "credibility": credibility,
                "star_weight": self.star_weight,
                "sentiment_weight": self.sentiment_weight,
                "base_rating_before_cred": round(base_rating, 2)
            }
        }
    
    def calculate_simple(self, stars: int, sentiment_score: float) -> float:
        """
        Simple calculation without credibility/sarcasm adjustments.
        
        Args:
            stars: Star rating (1-5)
            sentiment_score: Sentiment (-1 to +1)
            
        Returns:
            Adjusted rating (1.0-5.0)
        """
        sentiment_rating = self.sentiment_to_rating(sentiment_score)
        rating = (stars * self.star_weight) + (sentiment_rating * self.sentiment_weight)
        return round(max(1.0, min(5.0, rating)), 2)
    
    def calculate_batch(self, reviews: list[dict], show_progress: bool = True) -> list[dict]:
        """
        Calculate weighted ratings for multiple reviews.
        
        Args:
            reviews: List of dicts with:
                - stars (required)
                - sentiment_score (required)
                - credibility (optional)
                - is_sarcastic (optional)
                - sarcasm_confidence (optional)
                
        Returns:
            List of calculation results
        """
        results = []
        total = len(reviews)
        
        for i, review in enumerate(reviews):
            if show_progress and i % 100 == 0:
                print(f"Calculating {i}/{total}...")
            
            result = self.calculate(
                stars=review.get("stars", 3),
                sentiment_score=review.get("sentiment_score", 0.0),
                credibility=review.get("credibility", 1.0),
                is_sarcastic=review.get("is_sarcastic", False),
                sarcasm_confidence=review.get("sarcasm_confidence", 0.0)
            )
            results.append(result)
        
        if show_progress:
            print(f"Completed {total} reviews.")
        
        return results


# ============================================
# CLI Interface
# ============================================

def main():
    """Command-line interface for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Calculate weighted rating")
    parser.add_argument("--stars", type=int, required=True, help="Star rating (1-5)")
    parser.add_argument("--sentiment", type=float, required=True, help="Sentiment score (-1 to +1)")
    parser.add_argument("--credibility", type=float, default=1.0, help="Credibility (0-1)")
    parser.add_argument("--sarcastic", action="store_true", help="Flag as sarcastic")
    parser.add_argument("--star-weight", type=float, default=0.2, help="Star weight (default 0.2)")
    
    args = parser.parse_args()
    
    calculator = WeightedRatingCalculator(
        star_weight=args.star_weight,
        sentiment_weight=1.0 - args.star_weight
    )
    
    result = calculator.calculate(
        stars=args.stars,
        sentiment_score=args.sentiment,
        credibility=args.credibility,
        is_sarcastic=args.sarcastic,
        sarcasm_confidence=0.9 if args.sarcastic else 0.0
    )
    
    print(f"\nAdjusted Rating: {result['adjusted_rating']}")
    print(f"\nComponents:")
    for key, value in result['components'].items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
