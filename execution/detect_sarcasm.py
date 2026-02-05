#!/usr/bin/env python3
"""
Sarcasm Detection Module
========================
Detects sarcasm in reviews through star-sentiment contradiction and linguistic patterns.

Usage:
    from execution.detect_sarcasm import SarcasmDetector
    
    detector = SarcasmDetector()
    result = detector.detect("Oh great, it broke after 2 days!", stars=5, sentiment_score=-0.7)
    # {'is_sarcastic': True, 'confidence': 0.9, 'triggers': ['oh great', 'broke']}

Cost: $0 (all local processing)
"""

import re
from typing import Optional


class SarcasmDetector:
    """
    Detects sarcasm using star-sentiment mismatch and linguistic markers.
    
    Key signals:
        1. High stars (4-5) + negative sentiment
        2. Sarcasm markers ("oh great", "wonderful", "fantastic")
        3. Negative context words ("broke", "died", "terrible")
    """
    
    # Sarcasm trigger phrases (often used sarcastically with negative context)
    SARCASM_MARKERS = [
        "oh great", "just great", "oh wonderful", "just wonderful",
        "oh fantastic", "just fantastic", "oh perfect", "just perfect",
        "oh amazing", "sure", "yeah right", "right",
        "of course", "naturally", "obviously",
        "brilliant", "genius", "lovely", "nice job",
        "thanks for", "thank you for", "thanks a lot",
        "so glad", "so happy", "so pleased",
        "what a", "how wonderful", "how great", "how nice"
    ]
    
    # Negative context words (indicate actual negative experience)
    NEGATIVE_CONTEXT = [
        # Product failure
        "broke", "broken", "died", "dead", "failed", "fails",
        "doesn't work", "won't work", "stopped working", "quit working",
        "defective", "faulty", "malfunction",
        
        # Quality issues
        "terrible", "awful", "horrible", "worst", "garbage", "trash",
        "cheap", "flimsy", "junk", "waste", "useless", "worthless",
        
        # Service issues
        "never arrived", "didn't arrive", "lost", "damaged",
        "no response", "ignored", "unhelpful", "rude",
        
        # Money issues
        "refund", "returned", "return it", "money back", "scam", "ripoff",
        
        # Disappointment
        "disappointed", "disappointing", "regret", "mistake",
        "wish i hadn't", "don't buy", "avoid", "stay away"
    ]
    
    # Positive words that when combined with negative context = sarcasm
    POSITIVE_WORDS = [
        "great", "amazing", "wonderful", "fantastic", "perfect",
        "excellent", "awesome", "incredible", "love", "best"
    ]
    
    def __init__(self):
        pass
    
    def detect(self, text: str, 
               stars: Optional[int] = None,
               sentiment_score: Optional[float] = None) -> dict:
        """
        Detect if a review is sarcastic.
        
        Args:
            text: Review text
            stars: Star rating (1-5)
            sentiment_score: Sentiment from analyzer (-1 to +1)
            
        Returns:
            is_sarcastic: Boolean
            confidence: 0.0 to 1.0
            triggers: List of detected sarcasm signals
        """
        if not text or len(text.strip()) < 5:
            return {"is_sarcastic": False, "confidence": 0.0, "triggers": []}
        
        text_lower = text.lower()
        triggers = []
        sarcasm_score = 0.0
        
        # ============================================
        # Signal 1: Star-Sentiment Mismatch
        # ============================================
        
        if stars is not None and sentiment_score is not None:
            if stars >= 4 and sentiment_score < -0.3:
                # High stars + negative sentiment = very suspicious
                mismatch_strength = abs(sentiment_score) * (stars - 3) / 2
                sarcasm_score += mismatch_strength * 0.4
                triggers.append(f"star_sentiment_mismatch_{stars}star_{sentiment_score:.1f}sent")
            
            elif stars <= 2 and sentiment_score > 0.3:
                # Low stars + positive sentiment = also suspicious (less common)
                mismatch_strength = sentiment_score * (3 - stars) / 2
                sarcasm_score += mismatch_strength * 0.2
                triggers.append(f"inverse_mismatch_{stars}star_{sentiment_score:.1f}sent")
        
        # ============================================
        # Signal 2: Sarcasm Markers Present
        # ============================================
        
        markers_found = []
        for marker in self.SARCASM_MARKERS:
            if marker in text_lower:
                markers_found.append(marker)
        
        if markers_found:
            sarcasm_score += 0.25 * min(len(markers_found), 3)  # Cap at 3
            triggers.extend([f"marker:{m}" for m in markers_found[:3]])
        
        # ============================================
        # Signal 3: Negative Context Present
        # ============================================
        
        negatives_found = []
        for neg in self.NEGATIVE_CONTEXT:
            if neg in text_lower:
                negatives_found.append(neg)
        
        if negatives_found:
            sarcasm_score += 0.15 * min(len(negatives_found), 4)  # Cap at 4
            triggers.extend([f"negative:{n}" for n in negatives_found[:3]])
        
        # ============================================
        # Signal 4: Sarcasm Marker + Negative Context Combo
        # ============================================
        
        if markers_found and negatives_found:
            # Strong sarcasm signal: "oh great" + "broke"
            sarcasm_score += 0.3
            triggers.append("marker_negative_combo")
        
        # ============================================
        # Signal 5: Positive Word + Negative Context (Without Marker)
        # ============================================
        
        if not markers_found and negatives_found:
            positives_found = [p for p in self.POSITIVE_WORDS if p in text_lower]
            if positives_found:
                sarcasm_score += 0.2
                triggers.append("positive_negative_contrast")
        
        # ============================================
        # Signal 6: High stars but mostly negative words
        # ============================================
        
        if stars is not None and stars >= 4 and len(negatives_found) >= 3:
            sarcasm_score += 0.25
            triggers.append("high_stars_many_negatives")
        
        # ============================================
        # Finalize
        # ============================================
        
        # Normalize score to 0-1
        confidence = min(1.0, sarcasm_score)
        
        # Determine if sarcastic (threshold: 0.5)
        is_sarcastic = confidence >= 0.5
        
        return {
            "is_sarcastic": is_sarcastic,
            "confidence": round(confidence, 3),
            "triggers": triggers
        }
    
    def detect_batch(self, reviews: list[dict], show_progress: bool = True) -> list[dict]:
        """
        Detect sarcasm in multiple reviews.
        
        Args:
            reviews: List of dicts with 'text' and optionally 'stars', 'sentiment_score'
            
        Returns:
            List of sarcasm detection results
        """
        results = []
        total = len(reviews)
        
        for i, review in enumerate(reviews):
            if show_progress and i % 100 == 0:
                print(f"Checking sarcasm {i}/{total}...")
            
            result = self.detect(
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
    
    parser = argparse.ArgumentParser(description="Detect sarcasm in review text")
    parser.add_argument("text", nargs="?", help="Review text to analyze")
    parser.add_argument("--stars", type=int, help="Star rating (1-5)")
    parser.add_argument("--sentiment", type=float, help="Sentiment score (-1 to +1)")
    
    args = parser.parse_args()
    
    detector = SarcasmDetector()
    
    if args.text:
        result = detector.detect(args.text, stars=args.stars, sentiment_score=args.sentiment)
        print(f"Result: {result}")
    else:
        # Interactive mode
        print("Sarcasm Detector (type 'quit' to exit)")
        print("-" * 40)
        
        while True:
            text = input("\nEnter review text: ").strip()
            if text.lower() == "quit":
                break
            
            stars_input = input("Stars (1-5, or Enter to skip): ").strip()
            stars = int(stars_input) if stars_input.isdigit() else None
            
            sentiment_input = input("Sentiment (-1 to +1, or Enter to skip): ").strip()
            try:
                sentiment = float(sentiment_input) if sentiment_input else None
            except ValueError:
                sentiment = None
            
            result = detector.detect(text, stars=stars, sentiment_score=sentiment)
            print(f"  Sarcastic: {result['is_sarcastic']}")
            print(f"  Confidence: {result['confidence']:.2f}")
            print(f"  Triggers: {result['triggers']}")


if __name__ == "__main__":
    main()
