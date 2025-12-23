"""Unit tests for article deduplication service"""
import pytest
from app.services.deduplicator import ArticleDeduplicator
from app.services.data_collector import NewsArticle
from datetime import datetime


@pytest.mark.unit
class TestArticleDeduplicator:
    """Test ArticleDeduplicator class"""
    
    def test_generate_article_hash_consistency(self):
        """Test that same content generates same hash"""
        title = "Apple Reports Earnings"
        content = "Apple Inc. reported strong earnings..."
        
        hash1 = ArticleDeduplicator.generate_article_hash(title, content)
        hash2 = ArticleDeduplicator.generate_article_hash(title, content)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64 hex characters
    
    def test_generate_article_hash_case_insensitive(self):
        """Test that hash is case-insensitive"""
        hash1 = ArticleDeduplicator.generate_article_hash(
            "Apple Reports Earnings",
            "Strong performance"
        )
        hash2 = ArticleDeduplicator.generate_article_hash(
            "APPLE REPORTS EARNINGS",
            "STRONG PERFORMANCE"
        )
        
        assert hash1 == hash2
    
    def test_generate_article_hash_whitespace_normalized(self):
        """Test that extra whitespace is normalized"""
        hash1 = ArticleDeduplicator.generate_article_hash(
            "Apple Reports",
            "Content here"
        )
        hash2 = ArticleDeduplicator.generate_article_hash(
            "  Apple   Reports  ",
            "  Content   here  "
        )
        
        assert hash1 == hash2
    
    def test_generate_article_hash_different_content(self):
        """Test that different content generates different hash"""
        hash1 = ArticleDeduplicator.generate_article_hash(
            "Apple Reports Earnings",
            "Content 1"
        )
        hash2 = ArticleDeduplicator.generate_article_hash(
            "Microsoft Reports Earnings",
            "Content 2"
        )
        
        assert hash1 != hash2
    
    def test_is_duplicate_by_hash(self, db_session, sample_articles_in_db):
        """Test duplicate detection by hash"""
        dedup = ArticleDeduplicator(db_session)
        
        # Get hash of first article
        article = sample_articles_in_db[0]
        
        # Should detect duplicate
        assert dedup.is_duplicate_by_hash(article.article_hash) is True
        
        # Should not detect non-existent hash
        assert dedup.is_duplicate_by_hash("nonexistent_hash") is False
    
    def test_is_duplicate_by_url(self, db_session, sample_articles_in_db):
        """Test duplicate detection by URL"""
        dedup = ArticleDeduplicator(db_session)
        
        article = sample_articles_in_db[0]
        
        # Should detect duplicate URL
        assert dedup.is_duplicate_by_url(article.url) is True
        
        # Should not detect non-existent URL
        assert dedup.is_duplicate_by_url("https://example.com/nonexistent") is False
        
        # Should handle None URL
        assert dedup.is_duplicate_by_url(None) is False
    
    def test_find_similar_articles(self, db_session, sample_articles_in_db):
        """Test fuzzy title matching"""
        dedup = ArticleDeduplicator(db_session)
        
        # Very similar title (should match)
        similar = dedup.find_similar_articles(
            "Apple Reports Record Q4 Earnings Results",  # Slight variation
            "AAPL",
            similarity_threshold=0.85
        )
        
        assert len(similar) > 0
    
    def test_find_similar_articles_no_match(self, db_session, sample_articles_in_db):
        """Test that completely different titles don't match"""
        dedup = ArticleDeduplicator(db_session)
        
        similar = dedup.find_similar_articles(
            "Microsoft Announces Layoffs",  # Completely different
            "AAPL",
            similarity_threshold=0.85
        )
        
        assert len(similar) == 0
    
    def test_is_duplicate_comprehensive(
        self, 
        db_session, 
        sample_news_articles,
        sample_articles_in_db
    ):
        """Test comprehensive duplicate detection"""
        dedup = ArticleDeduplicator(db_session)
        
        # Test with exact duplicate (same title/content)
        duplicate = sample_news_articles[0]
        assert dedup.is_duplicate(duplicate, "AAPL") is True
        
        # Test with new article
        new_article = NewsArticle(
            title="Completely New Article",
            content="This is brand new content",
            url="https://example.com/new",
            source="New Source",
            published_at=datetime.now()
        )
        assert dedup.is_duplicate(new_article, "AAPL") is False
    
    def test_filter_duplicates(
        self,
        db_session,
        sample_news_articles,
        sample_articles_in_db,
        duplicate_news_article
    ):
        """Test filtering duplicates from list"""
        dedup = ArticleDeduplicator(db_session)
        
        # Mix of new and duplicate articles
        articles = [
            NewsArticle(
                title="Brand New Article 1",
                content="New content 1",
                url="https://example.com/new1",
                source="Source",
                published_at=datetime.now()
            ),
            sample_news_articles[0],  # Duplicate (in DB)
            NewsArticle(
                title="Brand New Article 2",
                content="New content 2",
                url="https://example.com/new2",
                source="Source",
                published_at=datetime.now()
            ),
            duplicate_news_article  # Duplicate (same content)
        ]
        
        unique = dedup.filter_duplicates(articles, "AAPL")
        
        # Should only keep the 2 brand new articles
        assert len(unique) == 2
        assert all("Brand New Article" in a.title for a in unique)
    
    def test_save_articles(self, db_session, sample_news_articles):
        """Test saving articles with automatic deduplication"""
        dedup = ArticleDeduplicator(db_session)
        
        # Save articles first time
        saved1 = dedup.save_articles(sample_news_articles, "AAPL")
        assert len(saved1) == len(sample_news_articles)
        
        # Try to save again (should deduplicate)
        saved2 = dedup.save_articles(sample_news_articles, "AAPL")
        assert len(saved2) == 0  # All duplicates
    
    def test_save_articles_partial_duplicates(
        self,
        db_session,
        sample_news_articles
    ):
        """Test saving mix of new and duplicate articles"""
        dedup = ArticleDeduplicator(db_session)
        
        # Save first article
        dedup.save_articles([sample_news_articles[0]], "AAPL")
        
        # Try to save all articles (first is duplicate)
        saved = dedup.save_articles(sample_news_articles, "AAPL")
        
        # Should only save the last 2 articles
        assert len(saved) == 2
