/**
 * TrueRate.ai - Content Script
 * Injected into web pages to extract reviews
 */

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'extractReviews') {
        const reviews = extractReviews();
        const pageInfo = detectPageType();
        sendResponse({ reviews, pageInfo });
    } else if (request.action === 'loadMoreReviews') {
        handleLoadMore().then(result => sendResponse(result));
        return true; // Indicates async response
    }
});

// Detect what type of page we're on
function detectPageType() {
    const url = window.location.href;
    const hostname = window.location.hostname;

    // Amazon detection
    if (hostname.includes('amazon')) {
        // Extract the overall displayed rating (e.g., "4.7 out of 5")
        let displayedRating = null;

        // Try multiple selectors for the overall rating
        const ratingSelectors = [
            '[data-hook="rating-out-of-text"]',  // "4.7 out of 5"
            '.a-icon-star .a-icon-alt',
            '#acrPopover .a-icon-alt',
            '[data-hook="acr-average-stars-rating-text"]',
            '.averageStarRating .a-icon-alt',
            '#averageCustomerReviews .a-icon-alt'
        ];

        for (const selector of ratingSelectors) {
            const el = document.querySelector(selector);
            if (el) {
                const text = el.textContent || el.getAttribute('aria-label') || '';
                const match = text.match(/(\d+(?:\.\d+)?)\s*(?:out of|\/)/i);
                if (match) {
                    displayedRating = parseFloat(match[1]);
                    break;
                }
            }
        }

        // Also try the star class (a-star-4-5 means 4.5)
        if (!displayedRating) {
            const starEl = document.querySelector('#acrPopover .a-icon-star, .averageStarRating .a-icon-star');
            if (starEl) {
                const classMatch = starEl.className.match(/a-star-(\d)-(\d)/);
                if (classMatch) {
                    displayedRating = parseFloat(`${classMatch[1]}.${classMatch[2]}`);
                }
            }
        }

        if (url.includes('/product-reviews/') || url.includes('/customer-reviews/')) {
            return {
                site: 'amazon',
                type: 'reviews',
                hasMorePages: !!document.querySelector('.a-pagination .a-last:not(.a-disabled)'),
                displayedRating: displayedRating
            };
        }
        if (url.includes('/dp/') || url.includes('/gp/product/')) {
            const seeAllLink = document.querySelector('a[data-hook="see-all-reviews-link-foot"]') ||
                document.querySelector('a[href*="/product-reviews/"]') ||
                document.querySelector('[data-hook="see-all-reviews"]');
            const totalReviewsEl = document.querySelector('[data-hook="total-review-count"]') ||
                document.querySelector('.averageStarRatingNumerical');
            let totalReviews = 0;
            if (totalReviewsEl) {
                const match = totalReviewsEl.textContent.match(/([\d,]+)/);
                if (match) totalReviews = parseInt(match[1].replace(/,/g, ''));
            }
            return {
                site: 'amazon',
                type: 'product',
                reviewsUrl: seeAllLink?.href,
                totalReviews: totalReviews,
                displayedRating: displayedRating
            };
        }
    }

    // Yelp detection
    if (hostname.includes('yelp')) {
        return { site: 'yelp', type: 'reviews' };
    }

    // TripAdvisor detection
    if (hostname.includes('tripadvisor')) {
        return { site: 'tripadvisor', type: 'reviews' };
    }

    // Trustpilot detection
    if (hostname.includes('trustpilot')) {
        return { site: 'trustpilot', type: 'reviews' };
    }

    return { site: 'unknown', type: 'unknown' };
}

