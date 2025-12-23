"""Pytest configuration and shared fixtures"""
import pytest
from datetime import datetime, timedelta
from typing import List
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.database import Base
from app.models import Article, Recommendation
from app.services.data_collector import NewsArticle, StockData
from app import schemas


@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine (in-memory SQLite)"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db_engine):
    """Create a new database session for a test"""
    TestSessionLocal = sessionmaker(bind=test_db_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def sample_stock_data():
    """Sample stock data for testing"""
    return StockData(
        ticker="AAPL",
        company_name="Apple Inc.",
        current_price=185.50,
        prev_close=182.00,
        day_change_percent=1.92,
        volume=75000000,
        avg_volume=65000000,
        market_cap=2900000000000,
        pe_ratio=28.5,
        fifty_two_week_high=199.62,
        fifty_two_week_low=164.08,
        beta=1.25
    )


@pytest.fixture
def sample_news_articles():
    """Sample news articles for testing"""
    now = datetime.now()
    return [
        NewsArticle(
            title="Apple Reports Record Q4 Earnings",
            content="Apple Inc. reported record earnings for Q4, beating analyst expectations with strong iPhone sales...",
            url="https://example.com/news1",
            source="Tech News",
            published_at=now - timedelta(days=1)
        ),
        NewsArticle(
            title="Apple Announces New Product Line",
            content="In a surprise announcement, Apple unveiled a new line of products including updated MacBooks...",
            url="https://example.com/news2",
            source="Business Daily",
            published_at=now - timedelta(days=2)
        ),
        NewsArticle(
            title="Concerns About Supply Chain Issues",
            content="Analysts express concern about potential supply chain disruptions affecting Apple's production...",
            url="https://example.com/news3",
            source="Market Watch",
            published_at=now - timedelta(days=3)
        )
    ]


@pytest.fixture
def duplicate_news_article(sample_news_articles):
    """Duplicate of first article with slight variation"""
    original = sample_news_articles[0]
    return NewsArticle(
        title=original.title,  # Same title
        content=original.content,  # Same content
        url="https://example.com/news1-duplicate",  # Different URL
        source="Different Source",
        published_at=original.published_at
    )


@pytest.fixture
def sample_price_history():
    """Sample price history for testing"""
    dates = [datetime.now() - timedelta(days=i) for i in range(30, 0, -1)]
    return {
        'dates': dates,
        'close': [180.0 + i * 0.5 for i in range(30)],
        'volume': [60000000 + i * 1000000 for i in range(30)],
        'high': [182.0 + i * 0.5 for i in range(30)],
        'low': [178.0 + i * 0.5 for i in range(30)]
    }


@pytest.fixture
def sample_llm_analysis():
    """Sample LLM analysis response"""
    return {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "analysis_date": "2025-12-22",
        "recommendation": "BUY",
        "confidence": "HIGH",
        "sentiment_score": 0.65,
        "risk_level": "MEDIUM",
        "volatility_assessment": "Moderate volatility with stable long-term trends",
        "key_factors": [
            {"factor": "Strong Q4 earnings", "impact": "POSITIVE"},
            {"factor": "New product launches", "impact": "POSITIVE"},
            {"factor": "Supply chain concerns", "impact": "NEGATIVE"}
        ],
        "summary": "Strong fundamentals with positive recent news outweigh supply chain concerns.",
        "reasoning": "Recent earnings beat expectations and new product announcements indicate continued growth. While supply chain issues are a concern, the company has historically managed these well.",
        "price_target": 195.00,
        "time_horizon": "MEDIUM_TERM",
        "warnings": ["Monitor supply chain developments"]
    }


@pytest.fixture
def sample_articles_in_db(db_session, sample_news_articles):
    """Create sample articles in database"""
    articles = []
    for news in sample_news_articles:
        from app.services.deduplicator import ArticleDeduplicator
        article_hash = ArticleDeduplicator.generate_article_hash(
            news.title, 
            news.content
        )
        article = Article(
            article_hash=article_hash,
            url=news.url,
            ticker="AAPL",
            title=news.title,
            content=news.content,
            source=news.source,
            published_at=news.published_at
        )
        db_session.add(article)
        articles.append(article)
    
    db_session.commit()
    return articles


@pytest.fixture
def sample_recommendation_in_db(db_session, sample_llm_analysis):
    """Create sample recommendation in database"""
    recommendation = Recommendation(
        ticker=sample_llm_analysis['ticker'],
        company_name=sample_llm_analysis['company_name'],
        recommendation=sample_llm_analysis['recommendation'],
        confidence=sample_llm_analysis['confidence'],
        sentiment_score=sample_llm_analysis['sentiment_score'],
        risk_level=sample_llm_analysis['risk_level'],
        summary=sample_llm_analysis['summary'],
        reasoning=sample_llm_analysis['reasoning'],
        price_at_analysis=185.50,
        price_target=sample_llm_analysis['price_target'],
        time_horizon=sample_llm_analysis['time_horizon'],
        raw_analysis_json=sample_llm_analysis,
        article_ids=[1, 2, 3]
    )
    db_session.add(recommendation)
    db_session.commit()
    return recommendation


@pytest.fixture
def mock_finnhub_response():
    """Mock Finnhub API response"""
    now = datetime.now()
    return [
        {
            'datetime': int((now - timedelta(days=1)).timestamp()),
            'headline': 'Apple Reports Record Q4 Earnings',
            'summary': 'Apple Inc. reported record earnings for Q4...',
            'url': 'https://example.com/news1',
            'source': 'Tech News'
        },
        {
            'datetime': int((now - timedelta(days=2)).timestamp()),
            'headline': 'Apple Announces New Product Line',
            'summary': 'In a surprise announcement, Apple unveiled...',
            'url': 'https://example.com/news2',
            'source': 'Business Daily'
        }
    ]


@pytest.fixture
def mock_yfinance_info():
    """Mock yfinance stock info"""
    return {
        'regularMarketPrice': 185.50,
        'previousClose': 182.00,
        'volume': 75000000,
        'averageVolume': 65000000,
        'marketCap': 2900000000000,
        'trailingPE': 28.5,
        'fiftyTwoWeekHigh': 199.62,
        'fiftyTwoWeekLow': 164.08,
        'beta': 1.25,
        'longName': 'Apple Inc.'
    }


@pytest.fixture
def mock_ollama_generate_response():
    """Mock Ollama generate API response"""
    import json
    analysis = {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "analysis_date": "2025-12-22",
        "recommendation": "BUY",
        "confidence": "HIGH",
        "sentiment_score": 0.65,
        "risk_level": "MEDIUM",
        "volatility_assessment": "Moderate volatility",
        "key_factors": [
            {"factor": "Strong earnings", "impact": "POSITIVE"}
        ],
        "summary": "Strong fundamentals with positive news.",
        "reasoning": "Recent earnings beat expectations.",
        "price_target": 195.00,
        "time_horizon": "MEDIUM_TERM",
        "warnings": []
    }
    return {
        'response': json.dumps(analysis)
    }
