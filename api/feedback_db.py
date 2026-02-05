#!/usr/bin/env python3
"""
Supabase Feedback Database Module
=================================
Cloud storage for user feedback on review classifications.
Enables adaptive learning from multi-user feedback.
"""

import os
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://siithpbnuknngkqeyxui.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNpaXRocGJudWtubmdrcWV5eHVpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzAzMDg3NjgsImV4cCI6MjA4NTg4NDc2OH0.iuoBUceiFHDlQBV4vaV6LqBPNMkDkh5kOVn8eHtD2Po")

# Try to import supabase
try:
    from supabase import create_client, Client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    SUPABASE_AVAILABLE = True
except ImportError:
    print("Warning: supabase-py not installed. Run: pip install supabase")
    supabase = None
    SUPABASE_AVAILABLE = False


def hash_text(text: str) -> str:
    """Generate hash of review text for deduplication."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def save_feedback(
    text: str,
    stars: int,
    predicted_class: str,
    user_vote: int,  # 1 = agree, -1 = disagree
    predicted_score: float = None,
    user_agent: str = None
) -> Dict[str, Any]:
    """
    Save user feedback on a review classification to Supabase.
    
    Args:
        text: Review text
        stars: Original star rating
        predicted_class: bot/low_effort/human
        user_vote: 1 if user agrees, -1 if disagrees
        predicted_score: Optional credibility score
        user_agent: Optional browser user agent
    
    Returns:
        Result dict with success status
    """
    if not SUPABASE_AVAILABLE:
        return {"success": False, "error": "Supabase not available"}
    
    text_hash = hash_text(text)
    
    try:
        # Upsert to handle duplicates gracefully
        result = supabase.table("feedback").upsert({
            "text_hash": text_hash,
            "review_text": text,
            "stars": stars,
            "predicted_class": predicted_class,
            "predicted_score": predicted_score,
            "user_vote": user_vote,
            "user_agent": user_agent
        }, on_conflict="text_hash,user_vote").execute()
        
        return {
            "success": True,
            "text_hash": text_hash,
            "message": "Feedback saved to cloud"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_feedback_stats() -> Dict[str, Any]:
    """Get statistics on collected feedback from Supabase."""
    if not SUPABASE_AVAILABLE:
        return {"error": "Supabase not available"}
    
    try:
        # Get all feedback
        result = supabase.table("feedback").select("*").execute()
        feedback_list = result.data or []
        
        total = len(feedback_list)
        agrees = sum(1 for f in feedback_list if f.get("user_vote") == 1)
        disagrees = sum(1 for f in feedback_list if f.get("user_vote") == -1)
        
        # By predicted class
        by_class = {}
        for f in feedback_list:
            cls = f.get("predicted_class", "unknown")
            if cls not in by_class:
                by_class[cls] = {"agree": 0, "disagree": 0}
            if f.get("user_vote") == 1:
                by_class[cls]["agree"] += 1
            else:
                by_class[cls]["disagree"] += 1
        
        accuracy = agrees / total if total > 0 else 0
        
        return {
            "total_feedback": total,
            "agreements": agrees,
            "disagreements": disagrees,
            "accuracy_rate": round(accuracy * 100, 1),
            "by_class": by_class,
            "storage": "supabase_cloud"
        }
    except Exception as e:
        return {"error": str(e)}


def get_training_data(limit: int = 500) -> List[Dict]:
    """
    Get feedback data suitable for retraining.
    Returns disagreements as correction examples.
    """
    if not SUPABASE_AVAILABLE:
        return []
    
    try:
        result = supabase.table("feedback") \
            .select("review_text, stars, predicted_class, user_vote") \
            .eq("user_vote", -1) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        
        return [
            {
                "text": row["review_text"],
                "stars": row["stars"],
                "predicted_class": row["predicted_class"],
                "correct": False  # User disagreed = prediction was wrong
            }
            for row in (result.data or [])
        ]
    except Exception as e:
        print(f"Error getting training data: {e}")
        return []


def get_class_adjustments() -> Dict[str, float]:
    """
    Calculate threshold adjustments based on all user feedback.
    Returns adjustment factors per class.
    """
    stats = get_feedback_stats()
    adjustments = {"bot": 0.0, "low_effort": 0.0, "human": 0.0}
    
    for cls, counts in stats.get("by_class", {}).items():
        if cls in adjustments:
            total = counts["agree"] + counts["disagree"]
            if total >= 5:  # Minimum samples
                disagree_rate = counts["disagree"] / total
                # Positive adjustment = more lenient, Negative = stricter
                adjustments[cls] = (disagree_rate - 0.5) * 0.2
    
    return adjustments


def update_weight_adjustment(feature_name: str, delta: float) -> None:
    """Update a feature weight adjustment based on feedback."""
    if not SUPABASE_AVAILABLE:
        return
    
    try:
        # Try to get existing
        existing = supabase.table("weight_adjustments") \
            .select("*") \
            .eq("feature_name", feature_name) \
            .execute()
        
        if existing.data:
            # Update existing
            current = existing.data[0]
            supabase.table("weight_adjustments").update({
                "adjustment": current["adjustment"] + delta * 0.1,
                "sample_count": current["sample_count"] + 1,
                "last_updated": "now()"
            }).eq("feature_name", feature_name).execute()
        else:
            # Insert new
            supabase.table("weight_adjustments").insert({
                "feature_name": feature_name,
                "adjustment": delta,
                "sample_count": 1
            }).execute()
    except Exception as e:
        print(f"Error updating weight: {e}")


def get_all_weight_adjustments() -> Dict[str, float]:
    """Get all current weight adjustments from cloud."""
    if not SUPABASE_AVAILABLE:
        return {}
    
    try:
        result = supabase.table("weight_adjustments").select("*").execute()
        return {
            row["feature_name"]: row["adjustment"]
            for row in (result.data or [])
        }
    except Exception as e:
        print(f"Error getting weights: {e}")
        return {}


if __name__ == "__main__":
    import json
    
    print("Testing Supabase feedback database...")
    print(f"Supabase available: {SUPABASE_AVAILABLE}")
    
    if SUPABASE_AVAILABLE:
        # Test save
        result = save_feedback(
            text="This is a test review from Python",
            stars=5,
            predicted_class="human",
            user_vote=1
        )
        print(f"Save result: {result}")
        
        # Get stats
        stats = get_feedback_stats()
        print(f"Stats: {json.dumps(stats, indent=2)}")
