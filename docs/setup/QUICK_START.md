# Quick Start Guide

## 🚀 Get Running in 5 Minutes

### Prerequisites

Before starting, ensure you have:
- ✅ **Docker Desktop** installed and running
- ✅ **20GB+ free disk space** (for Mixtral model)
- ✅ **16GB+ RAM** (24GB recommended)
- ✅ **Internet connection** (for downloading model)

### 1. Get Finnhub API Key (2 minutes)

1. Go to https://finnhub.io/
2. Click "Get free API key"
3. Sign up with email
4. Copy your API key from dashboard

**Important:** Free tier gives you 60 API calls/minute, which is plenty!

### 2. Navigate to Project Directory

```bash
cd "/Users/rob.ronayne/Desktop/Sentiment Analysis"
```

**Verify you're in the right place:**
```bash
ls -la
# You should see: docker-compose.yml, app/, schema.sql, etc.
```

### 3. Configure Environment Variables

#### **Step 3a: Copy the Example File**

```bash
cp .env.example .env
```

#### **Step 3b: Edit the Configuration**

```bash
nano .env
# Or use any text editor: open .env, code .env, vim .env, etc.
```

#### **Step 3c: Required Changes**

Find these lines and modify them:

```bash
# REQUIRED: Add your Finnhub API key
FINNHUB_API_KEY=your_actual_key_here    # ⚠️ CHANGE THIS

# RECOMMENDED: Change MySQL password
MYSQL_PASSWORD=changeme123              # ⚠️ CHANGE THIS for security
```

**Example .env file after editing:**
```bash
# Database Configuration
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_DATABASE=sentiment_analysis
MYSQL_USER=sentimentbot
MYSQL_PASSWORD=my_secure_password_123   # ✅ Changed

# API Keys
FINNHUB_API_KEY=abcdef123456789        # ✅ Your actual key

# Application Settings
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=mixtral:8x7b               # Default: most accurate
API_HOST=0.0.0.0
API_PORT=8000

# Rate Limiting
MAX_REQUESTS_PER_HOUR=60

# Data Collection Settings
NEWS_LOOKBACK_DAYS=7
ARTICLE_RETENTION_DAYS=30

# Validation Settings
RUN_VALIDATION_HOUR=2
```

**Save and exit:**
- Nano: Press `Ctrl+X`, then `Y`, then `Enter`
- Vim: Press `Esc`, type `:wq`, press `Enter`
- VS Code: Press `Cmd+S` (Mac) or `Ctrl+S` (Windows)

#### **Step 3d: Verify Configuration**

```bash
cat .env | grep FINNHUB_API_KEY
# Should show: FINNHUB_API_KEY=your_actual_key
```

### 4. Optional: Choose Different Model

**Default model (Mixtral 8x7B):**
- Most accurate
- Requires 20GB+ RAM
- Slower (~45-90 seconds per analysis)

**Alternative (Llama 3.1 8B):**
- Faster (~30-45 seconds per analysis)
- Requires 8GB+ RAM
- Slightly less accurate

**To use Llama instead:**
```bash
# Edit .env and change:
OLLAMA_MODEL=llama3.1:8b
```

### 5. Start the System

#### **Option A: Automated Setup (Recommended)**

```bash
# Make script executable
chmod +x setup.sh

# Run setup script
./setup.sh
```

**What happens:**
1. Creates `.env` if missing (prompts for API key)
2. Checks Docker is running
3. Starts all services (`docker compose up -d`)
4. Downloads Mixtral model (~26GB, 15-30 minutes)
5. Initializes MySQL database
6. Waits for all services to be healthy
7. Runs health checks

**Expected output:**
```
================================================
Stock Sentiment Analysis Bot - Setup
================================================

✓ Created .env file
✓ Docker is installed
✓ Docker Compose is installed

Starting services...
[+] Running 3/3
 ✔ Container sentiment-mysql    Started
 ✔ Container sentiment-ollama   Started  
 ✔ Container sentiment-api      Started

✓ MySQL is ready
✓ Ollama is ready
✓ API server is ready

================================================
✓ Setup Complete!
================================================

Services are running:
  • API Server: http://localhost:8000
  • API Docs:   http://localhost:8000/docs
```

#### **Option B: Manual Setup**

If you prefer manual control:

```bash
# Start all services
docker compose up -d

# Watch logs
docker compose logs -f
```

