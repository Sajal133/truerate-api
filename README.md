# TrueRate.ai

**AI-powered review analysis platform that detects fake reviews and calculates the true rating of products.**

## 🚀 Live Demo

- **API**: https://web-production-ecdd.up.railway.app
- **API Docs**: https://web-production-ecdd.up.railway.app/docs

## 📁 Project Structure

```
TrueRate.ai/
├── api/                    # FastAPI backend
│   ├── main.py            # API endpoints
│   └── feedback_db.py     # Supabase feedback storage
├── extension/             # Chrome extension
│   ├── manifest.json      # Extension config
│   ├── popup.html/js/css  # Extension UI
│   └── content.js         # Review extraction
├── execution/             # Analysis modules
│   ├── analyze_sentiment.py
│   ├── score_credibility.py
│   ├── detect_sarcasm.py
│   ├── calculate_weighted_rating.py
│   └── adaptive_learner.py
├── bookmarklet/           # Bookmarklet version
│   ├── index.html         # Install page
│   └── truth-gap-bookmarklet.js
├── frontend/              # React demo app (optional)
└── requirements.txt       # Python dependencies
```

## 🔧 Installation

### Chrome Extension (For Users)

1. Download or clone this repo
2. Open `chrome://extensions/`
3. Enable "Developer mode"
4. Click "Load unpacked" → Select `extension/` folder
5. Pin the extension and use on Amazon product pages

### API (For Developers)

```bash
# Clone repo
git clone https://github.com/Sajal133/truerate-api.git
cd truerate-api

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SUPABASE_URL="your-supabase-url"
export SUPABASE_KEY="your-supabase-key"

# Run locally
uvicorn api.main:app --reload
```

## 🎯 Features

- **Truth Gap Analysis**: Shows difference between displayed and true rating
- **Fake Review Detection**: Identifies bot/low-effort/genuine reviews
- **Sentiment Analysis**: Analyzes review text sentiment
- **Sarcasm Detection**: Catches sarcastic negative reviews
- **User Feedback**: Learns from user corrections (👍/👎)

## 📊 How It Works

1. **Extract Reviews**: Content script scrapes reviews from Amazon
2. **Analyze Each Review**:
   - Sentiment score (positive/negative)
   - Credibility score (genuine/fake)
   - Sarcasm detection
3. **Calculate True Rating**: 20/80 weighted (stars/sentiment)
4. **Display Truth Gap**: Shows adjusted rating vs displayed

## 🔗 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/analyze/reviews` | POST | Analyze reviews |
| `/analyze/product` | POST | Full product analysis |
| `/feedback` | POST | Submit user feedback |
| `/feedback/stats` | GET | View feedback statistics |

## 📝 License

MIT License

## 👤 Author

Sajal Kumar - [@Sajal133](https://github.com/Sajal133)
