import { useState, useEffect } from 'react'
import './App.css'

const API_URL = 'https://web-production-ecdd.up.railway.app'

function App() {
  // Tab state
  const [activeTab, setActiveTab] = useState('url') // 'review', 'product', or 'url'

  // Single review state
  const [reviewText, setReviewText] = useState('')
  const [stars, setStars] = useState(5)
  const [result, setResult] = useState(null)

  // Product analysis state
  const [productId, setProductId] = useState('')
  const [products, setProducts] = useState([])
  const [productResult, setProductResult] = useState(null)
  const [datasetStats, setDatasetStats] = useState(null)

  // Shared state
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // URL analysis state
  const [amazonUrl, setAmazonUrl] = useState('')
  const [urlResult, setUrlResult] = useState(null)
  const [scrapingStatus, setScrapingStatus] = useState(null)

  // Load available products on mount
  useEffect(() => {
    if (activeTab === 'product') {
      loadProducts()
    }
  }, [activeTab])

  const loadProducts = async () => {
    try {
      const response = await fetch(`${API_URL}/products?limit=30`)
      if (response.ok) {
        const data = await response.json()
        setProducts(data.products || [])
        setDatasetStats(data.dataset_stats || null)
      }
    } catch (err) {
      console.error('Failed to load products:', err)
    }
  }

  const analyzeReview = async () => {
    if (!reviewText.trim()) {
      setError('Please enter review text')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: reviewText, stars })
      })

      if (!response.ok) throw new Error('API request failed')

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError('Failed to analyze. Make sure the API is running on port 8000.')
    } finally {
      setLoading(false)
    }
  }

  const analyzeProduct = async () => {
    if (!productId.trim()) {
      setError('Please enter or select a product ID')
      return
    }

    setLoading(true)
    setError(null)
    setProductResult(null)

    try {
      const response = await fetch(`${API_URL}/analyze/product`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: productId, max_reviews: 100 })
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || 'Product not found')
      }

      const data = await response.json()
      setProductResult(data)
    } catch (err) {
      setError(err.message || 'Failed to analyze product')
    } finally {
      setLoading(false)
    }
  }

  const analyzeUrl = async () => {
    if (!amazonUrl.trim()) {
      setError('Please enter an Amazon product URL')
      return
    }

    setLoading(true)
    setError(null)
    setUrlResult(null)
    setScrapingStatus('Extracting product info...')

    try {
      // First request to get the review URL
      const initResponse = await fetch(`${API_URL}/analyze/url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: amazonUrl })
      })

      const initData = await initResponse.json()

      if (initData.status === 'pending_html') {
        // We need to fetch the HTML from the review page
        setScrapingStatus(`Scraping reviews from ${initData.domain}...`)

        // Use a CORS proxy or fetch directly (may fail due to CORS)
        try {
          // Try fetching through a CORS proxy
          const proxyUrl = `https://api.allorigins.win/raw?url=${encodeURIComponent(initData.review_url)}`
          const htmlResponse = await fetch(proxyUrl)
          const html = await htmlResponse.text()

          setScrapingStatus('Analyzing reviews...')

          // Resubmit with HTML
          const finalResponse = await fetch(`${API_URL}/analyze/url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              url: amazonUrl,
              html_content: html,
              max_reviews: 50
            })
          })

          const finalData = await finalResponse.json()

          if (finalData.error || finalData.status === 'pending_html') {
            throw new Error('Could not parse reviews from page. Amazon may be blocking the request.')
          }

          setUrlResult(finalData)
        } catch (proxyError) {
          // Proxy failed, show manual instructions
          setUrlResult({
            ...initData,
            manual_mode: true,
            instructions: 'Direct scraping blocked. Try copying the page HTML manually.'
          })
        }
      } else if (initData.error) {
        throw new Error(initData.error || initData.detail)
      } else {
        setUrlResult(initData)
      }
    } catch (err) {
      setError(err.message || 'Failed to analyze URL')
    } finally {
      setLoading(false)
      setScrapingStatus(null)
    }
  }

  const getCredibilityColor = (score) => {
    if (score >= 0.7) return '#10b981'
    if (score >= 0.4) return '#f59e0b'
    return '#ef4444'
  }

  const getRatingColor = (delta) => {
    if (delta > 0.5) return '#10b981'
    if (delta < -0.5) return '#ef4444'
    return '#6b7280'
  }

  const getTruthGapColor = (gap) => {
    if (gap >= 0) return '#10b981' // Positive = underrated
    if (gap <= -0.5) return '#ef4444' // Negative = overrated
    return '#f59e0b'
  }

  return (
    <div className="app">
      <header className="header">
        <h1>🔍 TrueRate.ai</h1>
        <p>Uncover the real story behind product reviews</p>
      </header>

      {/* Tab Navigation */}
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'product' ? 'active' : ''}`}
          onClick={() => setActiveTab('product')}
        >
          📦 Product Analysis
        </button>
        <button
          className={`tab ${activeTab === 'review' ? 'active' : ''}`}
          onClick={() => setActiveTab('review')}
        >
          📝 Single Review
        </button>
        <button
          className={`tab ${activeTab === 'url' ? 'active' : ''}`}
          onClick={() => setActiveTab('url')}
        >
          🌐 Live URL
        </button>
      </div>

      <main className="main">
        {/* Product Analysis Tab */}
        {activeTab === 'product' && (
          <>
            <section className="input-section">
              <h2>Analyze a Product</h2>
              <p className="subtitle">Enter a product ID or select from available products</p>

              <div className="form-group">
                <label>Product ID (Amazon ASIN)</label>
                <input
                  type="text"
                  value={productId}
                  onChange={(e) => setProductId(e.target.value)}
                  placeholder="e.g., B00001P4ZH"
                />
              </div>

              <button
                onClick={analyzeProduct}
                disabled={loading}
                className="analyze-btn"
              >
                {loading ? '⏳ Analyzing Product...' : '🔍 Analyze Product Reviews'}
              </button>

              {error && <div className="error">{error}</div>}

              {/* Available Products */}
              {products.length > 0 && (
                <div className="products-list">
                  <h3>Available Products ({datasetStats?.total_products?.toLocaleString() || 'Loading...'} total)</h3>
                  <div className="products-grid">
                    {products.map((p, i) => (
                      <button
                        key={i}
                        className="product-btn"
                        onClick={() => setProductId(p.asin)}
                      >
                        <span className="product-asin">{p.asin}</span>
                        <span className="product-count">{p.review_count} reviews</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </section>

            {/* Product Analysis Results */}
            {productResult && (
              <section className="results-section product-results">
                <h2>Product Analysis: {productResult.product_id}</h2>

                <div className="truth-gap-hero">
                  <div className="rating-comparison">
                    <div className="rating-box original">
                      <span className="label">Displayed Rating</span>
                      <span className="value">{productResult.original_average} ⭐</span>
                    </div>
                    <div className="arrow">→</div>
                    <div className="rating-box adjusted">
                      <span className="label">True Rating</span>
                      <span className="value" style={{ color: getTruthGapColor(productResult.truth_gap) }}>
                        {productResult.adjusted_average} ⭐
                      </span>
                    </div>
                  </div>
                  <div
                    className="truth-gap-badge"
                    style={{ backgroundColor: getTruthGapColor(productResult.truth_gap) }}
                  >
                    Truth Gap: {productResult.truth_gap >= 0 ? '+' : ''}{productResult.truth_gap}
                  </div>
                </div>

                <div className="results-grid">
                  {/* Stats Card */}
                  <div className="card">
                    <h3>📊 Review Statistics</h3>
                    <div className="metric">
                      <span className="label">Total Reviews Analyzed</span>
                      <span className="value">{productResult.review_count}</span>
                    </div>
                    <div className="metric">
                      <span className="label">Bot/Spam Reviews</span>
                      <span className="value negative">{productResult.bot_percentage}%</span>
                    </div>
                  </div>

                  {/* Credibility Distribution */}
                  <div className="card">
                    <h3>🛡️ Review Quality</h3>
                    <div className="distribution-bars">
                      <div className="bar-item">
                        <span className="bar-label">✅ Human</span>
                        <div className="bar-container">
                          <div
                            className="bar human"
                            style={{ width: `${productResult.credibility_distribution.human}%` }}
                          ></div>
                        </div>
                        <span className="bar-value">{productResult.credibility_distribution.human}%</span>
                      </div>
                      <div className="bar-item">
                        <span className="bar-label">😐 Low Effort</span>
                        <div className="bar-container">
                          <div
                            className="bar low-effort"
                            style={{ width: `${productResult.credibility_distribution.low_effort}%` }}
                          ></div>
                        </div>
                        <span className="bar-value">{productResult.credibility_distribution.low_effort}%</span>
                      </div>
                      <div className="bar-item">
                        <span className="bar-label">🤖 Bot/Spam</span>
                        <div className="bar-container">
                          <div
                            className="bar bot"
                            style={{ width: `${productResult.credibility_distribution.bot}%` }}
                          ></div>
                        </div>
                        <span className="bar-value">{productResult.credibility_distribution.bot}%</span>
                      </div>
                    </div>
                  </div>

                  {/* Rating Distribution */}
                  <div className="card">
                    <h3>⭐ Star Distribution</h3>
                    <div className="star-distribution">
                      {[5, 4, 3, 2, 1].map(star => {
                        const count = productResult.rating_distribution[star] || 0
                        const pct = (count / productResult.review_count * 100).toFixed(0)
                        return (
                          <div key={star} className="star-row">
                            <span className="star-label">{star}★</span>
                            <div className="star-bar-container">
                              <div className="star-bar" style={{ width: `${pct}%` }}></div>
                            </div>
                            <span className="star-count">{count}</span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>

                {/* Sample Reviews */}
                <div className="sample-reviews">
                  <h3>📝 Sample Reviews</h3>
                  <div className="reviews-list">
                    {productResult.sample_reviews.map((r, i) => (
                      <div key={i} className={`review-item ${r.credibility}`}>
                        <div className="review-header">
                          <span className="review-stars">{r.original_stars}★</span>
                          <span className="review-adjusted">→ {r.adjusted_rating.toFixed(1)}★</span>
                          <span className={`review-badge ${r.credibility}`}>
                            {r.credibility === 'human' && '✅ Human'}
                            {r.credibility === 'low_effort' && '😐 Low Effort'}
                            {r.credibility === 'bot' && '🤖 Bot'}
                          </span>
                          {r.is_sarcastic && <span className="sarcasm-badge">😏 Sarcasm</span>}
                        </div>
                        <p className="review-text">{r.text_preview}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            )}
          </>
        )}

        {/* Single Review Tab */}
        {activeTab === 'review' && (
          <>
            <section className="input-section">
              <h2>Analyze a Review</h2>

              <div className="form-group">
                <label>Review Text</label>
                <textarea
                  value={reviewText}
                  onChange={(e) => setReviewText(e.target.value)}
                  placeholder="Enter review text here... e.g., 'This product is amazing! The quality exceeded my expectations.'"
                  rows={4}
                />
              </div>

              <div className="form-group">
                <label>Star Rating: {stars} ⭐</label>
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={stars}
                  onChange={(e) => setStars(Number(e.target.value))}
                />
                <div className="star-labels">
                  <span>1</span>
                  <span>2</span>
                  <span>3</span>
                  <span>4</span>
                  <span>5</span>
                </div>
              </div>

              <button
                onClick={analyzeReview}
                disabled={loading}
                className="analyze-btn"
              >
                {loading ? '⏳ Analyzing...' : '🔍 Analyze Review'}
              </button>

              {error && <div className="error">{error}</div>}
            </section>

            {result && (
              <section className="results-section">
                <h2>Analysis Results</h2>

                <div className="results-grid">
                  {/* Rating Card */}
                  <div className="card rating-card">
                    <h3>Rating Adjustment</h3>
                    <div className="rating-display">
                      <div className="original">
                        <span className="label">Original</span>
                        <span className="value">{result.original_stars} ⭐</span>
                      </div>
                      <div className="arrow">→</div>
                      <div className="adjusted">
                        <span className="label">Adjusted</span>
                        <span
                          className="value"
                          style={{ color: getRatingColor(result.rating_delta) }}
                        >
                          {result.adjusted_rating} ⭐
                        </span>
                      </div>
                    </div>
                    <div
                      className="delta"
                      style={{ color: getRatingColor(result.rating_delta) }}
                    >
                      {result.rating_delta > 0 ? '+' : ''}{result.rating_delta} change
                    </div>
                  </div>

                  {/* Sentiment Card */}
                  <div className="card">
                    <h3>Sentiment Analysis</h3>
                    <div className="metric">
                      <span className="label">Score</span>
                      <span className={`value ${result.sentiment.sentiment_score >= 0 ? 'positive' : 'negative'}`}>
                        {result.sentiment.sentiment_score >= 0 ? '+' : ''}{result.sentiment.sentiment_score.toFixed(3)}
                      </span>
                    </div>
                    <div className="metric">
                      <span className="label">Confidence</span>
                      <span className="value">{(result.sentiment.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div className="metric">
                      <span className="label">Model</span>
                      <span className="value tag">{result.sentiment.model_used}</span>
                    </div>
                  </div>

                  {/* Credibility Card */}
                  <div className="card">
                    <h3>Credibility Score</h3>
                    <div className="credibility-score" style={{ borderColor: getCredibilityColor(result.credibility.score) }}>
                      <span
                        className="score-value"
                        style={{ color: getCredibilityColor(result.credibility.score) }}
                      >
                        {(result.credibility.score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className={`classification ${result.credibility.classification}`}>
                      {result.credibility.classification === 'bot' && '🤖 Bot/Spam'}
                      {result.credibility.classification === 'low_effort' && '😐 Low Effort'}
                      {result.credibility.classification === 'human' && '✅ Human'}
                    </div>
                    {result.credibility.flags.length > 0 && (
                      <div className="flags">
                        {result.credibility.flags.map((flag, i) => (
                          <span key={i} className="flag">{flag}</span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Sarcasm Card */}
                  <div className={`card ${result.sarcasm.is_sarcastic ? 'sarcasm-detected' : ''}`}>
                    <h3>Sarcasm Detection</h3>
                    <div className={`sarcasm-badge ${result.sarcasm.is_sarcastic ? 'detected' : 'not-detected'}`}>
                      {result.sarcasm.is_sarcastic ? '😏 Sarcasm Detected!' : '✓ No Sarcasm'}
                    </div>
                    <div className="metric">
                      <span className="label">Confidence</span>
                      <span className="value">{(result.sarcasm.confidence * 100).toFixed(0)}%</span>
                    </div>
                    {result.sarcasm.triggers.length > 0 && (
                      <div className="triggers">
                        <span className="label">Triggers:</span>
                        {result.sarcasm.triggers.map((trigger, i) => (
                          <span key={i} className="trigger">{trigger}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </section>
            )}

            {/* Example Reviews */}
            <section className="examples-section">
              <h2>Try These Examples</h2>
              <div className="examples">
                {[
                  { text: "Great!", stars: 5, label: "Generic Bot" },
                  { text: "Oh great, another phone that broke after 2 days. Thanks for nothing.", stars: 5, label: "Sarcastic" },
                  { text: "This phone exceeded my expectations. The camera quality is stunning, battery lasts all day.", stars: 5, label: "Genuine" },
                  { text: "Haven't opened it yet but giving 5 stars!", stars: 5, label: "Not Used" }
                ].map((example, i) => (
                  <button
                    key={i}
                    className="example-btn"
                    onClick={() => { setReviewText(example.text); setStars(example.stars); }}
                  >
                    <span className="example-label">{example.label}</span>
                    <span className="example-text">{example.text.substring(0, 40)}...</span>
                  </button>
                ))}
              </div>
            </section>
          </>
        )}
      </main>

      {/* Live URL Tab */}
      {activeTab === 'url' && (
        <main className="main">
          <section className="input-section">
            <h2>🌐 Analyze Amazon Product URL</h2>
            <p className="subtitle">Paste any Amazon product URL to analyze real reviews</p>

            <div className="form-group">
              <label>Amazon Product URL</label>
              <input
                type="url"
                value={amazonUrl}
                onChange={(e) => setAmazonUrl(e.target.value)}
                placeholder="https://amazon.com/dp/B0XXXXX or https://amazon.in/product/..."
                className="url-input"
              />
            </div>

            <button
              className="analyze-btn"
              onClick={analyzeUrl}
              disabled={loading}
            >
              {loading ? (scrapingStatus || 'Analyzing...') : '🔍 Analyze Product Reviews'}
            </button>

            {error && <div className="error">{error}</div>}
          </section>

          {/* URL Results */}
          {urlResult && !urlResult.manual_mode && (
            <section className="results-section">
              <div className="truth-gap-hero">
                <div className="product-header">
                  <h2>{urlResult.product_title || `Product: ${urlResult.asin}`}</h2>
                  <span className="domain-badge">{urlResult.domain}</span>
                </div>

                <div className="ratings-comparison">
                  <div className="rating-box">
                    <span className="rating-label">Displayed Rating</span>
                    <span className="rating-value">{urlResult.original_average?.toFixed(1)} ⭐</span>
                  </div>
                  <div className="arrow">→</div>
                  <div className="rating-box">
                    <span className="rating-label">True Rating</span>
                    <span className="rating-value">{urlResult.adjusted_average?.toFixed(1)} ⭐</span>
                  </div>
                </div>

                <div className="truth-gap-display">
                  <span>Truth Gap:</span>
                  <span
                    className="truth-gap-badge"
                    style={{ backgroundColor: getTruthGapColor(urlResult.truth_gap) }}
                  >
                    {urlResult.truth_gap > 0 ? '+' : ''}{urlResult.truth_gap?.toFixed(2)}
                  </span>
                </div>
              </div>

              <div className="stats-grid">
                <div className="stat-card">
                  <h3>📊 Review Statistics</h3>
                  <div className="stat-row">
                    <span>Total Reviews Analyzed</span>
                    <span className="stat-value">{urlResult.review_count}</span>
                  </div>
                  <div className="stat-row">
                    <span>Bot/Spam Reviews</span>
                    <span className="stat-value" style={{ color: '#ef4444' }}>
                      {urlResult.bot_percentage?.toFixed(0)}%
                    </span>
                  </div>
                </div>

                <div className="stat-card">
                  <h3>🎯 Review Quality</h3>
                  {urlResult.credibility_distribution && Object.entries(urlResult.credibility_distribution).map(([key, val]) => (
                    <div key={key} className="bar-item">
                      <span className="bar-label">
                        {key === 'human' ? '✅ Human' : key === 'low_effort' ? '😐 Low Effort' : '🤖 Bot/Spam'}
                      </span>
                      <div className="bar-track">
                        <div
                          className="bar-fill"
                          style={{
                            width: `${val}%`,
                            backgroundColor: key === 'human' ? '#10b981' : key === 'low_effort' ? '#f59e0b' : '#ef4444'
                          }}
                        />
                      </div>
                      <span className="bar-value">{val?.toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Sample Reviews */}
              {urlResult.sample_reviews?.length > 0 && (
                <div className="stat-card">
                  <h3>📝 Sample Reviews</h3>
                  <div className="sample-reviews">
                    {urlResult.sample_reviews.slice(0, 5).map((review, i) => (
                      <div key={i} className="sample-review">
                        <div className="review-header">
                          <span className="stars">{'⭐'.repeat(review.original_stars)}</span>
                          <span className="arrow">→</span>
                          <span className="adjusted">{review.adjusted_rating}⭐</span>
                          <span className={`cred-badge ${review.credibility}`}>{review.credibility}</span>
                          {review.verified && <span className="verified-badge">✓ Verified</span>}
                          {review.is_sarcastic && <span className="sarcasm-badge">🎭 Sarcasm</span>}
                        </div>
                        {review.title && <div className="review-title">{review.title}</div>}
                        <p className="review-text">{review.text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}

          {/* Manual mode fallback */}
          {urlResult?.manual_mode && (
            <section className="results-section">
              <div className="manual-mode-notice">
                <h3>⚠️ Direct Scraping Blocked</h3>
                <p>Amazon is blocking automated requests. You can still analyze this product:</p>
                <ol>
                  <li>Open this URL in your browser: <a href={urlResult.review_url} target="_blank" rel="noopener noreferrer">{urlResult.review_url}</a></li>
                  <li>Copy the page HTML (Ctrl+U or View Source)</li>
                  <li>Use the Product Analysis tab with ASIN: <strong>{urlResult.asin}</strong></li>
                </ol>
              </div>
            </section>
          )}

          {/* Example URLs */}
          <section className="examples-section">
            <h2>Try These Example URLs</h2>
            <div className="examples">
              {[
                { url: 'https://www.amazon.com/dp/B0BTZT4GKZ', label: 'Fire TV Stick' },
                { url: 'https://www.amazon.in/dp/B09V3KXJPB', label: 'Echo Dot' },
                { url: 'https://www.amazon.com/dp/B08N5WRWNW', label: 'Apple AirPods' }
              ].map((example, i) => (
                <button
                  key={i}
                  className="example-btn"
                  onClick={() => setAmazonUrl(example.url)}
                >
                  <span className="example-label">{example.label}</span>
                  <span className="example-text">{example.url.substring(0, 35)}...</span>
                </button>
              ))}
            </div>
          </section>
        </main>
      )}

      <footer className="footer">
        <p>TrueRate.ai • 20/80 Star-Sentiment Fusion • $0 Cost</p>
      </footer>
    </div>
  )
}

export default App
