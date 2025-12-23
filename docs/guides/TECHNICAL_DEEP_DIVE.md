# Technical Deep Dive - Stock Sentiment Analysis Bot v1.0

## 🔬 Complete System Architecture & Data Flow

This document provides an in-depth technical analysis of how the system works from initial API call to final response.

---

## 📡 Request Flow: End-to-End

### **User Request Entry Point**

```bash
curl -X POST http://localhost:8000/api/analyze/AAPL
```

---

## 🔄 Stage 1: Request Handling & Validation

**File**: `app/main.py:118-245`

### **1.1 FastAPI Receives Request**
```python
@app.post("/api/analyze/{ticker}", response_model=schemas.AnalysisResponse)
async def analyze_stock(
    ticker: str,
    force_refresh: bool = False,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
```

**What Happens:**
1. FastAPI extracts `ticker` from URL path (`/api/analyze/AAPL` → `ticker="AAPL"`)
2. Dependency injection provides fresh database session via `Depends(get_db)`
3. Optional `force_refresh` query parameter bypasses cache
4. Ticker normalized to uppercase: `ticker = ticker.upper()` (line 135)

### **1.2 Cache Check (Smart Caching)**
```python
# Lines 139-162
if not force_refresh:
    recent_analysis = db.query(models.Recommendation).filter(
        models.Recommendation.ticker == ticker,
        models.Recommendation.analysis_date >= datetime.now() - timedelta(hours=1)
    ).order_by(desc(models.Recommendation.analysis_date)).first()
```

**Technical Details:**
- **Cache TTL**: 1 hour (configurable at line 142)
- **Database Query**: Uses indexed `ticker` and `analysis_date` fields
- **SQL Generated**:
  ```sql
  SELECT * FROM recommendations 
  WHERE ticker = 'AAPL' 
    AND analysis_date >= '2025-12-22 19:28:57'
  ORDER BY analysis_date DESC 
  LIMIT 1;
  ```
- **If Found**: Reconstructs `AnalysisResponse` from stored `raw_analysis_json` (JSON field)
- **If Not Found**: Continues to full analysis

**Why This Matters:**
- Prevents duplicate API calls to Finnhub (rate limited)
- Avoids expensive LLM inference (~30-60 seconds)
- Reduces costs if using paid LLM service

---

## 🔄 Stage 2: Data Collection

**File**: `app/services/data_collector.py`

### **2.1 Stock Fundamentals Collection**

```python
# Lines 50-92
stock_data, error = data_collector.get_stock_data(ticker)
```

**Technical Implementation:**
```python
def get_stock_data(self, ticker: str) -> Tuple[Optional[StockData], Optional[str]]:
    stock = yf.Ticker(ticker)
    info = stock.info  # Triggers HTTP request to Yahoo Finance
```

**Data Retrieved:**
- **Price Data**: `regularMarketPrice`, `previousClose`
- **Volume**: `volume`, `averageVolume`
- **Valuation**: `marketCap`, `trailingPE`
- **Volatility**: `beta`, `fiftyTwoWeekHigh`, `fiftyTwoWeekLow`

**Calculations Performed:**
```python
# Line 71: Day change percentage
day_change = ((current_price - prev_close) / prev_close * 100) if prev_close else 0
```

**Error Handling:**
- Invalid ticker → Returns `(None, "Invalid ticker symbol: AAPL")`
- Network error → Returns `(None, str(exception))`
- Missing price data → Returns `(None, "Unable to fetch price data")`

**HTTP Request Made:**
```
GET https://query2.finance.yahoo.com/v10/finance/quoteSummary/AAPL
    ?modules=price,summaryDetail,defaultKeyStatistics
```

### **2.2 News Articles Collection**

```python
# Lines 94-144
news_articles = data_collector.get_news_articles(ticker, settings.news_lookback_days)
```

**Technical Implementation:**
```python
def get_news_articles(self, ticker: str, days_back: int = 7):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    news_data = self.finnhub_client.company_news(
        ticker.upper(),
        _from=start_date.strftime('%Y-%m-%d'),
        to=end_date.strftime('%Y-%m-%d')
    )
```

**HTTP Request Made:**
```
GET https://finnhub.io/api/v1/company-news
    ?symbol=AAPL
    &from=2025-12-15
    &to=2025-12-22
    &token=YOUR_API_KEY
```

