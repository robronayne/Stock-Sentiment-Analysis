# Test Suite Documentation

## Overview

Comprehensive test suite for the Stock Sentiment Analysis Bot using pytest.

## Test Structure

```
tests/
├── conftest.py                          # Shared fixtures and configuration
├── unit/                                # Unit tests for individual functions
│   ├── test_deduplicator.py           # Article deduplication logic
│   ├── test_data_collector.py         # Data collection from APIs
│   ├── test_validator.py              # Recommendation validation
│   ├── test_llm_service.py            # LLM integration
│   └── test_prompts.py                # Prompt engineering
└── integration/                         # End-to-end workflow tests
    ├── test_analysis_workflow.py      # Complete analysis pipeline
    ├── test_validation_workflow.py    # Validation pipeline
    └── test_recommendation_scenarios.py # Real-world scenarios
```

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run with coverage report
pytest --cov=app --cov-report=html
```

### Run Specific Test Files

```bash
# Test deduplication
pytest tests/unit/test_deduplicator.py

# Test analysis workflow
pytest tests/integration/test_analysis_workflow.py

# Test specific function
pytest tests/unit/test_validator.py::TestRecommendationValidator::test_calculate_accuracy_score_buy_perfect
```

### Verbose Output

```bash
# Show print statements
pytest -v -s

# Show test names as they run
pytest -v
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)

Test individual functions and methods in isolation using mocks.

**Coverage:**
- ✅ Article deduplication (hash generation, duplicate detection)
- ✅ Data collection (yfinance, Finnhub API)
- ✅ Validation logic (accuracy scoring, status determination)
- ✅ LLM service (completion generation, JSON parsing)
- ✅ Prompt engineering (formatting, template building)

### Integration Tests (`@pytest.mark.integration`)

Test complete workflows with multiple components.

**Coverage:**
- ✅ Full analysis pipeline (data → dedup → LLM → save)
- ✅ Validation pipeline (pending → validate → metrics)
- ✅ Duplicate handling in workflows
- ✅ Mixed sentiment scenarios

### Scenario Tests (`@pytest.mark.slow`)

Test realistic recommendation scenarios with expected outcomes.

**Scenarios Tested:**
1. **Positive Earnings** → BUY with HIGH confidence
2. **Multiple Negatives** → SELL with warnings
3. **Mixed Signals** → HOLD with MEDIUM confidence
4. **Validation Accuracy** → Correct validation scores

## Test Fixtures

### Database Fixtures
- `test_db_engine` - In-memory SQLite database
- `db_session` - Fresh database session per test
- `sample_articles_in_db` - Pre-populated articles
- `sample_recommendation_in_db` - Pre-populated recommendation

### Data Fixtures
- `sample_stock_data` - Mock stock fundamentals
- `sample_news_articles` - Mock news articles
- `sample_llm_analysis` - Mock LLM response
- `sample_price_history` - Mock price data

### Mock Fixtures
- `mock_finnhub_response` - Mock Finnhub API response
- `mock_yfinance_info` - Mock yfinance data
- `mock_ollama_generate_response` - Mock Ollama response

## Key Test Patterns

### Testing Deduplication

```python
def test_duplicate_detection(db_session, sample_news_articles):
    dedup = ArticleDeduplicator(db_session)
    
    # Save articles
    dedup.save_articles(sample_news_articles, "AAPL")
    
    # Try to save again - should detect duplicates
    saved = dedup.save_articles(sample_news_articles, "AAPL")
    assert len(saved) == 0  # All duplicates
```

### Testing Accuracy Scoring

```python
def test_accuracy_score():
    validator = RecommendationValidator(Mock())
    
    # BUY with 6% gain = perfect
    score = validator.calculate_accuracy_score("BUY", 6.0)
    assert score == 1.0
    
    # BUY with 6% loss = wrong
    score = validator.calculate_accuracy_score("BUY", -6.0)
    assert score == 0.0
```

### Testing LLM Parsing

```python
async def test_json_parsing():
    service = LLMService()
    
    # Test with markdown wrapping
    response = '''
    ```json
    {"recommendation": "BUY"}
    ```
    '''
    
    result = service.parse_json_response(response)
    assert result == {"recommendation": "BUY"}
```

### Testing Complete Workflow

```python
@patch('app.services.data_collector.yf.Ticker')
@patch('app.services.data_collector.finnhub.Client')
async def test_full_workflow(mock_finnhub, mock_yf, db_session):
    # 1. Collect data
    collector = DataCollector()
    stock_data, _ = collector.get_stock_data("AAPL")
    
    # 2. Deduplicate articles
    dedup = ArticleDeduplicator(db_session)
    articles = dedup.save_articles(news, "AAPL")
    
    # 3. Generate analysis
    llm = LLMService()
    analysis = await llm.analyze_stock(...)
    
    # 4. Verify results
    assert analysis['recommendation'] in ["BUY", "SELL", "HOLD"]
```

