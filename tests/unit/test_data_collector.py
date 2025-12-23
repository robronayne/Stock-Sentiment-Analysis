"""Unit tests for data collection service"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from app.services.data_collector import DataCollector, StockData, NewsArticle


@pytest.mark.unit
class TestDataCollector:
    """Test DataCollector class"""
    
    @patch('app.services.data_collector.yf.Ticker')
    def test_get_stock_data_success(self, mock_ticker, mock_yfinance_info):
        """Test successful stock data retrieval"""
        # Setup mock
        mock_instance = Mock()
        mock_instance.info = mock_yfinance_info
        mock_ticker.return_value = mock_instance
        
        collector = DataCollector()
        stock_data, error = collector.get_stock_data("AAPL")
        
        # Assertions
        assert error is None
        assert stock_data is not None
        assert stock_data.ticker == "AAPL"
        assert stock_data.company_name == "Apple Inc."
        assert stock_data.current_price == 185.50
        assert stock_data.prev_close == 182.00
        assert stock_data.market_cap == 2900000000000
    
    @patch('app.services.data_collector.yf.Ticker')
    def test_get_stock_data_invalid_ticker(self, mock_ticker):
        """Test handling of invalid ticker"""
        # Setup mock to return empty info
        mock_instance = Mock()
        mock_instance.info = {}
        mock_ticker.return_value = mock_instance
        
        collector = DataCollector()
        stock_data, error = collector.get_stock_data("INVALID")
        
        # Should return None with error message
        assert stock_data is None
        assert error is not None
        assert "Invalid ticker" in error
    
    @patch('app.services.data_collector.yf.Ticker')
    def test_get_stock_data_day_change_calculation(self, mock_ticker):
        """Test day change percentage calculation"""
        mock_instance = Mock()
        mock_instance.info = {
            'regularMarketPrice': 110.0,
            'previousClose': 100.0,
            'volume': 1000000,
            'averageVolume': 1000000,
            'longName': 'Test Company'
        }
        mock_ticker.return_value = mock_instance
        
        collector = DataCollector()
        stock_data, error = collector.get_stock_data("TEST")
        
        assert error is None
        assert stock_data.day_change_percent == pytest.approx(10.0, rel=0.01)
    
    @patch('app.services.data_collector.finnhub.Client')
    def test_get_news_articles_success(self, mock_client, mock_finnhub_response):
        """Test successful news article retrieval"""
        # Setup mock
        mock_instance = Mock()
        mock_instance.company_news.return_value = mock_finnhub_response
        mock_client.return_value = mock_instance
        
        collector = DataCollector()
        collector.finnhub_client = mock_instance
        
        articles = collector.get_news_articles("AAPL", days_back=7)
        
        # Assertions
        assert len(articles) == 2
        assert all(isinstance(a, NewsArticle) for a in articles)
        assert articles[0].title == "Apple Reports Record Q4 Earnings"
        assert articles[0].source == "Tech News"
    
    def test_get_news_articles_no_api_key(self):
        """Test news collection without API key"""
        collector = DataCollector()
        collector.finnhub_client = None
        
        articles = collector.get_news_articles("AAPL")
        
        # Should return empty list without error
        assert articles == []
    
    @patch('app.services.data_collector.finnhub.Client')
    def test_get_news_articles_api_error(self, mock_client):
        """Test handling of API errors"""
        mock_instance = Mock()
        mock_instance.company_news.side_effect = Exception("API Error")
        mock_client.return_value = mock_instance
        
        collector = DataCollector()
        collector.finnhub_client = mock_instance
        
        articles = collector.get_news_articles("AAPL")
        
        # Should handle error gracefully
        assert articles == []
    
    @patch('app.services.data_collector.yf.Ticker')
    def test_get_historical_prices_success(self, mock_ticker):
        """Test historical price retrieval"""
        # Setup mock
        import pandas as pd
        mock_hist = pd.DataFrame({
            'Close': [100.0, 101.0, 102.0],
            'Volume': [1000000, 1100000, 1200000],
            'High': [102.0, 103.0, 104.0],
            'Low': [99.0, 100.0, 101.0]
        })
        mock_instance = Mock()
        mock_instance.history.return_value = mock_hist
        mock_ticker.return_value = mock_instance
        
        collector = DataCollector()
        history = collector.get_historical_prices("AAPL", days_back=30)
        
        assert history is not None
        assert 'close' in history
        assert 'volume' in history
        assert len(history['close']) == 3
    
    @patch('app.services.data_collector.yf.Ticker')
    def test_get_historical_prices_empty(self, mock_ticker):
        """Test handling of empty price history"""
        import pandas as pd
        mock_instance = Mock()
        mock_instance.history.return_value = pd.DataFrame()
        mock_ticker.return_value = mock_instance
        
        collector = DataCollector()
        history = collector.get_historical_prices("AAPL")
        
        assert history is None