**Response Processing:**
```python
# Lines 126-137
for item in news_data:
    published_at = datetime.fromtimestamp(item.get('datetime', 0))  # Unix timestamp
    
    article = NewsArticle(
        title=item.get('headline', ''),
        content=item.get('summary', ''),
        url=item.get('url', ''),
        source=item.get('source', 'Unknown'),
        published_at=published_at
    )
```

**Data Structure:**
```python
@dataclass
class NewsArticle:
    title: str           # "Apple Reports Record Q4 Earnings"
    content: str         # "Apple Inc. reported earnings that..."
    url: str             # "https://example.com/news/123"
    source: str          # "Reuters"
    published_at: datetime  # 2025-12-22 10:30:00
```

### **2.3 Historical Price Collection**

```python
# Lines 146-174
price_history = data_collector.get_historical_prices(ticker, days_back=30)
```

**Technical Implementation:**
```python
def get_historical_prices(self, ticker: str, days_back: int = 30):
    stock = yf.Ticker(ticker)
    hist = stock.history(period=f"{days_back}d")  # Pandas DataFrame
    
    return {
        'dates': hist.index.tolist(),      # [datetime, datetime, ...]
        'close': hist['Close'].tolist(),   # [180.5, 182.3, 181.9, ...]
        'volume': hist['Volume'].tolist(), # [65M, 72M, 68M, ...]
        'high': hist['High'].tolist(),
        'low': hist['Low'].tolist()
    }
```

**HTTP Request Made:**
```
GET https://query2.finance.yahoo.com/v8/finance/chart/AAPL
    ?range=30d&interval=1d
```

---

## 🔄 Stage 3: Article Deduplication

**File**: `app/services/deduplicator.py`

### **3.1 Deduplication Strategy (Multi-Level)**

```python
# main.py lines 173-176
deduplicator = ArticleDeduplicator(db)
saved_articles = deduplicator.save_articles(news_articles, ticker)
```

**Implementation Flow:**

#### **Level 1: Content Hash (SHA-256)**
```python
# Lines 21-38
@staticmethod
def generate_article_hash(title: str, content: str) -> str:
    # Normalize text
    normalized_title = title.lower().strip()
    normalized_content = (content or "").lower().strip()[:500]  # First 500 chars only
    
    # Combine and hash
    combined = f"{normalized_title}|{normalized_content}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()
```

**Example:**
```python
title = "Apple Reports Record Q4 Earnings"
content = "Apple Inc. reported earnings that exceeded expectations..."

# Normalization:
normalized = "apple reports record q4 earnings|apple inc. reported earnings..."

# SHA-256 Hash:
hash = "a8f3d2e1b4c6..."  # 64 character hex string
```

**Database Check:**
```sql
SELECT * FROM articles WHERE article_hash = 'a8f3d2e1b4c6...';
```

#### **Level 2: URL Deduplication**
```python
# Lines 55-71
def is_duplicate_by_url(self, url: str) -> bool:
    exists = self.db.query(Article).filter(
        Article.url == url
    ).first()
    return exists is not None
```

**SQL Query:**
```sql
SELECT * FROM articles WHERE url = 'https://example.com/news/123' LIMIT 1;
```

**Why URL Check?**
- Catches articles with updated content
- Same story from same source
- Unique constraint on URL field

#### **Level 3: Fuzzy Title Matching**
```python
# Lines 73-108
def find_similar_articles(self, title: str, ticker: str, similarity_threshold: float = 0.85):
    # Get recent 50 articles for same ticker
    recent_articles = self.db.query(Article).filter(
        Article.ticker == ticker
    ).order_by(Article.published_at.desc()).limit(50).all()
    
    # Compare titles using Levenshtein-like algorithm
    for article in recent_articles:
        similarity = SequenceMatcher(
            None,
            title.lower().strip(),
            article.title.lower().strip()
        ).ratio()  # Returns 0.0 to 1.0
        
        if similarity >= similarity_threshold:
            similar.append(article)
```

**Example Similarity Calculation:**
```python
title1 = "Apple Reports Record Q4 Earnings"
title2 = "Apple Reports Record Q4 Earnings Results"  # Slightly different

# SequenceMatcher calculates:
similarity = 0.92  # 92% similar → DUPLICATE (threshold 0.85)
```