// Extract star rating from an element
function extractStarRating(parent) {
    // 1. Amazon-specific: Check for data-hook star rating elements first
    const amazonStarEl = parent.querySelector('[data-hook="review-star-rating"], [data-hook="cmps-review-star-rating"]');
    if (amazonStarEl) {
        const classMatch = amazonStarEl.className.match(/a-star-(\d)/);
        if (classMatch) return parseInt(classMatch[1]);

        const altText = amazonStarEl.querySelector('.a-icon-alt')?.textContent || '';
        const altMatch = altText.match(/(\d+(?:\.\d+)?)/);
        if (altMatch) return Math.round(parseFloat(altMatch[1]));

        const innerMatch = (amazonStarEl.innerText || '').match(/(\d+(?:\.\d+)?)/);
        if (innerMatch) return Math.round(parseFloat(innerMatch[1]));
    }

    // 2. Generic star icon with class name
    const iconStarEl = parent.querySelector('.a-icon-star, .a-icon-star-small, [class*="a-star-"]');
    if (iconStarEl) {
        const classMatch = iconStarEl.className.match(/a-star-(\d)/);
        if (classMatch) return parseInt(classMatch[1]);

        const altText = iconStarEl.querySelector('.a-icon-alt')?.textContent || '';
        const altMatch = altText.match(/(\d+(?:\.\d+)?)/);
        if (altMatch) return Math.round(parseFloat(altMatch[1]));
    }

    // 3. Data-rating attribute
    const dataRatingEl = parent.querySelector('[data-rating]');
    if (dataRatingEl) {
        const rating = parseFloat(dataRatingEl.getAttribute('data-rating'));
        if (!isNaN(rating)) return Math.round(rating);
    }

    // 4. Aria-label with star info
    const ariaEl = parent.querySelector('[aria-label*="star"], [aria-label*="Star"], [aria-label*="rating"]');
    if (ariaEl) {
        const ariaLabel = ariaEl.getAttribute('aria-label') || '';
        const match = ariaLabel.match(/(\d+(?:\.\d+)?)/);
        if (match) return Math.round(parseFloat(match[1]));
    }

    // 5. Look for text containing "X out of 5" pattern
    const ratingText = parent.innerHTML.match(/(\d+(?:\.\d+)?)\s*(?:out of|\/)\s*5/i);
    if (ratingText) return Math.round(parseFloat(ratingText[1]));

    // 6. Count filled star icons
    const filledStars = parent.querySelectorAll('.star-filled, .star-full, [class*="star"][class*="full"], [class*="star"][class*="active"]');
    if (filledStars.length > 0 && filledStars.length <= 5) return filledStars.length;

    return null;
}

// Extract reviews from the page
function extractReviews() {
    const reviews = [];

    const selectors = [
        // Amazon
        '[data-hook="review-body"]',
        '.review-text-content',
        '.a-size-base.review-text',
        // Yelp
        '.comment__09f24__D0cxf',
        '.raw__09f24__T4Ezm',
        // TripAdvisor
        '.biGQs._P.pZUbB.KxBGd',
        '[data-automation="reviewCard"]',
        // Google Reviews
        '.MyEned',
        '.wiI7pd',
        // Trustpilot
        '[data-service-review-text-typography]',
        '.typography_body-l__KUYFJ',
        // G2
        '[itemprop="reviewBody"]',
        '.pjax',
        // Generic patterns
        '[class*="review-text"]',
        '[class*="review-body"]',
        '[class*="review-content"]',
        '[class*="comment-text"]',
        '[class*="feedback-text"]',
        '.review p',
        '.comment p',
    ];

    for (const selector of selectors) {
        try {
            const elements = document.querySelectorAll(selector);
            elements.forEach(el => {
                const text = el.innerText?.trim();
                if (text && text.length > 20 && text.length < 5000) {
                    if (!reviews.some(r => r.text === text)) {
                        let stars = 3;

                        const reviewContainer = el.closest('[data-hook="review"]') ||
                            el.closest('[class*="review"]') ||
                            el.closest('[class*="Review"]') ||
                            el.parentElement?.parentElement?.parentElement;

                        if (reviewContainer) {
                            const extractedStars = extractStarRating(reviewContainer);
                            if (extractedStars !== null) stars = extractedStars;
                        }

                        reviews.push({
                            text: text,
                            stars: Math.min(5, Math.max(1, Math.round(stars)))
                        });
                    }
                }
            });
        } catch (e) {
            // Ignore selector errors
        }
    }

    // Check for selected text
    const selection = window.getSelection()?.toString()?.trim();
    if (selection && selection.length > 20) {
        reviews.unshift({ text: selection, stars: 3 });
    }

    return reviews.slice(0, 50);
}

// Handle load more reviews - just re-extracts from current page state without scrolling
async function handleLoadMore() {
    // Simply re-extract reviews from the current DOM state
    // We don't scroll or click pagination as that disrupts the page
    const reviews = extractReviews();
    const pageInfo = detectPageType();
    return { reviews, pageInfo, message: 'Re-extracted from current page. Navigate manually for more reviews.' };
}

// Log when content script loads
console.log('TrueRate.ai content script loaded');
