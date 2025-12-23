# Testing Guide

## Quick Start

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Run Tests

```bash
# All tests
./run_tests.sh

# With coverage report
./run_tests.sh all coverage

# Unit tests only
./run_tests.sh unit

# Integration tests
./run_tests.sh integration

# Fast tests (skip slow)
./run_tests.sh fast
```

## Test Suite Overview

### 📊 Test Statistics

- **Total Tests**: ~79 tests
- **Unit Tests**: ~64 tests
- **Integration Tests**: ~15 tests
- **Execution Time**: ~5-7 seconds
- **Target Coverage**: >80%

### 🎯 What's Tested

#### Unit Tests
✅ **Deduplication** (12 tests)
- Hash generation consistency
- URL and content-based duplicate detection
- Fuzzy title matching
- Batch filtering

✅ **Data Collection** (10 tests)
- Stock data retrieval
- News article collection
- Historical price data
- Error handling

✅ **Validation** (17 tests)
- Accuracy score calculation for all recommendation types
- Validation status determination
- Time horizon respecting
- Batch validation logic

✅ **LLM Service** (12 tests)
- Health checks
- Completion generation
- JSON parsing (clean, markdown-wrapped, malformed)
- Analysis workflow
- Error handling

✅ **Prompt Engineering** (13 tests)
- Data formatting
- Template building
- Required sections presence
- Guidelines inclusion

#### Integration Tests
✅ **Analysis Workflow** (4 tests)
- End-to-end analysis pipeline
- Duplicate handling in workflows
- Analysis with no news
- Mixed sentiment scenarios

✅ **Validation Workflow** (5 tests)
- Complete validation pipeline
- Wrong recommendation handling
- Metrics updates
- Time horizon validation

✅ **Recommendation Scenarios** (6 tests)
- Positive earnings → BUY
- Multiple negatives → SELL
- Mixed signals → HOLD
- Validation accuracy testing

## Test Examples

### Running Specific Tests

```bash
# Test deduplication
pytest tests/unit/test_deduplicator.py -v

# Test a specific function
pytest tests/unit/test_validator.py::TestRecommendationValidator::test_calculate_accuracy_score_buy_perfect -v

# Test with output
pytest tests/unit/test_llm_service.py -v -s
```

### Testing Patterns

#### Example 1: Unit Test with Mocks

```python
@patch('app.services.data_collector.yf.Ticker')
def test_get_stock_data(mock_ticker):
    # Arrange
    mock_ticker.return_value.info = {'regularMarketPrice': 185.50}
    
    # Act
    collector = DataCollector()
    stock_data, error = collector.get_stock_data("AAPL")
    
    # Assert
    assert error is None
    assert stock_data.current_price == 185.50
```

#### Example 2: Integration Test

```python
@pytest.mark.integration
async def test_full_workflow(db_session, mock_data):
    # Collect → Deduplicate → Analyze → Save
    collector = DataCollector()
    stock_data, _ = collector.get_stock_data("AAPL")
    
    dedup = ArticleDeduplicator(db_session)
    articles = dedup.save_articles(news, "AAPL")
    
    llm = LLMService()
    analysis = await llm.analyze_stock(...)
    
    assert analysis['recommendation'] in ["BUY", "SELL", "HOLD"]
```

#### Example 3: Scenario Test

```python
async def test_positive_earnings_scenario():
    """
    Given: Positive earnings beat
    When: Analysis is performed
    Then: Should recommend BUY with HIGH confidence
    """
    # Mock positive fundamentals + news
    analysis = await analyze_stock(...)
    
    assert analysis['recommendation'] == "BUY"
    assert analysis['confidence'] == "HIGH"
    assert analysis['sentiment_score'] > 0.5
```

## Coverage Report

### Generate Coverage

```bash
./run_tests.sh all coverage
```

### View Report

```bash
# Terminal output shown automatically

# HTML report
open htmlcov/index.html
```