## Mock Strategy

### API Mocking

Tests mock external APIs to avoid:
- Network dependencies
- API rate limits
- Costs
- Flaky tests

**Mocked Services:**
- ✅ Yahoo Finance (yfinance)
- ✅ Finnhub API
- ✅ Ollama LLM API

### Database Mocking

Tests use **in-memory SQLite** instead of MySQL:
- ✅ Faster test execution
- ✅ No external dependencies
- ✅ Clean slate for each test

## Expected Test Results

### Success Criteria

```bash
tests/unit/test_deduplicator.py ................    [12 tests]
tests/unit/test_data_collector.py ..........        [10 tests]
tests/unit/test_validator.py .................      [17 tests]
tests/unit/test_llm_service.py ............         [12 tests]
tests/unit/test_prompts.py .............            [13 tests]
tests/integration/test_analysis_workflow.py ....    [4 tests]
tests/integration/test_validation_workflow.py ..... [5 tests]
tests/integration/test_recommendation_scenarios.py [6 tests]

========== 79 passed in 5.42s ==========
```

### Coverage Target

- **Target**: >80% code coverage
- **Critical paths**: 100% coverage
- **View report**: Open `htmlcov/index.html` after running with `--cov`

## Debugging Failed Tests

### Show Output

```bash
pytest -v -s tests/unit/test_deduplicator.py
```

### Run Single Test

```bash
pytest tests/unit/test_validator.py::TestRecommendationValidator::test_calculate_accuracy_score_buy_perfect -v
```

### Drop into Debugger on Failure

```bash
pytest --pdb
```

### View Logs

```bash
pytest --log-cli-level=DEBUG
```

## Continuous Integration

### Pre-commit Checks

```bash
# Run before committing
pytest -m "not slow"
```

### Full Test Suite

```bash
# Run all tests including slow ones
pytest
```

## Adding New Tests

### 1. Unit Test Template

```python
@pytest.mark.unit
class TestNewFeature:
    def test_basic_functionality(self):
        # Arrange
        input_data = ...
        
        # Act
        result = function_under_test(input_data)
        
        # Assert
        assert result == expected_output
```

### 2. Integration Test Template

```python
@pytest.mark.integration
async def test_new_workflow(db_session, sample_data):
    # Setup
    service = MyService(db_session)
    
    # Execute workflow
    result = await service.process(sample_data)
    
    # Verify end state
    assert result.status == "success"
    
    # Verify database state
    record = db_session.query(Model).first()
    assert record is not None
```

### 3. Add Fixture to conftest.py

```python
@pytest.fixture
def my_fixture():
    return MockData(...)
```

## Test Maintenance

### When to Update Tests

- ✅ When adding new features
- ✅ When fixing bugs (add regression test)
- ✅ When changing API contracts
- ✅ When modifying business logic

### When NOT to Update Tests

- ❌ Don't change tests to make them pass
- ❌ Don't skip tests that fail
- ❌ Don't reduce assertions to avoid failures

## Performance

### Test Execution Time

- Unit tests: ~2 seconds
- Integration tests: ~3-5 seconds
- Total suite: ~5-7 seconds

### Optimizations

- ✅ In-memory database (fast)
- ✅ Mocked external APIs (no network)
- ✅ Fixtures cached at session scope when possible
- ✅ Parallel execution ready (use `-n auto` with pytest-xdist)

## Limitations

### Not Tested (Requires Real Services)

- ❌ Actual Ollama model responses (quality/accuracy)
- ❌ Real API rate limiting
- ❌ Network failures
- ❌ Docker container orchestration

### Testing Real LLM (Optional)

To test with real Ollama:

```python
@pytest.mark.requires_ollama
async def test_real_llm():
    # Requires Ollama running locally
    service = LLMService()
    result = await service.generate_completion("Test")
    assert result is not None
```

Run with:
```bash
pytest -m requires_ollama
```

## Troubleshooting

### Import Errors

```bash
# Ensure app is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:."
pytest
```

### Async Test Errors

```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio
```

### Database Errors

```bash
# Check SQLite support
python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

## Resources

- pytest docs: https://docs.pytest.org/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/
- pytest-cov: https://pytest-cov.readthedocs.io/

---

**Questions?** Check test examples in each test file for patterns and best practices.
