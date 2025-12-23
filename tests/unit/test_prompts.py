"""Unit tests for prompt engineering"""
import pytest
from app.prompts.analysis_prompt import (
    format_stock_fundamentals,
    format_news_articles,
    format_price_history,
    build_analysis_prompt
)


@pytest.mark.unit
class TestPromptFormatting:
    """Test prompt formatting functions"""
    
    def test_format_stock_fundamentals(self, sample_stock_data):
        """Test stock fundamentals formatting"""
        result = format_stock_fundamentals(sample_stock_data)
        
        assert "Current Price: $185.50" in result
        assert "Previous Close: $182.00" in result
        assert "Day Change: +1.92%" in result
        assert "Market Cap:" in result
        assert "P/E Ratio:" in result
    
    def test_format_stock_fundamentals_missing_optional_data(self):
        """Test formatting with missing optional fields"""
        from app.services.data_collector import StockData
        
        stock = StockData(
            ticker="TEST",
            company_name="Test Inc.",
            current_price=100.0,
            prev_close=95.0,
            day_change_percent=5.26,
            volume=1000000,
            avg_volume=900000,
            market_cap=None,  # Missing
            pe_ratio=None,  # Missing
            fifty_two_week_high=None,
            fifty_two_week_low=None,
            beta=None
        )
        
        result = format_stock_fundamentals(stock)
        
        assert "Current Price:" in result
        assert "N/A" in result  # For missing data
    
    def test_format_news_articles_with_articles(self, sample_articles_in_db):
        """Test news articles formatting"""
        result = format_news_articles(sample_articles_in_db)
        
        assert "Article 1:" in result
        assert "Apple Reports Record Q4 Earnings" in result
        assert "Source:" in result
        assert "Summary:" in result
    
    def test_format_news_articles_empty(self):
        """Test formatting with no articles"""
        result = format_news_articles([])
        
        assert "No recent news articles available" in result
    
    def test_format_news_articles_limits_to_10(self, sample_articles_in_db):
        """Test that only first 10 articles are included"""
        # Create 15 articles
        many_articles = sample_articles_in_db * 5  # Repeat to get 15
        
        result = format_news_articles(many_articles)
        
        # Count article headers
        count = result.count("Article ")
        assert count <= 10
    
    def test_format_price_history_with_data(self, sample_price_history):
        """Test price history formatting"""
        result = format_price_history(sample_price_history)
        
        assert "7-Day Change:" in result
        assert "30-Day Change:" in result
        assert "Recent Volatility" in result
        assert "%" in result
    
    def test_format_price_history_empty(self):
        """Test formatting with no price history"""
        result = format_price_history(None)
        
        assert "No historical price data available" in result
    
    def test_format_price_history_insufficient_data(self):
        """Test formatting with insufficient data"""
        history = {
            'close': [100.0],  # Only 1 data point
            'volume': [1000000]
        }
        
        result = format_price_history(history)
        
        assert "Insufficient price history" in result
    
    def test_build_analysis_prompt_complete(
        self,
        sample_stock_data,
        sample_articles_in_db,
        sample_price_history
    ):
        """Test building complete analysis prompt"""
        prompt = build_analysis_prompt(
            ticker="AAPL",
            company_name="Apple Inc.",
            stock_data=sample_stock_data,
            articles=sample_articles_in_db,
            price_history=sample_price_history
        )
        
        # Check all major sections are included
        assert "AAPL" in prompt
        assert "Apple Inc." in prompt
        assert "STOCK INFORMATION" in prompt
        assert "FUNDAMENTAL DATA" in prompt
        assert "PRICE TRENDS" in prompt
        assert "RECENT NEWS" in prompt
        assert "YOUR TASK" in prompt
        assert "OUTPUT FORMAT" in prompt
        
        # Check guidelines are included
        assert "objective" in prompt.lower()
        assert "data-driven" in prompt.lower()
        assert "JSON" in prompt
        
        # Check required output fields are specified
        assert "recommendation" in prompt
        assert "confidence" in prompt
        assert "sentiment_score" in prompt
        assert "risk_level" in prompt
    
    def test_build_analysis_prompt_without_price_history(
        self,
        sample_stock_data,
        sample_articles_in_db
    ):
        """Test building prompt without price history"""
        prompt = build_analysis_prompt(
            ticker="AAPL",
            company_name="Apple Inc.",
            stock_data=sample_stock_data,
            articles=sample_articles_in_db,
            price_history=None
        )
        
        assert "No price history available" in prompt
    
    def test_prompt_includes_risk_guidelines(
        self,
        sample_stock_data,
        sample_articles_in_db
    ):
        """Test that prompt includes risk assessment guidelines"""
        prompt = build_analysis_prompt(
            ticker="AAPL",
            company_name="Apple Inc.",
            stock_data=sample_stock_data,
            articles=sample_articles_in_db
        )
        
        # Check for risk-related guidelines
        assert "volatile" in prompt.lower() or "volatility" in prompt.lower()
        assert "risk" in prompt.lower()
        assert "HOLD" in prompt  # Fallback recommendation
    
    def test_prompt_specifies_json_output(
        self,
        sample_stock_data,
        sample_articles_in_db
    ):
        """Test that prompt clearly specifies JSON output"""
        prompt = build_analysis_prompt(
            ticker="AAPL",
            company_name="Apple Inc.",
            stock_data=sample_stock_data,
            articles=sample_articles_in_db
        )
        
        assert "JSON" in prompt
        assert "{" in prompt and "}" in prompt
        assert "ONLY" in prompt or "only" in prompt  # Emphasize JSON-only output
