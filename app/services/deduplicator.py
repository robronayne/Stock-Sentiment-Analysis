"""Article deduplication service"""
import hashlib
from typing import List, Optional
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
import logging

from app.models import Article
from app.services.data_collector import NewsArticle

logger = logging.getLogger(__name__)


class ArticleDeduplicator:
    """Handles article deduplication logic"""
    
    def __init__(self, db: Session):
        self.db = db
    
    @staticmethod
    def generate_article_hash(title: str, content: str) -> str:
        """
        Generate unique hash for article based on title and content
        
        Args:
            title: Article title
            content: Article content/summary
            
        Returns:
            SHA-256 hash string
        """
        # Normalize text: lowercase, strip whitespace
        normalized_title = title.lower().strip()
        normalized_content = (content or "").lower().strip()[:500]  # First 500 chars
        
        # Combine and hash
        combined = f"{normalized_title}|{normalized_content}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    def is_duplicate_by_hash(self, article_hash: str) -> bool:
        """
        Check if article with this hash already exists
        
        Args:
            article_hash: SHA-256 hash of article
            
        Returns:
            True if duplicate exists
        """
        exists = self.db.query(Article).filter(
            Article.article_hash == article_hash
        ).first()
        return exists is not None
    
    def is_duplicate_by_url(self, url: str) -> bool:
        """
        Check if article with this URL already exists
        
        Args:
            url: Article URL
            
        Returns:
            True if duplicate exists
        """
        if not url:
            return False
        
        exists = self.db.query(Article).filter(
            Article.url == url
        ).first()
        return exists is not None
    
    def find_similar_articles(
        self, 
        title: str, 
        ticker: str, 
        similarity_threshold: float = 0.85
    ) -> List[Article]:
        """
        Find articles with similar titles (fuzzy matching)
        
        Args:
            title: Article title to check
            ticker: Stock ticker
            similarity_threshold: Minimum similarity ratio (0-1)
            
        Returns:
            List of similar articles
        """
        # Get recent articles for the same ticker
        recent_articles = self.db.query(Article).filter(
            Article.ticker == ticker
        ).order_by(Article.published_at.desc()).limit(50).all()
        
        similar = []
        title_lower = title.lower().strip()
        
        for article in recent_articles:
            similarity = SequenceMatcher(
                None,
                title_lower,
                article.title.lower().strip()
            ).ratio()
            
            if similarity >= similarity_threshold:
                similar.append(article)
        
        return similar
    
    def is_duplicate(
        self, 
        news_article: NewsArticle, 
        ticker: str,
        check_fuzzy: bool = True
    ) -> bool:
        """
        Comprehensive duplicate check
        
        Args:
            news_article: NewsArticle to check
            ticker: Stock ticker
            check_fuzzy: Whether to perform fuzzy title matching
            
        Returns:
            True if article is a duplicate
        """
        # Generate hash
        article_hash = self.generate_article_hash(
            news_article.title,
            news_article.content
        )
        
        # Check hash
        if self.is_duplicate_by_hash(article_hash):
            logger.debug(f"Duplicate found by hash: {news_article.title[:50]}")
            return True
        
        # Check URL
        if news_article.url and self.is_duplicate_by_url(news_article.url):
            logger.debug(f"Duplicate found by URL: {news_article.url}")
            return True
        
        # Optional: Check fuzzy title matching
        if check_fuzzy:
            similar = self.find_similar_articles(news_article.title, ticker)
            if similar:
                logger.debug(f"Duplicate found by fuzzy matching: {news_article.title[:50]}")
                return True
        
        return False
    
    def filter_duplicates(
        self, 
        news_articles: List[NewsArticle], 
        ticker: str
    ) -> List[NewsArticle]:
        """
        Filter out duplicate articles from a list
        
        Args:
            news_articles: List of NewsArticle objects
            ticker: Stock ticker
            
        Returns:
            List of non-duplicate articles
        """
        unique_articles = []
        seen_hashes = set()
        
        for article in news_articles:
            article_hash = self.generate_article_hash(article.title, article.content)
            
            # Skip if we've seen this hash in current batch
            if article_hash in seen_hashes:
                continue
            
            # Skip if duplicate in database
            if self.is_duplicate(article, ticker):
                continue
            
            unique_articles.append(article)
            seen_hashes.add(article_hash)
        
        logger.info(
            f"Filtered {len(news_articles) - len(unique_articles)} duplicates, "
            f"{len(unique_articles)} unique articles remaining"
        )
        
        return unique_articles
    
    def save_articles(
        self, 
        news_articles: List[NewsArticle], 
        ticker: str
    ) -> List[Article]:
        """
        Save articles to database after deduplication
        
        Args:
            news_articles: List of NewsArticle objects
            ticker: Stock ticker
            
        Returns:
            List of saved Article model instances
        """
        # Filter duplicates
        unique_articles = self.filter_duplicates(news_articles, ticker)
        
        saved_articles = []
        for news_article in unique_articles:
            article_hash = self.generate_article_hash(
                news_article.title,
                news_article.content
            )
            
            article = Article(
                article_hash=article_hash,
                url=news_article.url,
                ticker=ticker.upper(),
                title=news_article.title,
                content=news_article.content,
                source=news_article.source,
                published_at=news_article.published_at
            )
            
            self.db.add(article)
            saved_articles.append(article)
        
        try:
            self.db.commit()
            logger.info(f"Saved {len(saved_articles)} new articles for {ticker}")
        except Exception as e:
            logger.error(f"Error saving articles: {e}")
            self.db.rollback()
            raise
        
        return saved_articles