**Algorithm**: Uses Python's `difflib.SequenceMatcher` which implements Ratcliff-Obershelp algorithm
- Finds longest contiguous matching subsequence
- Recursively finds matches in remaining parts
- Formula: `similarity = 2 * M / T` where M = matches, T = total elements

### **3.2 Batch Deduplication**

```python
# Lines 152-189
def filter_duplicates(self, news_articles: List[NewsArticle], ticker: str):
    unique_articles = []
    seen_hashes = set()  # In-memory deduplication within batch
    
    for article in news_articles:
        article_hash = self.generate_article_hash(article.title, article.content)
        
        # Skip if seen in current batch
        if article_hash in seen_hashes:
            continue
        
        # Skip if duplicate in database
        if self.is_duplicate(article, ticker):
            continue
        
        unique_articles.append(article)
        seen_hashes.add(article_hash)
```

**Performance:**
- In-memory set for O(1) duplicate checks within batch
- Database queries use indexed fields (article_hash, url)
- Fuzzy matching limited to 50 most recent articles

### **3.3 Database Persistence**

```python
# Lines 191-237
def save_articles(self, news_articles: List[NewsArticle], ticker: str):
    unique_articles = self.filter_duplicates(news_articles, ticker)
    
    saved_articles = []
    for news_article in unique_articles:
        article = Article(
            article_hash=article_hash,
            url=news_article.url,
            ticker=ticker.upper(),
            title=news_article.title,
            content=news_article.content,
            source=news_article.source,
            published_at=news_article.published_at
        )
        
        self.db.add(article)
        saved_articles.append(article)
    
    self.db.commit()  # Single transaction for all articles
```

**SQL Generated (per article):**
```sql
INSERT INTO articles (
    article_hash, url, ticker, title, content, source, published_at, collected_at
) VALUES (
    'a8f3d2e1...', 
    'https://...', 
    'AAPL', 
    'Apple Reports...', 
    'Apple Inc...', 
    'Reuters', 
    '2025-12-22 10:30:00',
    '2025-12-22 20:28:57'
);
```

### **3.4 Article Retrieval for Analysis**

```python
# main.py lines 178-182
recent_articles = db.query(models.Article).filter(
    models.Article.ticker == ticker,
    models.Article.published_at >= datetime.now() - timedelta(days=settings.news_lookback_days)
).order_by(desc(models.Article.published_at)).limit(20).all()
```

**SQL Query:**
```sql
SELECT * FROM articles 
WHERE ticker = 'AAPL' 
  AND published_at >= '2025-12-15 20:28:57'
ORDER BY published_at DESC 
LIMIT 20;
```

**Why Retrieve Again After Saving?**
- Includes previously saved articles (not just this batch)
- Gets articles from last 7 days even if collected earlier
- Maximum of 20 articles to prevent prompt overflow

---

## 🔄 Stage 4: Prompt Construction

**File**: `app/prompts/analysis_prompt.py`

### **4.1 Fundamentals Formatting**

```python
# Lines 6-18
def format_stock_fundamentals(stock_data) -> str:
    return f"""
Current Price: ${stock_data.current_price:.2f}
Previous Close: ${stock_data.prev_close:.2f}
Day Change: {stock_data.day_change_percent:+.2f}%
Volume: {stock_data.volume:,} (Avg: {stock_data.avg_volume:,})
Market Cap: ${stock_data.market_cap:,}
P/E Ratio: {stock_data.pe_ratio:.2f}
52-Week High: ${stock_data.fifty_two_week_high:.2f}
52-Week Low: ${stock_data.fifty_two_week_low:.2f}
Beta: {stock_data.beta:.2f}
""".strip()
```

**Output Example:**
```
Current Price: $185.50
Previous Close: $182.00
Day Change: +1.92%
Volume: 75,000,000 (Avg: 65,000,000)
Market Cap: $2,900,000,000,000
P/E Ratio: 28.50
52-Week High: $199.62
52-Week Low: $164.08
Beta: 1.25
```

### **4.2 News Formatting**

```python
# Lines 21-36
def format_news_articles(articles: List) -> str:
    formatted = []
    for i, article in enumerate(articles[:10], 1):  # LIMIT: Only first 10
        formatted.append(f"""
Article {i}:
Title: {article.title}
Source: {article.source}
Date: {article.published_at.strftime('%Y-%m-%d')}
Summary: {article.content[:300]}...
""".strip())
    
    return "\n\n".join(formatted)
```

