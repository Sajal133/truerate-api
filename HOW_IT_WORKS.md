# 🧠 How TrueRate.ai Works - Simple Guide

> This guide explains everything about TrueRate.ai as if you're explaining it to a friend who knows nothing about coding.

---

## 🎯 What Problem Does TrueRate.ai Solve?

### The Problem: Fake Reviews
Imagine you want to buy a phone on Amazon. You see it has **4.5 stars** with great reviews. You buy it, but the phone is terrible!

**Why did this happen?**
- Companies pay people to write **fake 5-star reviews**
- Some competitors write **fake 1-star reviews** to hurt products
- Many reviews are written by **bots** (computer programs), not real people

### The Solution: TrueRate.ai
TrueRate.ai is like a **lie detector for reviews**. It:
1. Reads all the reviews
2. Figures out which reviews are **real** and which are **fake**
3. Calculates the **TRUE rating** (not the fake one)
4. Shows you the **Truth Gap** (difference between fake and real rating)

---

## 🏗️ How It's Built - The Big Picture

Think of TrueRate.ai like a **factory with 4 departments**:

```
┌─────────────────────────────────────────────────────────┐
│                    TrueRate.ai                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   📱 Frontend        →    🔌 API         →    🧠 Brain   │
│   (What you see)          (The messenger)     (Analysis) │
│                                                         │
│                           ↓                             │
│                       💾 Database                        │
│                    (Memory/Storage)                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

Let me explain each part:

---

## 📱 1. The Frontend (What You See)

### Chrome Extension
This is the **button you click** when you're on Amazon.

**How it works:**
1. You visit Amazon product page
2. Click the TrueRate.ai extension icon
3. It **reads all the reviews** from the page
4. Sends them to our API for analysis
5. Shows you the results in a nice popup

**Files involved:**
- `extension/popup.html` - The design of the popup
- `extension/popup.js` - The brain of the extension
- `extension/content.js` - Reads reviews from Amazon
- `extension/styles.css` - Makes it look pretty

### Bookmarklet
Same thing, but works on ANY website (not just Amazon). It's a simple bookmark you drag to your browser.

---

## 🔌 2. The API (The Messenger)

### What is an API?
Think of an API like a **waiter in a restaurant**:
- You (the extension) tell the waiter what you want
- The waiter goes to the kitchen (the brain)
- The kitchen prepares the food (analysis)
- The waiter brings back your food (results)

### Our API
- **Lives at:** `https://web-production-ecdd.up.railway.app`
- **Built with:** FastAPI (a Python tool for building APIs)
- **Hosted on:** Railway (a cloud service)

### How it works:
```
Extension sends:     →   API receives:     →   API returns:
{                        {                      {
  "text": "Great          "Analyzing..."         "credibility": 0.85,
   product!",                                    "sentiment": +0.9,
  "stars": 5                                     "label": "human"
}                                              }
```

### API Endpoints (Menu Options):

| Endpoint | What it does | Example |
|----------|--------------|---------|
| `/analyze` | Analyzes ONE review | "Is this review fake?" |
| `/batch-analyze` | Analyzes MANY reviews at once | "Check all 50 reviews" |
| `/product-summary` | Gets overall product analysis | "What's the TRUE rating?" |
| `/feedback` | Saves user feedback | "User said our prediction was wrong" |
| `/health` | Checks if API is working | "Is the server alive?" |

---

## 🧠 3. The Brain (ML Models & Analysis)

This is where the **magic** happens! We use **4 different "detectives"** to analyze each review:

### Detective 1: Sentiment Analyzer 🎭
**Job:** Figure out if the review is POSITIVE or NEGATIVE

**How it works:**
- Uses **VADER** (a dictionary of positive/negative words)
- If unsure, uses a **trained AI model** as backup
- Returns a score from `-1` (very negative) to `+1` (very positive)

**Example:**
```
"This product is amazing!" → Score: +0.92 (Very Positive)
"Worst purchase ever!"     → Score: -0.88 (Very Negative)
"It's okay I guess"        → Score: +0.12 (Slightly Positive)
```

**File:** `execution/analyze_sentiment.py`

---

### Detective 2: Credibility Scorer 🔍
**Job:** Figure out if the review is REAL or FAKE

**How it works (checks many things):**

| Check | What it means |
|-------|---------------|
| Length | Too short = suspicious ("Great!") |
| Details | Real reviews mention specific things |
| Language | Fake reviews use generic phrases |
| Exclamation marks | "AMAZING!!!!!!" = suspicious |
| Personal pronouns | "I", "my", "we" = more likely real |
| Repetition | Same words repeated = suspicious |

