"""Main FastAPI application"""
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from app.database import get_db, engine, Base
from app.config import get_settings
from app import models, schemas
from app.services.data_collector import DataCollector
from app.services.deduplicator import ArticleDeduplicator
from app.services.llm_service import LLMService
from app.services.validator import RecommendationValidator
from app.background.jobs import setup_scheduler, shutdown_scheduler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Stock Sentiment Analysis Bot",
    description="AI-powered market sentiment analysis with recommendation tracking",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize services
data_collector = DataCollector()
llm_service = LLMService()


@app.on_event("startup")
async def startup_event():
    """Initialize background jobs on startup"""
    logger.info("Starting up application...")
    
    # Ensure LLM model is available
    logger.info(f"Checking Ollama model: {settings.ollama_model}")
    model_ready = await llm_service.ensure_model_pulled()
    if not model_ready:
        logger.warning("LLM model not ready - analysis requests may fail")
    
    # Start background scheduler
    setup_scheduler()
    logger.info("Background scheduler started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down application...")
    shutdown_scheduler()


@app.get("/", response_model=dict)
async def root():
    """Root endpoint"""
    return {
        "service": "Stock Sentiment Analysis Bot",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "analyze": "POST /api/analyze/{ticker}",
            "recommendations": "GET /api/recommendations",
            "metrics": "GET /api/metrics"
        }
    }


