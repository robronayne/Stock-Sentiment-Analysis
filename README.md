# Stock Sentiment Analysis Bot

AI-powered market sentiment analysis system that provides trading recommendations based on news sentiment and stock fundamentals. The system tracks recommendation accuracy over time to improve decision-making.

## Features

- 🤖 **Self-hosted LLM Analysis** - Uses Mixtral 8x7B via Ollama (optimized for Apple Silicon)
- 📰 **Multi-source Data Collection** - Yahoo Finance + Finnhub API
- 🔄 **Smart Deduplication** - Prevents duplicate article processing
- 🎯 **Context-Aware Recommendations** - Historical context + fresh news weighting
- 📊 **Accuracy Tracking** - Validates recommendations against actual stock performance
- 🐳 **Docker-based** - Complete stack runs in containers
- 📈 **Historical Metrics** - Track model performance over time
- 🔌 **REST API** - JSON responses for automation integration

## Architecture

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│     FastAPI Server              │
│  ┌──────────────────────────┐  │
│  │  Analysis Endpoints      │  │
│  │  Validation Jobs         │  │
│  │  Metrics API             │  │
│  └──────────────────────────┘  │
└─────┬───────────────────┬───────┘
      │                   │
      ▼                   ▼
┌─────────────┐    ┌─────────────┐
│   Ollama    │    │   MySQL     │
│  (Mixtral)  │    │  Database   │
└─────────────┘    └─────────────┘
      │
      ▼
┌─────────────────────────────────┐
│  External Data Sources          │
│  • Yahoo Finance (yfinance)     │
│  • Finnhub API (news)           │
└─────────────────────────────────┘
```

## Prerequisites

- Docker Desktop installed
- 20GB+ RAM (24GB recommended for Mixtral)
- Apple Silicon Mac or x86_64 system
- Finnhub API key (free tier: https://finnhub.io/)

## Quick Start

### 1. Clone and Setup

```bash
cd "/Users/rob.ronayne/Desktop/Sentiment Analysis"
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your Finnhub API key
nano .env
```

Required configuration in `.env`:
```bash
FINNHUB_API_KEY=your_api_key_here
MYSQL_PASSWORD=your_secure_password
```

### 3. Start Services

```bash
# Build and start all services
docker-compose up -d

# Check logs
docker-compose logs -f
```

Initial startup will:
- Download MySQL and Ollama images
- Pull Mixtral 8x7B model (~26GB, takes 15-30 minutes depending on connection)
- Initialize database schema
- Start API server on port 8000

### 4. Verify Installation

```bash
# Check health
curl http://localhost:8000/health

# Should return:
# {
#   "status": "healthy",
#   "database": "healthy",
#   "ollama": "healthy",
#   "timestamp": "2025-12-22T..."
# }
```

### 5. Analyze Your First Stock

```bash
# Analyze Apple (AAPL)
curl -X POST http://localhost:8000/api/analyze/AAPL | jq

# Example response:
# {
#   "ticker": "AAPL",
#   "company_name": "Apple Inc.",
#   "recommendation": "BUY",
#   "confidence": "HIGH",
#   "sentiment_score": 0.65,
#   "risk_level": "MEDIUM",
#   "summary": "Positive market sentiment with strong fundamentals...",
#   ...
# }
```

## API Endpoints

### Analysis

```bash
# Analyze a stock
POST /api/analyze/{ticker}
  ?force_refresh=false  # Optional: bypass 1-hour cache

# Example
curl -X POST http://localhost:8000/api/analyze/TSLA
```

### Recommendations

```bash
# Get latest recommendation for a ticker
GET /api/recommendations/{ticker}

# List all recommendations (with filters)
GET /api/recommendations
  ?ticker=AAPL          # Optional: filter by ticker
  ?status=PENDING       # Optional: filter by validation status
  ?limit=50             # Optional: max results

# Examples
curl http://localhost:8000/api/recommendations/AAPL
curl http://localhost:8000/api/recommendations?status=ACCURATE
```

### Validation

```bash
# Manually validate a recommendation
POST /api/validate/{recommendation_id}

# Trigger batch validation of pending recommendations
POST /api/jobs/validate-pending