**Output Example:**
```
Article 1:
Title: Apple Reports Record Q4 Earnings
Source: Reuters
Date: 2025-12-21
Summary: Apple Inc. reported quarterly earnings that exceeded analyst expectations by 15%, driven by strong iPhone sales and growing services revenue...

Article 2:
Title: Apple Announces New MacBook Pro
Source: TechCrunch
Date: 2025-12-20
Summary: In a surprise announcement, Apple unveiled an updated MacBook Pro featuring the new M4 chip...
```

**Important Limitations:**
- **Only 10 articles** used (even if 20 retrieved)
- **Content truncated** to 300 characters per article
- **Oldest articles** beyond 10 are ignored

### **4.3 Price History Formatting**

```python
# Lines 39-68
def format_price_history(price_history: Dict) -> str:
    closes = price_history.get('close', [])
    
    # Calculate metrics
    week_ago = closes[-7] if len(closes) >= 7 else closes[0]
    month_ago = closes[0]
    current = closes[-1]
    
    week_change = ((current - week_ago) / week_ago * 100) if week_ago else 0
    month_change = ((current - month_ago) / month_ago * 100) if month_ago else 0
    
    # Simplified volatility calculation
    if len(closes) >= 7:
        recent_closes = closes[-7:]
        avg = sum(recent_closes) / len(recent_closes)
        variance = sum((x - avg) ** 2 for x in recent_closes) / len(recent_closes)
        volatility = f"{(variance ** 0.5 / avg * 100):.2f}%"
```

**Output Example:**
```
7-Day Change: +3.45%
30-Day Change: +8.92%
Recent Volatility (7d): 2.34%
```

**Volatility Calculation:**
- Standard deviation of last 7 closing prices
- Divided by average price (coefficient of variation)
- Expressed as percentage

### **4.4 Complete Prompt Assembly**

```python
# Lines 71-156
def build_analysis_prompt(ticker, company_name, stock_data, articles, price_history):
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    fundamentals = format_stock_fundamentals(stock_data)
    news = format_news_articles(articles)
    price_trends = format_price_history(price_history)
    
    prompt = f"""You are a professional financial analyst...

## STOCK INFORMATION
Ticker: {ticker}
Company: {company_name}
Analysis Date: {current_date}

## FUNDAMENTAL DATA
{fundamentals}

## PRICE TRENDS
{price_trends}

## RECENT NEWS & SENTIMENT (Last 7 Days)
{news}

## YOUR TASK
Analyze the provided information and provide a comprehensive trading recommendation.

Consider:
1. **Sentiment Analysis**: Assess overall market sentiment
2. **Risk Assessment**: Evaluate volatility and risks
3. **Technical Factors**: Price trends, volume patterns
4. **Fundamental Factors**: Company health, valuation
5. **News Impact**: How recent news may affect performance
6. **Confidence Level**: Your confidence based on data quality

## CRITICAL GUIDELINES
- Be objective and data-driven
- If data is insufficient, recommend HOLD with LOW confidence
- For highly volatile stocks (beta > 1.5), flag risks
- If news is overwhelmingly negative, consider SELL
- Base time horizon on opportunity type

## OUTPUT FORMAT
Respond with ONLY valid JSON in this EXACT structure:

{{
  "ticker": "{ticker}",
  "company_name": "{company_name}",
  "analysis_date": "{current_date}",
  "recommendation": "BUY|SELL|SHORT|HOLD",
  "confidence": "HIGH|MEDIUM|LOW",
  "sentiment_score": <float between -1.0 and 1.0>,
  "risk_level": "LOW|MEDIUM|HIGH|VERY_HIGH",
  "volatility_assessment": "<brief assessment>",
  "key_factors": [
    {{"factor": "<description>", "impact": "POSITIVE|NEGATIVE|NEUTRAL"}}
  ],
  "summary": "<2-3 sentence summary>",
  "reasoning": "<detailed explanation, 3-5 sentences>",
  "price_target": <number or null>,
  "time_horizon": "SHORT_TERM|MEDIUM_TERM|LONG_TERM",
  "warnings": ["<warning 1>", "<warning 2>"]
}}

Provide ONLY the JSON response, no other text.
"""
```