@app.get("/health", response_model=schemas.HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    # Check database
    try:
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    # Check Ollama
    ollama_healthy = await llm_service.check_health()
    ollama_status = "healthy" if ollama_healthy else "unhealthy"
    
    overall_status = "healthy" if db_status == "healthy" and ollama_status == "healthy" else "degraded"
    
    return schemas.HealthResponse(
        status=overall_status,
        database=db_status,
        ollama=ollama_status,
        timestamp=datetime.now()
    )


@app.post("/api/analyze/{ticker}", response_model=schemas.AnalysisResponse)
async def analyze_stock(
    ticker: str,
    force_refresh: bool = False,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Analyze a stock and generate recommendation
    
    Args:
        ticker: Stock ticker symbol
        force_refresh: Force new analysis even if recent one exists
        
    Returns:
        AnalysisResponse with recommendation
    """
    ticker = ticker.upper()
    logger.info(f"Analyzing stock: {ticker}")
    
    # Check for recent analysis (within last hour)
    if not force_refresh:
        recent_analysis = db.query(models.Recommendation).filter(
            models.Recommendation.ticker == ticker,
            models.Recommendation.analysis_date >= datetime.now() - timedelta(hours=1)
        ).order_by(desc(models.Recommendation.analysis_date)).first()
        
        if recent_analysis:
            logger.info(f"Returning cached analysis for {ticker}")
            return schemas.AnalysisResponse(
                ticker=recent_analysis.ticker,
                company_name=recent_analysis.company_name,
                analysis_date=recent_analysis.analysis_date,
                recommendation=recent_analysis.recommendation,
                confidence=recent_analysis.confidence,
                sentiment_score=recent_analysis.sentiment_score or 0.0,
                risk_level=recent_analysis.risk_level,
                volatility_assessment=recent_analysis.raw_analysis_json.get('volatility_assessment', 'N/A'),
                key_factors=recent_analysis.raw_analysis_json.get('key_factors', []),
                summary=recent_analysis.summary,
                reasoning=recent_analysis.reasoning,
                price_target=recent_analysis.price_target,
                time_horizon=recent_analysis.time_horizon,
                warnings=recent_analysis.raw_analysis_json.get('warnings', [])
            )
    
    # Step 1: Get stock data
    stock_data, error = data_collector.get_stock_data(ticker)
    if not stock_data:
        raise HTTPException(status_code=404, detail=f"Stock data not found: {error}")
    
    # Step 2: Collect news articles
    news_articles = data_collector.get_news_articles(ticker, settings.news_lookback_days)
    logger.info(f"Collected {len(news_articles)} news articles")
    
    # Step 3: Deduplicate and save articles
    deduplicator = ArticleDeduplicator(db)
    saved_articles = deduplicator.save_articles(news_articles, ticker)
    
    # Step 3b: Get articles for analysis (context-aware approach)
    # Get ALL recent articles for context/summary
    all_recent_articles = db.query(models.Article).filter(
        models.Article.ticker == ticker,
        models.Article.published_at >= datetime.now() - timedelta(days=settings.news_lookback_days)
    ).order_by(desc(models.Article.published_at)).limit(30).all()
    
    # Get ONLY UNUSED articles for recommendation weighting
    new_articles = db.query(models.Article).filter(
        models.Article.ticker == ticker,
        models.Article.used_in_analysis == 0,  # Only unused articles
        models.Article.published_at >= datetime.now() - timedelta(days=settings.news_lookback_days)
    ).order_by(desc(models.Article.published_at)).limit(20).all()
    
    # If no unused articles and force_refresh is True, treat all as new
    if not new_articles and force_refresh:
        logger.info(f"No unused articles for {ticker}, but force_refresh=True. Treating all as new.")
        new_articles = all_recent_articles
    
    if not new_articles:
        raise HTTPException(
            status_code=400,
            detail=f"No new articles available for {ticker}. All recent news has been analyzed. Check back later when new news is published."
        )
    
    logger.info(f"Context: {len(all_recent_articles)} total articles | Focus: {len(new_articles)} NEW articles for recommendation")
    
    # Step 4: Get price history
    price_history = data_collector.get_historical_prices(ticker, days_back=30)
    
    # Step 5: Generate LLM analysis
    # Pass both sets: all articles for context, new articles for recommendation focus
    analysis = await llm_service.analyze_stock(
        ticker=ticker,
        company_name=stock_data.company_name,
        stock_data=stock_data,
        articles=all_recent_articles,
        new_articles=new_articles,  # NEW: explicitly tell LLM which articles are new
        price_history=price_history
    )
    
    if not analysis:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate analysis. Please try again."
        )
    
    # Step 6: Save recommendation to database
    recommendation = models.Recommendation(
        ticker=ticker,
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
        article_ids=[a.id for a in new_articles]  # Only track new articles used
    )
    
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    
    # Step 7: Mark NEW articles as used
    # Only mark the new articles that drove the recommendation
    current_time = datetime.now()
    for article in new_articles:
        article.used_in_analysis = 1
        article.last_used_date = current_time
        article.used_in_recommendation_id = recommendation.id
    
    db.commit()
    logger.info(f"Marked {len(new_articles)} NEW articles as used in recommendation {recommendation.id}")
    
    logger.info(
        f"Analysis complete for {ticker}: {analysis['recommendation']} "
        f"({analysis['confidence']} confidence)"
    )
    
    # Return response
    return schemas.AnalysisResponse(
        ticker=ticker,
        company_name=stock_data.company_name,
        analysis_date=recommendation.analysis_date,
        recommendation=analysis['recommendation'],
        confidence=analysis['confidence'],
        sentiment_score=analysis['sentiment_score'],
        risk_level=analysis['risk_level'],
        volatility_assessment=analysis.get('volatility_assessment', 'N/A'),
        key_factors=analysis.get('key_factors', []),
        summary=analysis['summary'],
        reasoning=analysis['reasoning'],
        price_target=analysis.get('price_target'),
        time_horizon=analysis['time_horizon'],
        warnings=analysis.get('warnings', [])
    )


@app.get("/api/recommendations/{ticker}", response_model=schemas.RecommendationDetail)
async def get_latest_recommendation(ticker: str, db: Session = Depends(get_db)):
    """Get latest recommendation for a ticker"""
    ticker = ticker.upper()
    
    recommendation = db.query(models.Recommendation).filter(
        models.Recommendation.ticker == ticker
    ).order_by(desc(models.Recommendation.analysis_date)).first()
    
    if not recommendation:
        raise HTTPException(status_code=404, detail=f"No recommendations found for {ticker}")
    
    return recommendation


@app.get("/api/recommendations", response_model=List[schemas.RecommendationDetail])
async def list_recommendations(
    ticker: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List recommendations with optional filters
    
    Args:
        ticker: Filter by ticker symbol
        status: Filter by validation status (PENDING, ACCURATE, etc.)
        limit: Maximum number of results
    """
    query = db.query(models.Recommendation)
    
    if ticker:
        query = query.filter(models.Recommendation.ticker == ticker.upper())
    
    if status:
        query = query.filter(models.Recommendation.validation_status == status)
    
    recommendations = query.order_by(
        desc(models.Recommendation.analysis_date)
    ).limit(limit).all()
    
    return recommendations


@app.post("/api/validate/{recommendation_id}")
async def validate_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db)
):
    """Manually trigger validation for a specific recommendation"""
    recommendation = db.query(models.Recommendation).filter(
        models.Recommendation.id == recommendation_id
    ).first()
    
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    validator = RecommendationValidator(db)
    success, error = validator.validate_recommendation(recommendation)
    
    if not success:
        raise HTTPException(status_code=500, detail=f"Validation failed: {error}")
    
    return {
        "success": True,
        "recommendation_id": recommendation_id,
        "validation_status": recommendation.validation_status,
        "accuracy_score": recommendation.accuracy_score
    }