# Example
curl -X POST http://localhost:8000/api/validate/1
```

### Metrics

```bash
# Get overall accuracy metrics
GET /api/metrics

# Get metrics for specific ticker
GET /api/metrics/ticker/{ticker}

# Examples
curl http://localhost:8000/api/metrics
curl http://localhost:8000/api/metrics/ticker/AAPL
```

### Articles

```bash
# View collected articles for a ticker
GET /api/articles/{ticker}?limit=20&unused_only=false

# View only UNUSED articles (fresh news)
GET /api/articles/{ticker}?unused_only=true

# Get article usage statistics
GET /api/articles/{ticker}/stats

# Cleanup old articles
DELETE /api/articles/old

# Examples
curl http://localhost:8000/api/articles/TSLA
curl "http://localhost:8000/api/articles/TSLA?unused_only=true"
curl http://localhost:8000/api/articles/TSLA/stats
```

## Context-Aware Recommendations

The system uses a hybrid approach for smarter analysis:
- **Context**: All recent news (including yesterday's) for complete picture
- **Recommendation**: Heavily weighted (70%) toward NEW, unused articles
- **Result**: Informed decisions with fresh, actionable signals

### How It Works

1. **Collect News**: Fetches recent articles (last 7 days)
2. **Dual Analysis**: 
   - Context set: ALL recent articles
   - Focus set: Only UNUSED articles (marked as [NEW])
3. **LLM Decision**: Summary includes context, recommendation driven by new news
4. **Mark Used**: Only NEW articles marked, keeping history available

### Why This Matters

```
❌ Without context-awareness:
Day 2: All articles weighted equally
Result: 2 old positive + 2 new negative = HOLD (indecisive)

✅ With context-awareness:
Day 2: Context includes old positive, but recommendation 70% weighted to new negative
Summary: "Despite recent earnings beat, new supply chain issues..."
Recommendation: SELL (clear signal driven by fresh news)
```

### Check Article Status

```bash
# See how many fresh articles are available
curl http://localhost:8000/api/articles/AAPL/stats

# Response:
# {
#   "ticker": "AAPL",
#   "total_articles": 25,
#   "used_articles": 18,
#   "unused_articles": 7,
#   "ready_for_analysis": true
# }
```

**See [DAY_TRADING_MODE.md](DAY_TRADING_MODE.md) for complete documentation on context-aware analysis.**

---

## Understanding Recommendations

### Recommendation Types

- **BUY** - Positive sentiment, good fundamentals, upward momentum
- **SELL** - Negative sentiment or declining fundamentals
- **SHORT** - Strong negative indicators
- **HOLD** - Unclear signals, high volatility, or insufficient data

### Confidence Levels

- **HIGH** - Strong, consistent signals across multiple factors
- **MEDIUM** - Mixed signals or moderate uncertainty
- **LOW** - Conflicting data, high volatility, or insufficient information

### Time Horizons

- **SHORT_TERM** - 3 days (news-driven opportunities)
- **MEDIUM_TERM** - 7 days (technical patterns)
- **LONG_TERM** - 30 days (fundamental analysis)

### Risk Levels

- **LOW** - Stable stock, clear signals, low volatility
- **MEDIUM** - Normal market risk
- **HIGH** - Volatile stock or uncertain conditions
- **VERY_HIGH** - Extreme volatility or conflicting signals

## Validation System

The bot automatically validates recommendations after their time horizon expires:

1. **Analysis** - Bot makes recommendation at price $X
2. **Wait Period** - Time horizon passes (3, 7, or 30 days)
3. **Validation** - Bot checks actual price change
4. **Accuracy Score** - Calculates 0.0-1.0 score based on:
   - Correct direction (buy → up, sell → down)
   - Magnitude of change
   - Volatility expectations

### Accuracy Score Examples

**BUY Recommendation:**
- Price +5% or more: 1.0 (perfect)
- Price +2% to +5%: 0.8 (good)
- Price 0% to +2%: 0.6 (okay)
- Price -2% to 0%: 0.4 (poor)
- Price -5% or worse: 0.0 (wrong)

**HOLD Recommendation:**
- Price change ±2%: 1.0 (perfect)
- Price change ±5%: 0.7 (okay)
- Price change >±10%: 0.3 (poor)

## Configuration

### Environment Variables

Edit `.env` file:

```bash
# Database
MYSQL_PASSWORD=changeme123           # Change this!

