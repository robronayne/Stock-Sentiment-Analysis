"""Pydantic schemas for API request/response validation"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class RecommendationType(str, Enum):
    """Trading recommendation types"""
    BUY = "BUY"
    SELL = "SELL"
    SHORT = "SHORT"
    HOLD = "HOLD"


class ConfidenceLevel(str, Enum):
    """Confidence levels"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RiskLevel(str, Enum):
    """Risk assessment levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class TimeHorizon(str, Enum):
    """Investment time horizons"""
    SHORT_TERM = "SHORT_TERM"  # 3 days
    MEDIUM_TERM = "MEDIUM_TERM"  # 7 days
    LONG_TERM = "LONG_TERM"  # 30 days


class ValidationStatus(str, Enum):
    """Validation status types"""
    PENDING = "PENDING"
    ACCURATE = "ACCURATE"
    PARTIALLY_ACCURATE = "PARTIALLY_ACCURATE"
    INACCURATE = "INACCURATE"


class Impact(str, Enum):
    """Factor impact types"""
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class KeyFactor(BaseModel):
    """A key factor in the analysis"""
    factor: str
    impact: Impact


class AnalysisRequest(BaseModel):
    """Request to analyze a stock"""
    ticker: str = Field(..., description="Stock ticker symbol")
    force_refresh: bool = Field(False, description="Force new analysis even if recent one exists")


class AnalysisResponse(BaseModel):
    """Response from stock analysis"""
    ticker: str
    company_name: str
    analysis_date: datetime
    recommendation: RecommendationType
    confidence: ConfidenceLevel
    sentiment_score: float = Field(..., ge=-1.0, le=1.0)
    risk_level: RiskLevel
    volatility_assessment: str
    key_factors: List[KeyFactor]
    summary: str
    reasoning: str
    price_target: Optional[float]
    time_horizon: TimeHorizon
    warnings: List[str]
    class Config:
        from_attributes = True


class ArticleInfo(BaseModel):
    """Article information with usage tracking"""
    id: int
    ticker: str
    title: str
    content: str
    source: str
    published_at: datetime
    collected_at: datetime
    sentiment_score: Optional[float] = None
    
    # Usage tracking for day trading mode
    used_in_analysis: int = 0
    last_used_date: Optional[datetime] = None
    used_in_recommendation_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class RecommendationDetail(BaseModel):
    """Detailed recommendation with validation info"""
    id: int
    ticker: str
    company_name: Optional[str]
    analysis_date: datetime
    recommendation: RecommendationType
    confidence: ConfidenceLevel
    sentiment_score: Optional[float]
    risk_level: Optional[RiskLevel]
    summary: Optional[str]
    reasoning: Optional[str]
    price_at_analysis: Optional[float]
    price_target: Optional[float]
    time_horizon: Optional[TimeHorizon]
    
    # Validation info
    validation_status: ValidationStatus
    validation_date: Optional[datetime]
    price_at_validation: Optional[float]
    price_change_percent: Optional[float]
    accuracy_score: Optional[float]
    actual_outcome: Optional[str]
    
    class Config:
        from_attributes = True


class ValidationMetricsResponse(BaseModel):
    """Overall validation metrics"""
    date: datetime
    total_recommendations: int
    accurate_count: int
    partially_accurate_count: int
    inaccurate_count: int
    avg_accuracy_score: float
    accuracy_percentage: float
    recommendations_by_confidence: dict
    
    class Config:
        from_attributes = True


class TickerMetrics(BaseModel):
    """Metrics for a specific ticker"""
    ticker: str
    total_recommendations: int
    avg_accuracy_score: float
    best_recommendation: Optional[RecommendationDetail]
    worst_recommendation: Optional[RecommendationDetail]


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    database: str
    ollama: str
    timestamp: datetime
