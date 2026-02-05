/**
 * TrueRate.ai - Extension Popup Script
 */

// Configuration
const API_URL = 'https://web-production-ecdd.up.railway.app';

// State
let currentResults = [];
let pageInfo = null;
let isLoading = false;

// DOM Elements
const elements = {
    initialState: document.getElementById('initial-state'),
    loadingState: document.getElementById('loading-state'),
    resultsState: document.getElementById('results-state'),
    errorState: document.getElementById('error-state'),
    noReviewsState: document.getElementById('no-reviews-state'),
    analyzeBtn: document.getElementById('analyze-btn'),
    retryBtn: document.getElementById('retry-btn'),
    loadMoreBtn: document.getElementById('load-more-btn'),
    seeReviewsBtn: document.getElementById('see-reviews-btn'),
    loadingText: document.getElementById('loading-text'),
    errorMessage: document.getElementById('error-message'),
    noReviewsHint: document.getElementById('no-reviews-hint'),
    pageHint: document.getElementById('page-hint'),
    gapValue: document.getElementById('gap-value'),
    gapSubtitle: document.getElementById('gap-subtitle'),
    genuineCount: document.getElementById('genuine-count'),
    suspiciousCount: document.getElementById('suspicious-count'),
    lowEffortCount: document.getElementById('low-effort-count'),
    totalCount: document.getElementById('total-count'),
    reviewCount: document.getElementById('review-count'),
    reviewsList: document.getElementById('reviews-list'),
    overallFeedback: document.getElementById('overall-feedback'),
    overallLikeBtn: document.getElementById('overall-like-btn'),
    overallDislikeBtn: document.getElementById('overall-dislike-btn')
};

// Store current analysis data for feedback
let currentAnalysisData = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    elements.analyzeBtn.addEventListener('click', handleAnalyze);
    elements.retryBtn.addEventListener('click', handleAnalyze);
    elements.loadMoreBtn.addEventListener('click', handleLoadMore);

    // Overall feedback buttons
    elements.overallLikeBtn?.addEventListener('click', () => handleOverallFeedback(1));
    elements.overallDislikeBtn?.addEventListener('click', () => handleOverallFeedback(-1));
});

// Show a specific state
function showState(stateName) {
    const states = ['initial', 'loading', 'results', 'error', 'noReviews'];
    states.forEach(s => {
        const el = document.getElementById(`${s === 'noReviews' ? 'no-reviews' : s}-state`);
        if (el) el.classList.toggle('hidden', s !== stateName);
    });
}

// Set loading text
function setLoadingText(text) {
    elements.loadingText.textContent = text;
}

// Handle analyze button click
async function handleAnalyze() {
    if (isLoading) return;
    isLoading = true;

    showState('loading');
    setLoadingText('Extracting reviews...');

    try {
        // Get the active tab
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

        // First, try to inject the content script programmatically
        // This handles pages that were opened before the extension was installed
        try {
            await chrome.scripting.executeScript({
                target: { tabId: tab.id },
                files: ['content.js']
            });
        } catch (injectionError) {
            // Script may already be injected, that's fine
            console.log('Script injection note:', injectionError.message);
        }

        // Wait a moment for the script to load
        await new Promise(resolve => setTimeout(resolve, 100));

        // Send message to content script to extract reviews
        let response;
        try {
            response = await chrome.tabs.sendMessage(tab.id, { action: 'extractReviews' });
        } catch (msgError) {
            throw new Error('Could not connect to page. Please refresh the page and try again.');
        }

        if (!response || response.error) {
            throw new Error(response?.error || 'Failed to extract reviews');
        }

        const { reviews, pageInfo: info } = response;
        pageInfo = info;

        if (reviews.length === 0) {
            handleNoReviews();
            return;
        }

        setLoadingText(`Analyzing ${reviews.length} reviews...`);

        // Analyze reviews via API
        const results = await analyzeReviews(reviews);
        currentResults = results;

        if (results.length === 0) {
            throw new Error('API analysis failed. Make sure the API is running at localhost:8000');
        }

        renderResults(results);
        showState('results');

    } catch (error) {
        console.error('Analysis error:', error);
        elements.errorMessage.textContent = error.message || 'Unknown error occurred';
        showState('error');
    } finally {
        isLoading = false;
    }
}

// Handle no reviews found
function handleNoReviews() {
    if (pageInfo?.type === 'product' && pageInfo?.reviewsUrl) {
        elements.noReviewsHint.textContent = `Click below to go to the reviews page for a full analysis.`;
        elements.seeReviewsBtn.classList.remove('hidden');
        elements.seeReviewsBtn.onclick = () => {
            chrome.tabs.update({ url: pageInfo.reviewsUrl });
            window.close();
        };
    } else {
        elements.noReviewsHint.textContent = 'Navigate to a product page with reviews and try again.';
        elements.seeReviewsBtn.classList.add('hidden');
    }
    showState('noReviews');
    isLoading = false;
}

