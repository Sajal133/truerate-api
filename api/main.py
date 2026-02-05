#!/usr/bin/env python3
"""
TrueRate.ai API
======================
FastAPI backend for review analysis.

Run: uvicorn api.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""

import sys
import os
from pathlib import Path

# Add execution directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "execution"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import json

# Import execution modules
from analyze_sentiment import SentimentAnalyzer
from score_credibility import CredibilityScorer
from detect_sarcasm import SarcasmDetector
from calculate_weighted_rating import WeightedRatingCalculator
from load_dataset import DatasetLoader
from scrape_amazon import extract_asin, get_amazon_domain, build_review_url, AmazonScraper, scrape_with_firecrawl, scrape_with_scraperapi
from adaptive_learner import get_learner

# Import feedback database (from api directory)
from feedback_db import save_feedback, get_feedback_stats, get_class_adjustments

# Dataset path
DATASET_PATH = Path(__file__).parent.parent / "data" / "Cell_Phones_and_Accessories_5.json.gz"
dataset_loader = None  # Lazy loaded

# ============================================
# App Setup
# ============================================

app = FastAPI(
    title="TrueRate.ai API",
    description="Analyze product reviews for credibility, sentiment, and adjusted ratings",
    version="1.0.0"
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3030", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize modules (singleton pattern)
sentiment_analyzer = SentimentAnalyzer(mode="hybrid")  # Uses finetuned model when VADER confidence is low
credibility_scorer = CredibilityScorer()
sarcasm_detector = SarcasmDetector()
rating_calculator = WeightedRatingCalculator(star_weight=0.2, sentiment_weight=0.8)

# ============================================
# Request/Response Models
# ============================================

class ReviewInput(BaseModel):
    """Single review input."""
    text: str = Field(..., description="Review text content")
    stars: int = Field(..., ge=1, le=5, description="Star rating (1-5)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "This product is amazing! Great quality and fast shipping.",
                "stars": 5
            }
        }

class BatchReviewInput(BaseModel):
    """Batch review input."""
    reviews: list[ReviewInput] = Field(..., description="List of reviews to analyze")
    
    class Config:
        json_schema_extra = {
            "example": {
                "reviews": [
                    {"text": "Great product!", "stars": 5},
                    {"text": "Terrible, broke after 2 days", "stars": 1}
                ]
            }
        }

class SentimentResult(BaseModel):
    """Sentiment analysis result."""
    sentiment_score: float = Field(..., description="Sentiment from -1 (negative) to +1 (positive)")
    confidence: float
    model_used: str

class CredibilityResult(BaseModel):
    """Credibility scoring result."""
    score: float = Field(..., description="Credibility from 0 (bot) to 1 (human)")
    classification: str = Field(..., description="bot, low_effort, or human")
    flags: list[str]

class SarcasmResult(BaseModel):
    """Sarcasm detection result."""
    is_sarcastic: bool
    confidence: float
    triggers: list[str]

class ReviewAnalysis(BaseModel):
    """Complete review analysis."""
    original_stars: int
    adjusted_rating: float
    rating_delta: float
    sentiment: SentimentResult
    credibility: CredibilityResult
    sarcasm: SarcasmResult

class ProductSummary(BaseModel):
    """Aggregated product statistics."""
    product_id: str
    total_reviews: int
    original_average: float
    adjusted_average: float
    rating_difference: float
    bot_percentage: float
    credibility_score: float
    breakdown: dict

class ProductAnalysisInput(BaseModel):
    """Product analysis request."""
    product_id: str = Field(..., description="Amazon ASIN or product ID")
    max_reviews: int = Field(default=100, ge=1, le=500, description="Max reviews to analyze")

class ProductAnalysisResult(BaseModel):
    """Complete product analysis."""
    product_id: str
    review_count: int
    original_average: float
    adjusted_average: float
    truth_gap: float
    bot_percentage: float
    credibility_distribution: dict
    rating_distribution: dict
    sample_reviews: list

class UrlAnalysisInput(BaseModel):
    """Amazon URL analysis request."""
    url: str = Field(..., description="Amazon product URL")
    html_content: str = Field(default=None, description="Optional: pre-fetched HTML content from browser")
    max_reviews: int = Field(default=50, ge=1, le=100, description="Max reviews to analyze")

class UrlAnalysisResult(BaseModel):
    """Amazon URL analysis result."""
    asin: str
    domain: str
    review_url: str
    product_title: str = None
    review_count: int
    original_average: float
    adjusted_average: float
    truth_gap: float
    bot_percentage: float
    credibility_distribution: dict
    sample_reviews: list
    scrape_method: str

# ============================================
# Endpoints
# ============================================

@app.get("/")
async def root():
    """API health check."""
    return {
        "status": "healthy",
        "api": "TrueRate.ai API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.post("/analyze", response_model=ReviewAnalysis)
async def analyze_review(review: ReviewInput):
    """
    Analyze a single review.
    
    Returns sentiment, credibility, sarcasm detection, and adjusted rating.
    """
    try:
        # Step 1: Sentiment
        sentiment = sentiment_analyzer.analyze(review.text)
        sentiment_score = sentiment.get("sentiment_score", 0.0)
        
        # Step 2: Credibility
        credibility = credibility_scorer.score(
            text=review.text,
            stars=review.stars,
            sentiment_score=sentiment_score
        )
        
        # Step 3: Sarcasm
        sarcasm = sarcasm_detector.detect(
            text=review.text,
            stars=review.stars,
            sentiment_score=sentiment_score
        )
        
        # Step 4: Weighted Rating
        rating = rating_calculator.calculate(
            stars=review.stars,
            sentiment_score=sentiment_score,
            credibility=credibility["score"],
            is_sarcastic=sarcasm["is_sarcastic"],
            sarcasm_confidence=sarcasm["confidence"]
        )
        
        return ReviewAnalysis(
            original_stars=review.stars,
            adjusted_rating=rating["adjusted_rating"],
            rating_delta=round(rating["adjusted_rating"] - review.stars, 2),
            sentiment=SentimentResult(
                sentiment_score=sentiment_score,
                confidence=sentiment.get("confidence", 0.0),
                model_used=sentiment.get("model_used", "unknown")
            ),
            credibility=CredibilityResult(
                score=credibility["score"],
                classification=credibility["classification"],
                flags=credibility["flags"]
            ),
            sarcasm=SarcasmResult(
                is_sarcastic=sarcasm["is_sarcastic"],
                confidence=sarcasm["confidence"],
                triggers=sarcasm["triggers"]
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/batch")
async def analyze_batch(batch: BatchReviewInput):
    """
    Analyze multiple reviews and return aggregated statistics.
    """
    results = []
    
    for review in batch.reviews:
        analysis = await analyze_review(review)
        results.append({
            "input": {"text": review.text, "stars": review.stars},
            "analysis": analysis.model_dump()
        })
    
    # Calculate aggregates
    if results:
        original_ratings = [r["input"]["stars"] for r in results]
        adjusted_ratings = [r["analysis"]["adjusted_rating"] for r in results]
        classifications = [r["analysis"]["credibility"]["classification"] for r in results]
        
        summary = {
            "total_reviews": len(results),
            "original_average": round(sum(original_ratings) / len(original_ratings), 2),
            "adjusted_average": round(sum(adjusted_ratings) / len(adjusted_ratings), 2),
            "bot_count": classifications.count("bot"),
            "low_effort_count": classifications.count("low_effort"),
            "human_count": classifications.count("human"),
            "sarcasm_count": sum(1 for r in results if r["analysis"]["sarcasm"]["is_sarcastic"])
        }
    else:
        summary = {}
    
    return {
        "summary": summary,
        "results": results
    }

@app.get("/config")
async def get_config():
    """Get current analysis configuration."""
    return {
        "star_weight": rating_calculator.star_weight,
        "sentiment_weight": rating_calculator.sentiment_weight,
        "sentiment_mode": "vader",
        "sarcasm_mode": "rule-based"
    }

# ============================================
# Product Analysis Endpoints
# ============================================

def get_dataset():
    """Lazy load the dataset."""
    global dataset_loader
    if dataset_loader is None:
        if DATASET_PATH.exists():
            dataset_loader = DatasetLoader(str(DATASET_PATH))
            # Load first 100k reviews for faster startup (remove limit for full dataset)
            dataset_loader.load(max_reviews=100000, show_progress=True)
        else:
            raise HTTPException(status_code=404, detail=f"Dataset not found: {DATASET_PATH}")
    return dataset_loader

@app.get("/products")
async def list_products(limit: int = 20):
    """
    List available products sorted by review count.
    """
    try:
        loader = get_dataset()
        products = loader.search_products(limit=limit)
        stats = loader.get_stats()
        return {
            "products": products,
            "dataset_stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/{product_id}")
async def get_product_info(product_id: str):
    """
    Get basic info for a product.
    """
    try:
        loader = get_dataset()
        product = loader.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
        return product
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/product", response_model=ProductAnalysisResult)
async def analyze_product(request: ProductAnalysisInput):
    """
    Analyze all reviews for a product and return aggregate truth gap analysis.
    """
    try:
        loader = get_dataset()
        product = loader.get_product(request.product_id)
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {request.product_id} not found")
        
        reviews = product["reviews"][:request.max_reviews]
        
        # Analyze each review
        results = []
        classifications = {"bot": 0, "low_effort": 0, "human": 0}
        rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        for review in reviews:
            sentiment = sentiment_analyzer.analyze(review["text"])
            sentiment_score = sentiment.get("sentiment_score", 0.0)
            
            credibility = credibility_scorer.score(
                text=review["text"],
                stars=review["stars"],
                sentiment_score=sentiment_score
            )
            
            sarcasm = sarcasm_detector.detect(
                text=review["text"],
                stars=review["stars"],
                sentiment_score=sentiment_score
            )
            
            rating = rating_calculator.calculate(
                stars=review["stars"],
                sentiment_score=sentiment_score,
                credibility=credibility["score"],
                is_sarcastic=sarcasm["is_sarcastic"],
                sarcasm_confidence=sarcasm["confidence"]
            )
            
            # Track stats
            classifications[credibility["classification"]] += 1
            rating_dist[review["stars"]] += 1
            
            results.append({
                "original_stars": review["stars"],
                "adjusted_rating": rating["adjusted_rating"],
                "text_preview": review["text"][:100] + "..." if len(review["text"]) > 100 else review["text"],
                "credibility": credibility["classification"],
                "is_sarcastic": sarcasm["is_sarcastic"]
            })
        
        # Calculate aggregates
        original_avg = sum(r["original_stars"] for r in results) / len(results)
        adjusted_avg = sum(r["adjusted_rating"] for r in results) / len(results)
        
        return ProductAnalysisResult(
            product_id=request.product_id,
            review_count=len(results),
            original_average=round(original_avg, 2),
            adjusted_average=round(adjusted_avg, 2),
            truth_gap=round(adjusted_avg - original_avg, 2),
            bot_percentage=round(classifications["bot"] / len(results) * 100, 1),
            credibility_distribution={
                "human": round(classifications["human"] / len(results) * 100, 1),
                "low_effort": round(classifications["low_effort"] / len(results) * 100, 1),
                "bot": round(classifications["bot"] / len(results) * 100, 1)
            },
            rating_distribution={str(k): v for k, v in rating_dist.items()},
            sample_reviews=results[:10]  # Top 10 for preview
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Detailed health check."""
    learner = get_learner()
    return {
        "status": "healthy",
        "modules": {
            "sentiment_analyzer": "ok",
            "credibility_scorer": "ok",
            "sarcasm_detector": "ok",
            "rating_calculator": "ok",
            "adaptive_learner": "ok"
        },
        "learning_stats": learner.get_stats()
    }