**Final Prompt Size:**
- Typically 2,000-4,000 tokens
- Fits within Mixtral's 32K context window
- Structured to encourage consistent JSON output

---

## 🔄 Stage 5: LLM Analysis

**File**: `app/services/llm_service.py`

### **5.1 LLM Service Initialization**

```python
# Lines 14-20
class LLMService:
    def __init__(self):
        self.base_url = settings.ollama_url     # "http://ollama:11434"
        self.model = settings.ollama_model       # "mixtral:8x7b"
        self.timeout = 300.0                     # 5 minutes
```

**Docker Networking:**
- API container connects to Ollama container via Docker network
- Service name `ollama` resolves to Ollama container IP
- Port 11434 is Ollama's default REST API port

### **5.2 Completion Generation**

```python
# Lines 67-111
async def generate_completion(self, prompt: str, temperature: float = 0.3, max_tokens: int = 2000):
    async with httpx.AsyncClient(timeout=self.timeout) as client:
        response = await client.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            }
        )
```

**HTTP Request Details:**
```
POST http://ollama:11434/api/generate
Content-Type: application/json

{
  "model": "mixtral:8x7b",
  "prompt": "You are a professional financial analyst...",
  "stream": false,
  "options": {
    "temperature": 0.3,
    "num_predict": 2000
  }
}
```

**Parameters Explained:**
- **temperature: 0.3** - Low temperature for consistent, focused output (vs creative)
  - 0.0 = deterministic (always same output)
  - 1.0 = very creative/random
  - 0.3 = slightly varied but mostly consistent
- **num_predict: 2000** - Maximum tokens to generate
- **stream: false** - Wait for complete response (vs streaming chunks)

**Ollama Processing:**
1. Loads model into GPU/CPU memory (if not already loaded)
2. Tokenizes prompt using Mixtral tokenizer
3. Runs inference through Mixtral 8x7B model
4. Generates tokens autoregressively
5. Stops at JSON completion or max tokens
6. Returns complete response

**Response Structure:**
```json
{
  "model": "mixtral:8x7b",
  "created_at": "2025-12-22T20:28:57.123Z",
  "response": "{\"ticker\": \"AAPL\", \"recommendation\": \"BUY\", ...}",
  "done": true,
  "total_duration": 45123456789,
  "load_duration": 1234567890,
  "prompt_eval_count": 1234,
  "eval_count": 456
}
```

### **5.3 JSON Parsing (Robust)**

```python
# Lines 113-151
def parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
    try:
        # Try direct parsing first
        return json.loads(response)
    except json.JSONDecodeError:
        # Try to extract from markdown code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            json_str = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            json_str = response[start:end].strip()
        else:
            # Try to find JSON object boundaries
            start = response.find('{')
            end = response.rfind('}') + 1
            json_str = response[start:end]
```

**Why Multiple Parsing Strategies?**

LLMs sometimes wrap JSON in text:
```
Here's my analysis:

```json
{"ticker": "AAPL", ...}
```

I hope this helps!
```

**Parsing Strategy Hierarchy:**
1. **Direct parse** - Response is pure JSON
2. **Markdown json block** - Wrapped in ` ```json ... ``` `
3. **Generic markdown block** - Wrapped in ` ``` ... ``` `
4. **Boundary search** - Find first `{` and last `}`
5. **Fail** - Return None, log error

### **5.4 Response Validation**

```python
# Lines 204-213
required_fields = [
    'ticker', 'recommendation', 'confidence', 'sentiment_score',
    'risk_level', 'summary', 'reasoning', 'time_horizon'
]

missing_fields = [f for f in required_fields if f not in analysis]
if missing_fields:
    logger.error(f"Analysis missing required fields: {missing_fields}")
    return None
```

**Validation Ensures:**
- All critical fields present
- Proper data types (validated by Pydantic later)
- No partial/incomplete responses
- Fail fast if LLM didn't follow instructions

---

## 🔄 Stage 6: Recommendation Storage

**File**: `app/main.py:203-222`

### **6.1 Database Model Creation**

