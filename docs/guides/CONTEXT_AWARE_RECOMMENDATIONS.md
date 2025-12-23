# Context-Aware Recommendation System

## 📖 Complete Guide

**Last Updated:** 2025-12-22  
**Version:** 1.0

---

## 🎯 Overview

The system uses a **hybrid approach** for intelligent stock recommendations:
- **Context**: All recent news (including yesterday's) for complete picture
- **Recommendation**: Heavily weighted (70%) toward NEW, unused articles
- **Result**: Informed decisions with fresh, actionable signals

### **Key Principle**
> **"Context from the past, recommendations for the present"**  
> 
> Like an experienced trader who knows market history but acts on breaking news.

---

## 🤔 Why This Approach?

### **The Problem with Pure Approaches**

**❌ Only NEW news (no context):**
```
Day 2: Sees only "Minor supply delay"
Missing: Strong earnings from yesterday
Result: SELL (overreaction!)
```

**❌ All news equally weighted:**
```
Day 2: 2 old positive + 2 new negative = 50/50
Result: HOLD (indecisive)
```

**✅ Context-aware (70% NEW weight):**
```
Day 2: Strong earnings [context] + supply issues [NEW 70%]
Summary: "Despite strong earnings [past], supply issues [present]..."
Result: SELL with clear reasoning
```

---

## 🔄 How It Works

### **System Flow**

```
1. User requests analysis for AAPL
   ↓
2. System fetches TWO sets of articles:
   - ALL recent articles (last 7 days) → Context
   - ONLY UNUSED articles → Recommendation focus
   ↓
3. Articles sent to LLM with markers:
   - "[NEW - BREAKING NEWS]" → Fresh developments
   - "[Previous Context]" → Background only
   ↓
4. LLM analyzes:
   - Summary: Uses ALL articles for complete picture
   - Recommendation: 70% weighted toward NEW articles
   ↓
5. Only NEW articles marked as "used"
   ↓
6. Next analysis will treat today's news as "context"
```

### **Database Tracking**

Each article tracks:
```sql
used_in_analysis BOOLEAN DEFAULT FALSE  -- Has this been analyzed?
last_used_date DATETIME NULL            -- When was it used?
used_in_recommendation_id INT NULL      -- Which recommendation used it?
```

---

## 📊 Real Example

### **Day 1: Monday - Good Earnings**

```bash
curl -X POST http://localhost:8000/api/analyze/AAPL

# System fetches:
Context articles: None (first analysis)
New articles: 
  [NEW] "AAPL beats Q3 earnings by 15%"
  [NEW] "iPhone sales exceed expectations"

# LLM sees: 2 NEW positive articles

# Analysis generated:
{
  "recommendation": "BUY",
  "confidence": "HIGH",
  "summary": "Apple reported exceptional Q3 results with earnings 
              beating expectations and strong iPhone demand...",
  "reasoning": "Strong financial performance across key metrics 
               suggests continued upward momentum..."
}

# System marks: Both articles → USED
```

### **Day 2: Tuesday - Supply Chain Issues**

```bash
curl -X POST http://localhost:8000/api/analyze/AAPL

# System fetches:
Context articles (ALL recent):
  [Previous Context] "AAPL beats Q3 earnings by 15%"
  [Previous Context] "iPhone sales exceed expectations"
  [NEW - BREAKING NEWS] "Supply chain disruption in China"
  [NEW - BREAKING NEWS] "Analyst downgrades on production concerns"

# LLM prompt includes:
"**CRITICAL INSTRUCTION:**
 - Articles marked [NEW - BREAKING NEWS] = 70% weight
 - Articles marked [Previous Context] = background only
 - Recommendation driven by NEW developments"

# LLM analyzes:
- Sees previous good news (context)
- Sees new bad news (focus)
- Weighs new news more heavily

# Analysis generated:
{
  "recommendation": "SELL",
  "confidence": "MEDIUM",
  "summary": "Despite strong Q3 earnings reported yesterday, 
              today's breaking news about supply chain disruptions 
              and analyst downgrades creates near-term concern...",
  "reasoning": "While fundamentals showed strength in recent earnings,
               TODAY's supply chain issues and production concerns 
               outweigh previous positive sentiment for short-term 
               positions. The market hasn't yet priced in these risks..."
}

# System marks: Only NEW articles → USED
# Previous context remains available for tomorrow
```

### **Day 3: Wednesday - No New News**

```bash
curl -X POST http://localhost:8000/api/analyze/AAPL

# System fetches:
Context articles (ALL recent):
  [Previous Context] "AAPL beats Q3 earnings by 15%"
  [Previous Context] "iPhone sales exceed expectations"
  [Previous Context] "Supply chain disruption in China"
  [Previous Context] "Analyst downgrades on production concerns"

New articles (UNUSED): None

# Result:
Error 400: "No new articles available for AAPL. 
            All recent news has been analyzed. 
            Check back later when new news is published."
```

---

## 🛠️ API Usage

### **Standard Analysis**

```bash
# Normal analysis (requires new news)
curl -X POST http://localhost:8000/api/analyze/AAPL | jq

# Response includes:
{
  "ticker": "AAPL",
  "recommendation": "BUY|SELL|SHORT|HOLD",
  "summary": "Context + action...",
  "reasoning": "Why this recommendation based on NEW vs old news..."
}
```

### **Check Article Status**

```bash
# See how many fresh articles available
curl http://localhost:8000/api/articles/AAPL/stats | jq

Response:
{
  "ticker": "AAPL",
  "total_articles": 25,
  "used_articles": 18,
  "unused_articles": 7,
  "last_used_date": "2025-12-22T10:30:00",
  "newest_unused_published": "2025-12-22T14:20:00",
  "ready_for_analysis": true  # ← Can analyze now!
}
```

### **View Unused Articles**

```bash
# See only fresh, unanalyzed articles
curl "http://localhost:8000/api/articles/AAPL?unused_only=true" | jq

# Returns only articles that haven't been used yet
```

### **Force Refresh** (For Testing)

```bash
# Reanalyze even without new news
curl -X POST "http://localhost:8000/api/analyze/AAPL?force_refresh=true" | jq

# This will:
# 1. Bypass 1-hour cache
# 2. Treat all recent articles as "new" temporarily
# 3. Useful for testing/debugging
```

---

## 📈 Benefits

### **1. Human-Like Decision Making**
```
Real Trader:
"I remember earnings were great last week [context],
 but this morning's CEO resignation [new] changes everything"

Bot (Now):
[Previous Context] Good earnings
[NEW BREAKING NEWS] CEO resignation ← 70% weight
→ Recommendation: SELL
```

### **2. Prevents Signal Dilution**
```
Without context-awareness:
Day 2: All 4 articles equal → 2 good + 2 bad = HOLD (unclear)

With context-awareness:
Day 2: 2 old good [30%] + 2 new bad [70%] = SELL (clear)
```

### **3. Better Summaries**
```json
{
  "summary": "Apple demonstrated strong fundamentals in Q3 
              with record earnings [context], however today's 
              breaking news about supply chain disruptions [NEW] 
              and analyst concerns creates uncertainty...",
              
  "recommendation": "SELL",
  
  "reasoning": "While the company's financial health remains 
               solid based on recent results, the magnitude of 
               today's supply chain issues outweighs previous 
               optimism for near-term positions..."
}
```

### **4. Accurate Validation**
- Track which NEW articles drove each recommendation
- Validate: "Did the breaking news correctly predict the move?"
- Learn: "Supply chain news typically leads to -3% moves"

### **5. Efficient API Usage**
- System knows when there's actually new information
- Won't waste LLM calls re-analyzing old news
- Only analyzes when actionable information exists

---

## 🔧 Technical Implementation

### **1. Dual Article Fetching** (app/main.py)

```python
# Get ALL recent articles for context
all_recent_articles = db.query(Article).filter(
    Article.ticker == ticker,
    Article.published_at >= datetime.now() - timedelta(days=7)
).order_by(desc(Article.published_at)).limit(30).all()

# Get ONLY UNUSED articles for recommendation
new_articles = db.query(Article).filter(
    Article.ticker == ticker,
    Article.used_in_analysis == 0,  # Only unused!
    Article.published_at >= datetime.now() - timedelta(days=7)
).order_by(desc(Article.published_at)).limit(20).all()

# Pass both to LLM
analysis = await llm_service.analyze_stock(
    articles=all_recent_articles,    # Context
    new_articles=new_articles,        # Focus
    ...
)
```

### **2. Article Marking** (app/prompts/analysis_prompt.py)

```python
# Get IDs of new articles
new_article_ids = {a.id for a in new_articles}

# Mark each article appropriately
for article in all_articles:
    if article.id in new_article_ids:
        marker = " [NEW - BREAKING NEWS]"
    else:
        marker = " [Previous Context]"
    
    formatted_articles.append(f"""
Article {i}{marker}:
Title: {article.title}
Source: {article.source}
Date: {article.published_at}
Summary: {article.content[:300]}...
""")
```

### **3. LLM Instructions**

```
## CRITICAL INSTRUCTION FOR NEWS ANALYSIS:
- Articles marked "[NEW - BREAKING NEWS]" are fresh developments (70% weight)
- Articles marked "[Previous Context]" are for background only (30% weight)
- Your RECOMMENDATION should be driven by NEW articles
- Your SUMMARY can include context from previous articles
- If NEW news contradicts previous context, NEW dominates

Example:
- Previous Context: "Company beats earnings" (positive)
- NEW Breaking News: "CEO resigns unexpectedly" (negative)
- → Recommendation: SELL (driven by new development)
- → Summary: Can mention earnings for context, but emphasize resignation
```

### **4. Mark Articles as Used** (app/main.py)

```python
# After successful analysis, mark NEW articles as used
current_time = datetime.now()
for article in new_articles:
    article.used_in_analysis = 1
    article.last_used_date = current_time
    article.used_in_recommendation_id = recommendation.id

db.commit()
```

---

## 🗄️ Database Schema

### **Articles Table**

```sql
CREATE TABLE articles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    article_hash VARCHAR(64) UNIQUE,  -- For deduplication
    ticker VARCHAR(10),
    title TEXT,
    content TEXT,
    source VARCHAR(100),
    published_at DATETIME,
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Usage tracking
    used_in_analysis BOOLEAN DEFAULT FALSE,
    last_used_date DATETIME NULL,
    used_in_recommendation_id INT NULL,
    
    -- Indexes
    INDEX idx_ticker_date (ticker, published_at),
    INDEX idx_ticker_unused (ticker, used_in_analysis, published_at)
);
```

### **Query Examples**

```sql
-- Get unused articles for AAPL
SELECT * FROM articles 
WHERE ticker = 'AAPL' 
  AND used_in_analysis = 0
  AND published_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY published_at DESC;

-- See which articles were used in a recommendation
SELECT a.title, a.published_at, r.recommendation
FROM articles a
JOIN recommendations r ON a.used_in_recommendation_id = r.id
WHERE a.ticker = 'AAPL'
  AND a.used_in_analysis = 1
ORDER BY a.last_used_date DESC;

-- Reset article for testing
UPDATE articles 
SET used_in_analysis = 0,
    last_used_date = NULL,
    used_in_recommendation_id = NULL
WHERE id = 123;
```

---

## ⚙️ Configuration

### **Environment Variables**

```bash
# .env
NEWS_LOOKBACK_DAYS=7          # Days of news to consider (context)
ARTICLE_RETENTION_DAYS=30     # How long to keep articles
```

**Recommendations:**
- Keep `NEWS_LOOKBACK_DAYS=7` for good balance
- Shorter (2-3) for pure day trading
- Longer (14) for swing trading with more context

---

## 🔍 Monitoring

### **Check System Health**

```bash
# Overall health
curl http://localhost:8000/health | jq

# Article statistics
curl http://localhost:8000/api/articles/AAPL/stats | jq

# View unused articles
curl "http://localhost:8000/api/articles/AAPL?unused_only=true" | jq

# Recent recommendations
curl http://localhost:8000/api/recommendations?limit=10 | jq
```

### **Expected Patterns**

**Healthy System:**
```json
{
  "ticker": "AAPL",
  "total_articles": 45,
  "used_articles": 38,
  "unused_articles": 7,
  "ready_for_analysis": true
}
```

**Waiting for News:**
```json
{
  "ticker": "AAPL",
  "total_articles": 45,
  "used_articles": 45,
  "unused_articles": 0,
  "ready_for_analysis": false
}
```

---

## 🐛 Troubleshooting

### **Issue: "No new articles available"**

**Cause:** All recent news has been analyzed

**Solutions:**
```bash
# Option 1: Wait for new news to be published
# (Check back in a few hours)

# Option 2: Use force_refresh for testing
curl -X POST "http://localhost:8000/api/analyze/AAPL?force_refresh=true"

# Option 3: Reset articles in database (testing only)
UPDATE articles SET used_in_analysis = 0 WHERE ticker = 'AAPL';
```

### **Issue: Recommendations seem to ignore recent context**

**Cause:** May need to adjust lookback window

**Solution:**
```bash
# Increase context window in .env
NEWS_LOOKBACK_DAYS=14  # More historical context

# Restart API
docker compose restart sentiment-api
```

### **Issue: Too many repeated analyses**

**Cause:** New articles arriving frequently

**This is actually good!** It means the system is working correctly and responding to market activity.

---

## 📊 Comparison: Different Approaches

| Aspect | Pure NEW Only | Equal Weighting | Context-Aware (Current) |
|--------|---------------|-----------------|------------------------|
| **Context** | None | Full | Full |
| **NEW Weight** | 100% | 50% | 70% |
| **Summary** | Limited | Complete | Complete |
| **Recommendation** | Reactive | Diluted | Balanced |
| **Trading Style** | Scalping | Long-term | Active/Swing |
| **Signal Quality** | Clear but blind | Weak | Clear + informed |
| **Best For** | High-frequency | Buy & hold | Day/swing trading |

---

## 🎯 Best Practices

### **For Active Trading**

1. **Check availability first:**
   ```bash
   curl http://localhost:8000/api/articles/AAPL/stats | jq '.ready_for_analysis'
   ```

2. **Analyze when new news arrives:**
   ```bash
   if [ ready = true ]; then
       curl -X POST http://localhost:8000/api/analyze/AAPL
   fi
   ```

3. **Don't force_refresh in production:**
   - Defeats the purpose
   - Let system naturally wait for new information

### **For Testing/Development**

1. **Use force_refresh freely:**
   ```bash
   curl -X POST "http://localhost:8000/api/analyze/AAPL?force_refresh=true"
   ```

2. **Reset articles as needed:**
   ```sql
   UPDATE articles SET used_in_analysis = 0;
   ```

3. **Monitor logs:**
   ```bash
   docker compose logs -f sentiment-api
   ```

---

## 🚀 Summary

### **What Makes This Special**

✅ **Context-aware** - Knows market history  
✅ **Action-focused** - Driven by breaking news  
✅ **Balanced weighting** - 70% new / 30% context  
✅ **Clear signals** - No signal dilution  
✅ **Human-like** - Mirrors trader logic  
✅ **Trackable** - Know what drove each decision  
✅ **Efficient** - Only analyzes when needed  

### **Perfect For**

- 🎯 Active trading
- 📊 Swing trading
- ⚡ Event-driven strategies
- 🔍 Informed decision-making
- 🤖 Automated trading systems

---

**The bot now thinks like an experienced trader: aware of context, focused on action! 🎯📈**
