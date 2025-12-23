"""Data collection from yfinance and Finnhub"""
import yfinance as yf
import finnhub
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class NewsArticle:
    """News article data structure"""
    title: str
    content: str
    url: str
    source: str
    published_at: datetime


@dataclass
class StockData:
    """Stock fundamental and price data"""
    ticker: str
    company_name: str
    current_price: float
    prev_close: float
    day_change_percent: float
    volume: int
    avg_volume: float
    market_cap: Optional[float]
    pe_ratio: Optional[float]
    fifty_two_week_high: Optional[float]
    fifty_two_week_low: Optional[float]
    beta: Optional[float]


class DataCollector:
    """Collects data from yfinance and Finnhub"""
    
    def __init__(self):
        self.finnhub_client = None
        if settings.finnhub_api_key:
            self.finnhub_client = finnhub.Client(api_key=settings.finnhub_api_key)
    
    def get_stock_data(self, ticker: str) -> Tuple[Optional[StockData], Optional[str]]:
        """
        Get stock fundamentals and price data from yfinance
        
        Returns:
            Tuple of (StockData, error_message)
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Check if ticker is valid
            if not info or 'regularMarketPrice' not in info:
                return None, f"Invalid ticker symbol: {ticker}"
            
            # Get current price
            current_price = info.get('regularMarketPrice') or info.get('currentPrice')
            if not current_price:
                return None, f"Unable to fetch price data for {ticker}"
            
            prev_close = info.get('previousClose', current_price)
            day_change = ((current_price - prev_close) / prev_close * 100) if prev_close else 0
            
            stock_data = StockData(
                ticker=ticker.upper(),
                company_name=info.get('longName', ticker),
                current_price=current_price,
                prev_close=prev_close,
                day_change_percent=day_change,
                volume=info.get('volume', 0),
                avg_volume=info.get('averageVolume', 0),
                market_cap=info.get('marketCap'),
                pe_ratio=info.get('trailingPE'),
                fifty_two_week_high=info.get('fiftyTwoWeekHigh'),
                fifty_two_week_low=info.get('fiftyTwoWeekLow'),
                beta=info.get('beta')
            )
            
            return stock_data, None
            
        except Exception as e:
            logger.error(f"Error fetching stock data for {ticker}: {e}")
            return None, str(e)
    
    def get_news_articles(self, ticker: str, days_back: int = 7) -> List[NewsArticle]:
        """
        Get news articles from Finnhub
        
        Args:
            ticker: Stock ticker symbol
            days_back: Number of days to look back for news
            
        Returns:
            List of NewsArticle objects
        """
        if not self.finnhub_client:
            logger.warning("Finnhub API key not configured, skipping news collection")
            return []
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Format dates for Finnhub API (YYYY-MM-DD)
            from_date = start_date.strftime('%Y-%m-%d')
            to_date = end_date.strftime('%Y-%m-%d')
            
            # Fetch news from Finnhub
            news_data = self.finnhub_client.company_news(
                ticker.upper(),
                _from=from_date,
                to=to_date
            )
            
            articles = []
            for item in news_data:
                # Convert Unix timestamp to datetime
                published_at = datetime.fromtimestamp(item.get('datetime', 0))
                
                article = NewsArticle(
                    title=item.get('headline', ''),
                    content=item.get('summary', ''),
                    url=item.get('url', ''),
                    source=item.get('source', 'Unknown'),
                    published_at=published_at
                )
                articles.append(article)
            
            logger.info(f"Collected {len(articles)} news articles for {ticker}")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching news for {ticker}: {e}")
            return []
    
    def get_historical_prices(self, ticker: str, days_back: int = 30) -> Optional[Dict]:
        """
        Get historical price data
        
        Args:
            ticker: Stock ticker symbol
            days_back: Number of days of history to fetch
            
        Returns:
            Dictionary with price history or None
        """
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=f"{days_back}d")
            
            if hist.empty:
                return None
            
            return {
                'dates': hist.index.tolist(),
                'close': hist['Close'].tolist(),
                'volume': hist['Volume'].tolist(),
                'high': hist['High'].tolist(),
                'low': hist['Low'].tolist()
            }
            
        except Exception as e:
            logger.error(f"Error fetching historical prices for {ticker}: {e}")
            return None
