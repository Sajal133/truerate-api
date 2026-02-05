#!/usr/bin/env python3
"""
Amazon Review Scraper
=====================
Scrapes reviews from Amazon product pages using browser automation.

Usage:
    from execution.scrape_amazon import AmazonScraper
    
    scraper = AmazonScraper()
    reviews = scraper.scrape_reviews("https://amazon.in/dp/B0XXXXX")

Cost: $0 (browser automation, no API needed)
"""

import re
import time
import json
import os
import requests
from typing import List, Optional, Dict
from pathlib import Path
from urllib.parse import urlparse

# Firecrawl API configuration
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "fc-442ed1832033402e86f569b40c8b36f1")
FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1/scrape"

# ScraperAPI configuration - Free tier: 1000 credits/month
# Sign up at: https://www.scraperapi.com/
SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY", "")  # User must provide their own key
SCRAPERAPI_AMAZON_REVIEWS_URL = "https://api.scraperapi.com/structured/amazon/review"


def scrape_with_scraperapi(asin: str, domain: str = "amazon.com", page: int = 1) -> Optional[List[Dict]]:
    """
    Use ScraperAPI's Amazon Review endpoint to fetch reviews.
    
    ScraperAPI provides a dedicated Amazon Review API that:
    - Handles CAPTCHAs automatically
    - Returns structured JSON data
    - Supports multiple Amazon domains
    
    Args:
        asin: Amazon product ASIN
        domain: Amazon domain (amazon.com, amazon.in, etc.)
        page: Page number for pagination
        
    Returns:
        List of review dictionaries, or None if failed
    """
    if not SCRAPERAPI_KEY:
        print("ScraperAPI key not configured. Set SCRAPERAPI_KEY environment variable.")
        return None
    
    try:
        # Build the API URL with parameters
        params = {
            "api_key": SCRAPERAPI_KEY,
            "asin": asin,
            "country": _get_country_code(domain),
            "tld": _get_tld(domain),
            "page": page
        }
        
        response = requests.get(
            SCRAPERAPI_AMAZON_REVIEWS_URL,
            params=params,
            timeout=60  # ScraperAPI can take time for complex pages
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # ScraperAPI returns structured review data
            reviews = []
            for review_data in data.get("reviews", []):
                review = {
                    "stars": float(review_data.get("rating", 3)),
                    "title": review_data.get("title", ""),
                    "text": review_data.get("body", "") or review_data.get("review", ""),
                    "reviewer": review_data.get("author", ""),
                    "date": review_data.get("date", ""),
                    "verified": review_data.get("verified_purchase", False),
                    "helpful_votes": review_data.get("helpful_count", 0)
                }
                if review["text"]:
                    reviews.append(review)
            
            return reviews
        
        print(f"ScraperAPI error: {response.status_code} - {response.text[:200]}")
        return None
        
    except Exception as e:
        print(f"ScraperAPI request failed: {e}")
        return None


def _get_country_code(domain: str) -> str:
    """Get country code from Amazon domain."""
    domain_to_country = {
        "www.amazon.com": "us",
        "amazon.com": "us",
        "www.amazon.in": "in",
        "amazon.in": "in",
        "www.amazon.co.uk": "uk",
        "amazon.co.uk": "uk",
        "www.amazon.de": "de",
        "amazon.de": "de",
        "www.amazon.fr": "fr",
        "amazon.fr": "fr",
        "www.amazon.ca": "ca",
        "amazon.ca": "ca",
        "www.amazon.co.jp": "jp",
        "amazon.co.jp": "jp",
    }
    return domain_to_country.get(domain, "us")


def _get_tld(domain: str) -> str:
    """Get TLD from Amazon domain."""
    if ".co.uk" in domain:
        return "co.uk"
    elif ".co.jp" in domain:
        return "co.jp"
    elif ".com.br" in domain:
        return "com.br"
    elif ".com.mx" in domain:
        return "com.mx"
    elif ".in" in domain:
        return "in"
    elif ".de" in domain:
        return "de"
    elif ".fr" in domain:
        return "fr"
    elif ".ca" in domain:
        return "ca"
    return "com"


def scrape_with_firecrawl(url: str) -> Optional[str]:
    """
    Use Firecrawl API to scrape a webpage.
    Returns the HTML content of the page.
    """
    try:
        response = requests.post(
            FIRECRAWL_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {FIRECRAWL_API_KEY}"
            },
            json={
                "url": url,
                "formats": ["html"],
                "onlyMainContent": False,
                "waitFor": 2000  # Wait for dynamic content
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("data", {}).get("html", "")
        
        print(f"Firecrawl error: {response.status_code} - {response.text[:200]}")
        return None
        
    except Exception as e:
        print(f"Firecrawl request failed: {e}")
        return None


def extract_asin(url: str) -> Optional[str]:
    """
    Extract ASIN (Amazon Standard Identification Number) from various Amazon URL formats.
    
    Supported formats:
        - https://amazon.com/dp/B0XXXXX
        - https://amazon.in/product/B0XXXXX
        - https://amazon.com/gp/product/B0XXXXX
        - https://amazon.com/Some-Product-Name/dp/B0XXXXX/
        - https://amazon.in/dp/B0XXXXX?ref=xxx
    """
    if not url:
        return None
    
    # ASIN is always 10 characters, starts with B0 (usually) or is alphanumeric
    patterns = [
        r'/dp/([A-Z0-9]{10})',           # Most common: /dp/ASIN
        r'/gp/product/([A-Z0-9]{10})',    # Alternate: /gp/product/ASIN
        r'/product/([A-Z0-9]{10})',       # Short: /product/ASIN
        r'/ASIN/([A-Z0-9]{10})',          # Rare: /ASIN/ASIN
        r'([A-Z0-9]{10})(?:[/?]|$)',      # Fallback: any 10-char code
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            asin = match.group(1).upper()
            # Validate it looks like an ASIN
            if re.match(r'^[A-Z0-9]{10}$', asin):
                return asin
    
    return None


def get_amazon_domain(url: str) -> str:
    """Extract Amazon domain from URL (amazon.com, amazon.in, etc.)"""
    parsed = urlparse(url)
    return parsed.netloc or "www.amazon.com"


def build_review_url(asin: str, domain: str = "www.amazon.com", page: int = 1) -> str:
    """Build the Amazon reviews page URL for a product."""
    return f"https://{domain}/product-reviews/{asin}?pageNumber={page}&reviewerType=all_reviews"


class AmazonScraper:
    """
    Scrapes Amazon product reviews.
    
    Uses simple HTML parsing for the review page structure.
    """
    
    def __init__(self):
        self._session = None
    
    def _parse_review_html(self, html: str) -> List[Dict]:
        """
        Parse reviews from Amazon HTML.
        Uses regex patterns since Amazon's HTML structure is consistent.
        """
        reviews = []
        
        # Pattern for individual reviews
        # Each review is in a div with data-hook="review"
        review_pattern = r'data-hook="review"[^>]*>(.*?)</div>\s*</div>\s*</div>\s*</div>'
        
        # Find all review blocks
        review_blocks = re.findall(r'<div[^>]*data-hook="review"[^>]*>.*?(?=<div[^>]*data-hook="review"|$)', 
                                   html, re.DOTALL)
        
        for block in review_blocks:
            try:
                review = {}
                
                # Extract star rating
                star_match = re.search(r'(\d+(?:\.\d+)?)\s*out of\s*5\s*stars', block, re.IGNORECASE)
                if star_match:
                    review['stars'] = float(star_match.group(1))
                else:
                    continue  # Skip reviews without ratings
                
                # Extract review title
                title_match = re.search(r'data-hook="review-title"[^>]*>.*?<span[^>]*>(.+?)</span>', 
                                       block, re.DOTALL)
                if title_match:
                    review['title'] = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
                
                # Extract review text
                text_match = re.search(r'data-hook="review-body"[^>]*>.*?<span[^>]*>(.+?)</span>', 
                                      block, re.DOTALL)
                if text_match:
                    review['text'] = re.sub(r'<[^>]+>', '', text_match.group(1)).strip()
                else:
                    review['text'] = review.get('title', '')
                
                # Extract reviewer name
                name_match = re.search(r'class="a-profile-name">([^<]+)</span>', block)
                if name_match:
                    review['reviewer'] = name_match.group(1).strip()
                
                # Extract date
                date_match = re.search(r'data-hook="review-date"[^>]*>([^<]+)', block)
                if date_match:
                    review['date'] = date_match.group(1).strip()
                
                # Extract verified purchase
                review['verified'] = 'Verified Purchase' in block
                
                # Extract helpful votes
                helpful_match = re.search(r'(\d+)\s*people?\s*found this helpful', block, re.IGNORECASE)
                if helpful_match:
                    review['helpful_votes'] = int(helpful_match.group(1))
                else:
                    review['helpful_votes'] = 0
                
                if review.get('text'):
                    reviews.append(review)
                    
            except Exception as e:
                continue
        
        return reviews
    
    def scrape_reviews_from_html(self, html: str) -> List[Dict]:
        """Parse reviews from HTML content."""
        return self._parse_review_html(html)
    
    def get_product_info_from_html(self, html: str) -> Dict:
        """Extract product title and rating from HTML."""
        info = {}
        
        # Product title
        title_match = re.search(r'<title>([^<]+)</title>', html)
        if title_match:
            title = title_match.group(1)
            # Clean up Amazon's title format
            title = re.sub(r'\s*-\s*Amazon.*$', '', title)
            title = re.sub(r'\s*:\s*Customer reviews.*$', '', title, flags=re.IGNORECASE)
            info['title'] = title.strip()
        
        # Average rating
        rating_match = re.search(r'(\d+(?:\.\d+)?)\s*out of\s*5', html)
        if rating_match:
            info['average_rating'] = float(rating_match.group(1))
        
        # Total reviews
        total_match = re.search(r'([\d,]+)\s*(?:global\s*)?ratings?', html, re.IGNORECASE)
        if total_match:
            info['total_reviews'] = int(total_match.group(1).replace(',', ''))
        
        return info


# Convenience function for direct usage
def scrape_amazon_url(url: str, html_content: str = None) -> Dict:
    """
    Convenience function to scrape an Amazon product URL.
    
    Args:
        url: Amazon product URL
        html_content: Optional pre-fetched HTML content
        
    Returns:
        Dict with ASIN, product info, and reviews
    """
    asin = extract_asin(url)
    if not asin:
        return {"error": "Could not extract ASIN from URL", "url": url}
    
    domain = get_amazon_domain(url)
    review_url = build_review_url(asin, domain)
    
    result = {
        "asin": asin,
        "domain": domain,
        "review_url": review_url,
        "reviews": [],
        "product_info": {}
    }
    
    if html_content:
        scraper = AmazonScraper()
        result["reviews"] = scraper.scrape_reviews_from_html(html_content)
        result["product_info"] = scraper.get_product_info_from_html(html_content)
    
    return result


# CLI for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python scrape_amazon.py <amazon_url>")
        print("\nExample URLs:")
        print("  https://amazon.com/dp/B0BTZT4GKZ")
        print("  https://amazon.in/Some-Product/dp/B0XXXXX/")
        sys.exit(1)
    
    url = sys.argv[1]
    asin = extract_asin(url)
    
    if asin:
        print(f"✅ Extracted ASIN: {asin}")
        print(f"   Domain: {get_amazon_domain(url)}")
        print(f"   Review URL: {build_review_url(asin, get_amazon_domain(url))}")
    else:
        print(f"❌ Could not extract ASIN from: {url}")
