/**
 * Truth Gap Analyser - Bookmarklet
 * Analyzes reviews on any webpage for authenticity
 * 
 * How to use:
 * 1. Create a new bookmark in your browser
 * 2. Paste this code as the URL
 * 3. Click the bookmark on any review page
 */

(function () {
  // Configuration
  const API_URL = 'http://localhost:8000';
  const OVERLAY_ID = 'truth-gap-overlay';

  // Remove existing overlay if present
  const existingOverlay = document.getElementById(OVERLAY_ID);
  if (existingOverlay) {
    existingOverlay.remove();
  }

  // Create overlay container
  const overlay = document.createElement('div');
  overlay.id = OVERLAY_ID;
  overlay.innerHTML = `
    <style>
      #${OVERLAY_ID} {
        position: fixed;
        top: 20px;
        right: 20px;
        width: 380px;
        max-height: 80vh;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 16px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.4);
        z-index: 999999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: #fff;
        overflow: hidden;
      }
      #${OVERLAY_ID} .tg-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 16px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      #${OVERLAY_ID} .tg-title {
        font-size: 18px;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      #${OVERLAY_ID} .tg-close {
        background: rgba(255,255,255,0.2);
        border: none;
        color: white;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 18px;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      #${OVERLAY_ID} .tg-close:hover {
        background: rgba(255,255,255,0.3);
      }
      #${OVERLAY_ID} .tg-content {
        padding: 20px;
        max-height: 60vh;
        overflow-y: auto;
      }
      #${OVERLAY_ID} .tg-status {
        text-align: center;
        padding: 40px 20px;
        color: #a0aec0;
      }
      #${OVERLAY_ID} .tg-spinner {
        width: 40px;
        height: 40px;
        border: 3px solid #4a5568;
        border-top-color: #667eea;
        border-radius: 50%;
        animation: tg-spin 1s linear infinite;
        margin: 0 auto 16px;
      }
      @keyframes tg-spin {
        to { transform: rotate(360deg); }
      }
      #${OVERLAY_ID} .tg-truth-gap {
        background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin-bottom: 16px;
      }
      #${OVERLAY_ID} .tg-gap-value {
        font-size: 48px;
        font-weight: 800;
        margin: 8px 0;
      }
      #${OVERLAY_ID} .tg-gap-label {
        font-size: 14px;
        color: #a0aec0;
        text-transform: uppercase;
        letter-spacing: 1px;
      }
      #${OVERLAY_ID} .tg-stats {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin-bottom: 16px;
      }
      #${OVERLAY_ID} .tg-stat {
        background: rgba(255,255,255,0.05);
        border-radius: 8px;
        padding: 12px;
        text-align: center;
      }
      #${OVERLAY_ID} .tg-stat-value {
        font-size: 24px;
        font-weight: 700;
        color: #667eea;
      }
      #${OVERLAY_ID} .tg-stat-label {
        font-size: 11px;
        color: #718096;
        text-transform: uppercase;
        margin-top: 4px;
      }
      #${OVERLAY_ID} .tg-reviews {
        margin-top: 16px;
      }
      #${OVERLAY_ID} .tg-review {
        background: rgba(255,255,255,0.05);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        border-left: 3px solid #667eea;
      }
      #${OVERLAY_ID} .tg-review.suspicious {
        border-left-color: #f56565;
        background: rgba(245, 101, 101, 0.1);
      }
      #${OVERLAY_ID} .tg-review.genuine {
        border-left-color: #48bb78;
        background: rgba(72, 187, 120, 0.1);
      }
      #${OVERLAY_ID} .tg-review-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
      }
      #${OVERLAY_ID} .tg-review-stars {
        color: #fbbf24;
      }
      #${OVERLAY_ID} .tg-review-badge {
        font-size: 10px;
        padding: 2px 8px;
        border-radius: 12px;
        font-weight: 600;
        text-transform: uppercase;
      }
      #${OVERLAY_ID} .tg-review-badge.bot {
        background: #f56565;
        color: white;
      }
      #${OVERLAY_ID} .tg-review-badge.human {
        background: #48bb78;
        color: white;
      }
      #${OVERLAY_ID} .tg-review-badge.low-effort {
        background: #ed8936;
        color: white;
      }
      #${OVERLAY_ID} .tg-review-text {
        font-size: 13px;
        color: #cbd5e0;
        line-height: 1.5;
      }
      #${OVERLAY_ID} .tg-error {
        text-align: center;
        color: #f56565;
        padding: 20px;
      }
      #${OVERLAY_ID} .tg-no-reviews {
        text-align: center;
        color: #a0aec0;
        padding: 40px 20px;
      }
      #${OVERLAY_ID} .tg-page-hint {
        background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
        border: 1px solid #4a5568;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 10px;
      }
      #${OVERLAY_ID} .tg-page-hint-icon {
        font-size: 20px;
      }
      #${OVERLAY_ID} .tg-page-hint-text {
        font-size: 12px;
        color: #a0aec0;
        flex: 1;
      }
      #${OVERLAY_ID} .tg-page-hint-btn {
        background: #667eea;
        color: white;
        border: none;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 11px;
        cursor: pointer;
        font-weight: 600;
        white-space: nowrap;
      }
      #${OVERLAY_ID} .tg-page-hint-btn:hover {
        background: #5a6fd6;
      }
      #${OVERLAY_ID} .tg-load-more {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 12px 20px;
        border-radius: 8px;
        font-size: 13px;
        cursor: pointer;
        font-weight: 600;
        width: 100%;
        margin-top: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
      }
      #${OVERLAY_ID} .tg-load-more:hover {
        opacity: 0.9;
      }
      #${OVERLAY_ID} .tg-load-more:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      #${OVERLAY_ID} .tg-review-count {
        text-align: center;
        font-size: 11px;
        color: #718096;
        margin-top: 8px;
      }
    </style>
    <div class="tg-header">
      <div class="tg-title">🔍 Truth Gap Analyser</div>
      <button class="tg-close" onclick="document.getElementById('${OVERLAY_ID}').remove()">×</button>
    </div>
    <div class="tg-content">
      <div class="tg-status">
        <div class="tg-spinner"></div>
        <div>Extracting reviews from page...</div>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);

  // State for tracking analysis
  let currentResults = [];
  let allExtractedReviews = [];
  let isLoadingMore = false;

  // Detect what type of page we're on
  function detectPageType() {
    const url = window.location.href;
    const hostname = window.location.hostname;

    // Amazon detection
    if (hostname.includes('amazon')) {
      if (url.includes('/product-reviews/') || url.includes('/customer-reviews/')) {
        return { site: 'amazon', type: 'reviews', hasMorePages: !!document.querySelector('.a-pagination') };
      }
      if (url.includes('/dp/') || url.includes('/gp/product/')) {
        // Find the "See all reviews" link
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
          totalReviews: totalReviews
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

    return { site: 'unknown', type: 'unknown' };
  }

  // Scroll to load more reviews
  async function scrollToLoadMore() {
    return new Promise((resolve) => {
      const scrollHeight = document.documentElement.scrollHeight;
      window.scrollTo({ top: scrollHeight, behavior: 'smooth' });
      setTimeout(() => {
        // Click "Next" button if available (Amazon pagination)
        const nextBtn = document.querySelector('.a-pagination .a-last:not(.a-disabled) a');
        if (nextBtn) {
          nextBtn.click();
          setTimeout(resolve, 2000); // Wait for page to load
        } else {
          resolve();
        }
      }, 1000);
    });
  }

  // Extract reviews from the page
  function extractReviews() {
    const reviews = [];

    // Common review patterns across websites
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

    // Helper function to extract star rating from an element
    function extractStarRating(parent) {
      let stars = null;

      // 1. Amazon-specific: Check for data-hook star rating elements first
      const amazonStarEl = parent.querySelector('[data-hook="review-star-rating"], [data-hook="cmps-review-star-rating"]');
      if (amazonStarEl) {
        // Try class name (most reliable for Amazon: a-star-4, a-star-5, etc.)
        const classMatch = amazonStarEl.className.match(/a-star-(\d)/);
        if (classMatch) {
          return parseInt(classMatch[1]);
        }
        // Try .a-icon-alt text (e.g., "4.0 out of 5 stars")
        const altText = amazonStarEl.querySelector('.a-icon-alt')?.textContent || '';
        const altMatch = altText.match(/(\d+(?:\.\d+)?)/);
        if (altMatch) {
          return Math.round(parseFloat(altMatch[1]));
        }
        // Try inner text
        const innerMatch = (amazonStarEl.innerText || '').match(/(\d+(?:\.\d+)?)/);
        if (innerMatch) {
          return Math.round(parseFloat(innerMatch[1]));
        }
      }

      // 2. Generic star icon with class name (a-icon-star, a-star-X)
      const iconStarEl = parent.querySelector('.a-icon-star, .a-icon-star-small, [class*="a-star-"]');
      if (iconStarEl) {
        const classMatch = iconStarEl.className.match(/a-star-(\d)/);
        if (classMatch) {
          return parseInt(classMatch[1]);
        }
        const altText = iconStarEl.querySelector('.a-icon-alt')?.textContent || '';
        const altMatch = altText.match(/(\d+(?:\.\d+)?)/);
        if (altMatch) {
          return Math.round(parseFloat(altMatch[1]));
        }
      }

      // 3. Data-rating attribute (common on many sites)
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

      // 5. Look for text containing "X out of 5" pattern in the parent
      const ratingText = parent.innerHTML.match(/(\d+(?:\.\d+)?)\s*(?:out of|\/)\s*5/i);
      if (ratingText) {
        return Math.round(parseFloat(ratingText[1]));
      }

      // 6. Count filled star icons (for sites that use multiple star images)
      const filledStars = parent.querySelectorAll('.star-filled, .star-full, [class*="star"][class*="full"], [class*="star"][class*="active"]');
      if (filledStars.length > 0 && filledStars.length <= 5) {
        return filledStars.length;
      }

      return null; // Return null if we couldn't find a rating
    }

    // Try each selector
    for (const selector of selectors) {
      try {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
          const text = el.innerText?.trim();
          if (text && text.length > 20 && text.length < 5000) {
            // Avoid duplicates
            if (!reviews.some(r => r.text === text)) {
              // Try to find star rating nearby
              let stars = 3; // default

              // Try multiple parent levels to find the review container
              const reviewContainer = el.closest('[data-hook="review"]') ||
                el.closest('[class*="review"]') ||
                el.closest('[class*="Review"]') ||
                el.parentElement?.parentElement?.parentElement;

              if (reviewContainer) {
                const extractedStars = extractStarRating(reviewContainer);
                if (extractedStars !== null) {
                  stars = extractedStars;
                }
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

    // Also check for selected text
    const selection = window.getSelection()?.toString()?.trim();
    if (selection && selection.length > 20) {
      reviews.unshift({ text: selection, stars: 3 });
    }

    return reviews.slice(0, 50); // Limit to 50 reviews
  }

  // Analyze reviews via API
  async function analyzeReviews(reviews) {
    const results = [];

    for (const review of reviews.slice(0, 20)) { // Analyze up to 20
      try {
        const response = await fetch(`${API_URL}/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: review.text,
            stars: review.stars
          })
        });

        if (response.ok) {
          const data = await response.json();
          // Map API response fields to bookmarklet format
          results.push({
            ...review,
            weighted_rating: data.adjusted_rating,
            credibility_label: data.credibility?.classification || 'unknown',
            credibility_score: data.credibility?.score || 0,
            is_sarcastic: data.sarcasm?.is_sarcastic || false
          });
        }
      } catch (e) {
        console.error('Analysis error:', e);
      }
    }

    return results;
  }

  // Calculate truth gap
  function calculateTruthGap(results) {
    if (results.length === 0) return { gap: 0, avgDisplayed: 0, avgTrue: 0 };

    const avgDisplayed = results.reduce((sum, r) => sum + r.stars, 0) / results.length;
    const avgTrue = results.reduce((sum, r) => sum + (r.weighted_rating || r.stars), 0) / results.length;

    return {
      gap: avgDisplayed - avgTrue,
      avgDisplayed: avgDisplayed,
      avgTrue: avgTrue
    };
  }

  // Render results
  function renderResults(results, pageInfo = null) {
    const content = overlay.querySelector('.tg-content');
    currentResults = results;

    if (results.length === 0) {
      content.innerHTML = `
        <div class="tg-no-reviews">
          <div style="font-size: 48px; margin-bottom: 16px;">📭</div>
          <div style="font-size: 16px; margin-bottom: 8px;">No reviews found on this page</div>
          <div style="font-size: 13px;">Try selecting some review text and clicking the bookmarklet again</div>
        </div>
      `;
      return;
    }

    const { gap, avgDisplayed, avgTrue } = calculateTruthGap(results);
    const gapColor = gap > 0.5 ? '#f56565' : gap < -0.5 ? '#48bb78' : '#fbbf24';

    const credCounts = {
      human: results.filter(r => r.credibility_label === 'human').length,
      bot: results.filter(r => r.credibility_label === 'bot').length,
      lowEffort: results.filter(r => r.credibility_label === 'low_effort').length
    };

    // Build page hint HTML
    let pageHintHtml = '';
    if (pageInfo) {
      if (pageInfo.type === 'product' && pageInfo.reviewsUrl) {
        const totalText = pageInfo.totalReviews > 0 ? ` (${pageInfo.totalReviews.toLocaleString()} total)` : '';
        pageHintHtml = `
          <div class="tg-page-hint">
            <span class="tg-page-hint-icon">💡</span>
            <span class="tg-page-hint-text">You're on a product page. View all reviews for a more complete analysis${totalText}.</span>
            <button class="tg-page-hint-btn" onclick="window.location.href='${pageInfo.reviewsUrl}'">See All Reviews</button>
          </div>
        `;
      } else if (pageInfo.type === 'reviews' && pageInfo.hasMorePages) {
        pageHintHtml = `
          <div class="tg-page-hint">
            <span class="tg-page-hint-icon">📄</span>
            <span class="tg-page-hint-text">More review pages available. Click Load More to analyze additional reviews.</span>
          </div>
        `;
      }
    }

    // Build review count text
    const reviewCountText = pageInfo && pageInfo.totalReviews > 0
      ? `Analyzed ${results.length} of ~${pageInfo.totalReviews.toLocaleString()} reviews`
      : `Analyzed ${results.length} reviews on this page`;

    // Build load more button HTML
    const showLoadMore = pageInfo && (pageInfo.type === 'reviews' || allExtractedReviews.length < 50);
    const loadMoreHtml = showLoadMore ? `
      <button class="tg-load-more" id="tg-load-more-btn">
        <span>🔄</span> Load More Reviews
      </button>
    ` : '';

    content.innerHTML = `
      ${pageHintHtml}
      <div class="tg-truth-gap">
        <div class="tg-gap-label">Truth Gap</div>
        <div class="tg-gap-value" style="color: ${gapColor}">
          ${gap >= 0 ? '+' : ''}${gap.toFixed(2)} ⭐
        </div>
        <div style="font-size: 13px; color: #718096;">
          Displayed: ${avgDisplayed.toFixed(1)}⭐ → True: ${avgTrue.toFixed(1)}⭐
        </div>
      </div>
      
      <div class="tg-stats">
        <div class="tg-stat">
          <div class="tg-stat-value" style="color: #48bb78">${credCounts.human}</div>
          <div class="tg-stat-label">Genuine</div>
        </div>
        <div class="tg-stat">
          <div class="tg-stat-value" style="color: #f56565">${credCounts.bot}</div>
          <div class="tg-stat-label">Suspicious</div>
        </div>
        <div class="tg-stat">
          <div class="tg-stat-value" style="color: #ed8936">${credCounts.lowEffort}</div>
          <div class="tg-stat-label">Low Effort</div>
        </div>
        <div class="tg-stat">
          <div class="tg-stat-value">${results.length}</div>
          <div class="tg-stat-label">Analyzed</div>
        </div>
      </div>

      <div class="tg-review-count">${reviewCountText}</div>
      
      <div class="tg-reviews">
        <div style="font-size: 14px; font-weight: 600; margin-bottom: 12px;">Sample Reviews</div>
        ${results.slice(0, 5).map(r => `
          <div class="tg-review ${r.credibility_label === 'bot' ? 'suspicious' : r.credibility_label === 'human' ? 'genuine' : ''}">
            <div class="tg-review-header">
              <span class="tg-review-stars">${'⭐'.repeat(r.stars)}</span>
              <span class="tg-review-badge ${r.credibility_label}">${r.credibility_label === 'low_effort' ? 'Low Effort' : r.credibility_label}</span>
            </div>
            <div class="tg-review-text">${r.text.substring(0, 150)}${r.text.length > 150 ? '...' : ''}</div>
          </div>
        `).join('')}
      </div>
      
      ${loadMoreHtml}
    `;

    // Attach load more event handler
    const loadMoreBtn = document.getElementById('tg-load-more-btn');
    if (loadMoreBtn) {
      loadMoreBtn.addEventListener('click', handleLoadMore);
    }
  }

  // Handle Load More click
  async function handleLoadMore() {
    if (isLoadingMore) return;
    isLoadingMore = true;

    const btn = document.getElementById('tg-load-more-btn');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="tg-spinner" style="width:16px;height:16px;border-width:2px;margin:0;"></span> Loading more reviews...';
    }

    try {
      // Scroll to load more content
      await scrollToLoadMore();

      // Wait for DOM to update
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Extract new reviews
      const newReviews = extractReviews();

      // Find truly new reviews (not already analyzed)
      const existingTexts = new Set(currentResults.map(r => r.text));
      const additionalReviews = newReviews.filter(r => !existingTexts.has(r.text));

      if (additionalReviews.length > 0) {
        // Analyze new reviews
        const statusEl = overlay.querySelector('.tg-content');
        const newResults = await analyzeReviews(additionalReviews);

        // Merge with existing results
        currentResults = [...currentResults, ...newResults];
        allExtractedReviews = [...allExtractedReviews, ...additionalReviews];

        // Re-render with updated results
        const pageInfo = detectPageType();
        renderResults(currentResults, pageInfo);
      } else {
        // No new reviews found
        if (btn) {
          btn.innerHTML = '✓ No more reviews found';
          btn.disabled = true;
        }
      }
    } catch (error) {
      console.error('Load more error:', error);
      if (btn) {
        btn.innerHTML = '❌ Failed to load more';
        btn.disabled = false;
      }
    } finally {
      isLoadingMore = false;
    }
  }

  // Show error
  function showError(message) {
    const content = overlay.querySelector('.tg-content');
    content.innerHTML = `
      <div class="tg-error">
        <div style="font-size: 48px; margin-bottom: 16px;">❌</div>
        <div style="font-size: 16px; margin-bottom: 8px;">Analysis Failed</div>
        <div style="font-size: 13px; color: #a0aec0;">${message}</div>
        <div style="font-size: 12px; color: #718096; margin-top: 16px;">
          Make sure the API is running at ${API_URL}
        </div>
      </div>
    `;
  }

  // Main execution
  async function run() {
    try {
      // Detect page type first
      const pageInfo = detectPageType();

      // Update status
      overlay.querySelector('.tg-status div:last-child').textContent = 'Extracting reviews...';

      const reviews = extractReviews();
      allExtractedReviews = reviews;

      if (reviews.length === 0) {
        // Show helpful message based on page type
        if (pageInfo.type === 'product' && pageInfo.reviewsUrl) {
          const content = overlay.querySelector('.tg-content');
          const totalText = pageInfo.totalReviews > 0 ? ` (${pageInfo.totalReviews.toLocaleString()} total)` : '';
          content.innerHTML = `
            <div class="tg-no-reviews">
              <div style="font-size: 48px; margin-bottom: 16px;">💡</div>
              <div style="font-size: 16px; margin-bottom: 8px;">Product Page Detected</div>
              <div style="font-size: 13px; margin-bottom: 16px;">Click below to go to the reviews page for a full analysis${totalText}.</div>
              <button class="tg-page-hint-btn" style="padding: 12px 24px; font-size: 14px;" onclick="window.location.href='${pageInfo.reviewsUrl}'">📖 View All Reviews</button>
            </div>
          `;
        } else {
          renderResults([], pageInfo);
        }
        return;
      }

      overlay.querySelector('.tg-status div:last-child').textContent = `Analyzing ${reviews.length} reviews...`;

      const results = await analyzeReviews(reviews);
      renderResults(results, pageInfo);

    } catch (error) {
      showError(error.message);
    }
  }

  run();
})();
