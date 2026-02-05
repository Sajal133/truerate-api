#!/usr/bin/env python3
"""
Credibility Scoring Module
==========================
Scores review credibility to detect bots, spam, and low-effort reviews.

Usage:
    from execution.score_credibility import CredibilityScorer
    
    scorer = CredibilityScorer()
    result = scorer.score("", stars=5)
    # {'score': 0.1, 'classification': 'bot', 'flags': ['empty_review']}

Cost: $0 (all local processing)
"""

import re
from typing import Optional


class CredibilityScorer:
    """
    Scores review credibility based on text patterns, length, and content.
    
    Credibility tiers:
        0.0-0.3: Bot/spam (low weight in aggregate)
        0.3-0.6: Low-effort (reduced weight)
        0.6-1.0: Human/genuine (full weight)
    """
    
    # Generic phrases that indicate low-effort reviews
    GENERIC_PHRASES = {
        "good", "nice", "great", "amazing", "excellent", "perfect", 
        "love it", "awesome", "best", "wonderful", "fantastic",
        "highly recommend", "5 stars", "five stars", "loved it",
        "bad", "terrible", "worst", "hate it", "awful", "horrible"
    }
    
    # Spam template patterns
    SPAM_PATTERNS = [
        r"fast\s*shipping.*great\s*price",
        r"great\s*price.*fast\s*shipping",
        r"highly\s*recommend",
        r"best\s*(purchase|buy|product)\s*ever",
        r"(5|five)\s*stars?",
        r"a{3,}|o{3,}|!{3,}",  # Repeated characters: "aaaa", "!!!!"
        r"(love|great|amazing)\s*(it)?[!.]*$",  # Ends with just "love it!"
    ]
    
    # Words indicating product wasn't actually used
    NOT_USED_INDICATORS = [
        "haven't opened", "haven't used", "haven't tried",
        "just arrived", "just received", "just got",
        "not yet", "didn't open", "still in box",
        "haven't tested", "can't rate yet"
    ]
    
    # Words indicating mixed/nuanced review (good sign)
    MIXED_SENTIMENT_WORDS = {
        "but", "however", "although", "though", "except",
        "unfortunately", "sadly", "on the other hand",
        "pros", "cons", "downside", "upside"
    }
    
    # Specific feature mentions (good sign)
    SPECIFIC_FEATURES = [
        r"battery\s*(life)?", r"screen", r"display", r"camera",
        r"build\s*quality", r"sound", r"audio", r"speed",
        r"size", r"weight", r"design", r"material",
        r"customer\s*service", r"shipping", r"packaging",
        r"price", r"value", r"quality", r"durability"
    ]
    
    def __init__(self):
        # Compile regex patterns for efficiency
        self._spam_patterns = [re.compile(p, re.IGNORECASE) for p in self.SPAM_PATTERNS]
        self._feature_patterns = [re.compile(p, re.IGNORECASE) for p in self.SPECIFIC_FEATURES]
    
    def score(self, text: str, stars: Optional[int] = None, 
              sentiment_score: Optional[float] = None) -> dict:
        """
        Calculate credibility score for a review.
        
        Args:
            text: Review text
            stars: Star rating (1-5), optional
            sentiment_score: Sentiment from analyzer (-1 to +1), optional
            
        Returns:
            score: 0.0 to 1.0 credibility
            classification: 'bot', 'low_effort', or 'human'
            flags: List of detected issues/qualities
        """
        flags = []
        score = 1.0  # Start with full credibility
        
        # Normalize text
        text = text.strip() if text else ""
        text_lower = text.lower()
        word_count = len(text.split()) if text else 0
        
        # ============================================
        # NEGATIVE SIGNALS (Reduce credibility)
        # ============================================
        
        # Check 1: Empty or near-empty text
        if not text or word_count < 2:
            score *= 0.1
            flags.append("empty_review")
            return self._build_result(score, flags)
        
        # Check 2: Very short + generic phrase
        if word_count <= 5:
            if text_lower.rstrip("!.") in self.GENERIC_PHRASES:
                score *= 0.2
                flags.append("generic_phrase")
            else:
                score *= 0.5
                flags.append("very_short")
        
        # Check 3: Short review (6-15 words)
        elif word_count <= 15:
            score *= 0.7
            flags.append("short_review")
        
        # Check 4: Spam template matching
        for pattern in self._spam_patterns:
            if pattern.search(text_lower):
                score *= 0.3
                flags.append("spam_pattern_detected")
                break
        
        # Check 5: Product not used
        for indicator in self.NOT_USED_INDICATORS:
            if indicator in text_lower:
                score *= 0.15
                flags.append("product_not_used")
                break
        
        # Check 6: ALL CAPS (often spam or emotional)
        if text.isupper() and len(text) > 10:
            score *= 0.6
            flags.append("all_caps")
        
        # Check 7: Star-sentiment mismatch (suspicious)
        if stars is not None and sentiment_score is not None:
            expected_sentiment = (stars - 3) / 2  # 1★→-1, 3★→0, 5★→+1
            gap = abs(sentiment_score - expected_sentiment)
            
            if gap > 1.0:  # Huge mismatch
                score *= 0.7
                flags.append("star_sentiment_mismatch")
        
        # ============================================
        # POSITIVE SIGNALS (Increase credibility)
        # ============================================
        
        # Check 8: Mixed sentiment (sign of nuanced review)
        has_mixed = any(word in text_lower for word in self.MIXED_SENTIMENT_WORDS)
        if has_mixed:
            score *= 1.2
            flags.append("mixed_sentiment_detected")
        
        # Check 9: Specific features mentioned
        features_mentioned = sum(1 for p in self._feature_patterns if p.search(text_lower))
        if features_mentioned >= 2:
            score *= 1.15
            flags.append(f"specific_features_{features_mentioned}")
        
        # Check 10: Detailed review (50+ words)
        if word_count >= 50:
            score *= 1.1
            flags.append("detailed_review")
        
        # Check 11: Very detailed (100+ words)
        if word_count >= 100:
            score *= 1.1
            flags.append("very_detailed")
        
        # ============================================
        # Finalize
        # ============================================
        
        return self._build_result(score, flags)
    
    def _build_result(self, score: float, flags: list) -> dict:
        """Build the result dictionary with classification."""
        # Clamp score to [0, 1]
        score = max(0.0, min(1.0, score))
        
        # Classify based on score
        if score < 0.3:
            classification = "bot"
        elif score < 0.6:
            classification = "low_effort"
        else:
            classification = "human"
        
        return {
            "score": round(score, 3),
            "classification": classification,
            "flags": flags
        }
    
    def score_batch(self, reviews: list[dict], show_progress: bool = True) -> list[dict]:
        """
        Score multiple reviews.
        
        Args:
            reviews: List of dicts with 'text' and optionally 'stars', 'sentiment_score'
            show_progress: Print progress updates
            
        Returns:
            List of credibility results
        """
        results = []
        total = len(reviews)
        
        for i, review in enumerate(reviews):
            if show_progress and i % 100 == 0:
                print(f"Scoring {i}/{total}...")
            
            result = self.score(
                text=review.get("text", ""),
                stars=review.get("stars"),
                sentiment_score=review.get("sentiment_score")
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
    
    parser = argparse.ArgumentParser(description="Score review credibility")
    parser.add_argument("text", nargs="?", help="Review text to score")
    parser.add_argument("--stars", type=int, help="Star rating (1-5)")
    
    args = parser.parse_args()
    
    scorer = CredibilityScorer()
    
    if args.text:
        result = scorer.score(args.text, stars=args.stars)
        print(f"Result: {result}")
    else:
        # Interactive mode
        print("Credibility Scorer (type 'quit' to exit)")
        print("-" * 40)
        
        while True:
            text = input("\nEnter review text: ").strip()
            if text.lower() == "quit":
                break
            
            stars_input = input("Stars (1-5, or Enter to skip): ").strip()
            stars = int(stars_input) if stars_input.isdigit() else None
            
            result = scorer.score(text, stars=stars)
            print(f"  Credibility: {result['score']:.2f}")
            print(f"  Classification: {result['classification']}")
            print(f"  Flags: {result['flags']}")


if __name__ == "__main__":
    main()