```python
recommendation = models.Recommendation(
    ticker=ticker,                              # "AAPL"
    company_name=stock_data.company_name,       # "Apple Inc."
    recommendation=analysis['recommendation'],   # "BUY"
    confidence=analysis['confidence'],           # "HIGH"
    sentiment_score=analysis['sentiment_score'], # 0.72
    risk_level=analysis['risk_level'],          # "MEDIUM"
    summary=analysis['summary'],                 # "Strong fundamentals..."
    reasoning=analysis['reasoning'],             # "Recent earnings beat..."
    price_at_analysis=stock_data.current_price, # 185.50
    price_target=analysis.get('price_target'),  # 195.00
    time_horizon=analysis['time_horizon'],      # "MEDIUM_TERM"
    raw_analysis_json=analysis,                 # Full JSON blob
    article_ids=[a.id for a in recent_articles] # [1, 2, 3, ...]
)
```

### **6.2 SQL Transaction**

```python
db.add(recommendation)  # Adds to session (not committed yet)
db.commit()            # Commits transaction to MySQL
db.refresh(recommendation)  # Refreshes object with DB-generated ID
```

**SQL Generated:**
```sql
INSERT INTO recommendations (
    ticker, company_name, analysis_date, recommendation, confidence,
    sentiment_score, risk_level, summary, reasoning,
    price_at_analysis, price_target, time_horizon,
    raw_analysis_json, article_ids, validation_status
) VALUES (
    'AAPL', 
    'Apple Inc.', 
    '2025-12-22 20:28:57',
    'BUY',
    'HIGH',
    0.72,
    'MEDIUM',
    'Strong fundamentals with positive recent news...',
    'Recent earnings beat expectations by 15%...',
    185.50,
    195.00,
    'MEDIUM_TERM',
    '{"ticker": "AAPL", "recommendation": "BUY", ...}',
    '[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]',
    'PENDING'
);
```

**Default Values:**
- `analysis_date`: `CURRENT_TIMESTAMP` (set by MySQL)
- `validation_status`: `'PENDING'` (default in schema)
- `validation_date`: `NULL` (filled during validation)

### **6.3 Response Construction**

```python
# Lines 230-245
return schemas.AnalysisResponse(
    ticker=ticker,
    company_name=stock_data.company_name,
    analysis_date=recommendation.analysis_date,  # From DB
    recommendation=analysis['recommendation'],
    confidence=analysis['confidence'],
    sentiment_score=analysis['sentiment_score'],
    risk_level=analysis['risk_level'],
    volatility_assessment=analysis.get('volatility_assessment', 'N/A'),
    key_factors=analysis.get('key_factors', []),
    summary=analysis['summary'],
    reasoning=analysis['reasoning'],
    price_target=analysis.get('price_target'),
    time_horizon=analysis['time_horizon'],
    warnings=analysis.get('warnings', [])
)
```

**Pydantic Validation:**
- Ensures all fields match schema types
- Converts enums (e.g., "BUY" → `RecommendationType.BUY`)
- Validates ranges (sentiment_score: -1.0 to 1.0)
- Serializes to JSON for HTTP response

---

## 🔄 Stage 7: Background Validation

**File**: `app/background/jobs.py`, `app/services/validator.py`

### **7.1 Scheduler Setup**

```python
# jobs.py lines 56-88
def setup_scheduler():
    scheduler = BackgroundScheduler()  # APScheduler
    
    # Daily validation at 2 AM
    scheduler.add_job(
        validate_pending_recommendations_job,
        CronTrigger(hour=settings.run_validation_hour, minute=0),
        id='validate_recommendations',
        name='Validate pending recommendations',
        replace_existing=True
    )
    
    scheduler.start()
```

**Cron Expression:**
- `hour=2, minute=0` → Runs daily at 02:00
- Uses server's local timezone
- Configurable via `RUN_VALIDATION_HOUR` env var

### **7.2 Validation Job Execution**

```python
# jobs.py lines 19-32
def validate_pending_recommendations_job():
    with get_db_context() as db:
        validator = RecommendationValidator(db)
        validated_count = validator.validate_pending_recommendations()
```

**Database Context Manager:**
```python
# database.py lines 34-45
@contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
        db.commit()  # Auto-commit on success
    except Exception:
        db.rollback()  # Auto-rollback on error
        raise
    finally:
        db.close()
```

### **7.3 Recommendation Validation Logic**

