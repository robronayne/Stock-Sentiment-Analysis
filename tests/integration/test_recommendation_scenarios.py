"""Integration tests for realistic recommendation scenarios"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime, timedelta

from app.services.data_collector import DataCollector, NewsArticle
from app.services.deduplicator import ArticleDeduplicator
from app.services.llm_service import LLMService
from app.services.validator import RecommendationValidator
from app.models import Recommendation


@pytest.mark.integration
@pytest.mark.slow
class TestRecommendationScenarios:
    """Test realistic recommendation scenarios with expected outcomes"""
    
    @patch('app.services.data_collector.yf.Ticker')
    @patch('app.services.data_collector.finnhub.Client')
    async def test_scenario_positive_earnings_buy_recommendation(
        self,
        mock_finnhub,
        mock_yfinance,
        db_session
    ):
        """
        Scenario: Company reports positive earnings
        Expected: BUY recommendation with HIGH confidence
        """
        
        # Mock stock data with strong fundamentals
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = {
            'regularMarketPrice': 185.50,
            'previousClose': 180.00,  # +3% today
            'volume': 100000000,  # High volume
            'averageVolume': 65000000,
            'marketCap': 2900000000000,
            'trailingPE': 25.0,  # Reasonable P/E
            'beta': 1.1,
            'longName': 'Test Corp'
        }
        mock_yfinance.return_value = mock_ticker_instance
        
        # Mock positive news
        positive_news = [
            {
                'datetime': int(datetime.now().timestamp()),
                'headline': 'Test Corp Beats Earnings by 20%',
                'summary': 'Quarterly earnings significantly exceed analyst expectations...',
                'url': 'https://example.com/1',
                'source': 'Finance News'
            },
            {
                'datetime': int((datetime.now() - timedelta(days=1)).timestamp()),
                'headline': 'Test Corp Announces Stock Buyback Program',
                'summary': 'Company to repurchase $10 billion in shares...',
                'url': 'https://example.com/2',
                'source': 'Market Watch'
            },
            {
                'datetime': int((datetime.now() - timedelta(days=2)).timestamp()),
                'headline': 'Analysts Upgrade Test Corp to Strong Buy',
                'summary': 'Multiple analysts raise price targets...',
                'url': 'https://example.com/3',
                'source': 'Investment Daily'
            }
        ]
        
        mock_finnhub_instance = Mock()
        mock_finnhub_instance.company_news.return_value = positive_news
        mock_finnhub.return_value = mock_finnhub_instance
        
        # Expected LLM analysis for positive scenario
        expected_analysis = {
            "ticker": "TEST",
            "company_name": "Test Corp",
            "analysis_date": datetime.now().strftime('%Y-%m-%d'),
            "recommendation": "BUY",
            "confidence": "HIGH",
            "sentiment_score": 0.8,  # Strong positive
            "risk_level": "LOW",
            "volatility_assessment": "Low volatility with strong momentum",
            "key_factors": [
                {"factor": "Earnings beat expectations by 20%", "impact": "POSITIVE"},
                {"factor": "Stock buyback program announced", "impact": "POSITIVE"},
                {"factor": "Analyst upgrades", "impact": "POSITIVE"}
            ],
            "summary": "Strong buy signal with exceptional earnings and positive catalysts.",
            "reasoning": "The company demonstrated strong operational performance with earnings beating expectations by 20%. The stock buyback program and analyst upgrades provide additional confidence.",
            "price_target": 205.0,
            "time_horizon": "MEDIUM_TERM",
            "warnings": []
        }
        
        # Run workflow
        collector = DataCollector()
        collector.finnhub_client = mock_finnhub_instance
        
        stock_data, _ = collector.get_stock_data("TEST")
        news = collector.get_news_articles("TEST")
        
        dedup = ArticleDeduplicator(db_session)
        articles = dedup.save_articles(news, "TEST")
        
        llm_service = LLMService()
        with patch.object(
            llm_service,
            'generate_completion',
            return_value=AsyncMock(return_value=json.dumps(expected_analysis))()
        ):
            analysis = await llm_service.analyze_stock(
                ticker="TEST",
                company_name="Test Corp",
                stock_data=stock_data,
                articles=articles
            )
        
        # Verify recommendation
        assert analysis['recommendation'] == "BUY"
        assert analysis['confidence'] == "HIGH"
        assert analysis['sentiment_score'] > 0.5
        assert len(analysis['key_factors']) > 0
        assert all(f['impact'] == "POSITIVE" for f in analysis['key_factors'])
    
    @patch('app.services.data_collector.yf.Ticker')
    @patch('app.services.data_collector.finnhub.Client')
    async def test_scenario_negative_news_sell_recommendation(
        self,
        mock_finnhub,
        mock_yfinance,
        db_session
    ):
        """
        Scenario: Company faces multiple challenges
        Expected: SELL recommendation
        """
        
        # Mock stock with declining performance
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = {
            'regularMarketPrice': 150.00,
            'previousClose': 160.00,  # -6.25% today
            'volume': 120000000,  # High volume on decline
            'averageVolume': 70000000,
            'marketCap': 500000000000,
            'trailingPE': 35.0,  # High P/E
            'beta': 1.8,  # High volatility
            'longName': 'Declining Corp'
        }
        mock_yfinance.return_value = mock_ticker_instance
        
        # Mock negative news
        negative_news = [
            {
                'datetime': int(datetime.now().timestamp()),
                'headline': 'Declining Corp Misses Earnings, Cuts Guidance',
                'summary': 'Company reports significant earnings miss and reduces forward guidance...',
                'url': 'https://example.com/1',
                'source': 'Finance News'
            },
            {
                'datetime': int((datetime.now() - timedelta(days=1)).timestamp()),
                'headline': 'SEC Opens Investigation into Declining Corp',
                'summary': 'Regulatory investigation into accounting practices...',
                'url': 'https://example.com/2',
                'source': 'Legal News'
            },
            {
                'datetime': int((datetime.now() - timedelta(days=2)).timestamp()),
                'headline': 'Major Customer Cancels Contract',
                'summary': 'Loss of key customer relationship worth $500M annually...',
                'url': 'https://example.com/3',
                'source': 'Business Daily'
            }
        ]
        
        mock_finnhub_instance = Mock()
        mock_finnhub_instance.company_news.return_value = negative_news
        mock_finnhub.return_value = mock_finnhub_instance
        
        expected_analysis = {
            "ticker": "DECL",
            "company_name": "Declining Corp",
            "analysis_date": datetime.now().strftime('%Y-%m-%d'),
            "recommendation": "SELL",
            "confidence": "HIGH",
            "sentiment_score": -0.75,
            "risk_level": "VERY_HIGH",
            "volatility_assessment": "Extremely high volatility with downward momentum",
            "key_factors": [
                {"factor": "Earnings miss and guidance cut", "impact": "NEGATIVE"},
                {"factor": "SEC investigation", "impact": "NEGATIVE"},
                {"factor": "Loss of major customer", "impact": "NEGATIVE"}
            ],
            "summary": "Multiple significant negative catalysts suggest selling position.",
            "reasoning": "The combination of earnings miss, regulatory investigation, and major customer loss creates substantial downside risk.",
            "price_target": 120.0,
            "time_horizon": "SHORT_TERM",
            "warnings": ["Extreme volatility expected", "Regulatory risk"]
        }
        
        # Run workflow
        collector = DataCollector()
        collector.finnhub_client = mock_finnhub_instance
        
        stock_data, _ = collector.get_stock_data("DECL")
        news = collector.get_news_articles("DECL")
        
        dedup = ArticleDeduplicator(db_session)
        articles = dedup.save_articles(news, "DECL")
        
        llm_service = LLMService()
        with patch.object(
            llm_service,
            'generate_completion',
            return_value=AsyncMock(return_value=json.dumps(expected_analysis))()
        ):
            analysis = await llm_service.analyze_stock(
                ticker="DECL",
                company_name="Declining Corp",
                stock_data=stock_data,
                articles=articles
            )
        
        # Verify recommendation
        assert analysis['recommendation'] == "SELL"
        assert analysis['sentiment_score'] < 0
        assert analysis['risk_level'] in ["HIGH", "VERY_HIGH"]
        assert all(f['impact'] == "NEGATIVE" for f in analysis['key_factors'])
        assert len(analysis['warnings']) > 0
    
    @patch('app.services.data_collector.yf.Ticker')
    @patch('app.services.data_collector.finnhub.Client')
    async def test_scenario_mixed_signals_hold_recommendation(
        self,
        mock_finnhub,
        mock_yfinance,
        db_session
    ):
        """
        Scenario: Mixed positive and negative signals
        Expected: HOLD recommendation with MEDIUM/LOW confidence
        """
        
        # Mock stock with neutral performance
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = {
            'regularMarketPrice': 100.00,
            'previousClose': 99.50,  # Barely up
            'volume': 50000000,
            'averageVolume': 50000000,
            'marketCap': 100000000000,
            'trailingPE': 20.0,
            'beta': 1.3,
            'longName': 'Mixed Corp'
        }
        mock_yfinance.return_value = mock_ticker_instance
        
        # Mock mixed news
        mixed_news = [
            {
                'datetime': int(datetime.now().timestamp()),
                'headline': 'Mixed Corp Beats Revenue, Misses EPS',
                'summary': 'Revenue exceeded expectations but earnings per share fell short...',
                'url': 'https://example.com/1',
                'source': 'Finance'
            },
            {
                'datetime': int((datetime.now() - timedelta(days=1)).timestamp()),
                'headline': 'New Product Launch Shows Promise',
                'summary': 'Early adoption metrics are positive...',
                'url': 'https://example.com/2',
                'source': 'Tech News'
            },
            {
                'datetime': int((datetime.now() - timedelta(days=2)).timestamp()),
                'headline': 'CFO Departure Raises Questions',
                'summary': 'Chief Financial Officer announces unexpected resignation...',
                'url': 'https://example.com/3',
                'source': 'Business'
            }
        ]
        
        mock_finnhub_instance = Mock()
        mock_finnhub_instance.company_news.return_value = mixed_news
        mock_finnhub.return_value = mock_finnhub_instance
        
        expected_analysis = {
            "ticker": "MIXED",
            "company_name": "Mixed Corp",
            "analysis_date": datetime.now().strftime('%Y-%m-%d'),
            "recommendation": "HOLD",
            "confidence": "MEDIUM",
            "sentiment_score": 0.1,  # Slightly positive
            "risk_level": "MEDIUM",
            "volatility_assessment": "Moderate volatility with unclear direction",
            "key_factors": [
                {"factor": "Revenue beat expectations", "impact": "POSITIVE"},
                {"factor": "EPS miss", "impact": "NEGATIVE"},
                {"factor": "Promising product launch", "impact": "POSITIVE"},
                {"factor": "CFO departure", "impact": "NEGATIVE"}
            ],
            "summary": "Mixed signals suggest waiting for clearer direction.",
            "reasoning": "While revenue growth is positive and the new product shows promise, the EPS miss and CFO departure create uncertainty.",
            "price_target": None,
            "time_horizon": "SHORT_TERM",
            "warnings": ["Wait for clarity on leadership changes", "Monitor earnings trends"]
        }
        
        # Run workflow
        collector = DataCollector()
        collector.finnhub_client = mock_finnhub_instance
        
        stock_data, _ = collector.get_stock_data("MIXED")
        news = collector.get_news_articles("MIXED")
        
        dedup = ArticleDeduplicator(db_session)
        articles = dedup.save_articles(news, "MIXED")
        
        llm_service = LLMService()
        with patch.object(
            llm_service,
            'generate_completion',
            return_value=AsyncMock(return_value=json.dumps(expected_analysis))()
        ):
            analysis = await llm_service.analyze_stock(
                ticker="MIXED",
                company_name="Mixed Corp",
                stock_data=stock_data,
                articles=articles
            )
        
        # Verify recommendation
        assert analysis['recommendation'] == "HOLD"
        assert analysis['confidence'] in ["MEDIUM", "LOW"]
        assert abs(analysis['sentiment_score']) < 0.3  # Near neutral
        
        # Should have both positive and negative factors
        factors = analysis['key_factors']
        has_positive = any(f['impact'] == "POSITIVE" for f in factors)
        has_negative = any(f['impact'] == "NEGATIVE" for f in factors)
        assert has_positive and has_negative
    
    @patch('app.services.validator.DataCollector')
    def test_scenario_validation_accurate_buy(self, mock_collector_class, db_session):
        """
        Scenario: BUY recommendation followed by price increase
        Expected: ACCURATE validation with high accuracy score
        """
        
        # Create historical BUY recommendation
        rec = Recommendation(
            ticker="TEST",
            company_name="Test Corp",
            recommendation="BUY",
            confidence="HIGH",
            price_at_analysis=100.0,
            time_horizon="MEDIUM_TERM",
            analysis_date=datetime.now() - timedelta(days=8),
            validation_status="PENDING",
            raw_analysis_json={}
        )
        db_session.add(rec)
        db_session.commit()
        
        # Mock price went up 8%
        mock_collector = Mock()
        mock_stock = Mock()
        mock_stock.current_price = 108.0
        mock_collector.get_stock_data.return_value = (mock_stock, None)
        mock_collector_class.return_value = mock_collector
        
        # Validate
        validator = RecommendationValidator(db_session)
        validator.data_collector = mock_collector
        success, error = validator.validate_recommendation(rec)
        
        # Verify accurate validation
        assert success is True
        db_session.refresh(rec)
        assert rec.validation_status == "ACCURATE"
        assert rec.price_change_percent == pytest.approx(8.0, rel=0.01)
        assert rec.accuracy_score == 1.0  # Perfect score for BUY with 8% gain
    
    @patch('app.services.validator.DataCollector')
    def test_scenario_validation_inaccurate_sell(
        self,
        mock_collector_class,
        db_session
    ):
        """
        Scenario: SELL recommendation but price increased
        Expected: INACCURATE validation
        """
        
        rec = Recommendation(
            ticker="TEST",
            recommendation="SELL",
            confidence="MEDIUM",
            price_at_analysis=200.0,
            time_horizon="SHORT_TERM",
            analysis_date=datetime.now() - timedelta(days=4),
            validation_status="PENDING",
            raw_analysis_json={}
        )
        db_session.add(rec)
        db_session.commit()
        
        # Price actually went up 6%
        mock_collector = Mock()
        mock_stock = Mock()
        mock_stock.current_price = 212.0
        mock_collector.get_stock_data.return_value = (mock_stock, None)
        mock_collector_class.return_value = mock_collector
        
        validator = RecommendationValidator(db_session)
        validator.data_collector = mock_collector
        success, _ = validator.validate_recommendation(rec)
        
        assert success is True
        db_session.refresh(rec)
        assert rec.validation_status == "INACCURATE"
        assert rec.accuracy_score == 0.0  # SELL but went up 6%