**Wait for:**
- MySQL initialization (~30 seconds)
- Ollama model download (~15-30 minutes first time)
- API server startup (~10 seconds)

**Check status:**
```bash
# View running containers
docker compose ps

# Should show:
# NAME              STATE    PORTS
# sentiment-api     Up       0.0.0.0:8000->8000/tcp
# sentiment-mysql   Up       0.0.0.0:3306->3306/tcp
# sentiment-ollama  Up       0.0.0.0:11434->11434/tcp
```

### 6. Verify Installation

#### **6a. Health Check**

```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "database": "healthy",
  "ollama": "healthy",
  "timestamp": "2025-12-22T20:28:57.123456"
}
```

**If you see `"ollama": "unhealthy"`:**
```bash
# Ollama is still downloading the model, wait a few minutes
# Check progress:
docker compose logs ollama | tail -20
```

#### **6b. API Documentation**

Open in browser:
```
http://localhost:8000/docs
```

You should see interactive Swagger UI with all endpoints.

#### **6c. First Analysis (Important!)**

```bash
# Analyze a stock (takes 30-90 seconds first time)
curl -X POST http://localhost:8000/api/analyze/AAPL | jq
```

**What you'll see:**
```
Downloading model layers... (first time only)
Analyzing stock...
```

**Expected response:**
```json
{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "analysis_date": "2025-12-22T20:28:57",
  "recommendation": "BUY",
  "confidence": "HIGH",
  "sentiment_score": 0.72,
  "risk_level": "MEDIUM",
  "volatility_assessment": "Moderate volatility with stable trends",
  "key_factors": [
    {
      "factor": "Strong Q4 earnings beat",
      "impact": "POSITIVE"
    },
    {
      "factor": "New product launches",
      "impact": "POSITIVE"
    }
  ],
  "summary": "Strong fundamentals with positive recent news...",
  "reasoning": "Recent earnings exceeded expectations by 15%...",
  "price_target": 195.0,
  "time_horizon": "MEDIUM_TERM",
  "warnings": ["Monitor for market volatility"]
}
```

**If you get an error:**
```bash
# Check logs
docker compose logs sentiment-api | tail -50

# Common issues:
# - "Finnhub API key not configured" → Check .env file
# - "Ollama not responding" → Model still downloading
# - "Database connection failed" → MySQL not ready yet
```

## 📊 Try More Examples

### **Analyze Different Stocks**

```bash
# Tesla
curl -X POST http://localhost:8000/api/analyze/TSLA | jq

# Microsoft
curl -X POST http://localhost:8000/api/analyze/MSFT | jq

# Google (Alphabet)
curl -X POST http://localhost:8000/api/analyze/GOOGL | jq
```

**Note:** First analysis takes longer (~60-90s), subsequent ones are faster (~30-45s)

### **View Recommendations**

```bash
# Get latest recommendation for AAPL
curl http://localhost:8000/api/recommendations/AAPL | jq

# List all recommendations
curl http://localhost:8000/api/recommendations | jq

# Filter by status
curl "http://localhost:8000/api/recommendations?status=PENDING" | jq
```

### **View Collected News**

```bash
# See what news was analyzed for AAPL
curl http://localhost:8000/api/articles/AAPL | jq
```

### **Check Metrics (After a Few Days)**

```bash
# Overall accuracy metrics
curl http://localhost:8000/api/metrics | jq

# Metrics for specific ticker
curl http://localhost:8000/api/metrics/ticker/AAPL | jq
```

## 🔧 Management Commands

### **View Logs**

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f sentiment-api
docker compose logs -f ollama
docker compose logs -f mysql

# Last 50 lines only
docker compose logs --tail=50 sentiment-api
```

### **Stop Services**

```bash
# Stop all services (keeps data)
docker compose stop

# Stop and remove containers (keeps data)
docker compose down

# Stop and remove everything including data
docker compose down -v  # ⚠️ WARNING: Deletes all recommendations!
```

### **Restart Services**

```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart sentiment-api
```

### **Check Service Status**

```bash
# View running containers
docker compose ps

# Check resource usage
docker stats

# View disk usage
docker system df
```

### **Update Configuration**

```bash
# After changing .env file:
docker compose down
docker compose up -d

# Or just restart API:
docker compose restart sentiment-api
```

## 🐛 Troubleshooting

### **Issue: Docker not running**

**Error:** `Cannot connect to the Docker daemon`

**Solution:**
```bash
# Mac: Open Docker Desktop application
open -a Docker