// Analyze reviews via API
async function analyzeReviews(reviews) {
    const results = [];

    for (const review of reviews.slice(0, 20)) {
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
                results.push({
                    ...review,
                    weighted_rating: data.adjusted_rating,
                    credibility_label: data.credibility?.classification || 'unknown',
                    credibility_score: data.credibility?.score || 0,
                    is_sarcastic: data.sarcasm?.is_sarcastic || false
                });
            }
        } catch (e) {
            console.error('API error:', e);
        }
    }

    return results;
}

// Calculate truth gap
function calculateTruthGap(results, displayedRating = null) {
    if (results.length === 0) return { gap: 0, avgDisplayed: 0, avgTrue: 0 };

    // Use Amazon's actual displayed rating if available, otherwise calculate from reviews
    const avgDisplayed = displayedRating || (results.reduce((sum, r) => sum + r.stars, 0) / results.length);
    const avgTrue = results.reduce((sum, r) => sum + (r.weighted_rating || r.stars), 0) / results.length;

    return {
        gap: avgDisplayed - avgTrue,
        avgDisplayed,
        avgTrue
    };
}

// Render results
function renderResults(results) {
    showState('results');

    // Use Amazon's actual displayed rating from pageInfo
    const displayedRating = pageInfo?.displayedRating || null;
    const { gap, avgDisplayed, avgTrue } = calculateTruthGap(results, displayedRating);

    // Store analysis data for overall feedback
    currentAnalysisData = {
        gap: gap,
        avgDisplayed: avgDisplayed,
        avgTrue: avgTrue,
        reviewCount: results.length,
        site: pageInfo?.site || 'unknown'
    };

    // Reset overall feedback UI
    if (elements.overallFeedback) {
        elements.overallFeedback.innerHTML = `
            <span class="feedback-prompt">Was this analysis helpful?</span>
            <button id="overall-like-btn" class="overall-feedback-btn like" title="Helpful">👍</button>
            <button id="overall-dislike-btn" class="overall-feedback-btn dislike" title="Not helpful">👎</button>
        `;
        document.getElementById('overall-like-btn')?.addEventListener('click', () => handleOverallFeedback(1));
        document.getElementById('overall-dislike-btn')?.addEventListener('click', () => handleOverallFeedback(-1));
    }

    // Truth Gap value and color
    const gapClass = gap > 0.5 ? 'positive' : gap < -0.5 ? 'negative' : 'neutral';
    elements.gapValue.textContent = `${gap >= 0 ? '+' : ''}${gap.toFixed(2)} ⭐`;
    elements.gapValue.className = `gap-value ${gapClass}`;
    elements.gapSubtitle.textContent = `Displayed: ${avgDisplayed.toFixed(1)}⭐ → True: ${avgTrue.toFixed(1)}⭐`;

    // Stats
    const credCounts = {
        human: results.filter(r => r.credibility_label === 'human').length,
        bot: results.filter(r => r.credibility_label === 'bot').length,
        lowEffort: results.filter(r => r.credibility_label === 'low_effort').length
    };

    elements.genuineCount.textContent = credCounts.human;
    elements.suspiciousCount.textContent = credCounts.bot;
    elements.lowEffortCount.textContent = credCounts.lowEffort;
    elements.totalCount.textContent = results.length;

    // Review count text
    const reviewCountText = pageInfo?.totalReviews > 0
        ? `Analyzed ${results.length} of ~${pageInfo.totalReviews.toLocaleString()} reviews`
        : `Analyzed ${results.length} reviews on this page`;
    elements.reviewCount.textContent = reviewCountText;

    // Page hint
    renderPageHint();

    // Sample reviews
    renderReviewsList(results);

    // Hide load more button - all visible reviews are extracted on first load
    // For more reviews, user should navigate to reviews page manually
    elements.loadMoreBtn.classList.add('hidden');
}

// Render page hint banner
function renderPageHint() {
    if (!pageInfo) {
        elements.pageHint.classList.add('hidden');
        return;
    }

    if (pageInfo.type === 'product' && pageInfo.reviewsUrl) {
        const totalText = pageInfo.totalReviews > 0 ? ` (${pageInfo.totalReviews.toLocaleString()} total)` : '';
        elements.pageHint.innerHTML = `
      <span class="page-hint-icon">💡</span>
      <span class="page-hint-text">You're on a product page. View all reviews for a more complete analysis${totalText}.</span>
      <button class="page-hint-btn" id="hint-see-reviews">See All Reviews</button>
    `;
        elements.pageHint.classList.remove('hidden');

        document.getElementById('hint-see-reviews').onclick = () => {
            chrome.tabs.update({ url: pageInfo.reviewsUrl });
            window.close();
        };
    } else if (pageInfo.type === 'reviews' && pageInfo.hasMorePages) {
        elements.pageHint.innerHTML = `
      <span class="page-hint-icon">📄</span>
      <span class="page-hint-text">More review pages available. Click Load More to analyze additional reviews.</span>
    `;
        elements.pageHint.classList.remove('hidden');
    } else {
        elements.pageHint.classList.add('hidden');
    }
}