@app.get("/api/metrics", response_model=schemas.ValidationMetricsResponse)
async def get_overall_metrics(db: Session = Depends(get_db)):
    """Get overall validation metrics"""
    # Get latest metrics
    metric = db.query(models.ValidationMetric).order_by(
        desc(models.ValidationMetric.created_at)
    ).first()
    
    if not metric:
        raise HTTPException(status_code=404, detail="No metrics available yet")
    
    accuracy_percentage = (
        (metric.accurate_count / metric.total_recommendations * 100)
        if metric.total_recommendations > 0 else 0
    )
    
    return schemas.ValidationMetricsResponse(
        date=metric.date,
        total_recommendations=metric.total_recommendations,
        accurate_count=metric.accurate_count,
        partially_accurate_count=metric.partially_accurate_count,
        inaccurate_count=metric.inaccurate_count,
        avg_accuracy_score=metric.avg_accuracy_score,
        accuracy_percentage=accuracy_percentage,
        recommendations_by_confidence=metric.recommendations_by_confidence
    )


@app.get("/api/metrics/ticker/{ticker}", response_model=schemas.TickerMetrics)
async def get_ticker_metrics(ticker: str, db: Session = Depends(get_db)):
    """Get metrics for a specific ticker"""
    ticker = ticker.upper()
    
    recommendations = db.query(models.Recommendation).filter(
        models.Recommendation.ticker == ticker,
        models.Recommendation.validation_status != schemas.ValidationStatus.PENDING
    ).all()
    
    if not recommendations:
        raise HTTPException(status_code=404, detail=f"No validated recommendations for {ticker}")
    
    total = len(recommendations)
    avg_score = sum(r.accuracy_score for r in recommendations if r.accuracy_score) / total
    
    # Find best and worst
    sorted_recs = sorted(recommendations, key=lambda r: r.accuracy_score or 0)
    best = sorted_recs[-1] if sorted_recs else None
    worst = sorted_recs[0] if sorted_recs else None
    
    return schemas.TickerMetrics(
        ticker=ticker,
        total_recommendations=total,
        avg_accuracy_score=avg_score,
        best_recommendation=best,
        worst_recommendation=worst
    )


@app.get("/api/articles/{ticker}", response_model=List[schemas.ArticleInfo])
async def get_articles(
    ticker: str, 
    limit: int = 20, 
    unused_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get collected articles for a ticker
    
    Args:
        ticker: Stock ticker symbol
        limit: Maximum number of articles to return
        unused_only: If True, only return articles not yet used in analysis
    """
    ticker = ticker.upper()
    
    query = db.query(models.Article).filter(
        models.Article.ticker == ticker
    )
    
    if unused_only:
        query = query.filter(models.Article.used_in_analysis == 0)
    
    articles = query.order_by(desc(models.Article.published_at)).limit(limit).all()
    
    return articles


@app.delete("/api/articles/old")
async def cleanup_old_articles(db: Session = Depends(get_db)):
    """Delete articles older than retention period"""
    cutoff_date = datetime.now() - timedelta(days=settings.article_retention_days)
    
    deleted = db.query(models.Article).filter(
        models.Article.published_at < cutoff_date
    ).delete()
    
    db.commit()
    
    return {
        "success": True,
        "deleted_count": deleted,
        "cutoff_date": cutoff_date
    }


@app.post("/api/jobs/validate-pending")
async def run_validation_job(db: Session = Depends(get_db)):
    """Manually trigger validation of pending recommendations"""
    validator = RecommendationValidator(db)
    validated_count = validator.validate_pending_recommendations()
    
    return {
        "success": True,
        "validated_count": validated_count
    }


@app.get("/api/articles/{ticker}/stats")
async def get_article_stats(ticker: str, db: Session = Depends(get_db)):
    """
    Get article usage statistics for a ticker
    
    Useful for understanding how much fresh news is available
    """
    ticker = ticker.upper()
    
    total_articles = db.query(models.Article).filter(
        models.Article.ticker == ticker
    ).count()
    
    used_articles = db.query(models.Article).filter(
        models.Article.ticker == ticker,
        models.Article.used_in_analysis == 1
    ).count()
    
    unused_articles = db.query(models.Article).filter(
        models.Article.ticker == ticker,
        models.Article.used_in_analysis == 0
    ).count()
    
    # Get most recently used article
    last_used = db.query(models.Article).filter(
        models.Article.ticker == ticker,
        models.Article.used_in_analysis == 1
    ).order_by(desc(models.Article.last_used_date)).first()
    
    # Get newest unused article
    newest_unused = db.query(models.Article).filter(
        models.Article.ticker == ticker,
        models.Article.used_in_analysis == 0
    ).order_by(desc(models.Article.published_at)).first()
    
    return {
        "ticker": ticker,
        "total_articles": total_articles,
        "used_articles": used_articles,
        "unused_articles": unused_articles,
        "last_used_date": last_used.last_used_date if last_used else None,
        "newest_unused_published": newest_unused.published_at if newest_unused else None,
        "ready_for_analysis": unused_articles > 0
    }