# API Keys
FINNHUB_API_KEY=your_key_here       # Required for news

# LLM Settings
OLLAMA_MODEL=mixtral:8x7b           # Model to use (default)
# Alternatives:
#   - mixtral:8x7b (default, most accurate)
#   - llama3.1:8b (faster, less RAM)
#   - llama2:13b (alternative)

# Data Collection
NEWS_LOOKBACK_DAYS=7                # Days of news to analyze
ARTICLE_RETENTION_DAYS=30           # Keep articles for X days

# Validation
RUN_VALIDATION_HOUR=2               # Hour to run daily validation (0-23)
```

### Changing LLM Model

Current default is Mixtral 8x7B for best accuracy. For faster performance with less RAM:

```bash
# Edit .env for lighter model
OLLAMA_MODEL=llama3.1:8b

# Restart services
docker-compose restart sentiment-api

# Wait for model to download (~4.7GB)
docker-compose logs -f sentiment-api
```

## Data Sources

### Yahoo Finance (yfinance)
- ✅ Free, no API key needed
- Stock prices, fundamentals, historical data
- Real-time quotes
- No rate limits for reasonable use

### Finnhub API
- ✅ Free tier: 60 calls/minute
- Company news and press releases
- Signup: https://finnhub.io/
- Rate limits are generous for personal use

## Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f sentiment-api
docker-compose logs -f ollama
docker-compose logs -f mysql
```

### Database Access

```bash
# Connect to MySQL
docker-compose exec mysql mysql -u sentimentbot -p sentiment_analysis

# View recommendations
mysql> SELECT ticker, recommendation, confidence, analysis_date 
       FROM recommendations 
       ORDER BY analysis_date DESC 
       LIMIT 10;

# View validation metrics
mysql> SELECT * FROM validation_metrics ORDER BY date DESC LIMIT 5;
```

### Check Resource Usage

```bash
# Container stats
docker stats

# Disk usage
docker system df
```

## Background Jobs

Automated jobs run daily:

### Validation Job
- **Schedule**: Daily at 2 AM (configurable)
- **Purpose**: Validates pending recommendations
- **Manual trigger**: `POST /api/jobs/validate-pending`

### Cleanup Job
- **Schedule**: Daily at midnight
- **Purpose**: Deletes articles older than retention period
- **Manual trigger**: `DELETE /api/articles/old`

## Performance Tips

### For Faster Analysis
1. Use smaller model: `llama3.1:8b` (lighter alternative)
2. Reduce news lookback: `NEWS_LOOKBACK_DAYS=3`
3. Increase cache time (modify `main.py` line ~120)

### For Better Accuracy
1. Use larger model: `mixtral:8x7b`
2. Increase news lookback: `NEWS_LOOKBACK_DAYS=14`
3. Collect more articles per ticker

### Memory Usage
- `mixtral:8x7b` (default): ~15-20GB RAM
- `llama3.1:8b` (lighter): ~6-8GB RAM
- MySQL: ~200-500MB
- API Server: ~100-200MB

## Troubleshooting

### Ollama Model Not Loading

```bash
# Check if model exists
docker-compose exec ollama ollama list

# Pull model manually (default)
docker-compose exec ollama ollama pull mixtral:8x7b

# Or pull lighter model
docker-compose exec ollama ollama pull llama3.1:8b

# Check logs
docker-compose logs ollama
```

### Database Connection Issues

```bash
# Check if MySQL is ready
docker-compose exec mysql mysqladmin ping -h localhost

# Verify credentials in .env match schema.sql
cat .env | grep MYSQL
```

### Analysis Fails or Returns Errors

```bash
# Check if services are healthy
curl http://localhost:8000/health

# Verify Finnhub API key
curl "https://finnhub.io/api/v1/quote?symbol=AAPL&token=YOUR_KEY"

# Check API logs
docker-compose logs -f sentiment-api
```

### Out of Memory