```python
# validator.py lines 204-243
def validate_pending_recommendations(self):
    # Get all PENDING recommendations
    pending = self.db.query(Recommendation).filter(
        Recommendation.validation_status == ValidationStatus.PENDING
    ).all()
    
    for rec in pending:
        # Check if time horizon elapsed
        window_days = VALIDATION_WINDOWS.get(rec.time_horizon, 7)
        validation_due_date = rec.analysis_date + timedelta(days=window_days)
        
        if datetime.now() >= validation_due_date:
            success, error = self.validate_recommendation(rec)
```

**Time Horizons:**
```python
VALIDATION_WINDOWS = {
    TimeHorizon.SHORT_TERM: 3,    # 3 days
    TimeHorizon.MEDIUM_TERM: 7,   # 7 days
    TimeHorizon.LONG_TERM: 30     # 30 days
}
```

**Example Timeline:**
```
Dec 22 20:00: Recommendation created (MEDIUM_TERM)
Dec 29 20:00: Validation eligible (7 days passed)
Dec 30 02:00: Background job validates
```

### **7.4 Price Change Calculation**

```python
# validator.py lines 135-197
def validate_recommendation(self, recommendation):
    # Fetch current price
    stock_data, error = self.data_collector.get_stock_data(recommendation.ticker)
    current_price = stock_data.current_price
    original_price = recommendation.price_at_analysis
    
    # Calculate percentage change
    price_change_percent = (
        (current_price - original_price) / original_price * 100
    )
```

**Example:**
```python
original_price = 185.50  # Price at analysis
current_price = 197.30    # Price 7 days later

price_change = (197.30 - 185.50) / 185.50 * 100
             = 11.80 / 185.50 * 100
             = 6.36%
```

### **7.5 Accuracy Scoring Algorithm**

```python
# validator.py lines 30-84
def calculate_accuracy_score(self, recommendation: str, price_change_percent: float):
    if recommendation == "BUY":
        if price_change_percent > 5:
            return 1.0  # Perfect
        elif price_change_percent > 2:
            return 0.8  # Good
        elif price_change_percent > 0:
            return 0.6  # Okay
        elif price_change_percent > -2:
            return 0.4  # Poor
        elif price_change_percent > -5:
            return 0.2  # Bad
        else:
            return 0.0  # Wrong
```

**Scoring Matrix:**

| Recommendation | Price Change | Score | Status |
|----------------|--------------|-------|---------|
| BUY | > +5% | 1.0 | ACCURATE |
| BUY | +2% to +5% | 0.8 | ACCURATE |
| BUY | 0% to +2% | 0.6 | PARTIALLY_ACCURATE |
| BUY | -2% to 0% | 0.4 | PARTIALLY_ACCURATE |
| BUY | -5% to -2% | 0.2 | INACCURATE |
| BUY | < -5% | 0.0 | INACCURATE |

**Status Thresholds:**
```python
# Lines 86-101
if accuracy_score >= 0.7:
    return ValidationStatus.ACCURATE
elif accuracy_score >= 0.4:
    return ValidationStatus.PARTIALLY_ACCURATE
else:
    return ValidationStatus.INACCURATE
```

### **7.6 Metrics Aggregation**

```python
# validator.py lines 245-305
def update_daily_metrics(self):
    validated = self.db.query(Recommendation).filter(
        Recommendation.validation_status != ValidationStatus.PENDING
    ).all()
    
    total = len(validated)
    accurate = len([r for r in validated if r.validation_status == ValidationStatus.ACCURATE])
    partially = len([r for r in validated if r.validation_status == ValidationStatus.PARTIALLY_ACCURATE])
    inaccurate = len([r for r in validated if r.validation_status == ValidationStatus.INACCURATE])
    
    avg_score = sum(r.accuracy_score for r in validated if r.accuracy_score) / total
    
    # Breakdown by confidence level
    by_confidence = {}
    for conf in ["HIGH", "MEDIUM", "LOW"]:
        conf_recs = [r for r in validated if r.confidence == conf]
        if conf_recs:
            by_confidence[conf] = {
                "total": len(conf_recs),
                "avg_accuracy": sum(r.accuracy_score for r in conf_recs) / len(conf_recs)
            }
```

**SQL Generated:**
```sql
INSERT INTO validation_metrics (
    date, total_recommendations, accurate_count,
    partially_accurate_count, inaccurate_count,
    avg_accuracy_score, recommendations_by_confidence
) VALUES (
    '2025-12-22',
    45,
    32,
    8,
    5,
    0.78,
    '{"HIGH": {"total": 20, "avg_accuracy": 0.85}, "MEDIUM": {...}, "LOW": {...}}'
);
```