# Wait for Docker to start (~30 seconds)
# Then retry: docker compose up -d
```

### **Issue: Port already in use**

**Error:** `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solution:**
```bash
# Find what's using the port
lsof -i :8000

# Kill the process or change port in docker-compose.yml:
# ports:
#   - "8001:8000"  # Use 8001 instead
```

### **Issue: Out of memory**

**Error:** `Killed` or system becomes very slow

**Solution:**
```bash
# Option 1: Use smaller model
# Edit .env:
OLLAMA_MODEL=llama3.1:8b

# Option 2: Increase Docker memory limit
# Docker Desktop → Settings → Resources → Memory → 24GB
```

### **Issue: Ollama model not downloading**

**Symptoms:** Health check shows `"ollama": "unhealthy"`

**Solution:**
```bash
# Check Ollama logs
docker compose logs ollama

# Manually pull model
docker compose exec ollama ollama pull mixtral:8x7b

# If download stalls, restart Ollama
docker compose restart ollama
```

### **Issue: Finnhub API key not working**

**Error:** `Finnhub API key not configured` or `401 Unauthorized`

**Solution:**
```bash
# 1. Verify key in .env
cat .env | grep FINNHUB_API_KEY

# 2. Test key directly
curl "https://finnhub.io/api/v1/quote?symbol=AAPL&token=YOUR_KEY"
# Should return: {"c":185.5,"d":3.5,...}

# 3. If invalid, get new key at finnhub.io
# 4. Update .env and restart:
docker compose restart sentiment-api
```

### **Issue: Database connection failed**

**Error:** `Can't connect to MySQL server`

**Solution:**
```bash
# Check if MySQL is running
docker compose ps

# If not running, start it
docker compose up -d mysql

# Wait for MySQL to initialize (~30 seconds)
docker compose logs mysql | grep "ready for connections"

# Check credentials in .env match schema.sql
```

### **Issue: Analysis takes forever**

**Symptoms:** Request hangs for 5+ minutes

**Causes & Solutions:**
```bash
# 1. First run always slow (model loading)
#    → Wait 2-3 minutes for first request

# 2. Model still downloading
#    → Check: docker compose logs ollama

# 3. CPU maxed out
#    → Close other applications
#    → Use smaller model (llama3.1:8b)

# 4. LLM not responding
docker compose restart ollama
```

### **Issue: "No such file or directory"**

**Error when running commands:**

**Solution:**
```bash
# Make sure you're in the correct directory
cd "/Users/rob.ronayne/Desktop/Sentiment Analysis"
pwd  # Should show: .../Sentiment Analysis

# Check files exist
ls -la
# Should see: docker-compose.yml, .env, app/, etc.
```

### **Issue: Permission denied on setup.sh**

**Error:** `Permission denied: ./setup.sh`

**Solution:**
```bash
# Make script executable
chmod +x setup.sh

# Then run
./setup.sh
```

### **Get Help**

If you're still stuck:

1. **Check logs:**
   ```bash
   docker compose logs -f > logs.txt
   # Review logs.txt for errors
   ```

2. **Verify health:**
   ```bash
   curl http://localhost:8000/health | jq
   ```

3. **Check documentation:**
   - Full guide: `README.md`
   - Technical details: `TECHNICAL_DEEP_DIVE.md`
   - Common issues: Above troubleshooting section

## 📖 Full Documentation

See [README.md](README.md) for complete documentation.

## 🛑 Stop Services

```bash
docker compose down
```

## 🔄 Restart Services

```bash
docker compose restart
```

## 📈 View API Documentation

Open in browser: http://localhost:8000/docs

## 💡 Tips

- Analysis is cached for 1 hour per ticker
- First analysis takes longer (~60 seconds)
- Subsequent analyses are faster (~30 seconds)
- News is collected from last 7 days
- Validation happens automatically after time horizon expires
- Check metrics after a few days to see accuracy

## 🎯 Next Steps

1. Analyze multiple stocks
2. Wait 3-7 days for validation
3. Check `/api/metrics` to see accuracy
4. Integrate into your workflow via JSON API

## 🔗 Useful Endpoints

- Health: http://localhost:8000/health
- Docs: http://localhost:8000/docs
- OpenAPI: http://localhost:8000/openapi.json

---

**Need Help?** Check README.md or logs: `docker compose logs -f`
