#!/usr/bin/env python3
"""
Adaptive Learner Module
=======================
Online learning system that adjusts credibility scoring
based on user feedback.

Uses a simple Bayesian-style weight update approach:
- If user disagrees with prediction, decrease confidence in similar patterns
- If user agrees, slightly reinforce the pattern

The system tracks pattern-based adjustments that are applied
during credibility scoring to improve accuracy over time.
"""

import sys
from pathlib import Path

# Add API directory to path for feedback_db import
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from typing import Dict, List, Tuple
import re
import json

# Import Supabase weight functions
try:
    from feedback_db import update_weight_adjustment, get_all_weight_adjustments, SUPABASE_AVAILABLE
except ImportError:
    SUPABASE_AVAILABLE = False
    update_weight_adjustment = None
    get_all_weight_adjustments = None


class AdaptiveLearner:
    """
    Adaptive learning engine for credibility scoring.
    
    Tracks user feedback and generates adjustment factors
    that can be applied during prediction.
    """
    
    def __init__(self):
        # Pattern weights - adjusted through feedback
        self.pattern_weights: Dict[str, float] = {}
        self.class_thresholds = {
            "bot": 0.3,        # Below this = bot
            "low_effort": 0.6  # Below this = low_effort, above = human
        }
        self.learning_rate = 0.05
        self.min_samples_for_adjustment = 3
        
    def extract_features(self, text: str, stars: int) -> Dict[str, float]:
        """
        Extract features from review text for pattern matching.
        Returns normalized feature values.
        """
        text_lower = text.lower()
        word_count = len(text.split())
        
        features = {
            # Length features
            "very_short": 1.0 if word_count < 10 else 0.0,
            "short": 1.0 if 10 <= word_count < 30 else 0.0,
            "medium": 1.0 if 30 <= word_count < 100 else 0.0,
            "long": 1.0 if word_count >= 100 else 0.0,
            
            # Star features
            f"stars_{stars}": 1.0,
            
            # Content patterns
            "has_exclamation": 1.0 if "!" in text else 0.0,
            "excessive_exclamation": 1.0 if text.count("!") > 3 else 0.0,
            "all_caps_words": len(re.findall(r'\b[A-Z]{3,}\b', text)) / max(word_count, 1),
            "has_numbers": 1.0 if re.search(r'\d', text) else 0.0,
            
            # Sentiment indicators
            "extreme_positive": 1.0 if any(w in text_lower for w in ["perfect", "amazing", "best ever", "love it"]) else 0.0,
            "extreme_negative": 1.0 if any(w in text_lower for w in ["worst", "terrible", "awful", "never buy"]) else 0.0,
            "moderate_language": 1.0 if any(w in text_lower for w in ["decent", "okay", "fine", "not bad"]) else 0.0,
            
            # Suspicious patterns
            "repetitive": 1.0 if self._is_repetitive(text) else 0.0,
            "generic_praise": 1.0 if any(w in text_lower for w in ["great product", "highly recommend", "five stars"]) else 0.0,
            "product_mention": 1.0 if re.search(r'product|item|purchase|order', text_lower) else 0.0,
            
            # Quality indicators
            "has_specifics": 1.0 if re.search(r'\d+(?:\s*(?:days?|weeks?|months?|years?|%|dollars?|\$))', text_lower) else 0.0,
            "personal_experience": 1.0 if any(w in text_lower for w in ["i ", "my ", "me ", "we "]) else 0.0,
        }
        
        return features
    
    def _is_repetitive(self, text: str) -> bool:
        """Check if text has repetitive patterns."""
        words = text.lower().split()
        if len(words) < 4:
            return False
        word_set = set(words)
        return len(word_set) < len(words) * 0.5  # More than 50% repeated
    
    def update_from_feedback(
        self,
        text: str,
        stars: int,
        predicted_class: str,
        user_vote: int  # 1 = agree, -1 = disagree
    ) -> Dict[str, float]:
        """
        Update pattern weights based on user feedback.
        
        Returns the adjustments made.
        """
        features = self.extract_features(text, stars)
        adjustments = {}
        
        # Calculate update magnitude based on vote
        if user_vote == -1:  # User disagrees
            # Penalize features that led to wrong prediction
            magnitude = -self.learning_rate
        else:  # User agrees
            # Slightly reinforce (smaller magnitude to prevent overfitting)
            magnitude = self.learning_rate * 0.3
        
        # Create feature key based on prediction
        for feature_name, feature_value in features.items():
            if feature_value > 0:
                key = f"{predicted_class}:{feature_name}"
                
                current = self.pattern_weights.get(key, 0.0)
                update = magnitude * feature_value
                new_value = max(-0.5, min(0.5, current + update))  # Clamp
                
                self.pattern_weights[key] = new_value
                adjustments[key] = update
                
                # Persist to Supabase immediately
                if SUPABASE_AVAILABLE and update_weight_adjustment:
                    update_weight_adjustment(key, update)
        
        return adjustments
    
    def get_adjustment_factor(
        self,
        text: str,
        stars: int,
        base_score: float
    ) -> Tuple[float, Dict]:
        """
        Get credibility score adjustment based on learned patterns.
        
        Returns:
            Tuple of (adjusted_score, debug_info)
        """
        features = self.extract_features(text, stars)
        
        total_adjustment = 0.0
        applied_weights = {}
        
        for feature_name, feature_value in features.items():
            if feature_value > 0:
                # Check all class patterns
                for cls in ["bot", "low_effort", "human"]:
                    key = f"{cls}:{feature_name}"
                    if key in self.pattern_weights:
                        weight = self.pattern_weights[key]
                        contribution = weight * feature_value
                        total_adjustment += contribution
                        applied_weights[key] = contribution
        
        # Apply adjustment (clamped)
        adjusted_score = max(0.0, min(1.0, base_score + total_adjustment))
        
        return adjusted_score, {
            "base_score": base_score,
            "total_adjustment": total_adjustment,
            "adjusted_score": adjusted_score,
            "applied_weights": applied_weights
        }
    
    def get_class_from_score(self, score: float) -> str:
        """Convert credibility score to class label."""
        if score < self.class_thresholds["bot"]:
            return "bot"
        elif score < self.class_thresholds["low_effort"]:
            return "low_effort"
        else:
            return "human"
    
    def save_weights(self, filepath: str = None) -> None:
        """
        Save learned weights.
        Weights are already persisted to Supabase in update_from_feedback.
        This method saves a local backup for fallback.
        """
        if filepath is None:
            filepath = Path(__file__).parent.parent / "api" / "learned_weights.json"
        
        data = {
            "pattern_weights": self.pattern_weights,
            "class_thresholds": self.class_thresholds,
            "learning_rate": self.learning_rate,
            "source": "local_backup"
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save local backup: {e}")
    
    def load_weights(self, filepath: str = None) -> bool:
        """
        Load learned weights from Supabase (primary) or local file (fallback).
        Supabase weights are aggregated from ALL users' feedback.
        """
        # Try Supabase first (contains all users' feedback)
        if SUPABASE_AVAILABLE and get_all_weight_adjustments:
            try:
                cloud_weights = get_all_weight_adjustments()
                if cloud_weights:
                    self.pattern_weights = cloud_weights
                    print(f"Loaded {len(cloud_weights)} weights from Supabase (multi-user)")
                    return True
            except Exception as e:
                print(f"Could not load from Supabase: {e}")
        
        # Fallback to local file
        if filepath is None:
            filepath = Path(__file__).parent.parent / "api" / "learned_weights.json"
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                self.pattern_weights = data.get("pattern_weights", {})
                self.class_thresholds = data.get("class_thresholds", self.class_thresholds)
                self.learning_rate = data.get("learning_rate", self.learning_rate)
            print(f"Loaded weights from local file (fallback)")
            return True
        except FileNotFoundError:
            print("No weights found - starting fresh")
            return False
        except Exception as e:
            print(f"Error loading weights: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get learner statistics."""
        return {
            "total_patterns": len(self.pattern_weights),
            "thresholds": self.class_thresholds,
            "learning_rate": self.learning_rate,
            "top_positive_weights": dict(sorted(
                self.pattern_weights.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]),
            "top_negative_weights": dict(sorted(
                self.pattern_weights.items(),
                key=lambda x: x[1]
            )[:5])
        }


# Singleton instance
_learner = None

def get_learner() -> AdaptiveLearner:
    """Get singleton adaptive learner instance."""
    global _learner
    if _learner is None:
        _learner = AdaptiveLearner()
        _learner.load_weights()  # Try to load existing weights
    return _learner


if __name__ == "__main__":
    # Test the adaptive learner
    learner = AdaptiveLearner()
    
    # Simulate some feedback
    print("=== Testing Adaptive Learner ===\n")
    
    # User disagrees with a "human" classification on a short review
    adjustments = learner.update_from_feedback(
        text="Great product!",
        stars=5,
        predicted_class="human",
        user_vote=-1  # User thinks it's NOT human (probably low_effort)
    )
    print(f"Adjustments after disagree: {adjustments}\n")
    
    # User agrees with a "human" classification on detailed review
    adjustments = learner.update_from_feedback(
        text="I've been using this for 3 months now and it's fantastic. The battery lasts 2 days and the build quality is excellent.",
        stars=5,
        predicted_class="human",
        user_vote=1
    )
    print(f"Adjustments after agree: {adjustments}\n")
    
    # Get adjustment for a new review
    score, debug = learner.get_adjustment_factor(
        text="Great product!",
        stars=5,
        base_score=0.7
    )
    print(f"Adjusted score for 'Great product!': {score}")
    print(f"Debug: {json.dumps(debug, indent=2)}")
    
    print(f"\nLearner stats: {json.dumps(learner.get_stats(), indent=2)}")