**Returns:**
- Score: `0.0` (definitely fake) to `1.0` (definitely real)
- Label: `"bot"`, `"low_effort"`, or `"human"`

**Example:**
```
"Great product! Love it!"           → Score: 0.25 (bot)
"I've used this for 3 months..."    → Score: 0.85 (human)
```

**File:** `execution/score_credibility.py`

---

### Detective 3: Sarcasm Detector 🃏
**Job:** Figure out if someone is being SARCASTIC

**Why this matters:**
- "Oh wow, this phone only lasted 2 days. GREAT quality!" 
- The words sound positive, but the meaning is NEGATIVE!

**How it works:**
- Looks for patterns like:
  - "wow" + negative context
  - "thanks for nothing"
  - Extreme positive words + negative experience
  - "Oh great, another..." patterns

**File:** `execution/detect_sarcasm.py`

---

### Detective 4: Weighted Rating Calculator ⚖️
**Job:** Calculate the TRUE rating

**How it works:**
1. Takes all reviews
2. Gives MORE weight to genuine reviews
3. Gives LESS weight to fake reviews
4. Calculates the average

**Example:**
```
Review 1: 5 stars (fake, weight=0.2)
Review 2: 5 stars (real, weight=0.9)
Review 3: 3 stars (real, weight=0.85)
Review 4: 1 star (fake, weight=0.1)

Displayed Rating: (5+5+3+1)/4 = 3.5 stars
Weighted (True) Rating: (5×0.2 + 5×0.9 + 3×0.85 + 1×0.1) / (0.2+0.9+0.85+0.1)
                      = 4.07 stars

Truth Gap = 3.5 - 4.07 = -0.57 ⭐ (Product is BETTER than shown!)
```

**File:** `execution/calculate_weighted_rating.py`

---

## 🤖 4. Adaptive Learning (Getting Smarter Over Time)

### The Problem:
Sometimes our detectives make mistakes. How do we improve?

### The Solution: User Feedback!
When you see our prediction and click:
- 👍 **Agree** - We were RIGHT
- 👎 **Disagree** - We were WRONG

### How it learns:
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  User gives  │ →   │  Saved to    │ →   │  Model gets  │
│   feedback   │     │  Supabase    │     │   smarter    │
└──────────────┘     └──────────────┘     └──────────────┘
```

1. **User clicks 👎** (they disagree with our prediction)
2. **Feedback saved** to Supabase database (in the cloud)
3. **Adaptive Learner** reads all feedback
4. **Adjusts weights** - "If short review + 5 stars, more likely fake"
5. **Next time**, prediction is more accurate!

**Files:**
- `execution/adaptive_learner.py` - The learning logic
- `api/feedback_db.py` - Saves to Supabase

---

## 💾 5. Database (Memory/Storage)

### What is Supabase?
Supabase is like a **Google Sheets in the cloud** but for apps. It stores:

### Table 1: `feedback`
| Column | What it stores |
|--------|----------------|
| review_text | The review that was analyzed |
| stars | Star rating (1-5) |
| predicted_class | What we predicted (bot/human) |
| user_vote | Did user agree (1) or disagree (-1) |
| created_at | When feedback was given |

### Table 2: `weight_adjustments`
| Column | What it stores |
|--------|----------------|
| feature_name | What pattern we're tracking |
| adjustment | How much to adjust by |
| sample_count | How many times we've seen this |

**Why we need this:**
- Without database: Every time server restarts, we forget everything
- With database: We remember ALL user feedback FOREVER
- Multiple users: When User A teaches us, User B benefits too!

---

## ☁️ 6. Production Deployment (Making it Live)

### Where is everything hosted?

| Component | Where | URL |
|-----------|-------|-----|
| API | Railway | https://web-production-ecdd.up.railway.app |
| Database | Supabase | https://siithpbnuknngkqeyxui.supabase.co |
| Code | GitHub | https://github.com/Sajal133/truerate-api |

### How Railway works:
1. You **push code** to GitHub
2. Railway **detects the change**
3. Railway **automatically rebuilds** the app
4. New version is **live in 2 minutes**!

### Important files for deployment:
- `requirements.txt` - Python packages to install
- `Procfile` - How to start the server
- `railway.toml` - Railway settings

---

## 🔄 Complete Flow: From Click to Result

Let's trace what happens when you analyze a product:

```
Step 1: USER clicks extension on Amazon
        ↓
Step 2: EXTENSION reads all reviews from page
        ↓
Step 3: EXTENSION sends reviews to API
        Request: POST /batch-analyze
        Body: { reviews: [...50 reviews...] }
        ↓