# ============================================
# Feedback Endpoints
# ============================================

class FeedbackInput(BaseModel):
    """User feedback on a review classification."""
    text: str = Field(..., description="Review text")
    stars: int = Field(..., ge=1, le=5, description="Star rating")
    predicted_class: str = Field(..., description="The classification shown to user (bot/low_effort/human)")
    predicted_score: Optional[float] = Field(default=None, description="Credibility score if available")
    user_vote: int = Field(..., description="1 if user agrees, -1 if user disagrees")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Great product, highly recommend!",
                "stars": 5,
                "predicted_class": "human",
                "user_vote": 1
            }
        }


@app.post("/feedback")
async def submit_feedback(feedback: FeedbackInput):
    """
    Submit user feedback on a review classification.
    
    Use user_vote=1 if user thinks classification is correct (👍),
    Use user_vote=-1 if user thinks classification is wrong (👎).
    
    This feedback is used to improve the model over time.
    """
    try:
        # Save to database
        result = save_feedback(
            text=feedback.text,
            stars=feedback.stars,
            predicted_class=feedback.predicted_class,
            user_vote=feedback.user_vote,
            predicted_score=feedback.predicted_score
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to save feedback"))
        
        # Update adaptive learner
        learner = get_learner()
        adjustments = learner.update_from_feedback(
            text=feedback.text,
            stars=feedback.stars,
            predicted_class=feedback.predicted_class,
            user_vote=feedback.user_vote
        )
        
        # Save learned weights periodically
        learner.save_weights()
        
        return {
            "success": True,
            "message": "Thank you for your feedback!",
            "text_hash": result.get("text_hash"),
            "adjustments_applied": len(adjustments)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/feedback/stats")
async def get_feedback_statistics():
    """
    Get feedback statistics and learning progress.
    """
    try:
        stats = get_feedback_stats()
        learner = get_learner()
        
        return {
            "feedback_stats": stats,
            "learner_stats": learner.get_stats(),
            "class_adjustments": get_class_adjustments()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/url")
async def analyze_amazon_url(request: UrlAnalysisInput):
    """
    Analyze reviews from an Amazon product URL.
    
    Workflow:
    1. Extract ASIN from URL
    2. Parse reviews from provided HTML (browser fetches this)
    3. Analyze each review for sentiment + credibility
    4. Return truth gap analysis
    """
    try:
        # Extract ASIN
        asin = extract_asin(request.url)
        if not asin:
            raise HTTPException(status_code=400, detail="Could not extract ASIN from URL")
        
        domain = get_amazon_domain(request.url)
        review_url = build_review_url(asin, domain)
        
        # Parse reviews from HTML if provided
        reviews = []
        product_title = None
        scrape_method = "browser"
        
        if request.html_content:
            scraper = AmazonScraper()
            reviews = scraper.scrape_reviews_from_html(request.html_content)
            product_info = scraper.get_product_info_from_html(request.html_content)
            product_title = product_info.get('title')
            scrape_method = "manual_html"
        
        # If no HTML provided, try ScraperAPI first (best for Amazon - handles CAPTCHAs)
        if not reviews:
            print(f"Trying ScraperAPI for ASIN: {asin}, domain: {domain}")
            scraperapi_reviews = scrape_with_scraperapi(asin, domain)
            if scraperapi_reviews:
                reviews = scraperapi_reviews
                scrape_method = "scraperapi"
                print(f"ScraperAPI returned {len(reviews)} reviews")
        
        # Fallback to Firecrawl if ScraperAPI failed
        if not reviews:
            print(f"Trying Firecrawl for: {review_url}")
            scraped_html = scrape_with_firecrawl(review_url)
            if scraped_html:
                scraper = AmazonScraper()
                reviews = scraper.scrape_reviews_from_html(scraped_html)
                product_info = scraper.get_product_info_from_html(scraped_html)
                product_title = product_info.get('title')
                scrape_method = "firecrawl"
        
        if not reviews:
            # Return the review URL for browser to fetch
            return {
                "asin": asin,
                "domain": domain,
                "review_url": review_url,
                "status": "pending_html",
                "message": "Automated scraping unavailable. Please copy the HTML from the review page manually.",
                "instructions": [
                    "1. Click the review_url link above to open the Amazon reviews page",
                    "2. Right-click on the page and select 'View Page Source' or press Ctrl+U",
                    "3. Select all (Ctrl+A) and copy (Ctrl+C) the HTML",
                    "4. Paste it when prompted"
                ]
            }
        
        # Limit reviews
        reviews = reviews[:request.max_reviews]
        
        # Analyze each review
        results = []
        credibility_counts = {"human": 0, "low_effort": 0, "bot": 0}
        
        for review in reviews:
            stars = int(review.get('stars', 3))
            text = review.get('text', '')
            
            if not text or len(text) < 10:
                continue
            
            # Run analysis
            sentiment = sentiment_analyzer.analyze(text)
            credibility = credibility_scorer.score(text, stars)
            sarcasm = sarcasm_detector.detect(text)
            adjusted = rating_calculator.calculate(stars, sentiment['sentiment_score'])
            
            credibility_counts[credibility['classification']] += 1
            
            results.append({
                "original_stars": stars,
                "adjusted_rating": round(adjusted, 2),
                "title": review.get('title', ''),
                "text": text[:200] + '...' if len(text) > 200 else text,
                "credibility": credibility['classification'],
                "is_sarcastic": sarcasm['is_sarcastic'],
                "verified": review.get('verified', False)
            })
        
        if not results:
            raise HTTPException(status_code=400, detail="No valid reviews found in HTML")
        
        # Calculate aggregates
        original_avg = sum(r['original_stars'] for r in results) / len(results)
        adjusted_avg = sum(r['adjusted_rating'] for r in results) / len(results)
        total = len(results)
        
        return {
            "asin": asin,
            "domain": domain,
            "review_url": review_url,
            "product_title": product_title,
            "review_count": total,
            "original_average": round(original_avg, 2),
            "adjusted_average": round(adjusted_avg, 2),
            "truth_gap": round(adjusted_avg - original_avg, 2),
            "bot_percentage": round(credibility_counts['bot'] / total * 100, 1),
            "credibility_distribution": {
                "human": round(credibility_counts['human'] / total * 100, 1),
                "low_effort": round(credibility_counts['low_effort'] / total * 100, 1),
                "bot": round(credibility_counts['bot'] / total * 100, 1)
            },
            "sample_reviews": results[:10],
            "scrape_method": scrape_method
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# Run Server
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
