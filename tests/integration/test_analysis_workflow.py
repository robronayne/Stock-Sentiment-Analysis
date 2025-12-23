"""Integration tests for complete analysis workflow"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime

from app.services.data_collector import DataCollector
from app.services.deduplicator import ArticleDeduplicator
from app.services.llm_service import LLMService
from app.models import Article, Recommendation


@pytest.mark.integration
class TestAnalysisWorkflow:
    """Test complete analysis workflow end-to-end"""
    
    @patch('app.services.data_collector.yf.Ticker')
    @patch('app.services.data_collector.finnhub.Client')
    async def test_complete_analysis_workflow(
        self,
        mock_finnhub,
        mock_yfinance,
        db_session,
        mock_yfinance_info,
        mock_finnhub_response,
        sample_llm_analysis
    ):
        """Test complete workflow from data collection to recommendation"""
        
        # Setup mocks
        # 1. Mock yfinance
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = mock_yfinance_info
        mock_yfinance.return_value = mock_ticker_instance
        
        # 2. Mock Finnhub
        mock_finnhub_instance = Mock()
        mock_finnhub_instance.company_news.return_value = mock_finnhub_response
        mock_finnhub.return_value = mock_finnhub_instance
        
        # Step 1: Collect stock data
        collector = DataCollector()
        collector.finnhub_client = mock_finnhub_instance
        
        stock_data, error = collector.get_stock_data("AAPL")
        assert error is None
        assert stock_data.ticker == "AAPL"
        
        # Step 2: Collect news articles
        news_articles = collector.get_news_articles("AAPL", days_back=7)
        assert len(news_articles) > 0
        
        # Step 3: Deduplicate and save articles
        deduplicator = ArticleDeduplicator(db_session)
        saved_articles = deduplicator.save_articles(news_articles, "AAPL")
        assert len(saved_articles) > 0
        
        # Verify articles are in database
        db_articles = db_session.query(Article).filter(
            Article.ticker == "AAPL"
        ).all()
        assert len(db_articles) == len(saved_articles)
        
        # Step 4: Generate LLM analysis
        llm_service = LLMService()
        
        with patch.object(
            llm_service,
            'generate_completion',
            return_value=AsyncMock(return_value=json.dumps(sample_llm_analysis))()
        ):
            analysis = await llm_service.analyze_stock(
                ticker="AAPL",
                company_name=stock_data.company_name,
                stock_data=stock_data,
                articles=db_articles,
                price_history=None
            )
        
        assert analysis is not None
        assert analysis['recommendation'] in ["BUY", "SELL", "SHORT", "HOLD"]
        assert analysis['confidence'] in ["HIGH", "MEDIUM", "LOW"]
        
        # Step 5: Save recommendation to database
        recommendation = Recommendation(
            ticker="AAPL",
            company_name=stock_data.company_name,
            recommendation=analysis['recommendation'],
            confidence=analysis['confidence'],
            sentiment_score=analysis['sentiment_score'],
            risk_level=analysis['risk_level'],
            summary=analysis['summary'],
            reasoning=analysis['reasoning'],
            price_at_analysis=stock_data.current_price,
            price_target=analysis.get('price_target'),
            time_horizon=analysis['time_horizon'],
            raw_analysis_json=analysis,
            article_ids=[a.id for a in db_articles]
        )
        
        db_session.add(recommendation)
        db_session.commit()
        
        # Verify recommendation is saved
        saved_rec = db_session.query(Recommendation).filter(
            Recommendation.ticker == "AAPL"
        ).first()
        
        assert saved_rec is not None
        assert saved_rec.recommendation == analysis['recommendation']
        assert saved_rec.article_ids == [a.id for a in db_articles]
    
    @patch('app.services.data_collector.yf.Ticker')
    @patch('app.services.data_collector.finnhub.Client')
    async def test_duplicate_news_handling_in_workflow(
        self,
        mock_finnhub,
        mock_yfinance,
        db_session,
        mock_yfinance_info,
        mock_finnhub_response
    ):
        """Test that duplicate news is properly handled in workflow"""
        
        # Setup mocks
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = mock_yfinance_info
        mock_yfinance.return_value = mock_ticker_instance
        
        mock_finnhub_instance = Mock()
        mock_finnhub_instance.company_news.return_value = mock_finnhub_response
        mock_finnhub.return_value = mock_finnhub_instance
        
        collector = DataCollector()
        collector.finnhub_client = mock_finnhub_instance
        deduplicator = ArticleDeduplicator(db_session)
        
        # First collection
        news_1 = collector.get_news_articles("AAPL")
        saved_1 = deduplicator.save_articles(news_1, "AAPL")
        count_1 = len(saved_1)
        
        # Second collection (same news)
        news_2 = collector.get_news_articles("AAPL")
        saved_2 = deduplicator.save_articles(news_2, "AAPL")
        count_2 = len(saved_2)
        
        # Should not save duplicates
        assert count_1 > 0
        assert count_2 == 0
        
        # Total articles should be same as first collection
        total_articles = db_session.query(Article).filter(
            Article.ticker == "AAPL"
        ).count()
        assert total_articles == count_1
    
    @patch('app.services.data_collector.yf.Ticker')
    async def test_analysis_with_no_news(
        self,
        mock_yfinance,
        db_session,
        mock_yfinance_info,
        sample_llm_analysis
    ):
        """Test analysis workflow when no news is available"""
        
        # Setup mock
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = mock_yfinance_info
        mock_yfinance.return_value = mock_ticker_instance
        
        # Collect stock data
        collector = DataCollector()
        stock_data, error = collector.get_stock_data("AAPL")
        assert error is None
        
        # No Finnhub client (no news)
        collector.finnhub_client = None
        news_articles = collector.get_news_articles("AAPL")
        assert len(news_articles) == 0
        
        # LLM should still be able to analyze with just fundamentals
        llm_service = LLMService()
        
        with patch.object(
            llm_service,
            'generate_completion',
            return_value=AsyncMock(return_value=json.dumps(sample_llm_analysis))()
        ):
            analysis = await llm_service.analyze_stock(
                ticker="AAPL",
                company_name=stock_data.company_name,
                stock_data=stock_data,
                articles=[],  # No articles
                price_history=None
            )
        
        assert analysis is not None
        # With no news, might recommend HOLD with lower confidence
        assert analysis['recommendation'] in ["BUY", "SELL", "SHORT", "HOLD"]
    
    @patch('app.services.data_collector.yf.Ticker')
    @patch('app.services.data_collector.finnhub.Client')
    async def test_workflow_with_mixed_sentiment_news(
        self,
        mock_finnhub,
        mock_yfinance,
        db_session,
        mock_yfinance_info,
        sample_llm_analysis
    ):
        """Test analysis with both positive and negative news"""
        
        # Mock mixed sentiment news
        mixed_news = [
            {
                'datetime': int(datetime.now().timestamp()),
                'headline': 'Apple Beats Earnings Expectations',
                'summary': 'Strong quarterly results exceed analyst forecasts...',
                'url': 'https://example.com/positive',
                'source': 'News Source'
            },
            {
                'datetime': int(datetime.now().timestamp()),
                'headline': 'Apple Faces Supply Chain Issues',
                'summary': 'Significant disruptions in component supply...',
                'url': 'https://example.com/negative',
                'source': 'News Source'
            },
            {
                'datetime': int(datetime.now().timestamp()),
                'headline': 'Apple Announces Layoffs',
                'summary': 'Company reducing workforce by 5%...',
                'url': 'https://example.com/negative2',
                'source': 'News Source'
            }
        ]
        
        # Setup mocks
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = mock_yfinance_info
        mock_yfinance.return_value = mock_ticker_instance
        
        mock_finnhub_instance = Mock()
        mock_finnhub_instance.company_news.return_value = mixed_news
        mock_finnhub.return_value = mock_finnhub_instance
        
        # Run workflow
        collector = DataCollector()
        collector.finnhub_client = mock_finnhub_instance
        
        stock_data, _ = collector.get_stock_data("AAPL")
        news_articles = collector.get_news_articles("AAPL")
        
        deduplicator = ArticleDeduplicator(db_session)
        saved_articles = deduplicator.save_articles(news_articles, "AAPL")
        
        # Modify sample analysis to reflect mixed sentiment
        mixed_sentiment_analysis = sample_llm_analysis.copy()
        mixed_sentiment_analysis['sentiment_score'] = 0.1  # Slightly positive
        mixed_sentiment_analysis['confidence'] = "MEDIUM"  # Lower confidence
        mixed_sentiment_analysis['recommendation'] = "HOLD"  # Cautious
        
        llm_service = LLMService()
        with patch.object(
            llm_service,
            'generate_completion',
            return_value=AsyncMock(
                return_value=json.dumps(mixed_sentiment_analysis)
            )()
        ):
            analysis = await llm_service.analyze_stock(
                ticker="AAPL",
                company_name=stock_data.company_name,
                stock_data=stock_data,
                articles=saved_articles
            )
        
        # With mixed news, should be more cautious
        assert analysis is not None
        # Sentiment should reflect mixed signals
        assert -1.0 <= analysis['sentiment_score'] <= 1.0