Step 4: API receives reviews
        ↓
Step 5: For EACH review, API calls:
        ├─→ Sentiment Analyzer (happy or sad?)
        ├─→ Credibility Scorer (real or fake?)
        ├─→ Sarcasm Detector (joking?)
        └─→ Weighted Rating Calculator (adjust score)
        ↓
Step 6: API combines all results
        ↓
Step 7: API calculates:
        ├─→ Displayed Rating (4.5 stars)
        ├─→ True Rating (3.8 stars)
        └─→ Truth Gap (-0.7 stars)
        ↓
Step 8: API sends response back
        {
          "displayed_rating": 4.5,
          "true_rating": 3.8,
          "truth_gap": -0.7,
          "reviews_analyzed": 50,
          "genuine_count": 32,
          "suspicious_count": 18
        }
        ↓
Step 9: EXTENSION displays beautiful results to user!
```

---

## 📊 Understanding the Scores

### Credibility Score (0.0 to 1.0)
| Score | Label | What it means |
|-------|-------|---------------|
| 0.0 - 0.3 | 🤖 Bot | Almost certainly fake/automated |
| 0.3 - 0.6 | 😐 Low Effort | Suspicious, generic, or lazy |
| 0.6 - 1.0 | 👤 Human | Likely a real person |

### Sentiment Score (-1.0 to +1.0)
| Score | Meaning |
|-------|---------|
| -1.0 to -0.5 | Very Negative 😠 |
| -0.5 to -0.1 | Somewhat Negative 😕 |
| -0.1 to +0.1 | Neutral 😐 |
| +0.1 to +0.5 | Somewhat Positive 🙂 |
| +0.5 to +1.0 | Very Positive 😃 |

### Truth Gap
| Gap | Color | Meaning |
|-----|-------|---------|
| > +0.5 | 🔴 Red | Product is WORSE than shown |
| -0.5 to +0.5 | 🟡 Yellow | Rating is fairly accurate |
| < -0.5 | 🟢 Green | Product is BETTER than shown |

---

## 🗂️ File Structure Summary

```
TrueRate.ai/
│
├── 📱 extension/           ← Chrome extension (what user sees)
│   ├── manifest.json       ← Extension settings
│   ├── popup.html          ← Popup design
│   ├── popup.js            ← Popup logic
│   ├── content.js          ← Reads Amazon pages
│   └── styles.css          ← Makes it pretty
│
├── 🔌 api/                 ← The messenger (API)
│   ├── main.py             ← All API endpoints
│   └── feedback_db.py      ← Supabase connection
│
├── 🧠 execution/           ← The brain (ML models)
│   ├── analyze_sentiment.py    ← Happy or sad?
│   ├── score_credibility.py    ← Real or fake?
│   ├── detect_sarcasm.py       ← Joking?
│   ├── calculate_weighted_rating.py ← True rating
│   └── adaptive_learner.py     ← Gets smarter
│
├── 📑 bookmarklet/         ← Works on any website
│   ├── index.html          ← Install page
│   └── truth-gap-bookmarklet.js ← Bookmarklet code
│
└── 🖥️ frontend/            ← Demo web app
    └── src/App.jsx         ← React app
```

---

## 🔑 Key Technologies Used

| Technology | What it does | Why we use it |
|------------|--------------|---------------|
| **Python** | Main programming language | Easy to write, great for ML |
| **FastAPI** | Builds the API | Super fast, auto-generates docs |
| **VADER** | Sentiment analysis | Works without training |
| **Supabase** | Database | Free, easy, cloud-hosted |
| **Railway** | Hosts the API | Auto-deploys from GitHub |
| **Chrome Extension** | Browser plugin | Works directly on Amazon |
| **JavaScript** | Extension language | Runs in browsers |

---

## 🎓 Summary: How TrueRate.ai Works

1. **You click** the extension on a product page
2. **Extension reads** all the reviews
3. **Reviews sent** to our API (on Railway cloud)
4. **4 Detectives** analyze each review:
   - Is it positive or negative?
   - Is it real or fake?
   - Is it sarcastic?
   - What weight should it have?
5. **True Rating** calculated from weighted scores
6. **Truth Gap** shown = Displayed Rating - True Rating
7. **You give feedback** (agree/disagree)
8. **System learns** and improves for next time!

---

## 🚀 Live URLs

| What | URL |
|------|-----|
| API | https://web-production-ecdd.up.railway.app |
| API Docs | https://web-production-ecdd.up.railway.app/docs |
| GitHub Code | https://github.com/Sajal133/truerate-api |

---

*Made with ❤️ by Sajal - TrueRate.ai*
