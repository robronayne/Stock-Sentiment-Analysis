# Application Code

This directory contains the main application code for the Stock Sentiment Analysis Bot.

## 📁 Directory Structure

### Core Application Files

#### `main.py`
**FastAPI application and endpoints**
- 15+ REST API endpoints
- Health checks
- Analysis workflow orchestration
- Background job triggers

**Key endpoints:**
- `POST /api/analyze/{ticker}` - Main analysis endpoint
- `GET /api/recommendations` - List recommendations
- `GET /api/metrics` - Accuracy metrics
- `GET /api/articles/{ticker}/stats` - Article usage statistics

#### `config.py`
**Configuration management**
- Loads settings from environment variables
- Validates configuration
- Provides settings object to all modules

**Key settings:**
- Ollama URL and model
- Finnhub API key
- News lookback days
- Validation schedule

#### `database.py`
**Database connection management**
- SQLAlchemy engine setup
- Session management
- Database URL configuration
- Connection pooling

#### `models.py`
**SQLAlchemy ORM models**
- `Article` - News articles with usage tracking
- `Recommendation` - AI recommendations and validation
- `ValidationMetric` - Daily accuracy metrics
- `RateLimit` - API rate limiting

#### `schemas.py`
**Pydantic data models**
- Request validation schemas
- Response serialization schemas
- Enums for recommendation types, confidence levels, etc.

**Key schemas:**
- `AnalysisResponse` - Main analysis output
- `ArticleInfo` - Article with usage tracking
- `RecommendationDetail` - Full recommendation details

---

### `services/`
**Business logic and external integrations**

#### `data_collector.py`
**Data collection service**
- Yahoo Finance integration (via yfinance)
- Finnhub API integration
- Stock data fetching
- News article collection
- Price history retrieval

#### `deduplicator.py`
**Article deduplication service**
- SHA-256 content hashing
- URL-based deduplication
- Fuzzy title matching (85% threshold)
- Database persistence

#### `llm_service.py`
**LLM integration service**
- Ollama API communication
- Mixtral 8x7B model interaction
- JSON response parsing
- Error handling and retries

#### `validator.py`
**Recommendation validation service**
- Accuracy scoring (0.0 to 1.0)
- Price change calculation
- Status determination (ACCURATE/PARTIALLY_ACCURATE/INACCURATE)
- Metrics aggregation

---

### `prompts/`
**LLM prompt engineering**

#### `analysis_prompt.py`
**Prompt templates and builders**
- Context-aware article formatting
- Fundamental data formatting
- Price history formatting
- Complete prompt assembly with instructions

**Key features:**
- Marks articles as "[NEW]" vs "[Previous Context]"
- Instructs LLM to weight new articles 70%
- Structures output as JSON

---

### `background/`
**Background tasks and scheduled jobs**

#### `jobs.py`
**Scheduled background tasks**
- Daily validation job (2 AM default)
- Article cleanup job (midnight)
- Metrics aggregation
- APScheduler integration

---

## 🔧 Key Workflows

### **Analysis Workflow** (main.py)
```
1. Check cache (1-hour TTL)
2. Fetch stock data (Yahoo Finance)
3. Collect news (Finnhub)
4. Deduplicate articles
5. Get context articles (ALL recent)
6. Get focus articles (ONLY unused)
7. Build prompt with markers
8. Send to LLM (Mixtral)
9. Parse JSON response
10. Save recommendation
11. Mark new articles as used
12. Return response
```

### **Validation Workflow** (validator.py)
```
1. Find PENDING recommendations past time horizon
2. Fetch current stock price
3. Calculate price change percentage
4. Score accuracy (0.0 to 1.0)
5. Determine status
6. Update recommendation
7. Aggregate daily metrics
```

---

## 🔌 External Dependencies

### **APIs Used**
- **Yahoo Finance** - Stock data, fundamentals, price history
- **Finnhub** - News articles (requires API key)
- **Ollama** - LLM inference (Mixtral 8x7B)

### **Key Libraries**
- **FastAPI** - Web framework
- **SQLAlchemy** - ORM
- **Pydantic** - Data validation
- **yfinance** - Yahoo Finance API
- **httpx** - Async HTTP client
- **APScheduler** - Background jobs

---

## 🏗️ Code Organization Principles

### **Separation of Concerns**
- **main.py** - HTTP layer and orchestration
- **services/** - Business logic
- **prompts/** - LLM prompt engineering
- **background/** - Scheduled tasks
- **models.py** - Data layer
- **schemas.py** - API contracts

### **Dependency Injection**
```python
# Database sessions injected via FastAPI
async def endpoint(db: Session = Depends(get_db)):
    # Use db session
```

### **Error Handling**
- HTTPException for API errors
- Try/catch in service layers
- Logging throughout
- Graceful degradation

---

## 🧪 Testing

Tests are in `../tests/` directory:
- **Unit tests** - Test individual functions
- **Integration tests** - Test workflows
- **Fixtures** - Shared test data

Run tests:
```bash
scripts/run_tests.sh
```

---

## 📝 Adding New Features

### **New Endpoint**
1. Add route in `main.py`
2. Add schema in `schemas.py`
3. Add service logic in `services/`
4. Add tests in `tests/`
5. Update API reference docs

### **New Service**
1. Create file in `services/`
2. Add class with methods
3. Inject dependencies (db, config, etc.)
4. Add unit tests
5. Use in `main.py`

### **New Background Job**
1. Add function in `background/jobs.py`
2. Register with scheduler
3. Configure via environment variable
4. Test manually first

---

## 🔍 Debugging

### **Enable Debug Logging**
```python
# In config.py or environment
LOG_LEVEL=DEBUG
```

### **Check Logs**
```bash
docker compose logs -f sentiment-api
```

### **Interactive Debugging**
```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use VS Code debugger
```

---

## 📐 Code Style

- **PEP 8** - Python style guide
- **Type hints** - Use where helpful
- **Docstrings** - Document functions and classes
- **Logging** - Use logger, not print()
- **Error handling** - Be explicit

---

**All application code organized by purpose! 🐍**
