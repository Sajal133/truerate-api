#!/usr/bin/env python3
"""
Sentiment Analysis Module
=========================
Analyzes sentiment from review text using a hybrid VADER + Transformer approach.

Usage:
    from execution.analyze_sentiment import SentimentAnalyzer
    
    analyzer = SentimentAnalyzer()
    result = analyzer.analyze("This product is amazing!")
    # {'sentiment_score': 0.58, 'confidence': 0.58, 'model_used': 'vader'}

Cost: $0 (all local processing)
"""

import os
import sys
from typing import Optional

# Try importing VADER
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    print("Warning: vaderSentiment not installed. Run: pip install vaderSentiment")

# Try importing transformers (optional, for higher accuracy)
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class SentimentAnalyzer:
    """
    Hybrid sentiment analyzer using VADER (fast) + Transformers (accurate).
    
    Strategy:
        1. Always try VADER first (instant, free)
        2. If VADER confidence is low, escalate to Transformer
        3. If Transformers not available, use VADER result anyway
    """
    
    def __init__(self, 
                 mode: str = "hybrid",
                 confidence_threshold: float = 0.6,
                 transformer_model: str = "distilbert-base-uncased-finetuned-sst-2-english",
                 use_finetuned: bool = True):
        """
        Initialize the sentiment analyzer.
        
        Args:
            mode: "vader", "transformer", or "hybrid" (default)
            confidence_threshold: VADER confidence below this triggers transformer (0.0-1.0)
            transformer_model: HuggingFace model name for transformer mode
        """
        self.mode = mode
        self.confidence_threshold = confidence_threshold
        self.transformer_model = transformer_model
        self.use_finetuned = use_finetuned
        
        # Check for fine-tuned local model
        self.finetuned_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "models", "sentiment_finetuned"
        )
        self.has_finetuned = os.path.exists(os.path.join(self.finetuned_path, "model.safetensors"))
        
        # Initialize VADER
        if VADER_AVAILABLE:
            self._vader = SentimentIntensityAnalyzer()
        else:
            self._vader = None
        
        # Lazy-load transformer (heavy, only load if needed)
        self._transformer_pipeline = None
        self._finetuned_model = None
        self._finetuned_tokenizer = None
    
    def _load_transformer(self):
        """Lazy-load transformer model on first use."""
        # Try fine-tuned model first
        if self.use_finetuned and self.has_finetuned and self._finetuned_model is None:
            try:
                from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
                import torch
                print(f"Loading fine-tuned model from: {self.finetuned_path}")
                self._finetuned_tokenizer = DistilBertTokenizer.from_pretrained(self.finetuned_path)
                self._finetuned_model = DistilBertForSequenceClassification.from_pretrained(self.finetuned_path)
                self._finetuned_model.eval()
                return "finetuned"
            except Exception as e:
                print(f"Could not load fine-tuned model: {e}")
        
        # Fall back to HuggingFace pipeline
        if self._transformer_pipeline is None and TRANSFORMERS_AVAILABLE:
            print(f"Loading transformer model: {self.transformer_model}...")
            self._transformer_pipeline = pipeline(
                "sentiment-analysis",
                model=self.transformer_model,
                device=-1  # CPU
            )
            return "huggingface"
        return self._transformer_pipeline
    
    def analyze_vader(self, text: str) -> dict:
        """
        Analyze sentiment using VADER (rule-based, instant).
        
        Returns:
            sentiment_score: -1.0 (negative) to +1.0 (positive)
            confidence: Magnitude of compound score (0.0-1.0)
        """
        if not self._vader:
            return {"sentiment_score": 0.0, "confidence": 0.0, "error": "VADER not available"}
        
        if not text or len(text.strip()) < 2:
            return {"sentiment_score": 0.0, "confidence": 0.0}
        
        scores = self._vader.polarity_scores(text)
        
        return {
            "sentiment_score": scores["compound"],
            "confidence": abs(scores["compound"]),
            "positive": scores["pos"],
            "negative": scores["neg"],
            "neutral": scores["neu"],
            "model_used": "vader"
        }
    
    def analyze_transformer(self, text: str) -> dict:
        """
        Analyze sentiment using Transformer model (higher accuracy).
        
        Returns:
            sentiment_score: -1.0 to +1.0
            confidence: Model confidence (0.0-1.0)
        """
        model_type = self._load_transformer()
        
        if not text or len(text.strip()) < 2:
            return {"sentiment_score": 0.0, "confidence": 0.0}
        
        # Truncate to model's max length (512 tokens ~ 2000 chars)
        text = text[:2000]
        
        # Use fine-tuned model if available
        if model_type == "finetuned" and self._finetuned_model is not None:
            try:
                import torch
                inputs = self._finetuned_tokenizer(
                    text, 
                    truncation=True, 
                    padding=True, 
                    max_length=128, 
                    return_tensors="pt"
                )
                
                with torch.no_grad():
                    outputs = self._finetuned_model(**inputs)
                    probs = torch.softmax(outputs.logits, dim=1)[0]
                    predicted = torch.argmax(probs).item()
                    confidence = probs[predicted].item()
                
                # Label map: 0=negative, 1=neutral, 2=positive
                if predicted == 0:  # Negative
                    score = -confidence
                    label = "NEGATIVE"
                elif predicted == 2:  # Positive
                    score = confidence
                    label = "POSITIVE"
                else:  # Neutral
                    score = 0.0
                    label = "NEUTRAL"
                
                return {
                    "sentiment_score": round(score, 4),
                    "confidence": round(confidence, 4),
                    "label": label,
                    "model_used": "finetuned"
                }
            except Exception as e:
                return {"sentiment_score": 0.0, "confidence": 0.0, "error": str(e)}
        
        # Fall back to HuggingFace pipeline
        if not self._transformer_pipeline:
            return {"sentiment_score": 0.0, "confidence": 0.0, "error": "Transformers not available"}
        
        try:
            result = self._transformer_pipeline(text)[0]
            
            # Convert label to -1/+1 score
            if result["label"] == "POSITIVE":
                score = result["score"]
            else:  # NEGATIVE
                score = -result["score"]
            
            return {
                "sentiment_score": round(score, 4),
                "confidence": round(result["score"], 4),
                "label": result["label"],
                "model_used": "transformer"
            }
        except Exception as e:
            return {"sentiment_score": 0.0, "confidence": 0.0, "error": str(e)}
    
    def analyze(self, text: str) -> dict:
        """
        Analyze sentiment using configured mode (hybrid by default).
        
        Args:
            text: Review text to analyze
            
        Returns:
            dict with sentiment_score (-1 to +1), confidence, model_used
        """
        if not text or len(text.strip()) < 2:
            return {
                "sentiment_score": 0.0,
                "confidence": 0.0,
                "model_used": "none",
                "reason": "empty_or_too_short"
            }
        
        # Mode: VADER only
        if self.mode == "vader":
            return self.analyze_vader(text)
        
        # Mode: Transformer only
        if self.mode == "transformer":
            return self.analyze_transformer(text)
        
        # Mode: Hybrid (default)
        # Step 1: Fast VADER analysis
        vader_result = self.analyze_vader(text)
        
        # Step 2: If high confidence, use VADER
        if vader_result.get("confidence", 0) >= self.confidence_threshold:
            return vader_result
        
        # Step 3: Low confidence, try transformer
        if TRANSFORMERS_AVAILABLE:
            transformer_result = self.analyze_transformer(text)
            if "error" not in transformer_result:
                return transformer_result
        
        # Fallback to VADER if transformer fails
        return vader_result
    
    def analyze_batch(self, texts: list[str], show_progress: bool = True) -> list[dict]:
        """
        Analyze multiple texts efficiently.
        
        Args:
            texts: List of review texts
            show_progress: Print progress updates
            
        Returns:
            List of sentiment results
        """
        results = []
        total = len(texts)
        
        for i, text in enumerate(texts):
            if show_progress and i % 100 == 0:
                print(f"Processing {i}/{total}...")
            results.append(self.analyze(text))
        
        if show_progress:
            print(f"Completed {total} reviews.")
        
        return results


# ============================================
# CLI Interface
# ============================================

def main():
    """Command-line interface for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze sentiment of review text")
    parser.add_argument("text", nargs="?", help="Text to analyze")
    parser.add_argument("--mode", choices=["vader", "transformer", "hybrid"], default="hybrid")
    parser.add_argument("--threshold", type=float, default=0.6, help="Confidence threshold for hybrid mode")
    
    args = parser.parse_args()
    
    analyzer = SentimentAnalyzer(mode=args.mode, confidence_threshold=args.threshold)
    
    if args.text:
        result = analyzer.analyze(args.text)
        print(f"Result: {result}")
    else:
        # Interactive mode
        print("Sentiment Analyzer (type 'quit' to exit)")
        print(f"Mode: {args.mode}, Threshold: {args.threshold}")
        print("-" * 40)
        
        while True:
            text = input("\nEnter text: ").strip()
            if text.lower() == "quit":
                break
            result = analyzer.analyze(text)
            print(f"  Sentiment: {result['sentiment_score']:+.3f}")
            print(f"  Confidence: {result['confidence']:.3f}")
            print(f"  Model: {result.get('model_used', 'unknown')}")


if __name__ == "__main__":
    main()