```bash
# Use smaller model
OLLAMA_MODEL=llama3.1:8b

# Or increase Docker memory limit:
# Docker Desktop → Settings → Resources → Memory → 24GB
```

## Testing

### Run Test Suite

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
./run_tests.sh

# Run with coverage
./run_tests.sh all coverage

# Run specific test types
./run_tests.sh unit          # Unit tests only
./run_tests.sh integration   # Integration tests
./run_tests.sh fast          # Skip slow tests
```

### Test Coverage

- **79 comprehensive tests** covering all major components
- **Unit tests**: Deduplication, data collection, validation, LLM service
- **Integration tests**: Full workflows, realistic scenarios
- **Target coverage**: >80%

See [TESTING.md](TESTING.md) for detailed testing documentation.

## Development

### Project Structure

```
sentiment-analysis-bot/
├── docker-compose.yml          # Service orchestration
├── Dockerfile                  # API container image
├── requirements.txt            # Python dependencies
├── schema.sql                  # Database schema
├── .env                        # Configuration (create from .env.example)
└── app/
    ├── main.py                 # FastAPI application
    ├── config.py               # Settings management
    ├── database.py             # Database connection
    ├── models.py               # SQLAlchemy models
    ├── schemas.py              # Pydantic schemas
    ├── services/
    │   ├── data_collector.py   # Fetch stock data & news
    │   ├── deduplicator.py     # Article deduplication
    │   ├── llm_service.py      # Ollama integration
    │   └── validator.py        # Recommendation validation
    ├── prompts/
    │   └── analysis_prompt.py  # LLM prompt engineering
    └── background/
        └── jobs.py             # Scheduled tasks
```

### Running Without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Start MySQL locally
brew install mysql
mysql.server start
mysql < schema.sql

# Start Ollama locally
brew install ollama
ollama serve
ollama pull mixtral:8x7b

# Set environment
export DATABASE_URL="mysql+pymysql://user:pass@localhost:3306/sentiment_analysis"
export OLLAMA_URL="http://localhost:11434"
export FINNHUB_API_KEY="your_key"

# Run API
uvicorn app.main:app --reload
```

### API Documentation

Built-in interactive docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Limitations

- **Not Financial Advice**: This is an experimental tool for learning
- **Historical Data**: News sentiment doesn't predict black swan events
- **Rate Limits**: Free APIs have usage limits
- **Model Limitations**: LLM can hallucinate or misinterpret news
- **Market Hours**: Real-time data only available during trading hours

## Security Notes

- Change default MySQL password in `.env`
- Don't commit `.env` file to git
- API has no authentication (add auth for production)
- Finnhub API key is sensitive (don't expose publicly)

## License

MIT License - feel free to modify and use

## Contributing

This is a personal project but suggestions welcome:
- Open issues for bugs
- Pull requests for improvements
- Share your accuracy results!

## Additional Documentation

- **[DAY_TRADING_MODE.md](DAY_TRADING_MODE.md)** - Complete guide to article usage tracking
- **[TECHNICAL_DEEP_DIVE.md](TECHNICAL_DEEP_DIVE.md)** - Detailed system internals
- **[ROADMAP.md](ROADMAP.md)** - Future enhancements and improvement plans
- **[TESTING.md](TESTING.md)** - Testing guide and coverage
- **[QUICK_START.md](QUICK_START.md)** - Fast setup guide

## Roadmap

Potential future enhancements:
- [x] **Context-aware recommendations** - Smart article weighting ✓ Implemented
- [ ] Event tracking and learning system
- [ ] Web UI dashboard
- [ ] Multiple LLM model comparison
- [ ] Technical indicator integration
- [ ] Email/Slack notifications
- [ ] Portfolio tracking
- [ ] Backtesting framework
- [ ] Social sentiment (Reddit/Twitter)

See [ROADMAP.md](ROADMAP.md) for detailed implementation plans.

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Verify health: `curl http://localhost:8000/health`
3. Review this README
4. Check Ollama docs: https://ollama.ai/
5. Check Finnhub docs: https://finnhub.io/docs/api

---

**Disclaimer**: This tool is for educational purposes only. Stock trading involves risk. Past performance does not guarantee future results. Always do your own research and consult with financial professionals before making investment decisions.
