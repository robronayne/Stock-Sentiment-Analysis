"""Background job scheduler for validation tasks"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import logging

from app.database import get_db_context
from app.services.validator import RecommendationValidator
from app.models import Article
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def validate_pending_recommendations_job():
    """
    Background job to validate pending recommendations
    Runs daily at configured hour
    """
    logger.info("Running validation job...")
    
    try:
        with get_db_context() as db:
            validator = RecommendationValidator(db)
            validated_count = validator.validate_pending_recommendations()
            logger.info(f"Validation job complete: {validated_count} recommendations validated")
    except Exception as e:
        logger.error(f"Error in validation job: {e}")


def cleanup_old_articles_job():
    """
    Background job to delete old articles
    Runs daily at midnight
    """
    logger.info("Running article cleanup job...")
    
    try:
        with get_db_context() as db:
            cutoff_date = datetime.now() - timedelta(days=settings.article_retention_days)
            
            deleted = db.query(Article).filter(
                Article.published_at < cutoff_date
            ).delete()
            
            db.commit()
            logger.info(f"Cleanup job complete: {deleted} old articles deleted")
    except Exception as e:
        logger.error(f"Error in cleanup job: {e}")


def setup_scheduler():
    """Initialize and start the background scheduler"""
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler already initialized")
        return
    
    scheduler = BackgroundScheduler()
    
    # Daily validation job at configured hour
    scheduler.add_job(
        validate_pending_recommendations_job,
        CronTrigger(hour=settings.run_validation_hour, minute=0),
        id='validate_recommendations',
        name='Validate pending recommendations',
        replace_existing=True
    )
    
    # Daily cleanup at midnight
    scheduler.add_job(
        cleanup_old_articles_job,
        CronTrigger(hour=0, minute=0),
        id='cleanup_articles',
        name='Cleanup old articles',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(
        f"Scheduler started: validation at {settings.run_validation_hour}:00, "
        f"cleanup at 00:00"
    )


def shutdown_scheduler():
    """Shutdown the scheduler gracefully"""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler shutdown complete")