### Expected Coverage

```
app/services/deduplicator.py     98%
app/services/validator.py        95%
app/services/data_collector.py   92%
app/services/llm_service.py      90%
app/prompts/analysis_prompt.py   100%
-------------------------------------------
TOTAL                            >80%
```

## Test Fixtures

### Database
- `test_db_engine` - In-memory SQLite
- `db_session` - Fresh session per test

### Data
- `sample_stock_data` - Mock stock fundamentals
- `sample_news_articles` - Mock news
- `sample_llm_analysis` - Mock LLM response
- `sample_price_history` - Historical prices

### Mocks
- `mock_finnhub_response` - Finnhub API
- `mock_yfinance_info` - Yahoo Finance
- `mock_ollama_generate_response` - Ollama

See `tests/conftest.py` for all fixtures.

## CI/CD Integration

### Pre-commit Checks

```bash
# Fast tests before committing
./run_tests.sh fast
```

### GitHub Actions Example

```yaml
- name: Run Tests
  run: |
    pip install -r requirements-test.txt
    pytest --cov=app --cov-report=xml
```

## Debugging

### Show Test Output

```bash
pytest -v -s tests/unit/test_validator.py
```

### Drop into Debugger

```bash
pytest --pdb
```

### Run One Test

```bash
pytest tests/unit/test_deduplicator.py::TestArticleDeduplicator::test_generate_article_hash_consistency -v
```

### Show Logs

```bash
pytest --log-cli-level=DEBUG
```

## Test Data

### Mock News Articles

Tests use realistic mock news covering:
- ✅ Positive earnings beats
- ✅ Product launches
- ✅ Supply chain issues
- ✅ Executive departures
- ✅ Regulatory investigations

### Mock Stock Data

Tests cover various scenarios:
- ✅ High P/E valuations
- ✅ Different market caps
- ✅ Various volatility levels (beta)
- ✅ Price movements (up, down, flat)

### Mock LLM Responses

Tests validate parsing of:
- ✅ Clean JSON
- ✅ Markdown-wrapped JSON
- ✅ JSON with preamble
- ✅ Malformed JSON

## What's NOT Tested

❌ **Real LLM Responses** - Quality depends on model  
❌ **Actual API Rate Limits** - Mocked in tests  
❌ **Network Failures** - Would require integration environment  
❌ **Docker Orchestration** - Requires Docker  

For these, use manual testing or staging environment.

## Adding Tests

### 1. Add Test Function

```python
# tests/unit/test_myfeature.py

@pytest.mark.unit
def test_my_new_feature():
    result = my_function()
    assert result == expected
```

### 2. Add Fixture (if needed)

```python
# tests/conftest.py

@pytest.fixture
def my_fixture():
    return MockData()
```

### 3. Run Tests

```bash
pytest tests/unit/test_myfeature.py -v
```

## Best Practices

### ✅ Do

- Write tests for all new features
- Use descriptive test names
- Test edge cases and error paths
- Mock external dependencies
- Keep tests fast (<100ms each)
- Use fixtures for reusable test data

### ❌ Don't

- Make tests depend on each other
- Access real external APIs
- Skip failing tests without fixing
- Test implementation details
- Write overly complex tests

## Performance

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest -n auto
```

### Profile Slow Tests

```bash
pytest --durations=10
```

## Troubleshooting

### Import Errors

```bash
export PYTHONPATH="${PYTHONPATH}:."
pytest
```

### Async Errors

Ensure `pytest-asyncio` is installed:
```bash
pip install pytest-asyncio
```

### Database Errors

Check SQLite:
```bash
python -c "import sqlite3; print(sqlite3.version)"
```

## Resources

- **Test Suite**: `tests/README.md`
- **pytest docs**: https://docs.pytest.org/
- **Coverage**: https://coverage.readthedocs.io/

---

**Run tests before committing!** `./run_tests.sh fast`