// Render reviews list with feedback buttons on sample
function renderReviewsList(results) {
    const reviewsHtml = results.slice(0, 5).map((r, index) => {
        const cardClass = r.credibility_label === 'bot' ? 'suspicious' :
            r.credibility_label === 'human' ? 'genuine' : '';
        const badgeText = r.credibility_label === 'low_effort' ? 'Low Effort' : r.credibility_label;

        // Only show feedback buttons on first 2 reviews
        const showFeedback = index < 2;
        const feedbackHtml = showFeedback ? `
          <div class="feedback-row" data-index="${index}">
            <span class="feedback-label">Is this correct?</span>
            <button class="feedback-btn agree" data-vote="1" data-index="${index}" title="Yes, correct">👍</button>
            <button class="feedback-btn disagree" data-vote="-1" data-index="${index}" title="No, wrong">👎</button>
          </div>
        ` : '';

        return `
      <div class="review-card ${cardClass}" data-index="${index}">
        <div class="review-header">
          <span class="review-stars">${'⭐'.repeat(r.stars)}</span>
          <span class="review-badge ${r.credibility_label}">${badgeText}</span>
        </div>
        <div class="review-text">${r.text.substring(0, 150)}${r.text.length > 150 ? '...' : ''}</div>
        ${feedbackHtml}
      </div>
    `;
    }).join('');

    elements.reviewsList.innerHTML = reviewsHtml;

    // Add event listeners for feedback buttons
    document.querySelectorAll('.feedback-btn').forEach(btn => {
        btn.addEventListener('click', handleFeedbackClick);
    });
}

// Handle feedback button click
async function handleFeedbackClick(event) {
    const btn = event.target;
    const vote = parseInt(btn.dataset.vote);
    const index = parseInt(btn.dataset.index);
    const review = currentResults[index];

    if (!review) return;

    // Disable buttons and show loading
    const feedbackRow = btn.parentElement;
    feedbackRow.innerHTML = '<span class="feedback-loading">Sending...</span>';

    try {
        const response = await fetch(`${API_URL}/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: review.text,
                stars: review.stars,
                predicted_class: review.credibility_label,
                predicted_score: review.credibility_score || null,
                user_vote: vote
            })
        });

        if (response.ok) {
            feedbackRow.innerHTML = `<span class="feedback-thanks">Thanks for the feedback! ${vote === 1 ? '✓' : '📝'}</span>`;
        } else {
            feedbackRow.innerHTML = '<span class="feedback-error">Failed to send</span>';
        }
    } catch (e) {
        console.error('Feedback error:', e);
        feedbackRow.innerHTML = '<span class="feedback-error">Connection error</span>';
    }
}

// Handle overall analysis feedback (on the Truth Gap card)
async function handleOverallFeedback(vote) {
    if (!currentAnalysisData || !elements.overallFeedback) return;

    // Show loading state
    elements.overallFeedback.innerHTML = '<span class="feedback-loading">Sending feedback...</span>';

    try {
        const response = await fetch(`${API_URL}/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: `[OVERALL_ANALYSIS] Gap: ${currentAnalysisData.gap.toFixed(2)}, Displayed: ${currentAnalysisData.avgDisplayed.toFixed(1)}, True: ${currentAnalysisData.avgTrue.toFixed(1)}`,
                stars: Math.round(currentAnalysisData.avgTrue),
                predicted_class: 'overall_analysis',
                predicted_score: currentAnalysisData.gap,
                user_vote: vote
            })
        });

        if (response.ok) {
            elements.overallFeedback.innerHTML = `<span class="overall-feedback-thanks">Thanks for the feedback! ${vote === 1 ? '✓' : '📝 We\'ll improve!'}</span>`;
        } else {
            elements.overallFeedback.innerHTML = '<span class="feedback-error">Failed to send</span>';
        }
    } catch (e) {
        console.error('Overall feedback error:', e);
        elements.overallFeedback.innerHTML = '<span class="feedback-error">Connection error</span>';
    }
}

// Handle load more
async function handleLoadMore() {
    if (isLoading) return;
    isLoading = true;

    const btn = elements.loadMoreBtn;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner" style="width:16px;height:16px;border-width:2px;margin:0;"></span> Loading...';

    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

        // Tell content script to load more
        const response = await chrome.tabs.sendMessage(tab.id, { action: 'loadMoreReviews' });

        if (response?.reviews?.length > 0) {
            // Filter out already analyzed reviews
            const existingTexts = new Set(currentResults.map(r => r.text));
            const newReviews = response.reviews.filter(r => !existingTexts.has(r.text));

            if (newReviews.length > 0) {
                const newResults = await analyzeReviews(newReviews);
                currentResults = [...currentResults, ...newResults];
                pageInfo = response.pageInfo;
                renderResults(currentResults);
            } else {
                btn.innerHTML = '✓ No more reviews found';
            }
        } else {
            btn.innerHTML = '✓ No more reviews found';
        }
    } catch (error) {
        console.error('Load more error:', error);
        btn.innerHTML = '❌ Failed to load more';
    } finally {
        isLoading = false;
        btn.disabled = false;
    }
}
