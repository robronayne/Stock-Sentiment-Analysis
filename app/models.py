"""SQLAlchemy database models"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON
from sqlalchemy.sql import func
from datetime import datetime

from app.database import Base


class Article(Base):
    """News article with deduplication and usage tracking"""
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, index=True)
    article_hash = Column(String(64), unique=True, nullable=False, index=True)
    url = Column(String(1024), unique=True)
    ticker = Column(String(10), nullable=False, index=True)
    title = Column(Text, nullable=False)
    content = Column(Text)
    source = Column(String(100))
    published_at = Column(DateTime, nullable=False, index=True)
    collected_at = Column(DateTime, default=func.now())
    sentiment_score = Column(Float)
    
    # Usage tracking for day trading approach
    used_in_analysis = Column(Integer, default=0)  # Using Integer instead of Boolean for MySQL compatibility
    last_used_date = Column(DateTime, nullable=True)
    used_in_recommendation_id = Column(Integer, nullable=True)


class Recommendation(Base):
    """Stock analysis recommendation"""
    __tablename__ = "recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    company_name = Column(String(255))
    analysis_date = Column(DateTime, default=func.now(), index=True)
    recommendation = Column(String(20), nullable=False)
    confidence = Column(String(20), nullable=False)
    sentiment_score = Column(Float)
    risk_level = Column(String(20))
    summary = Column(Text)
    reasoning = Column(Text)
    price_at_analysis = Column(Float)
    price_target = Column(Float)
    time_horizon = Column(String(20))
    raw_analysis_json = Column(JSON)
    article_ids = Column(JSON)
    
    # Validation fields
    validation_date = Column(DateTime)
    validation_status = Column(String(20), default="PENDING", index=True)
    price_at_validation = Column(Float)
    price_change_percent = Column(Float)
    actual_outcome = Column(Text)
    accuracy_score = Column(Float)


class ValidationMetric(Base):
    """Daily validation metrics"""
    __tablename__ = "validation_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, unique=True)
    total_recommendations = Column(Integer)
    accurate_count = Column(Integer)
    partially_accurate_count = Column(Integer)
    inaccurate_count = Column(Integer)
    avg_accuracy_score = Column(Float)
    recommendations_by_confidence = Column(JSON)
    created_at = Column(DateTime, default=func.now())


class RateLimit(Base):
    """Rate limiting records"""
    __tablename__ = "rate_limits"
    
    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String(255), nullable=False, index=True)
    endpoint = Column(String(255), nullable=False)
    request_time = Column(DateTime, default=func.now(), index=True)