---

## 📊 Performance Characteristics

### **Timing Breakdown (Typical AAPL Analysis)**

```
Cache Check:              0.005s  (database query)
Stock Data (yfinance):    0.8s    (HTTP request)
News Collection (Finnhub): 1.2s   (HTTP request)
Price History (yfinance):  0.6s   (HTTP request)
Deduplication:            0.1s    (database queries + hashing)
Prompt Construction:      0.001s  (string formatting)
LLM Inference (Mixtral):  45s     (GPU/CPU computation)
JSON Parsing:             0.002s  (parsing + validation)
Database Save:            0.01s   (SQL INSERT)
──────────────────────────────────
Total:                    ~48s
```

### **Database Queries Per Request**

1. Cache check: 1 SELECT on recommendations
2. Deduplication: ~10-20 SELECTs on articles (hash + URL checks)
3. Article retrieval: 1 SELECT on articles
4. Save recommendation: 1 INSERT on recommendations
5. Save articles: 0-10 INSERTs on articles (only unique)

**Total: ~15-35 queries per analysis**

### **External API Calls Per Request**

1. Yahoo Finance (stock data): 1 call
2. Yahoo Finance (price history): 1 call
3. Finnhub (news): 1 call
4. Ollama (LLM): 1 call

**Total: 4 API calls**

### **Memory Usage**

- Python process: ~200-500 MB
- Database connection pool: ~50 MB
- Ollama (Mixtral): ~15-20 GB (separate container)
- MySQL: ~500 MB

**Total system: ~16-21 GB**

---

## 🔐 Security Considerations (Current State)

### **⚠️ Current Vulnerabilities**

1. **No Authentication** - Anyone can call API
2. **No Rate Limiting** - Vulnerable to abuse
3. **CORS Wide Open** - `allow_origins=["*"]`
4. **No Input Sanitization** - Potential SQL injection
5. **Secrets in Environment** - API keys in plain text

### **✅ Security Features Present**

1. **Parameterized Queries** - SQLAlchemy prevents SQL injection
2. **Database Isolation** - Separate container
3. **Docker Network** - Internal service communication
4. **Environment Variables** - Secrets not in code

---

## 🏗️ Infrastructure Requirements

### **Docker Compose Stack**

```yaml
services:
  mysql:        # 3306
  ollama:       # 11434
  sentiment-api: # 8000
```

### **Networking**

```
                ┌─────────────┐
                │   Internet  │
                └──────┬──────┘
                       │ Port 8000
                       ▼
                ┌─────────────┐
                │  sentiment  │
                │     API     │
                └──────┬──────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   ┌────────┐    ┌────────┐    ┌──────────┐
   │ MySQL  │    │ Ollama │    │ External │
   │  3306  │    │ 11434  │    │   APIs   │
   └────────┘    └────────┘    └──────────┘
        ↑                            ↑
        │                            │
        │      Docker Network        │
        └────────────────────────────┘
```

### **File System**

```
Docker Volumes:
  mysql_data/       # MySQL database files
  ollama_data/      # Downloaded LLM models

Host Filesystem:
  /app/             # Application code (mounted)
```

---

## 📝 Configuration Points

### **Environment Variables**

```bash
# .env file
DATABASE_URL=mysql+pymysql://...    # MySQL connection string
OLLAMA_URL=http://ollama:11434      # Ollama service URL
OLLAMA_MODEL=mixtral:8x7b           # Model to use
FINNHUB_API_KEY=xxx                 # Finnhub API key
NEWS_LOOKBACK_DAYS=7                # Days of news to collect
ARTICLE_RETENTION_DAYS=30           # Days to keep articles
RUN_VALIDATION_HOUR=2               # Hour for daily validation
```

### **Tunable Parameters**

```python
# Cache TTL
timedelta(hours=1)  # main.py:142

# Articles limit
.limit(20)          # main.py:181

# LLM temperature
temperature=0.3     # llm_service.py:188

# LLM max tokens
max_tokens=2000     # llm_service.py:189

# Deduplication similarity
similarity_threshold=0.85  # deduplicator.py:77
```

---

This technical deep-dive covers the complete request-response cycle, showing exactly how data flows through the system from initial HTTP request to final database storage and background validation.
