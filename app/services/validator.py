"""Recommendation validation service"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from app.models import Recommendation, ValidationMetric
from app.services.data_collector import DataCollector
from app.schemas import TimeHorizon, ValidationStatus

logger = logging.getLogger(__name__)


# Validation windows in days
VALIDATION_WINDOWS = {
    TimeHorizon.SHORT_TERM: 3,
    TimeHorizon.MEDIUM_TERM: 7,
    TimeHorizon.LONG_TERM: 30
}


class RecommendationValidator:
    """Validates recommendation accuracy after time horizon"""
    
    def __init__(self, db: Session):
        self.db = db
        self.data_collector = DataCollector()
    
    def calculate_accuracy_score(
        self, 
        recommendation: str, 
        price_change_percent: float
    ) -> float:
        """
        Calculate accuracy score based on recommendation and actual price change
        
        Args:
            recommendation: BUY, SELL, SHORT, or HOLD
            price_change_percent: Actual price change percentage
            
        Returns:
            Accuracy score from 0.0 (completely wrong) to 1.0 (perfect)
        """
        if recommendation == "BUY":
            if price_change_percent > 5:
                return 1.0
            elif price_change_percent > 2:
                return 0.8
            elif price_change_percent > 0:
                return 0.6
            elif price_change_percent > -2:
                return 0.4
            elif price_change_percent > -5:
                return 0.2
            else:
                return 0.0
                
        elif recommendation in ["SELL", "SHORT"]:
            if price_change_percent < -5:
                return 1.0
            elif price_change_percent < -2:
                return 0.8
            elif price_change_percent < 0:
                return 0.6
            elif price_change_percent < 2:
                return 0.4
            elif price_change_percent < 5:
                return 0.2
            else:
                return 0.0
                
        elif recommendation == "HOLD":
            abs_change = abs(price_change_percent)
            if abs_change < 2:
                return 1.0
            elif abs_change < 5:
                return 0.7
            elif abs_change < 10:
                return 0.4
            else:
                return 0.2
        
        return 0.5  # Default
    
    def determine_validation_status(self, accuracy_score: float) -> str:
        """
        Determine validation status based on accuracy score
        
        Args:
            accuracy_score: Score from 0.0 to 1.0
            
        Returns:
            ValidationStatus string
        """
        if accuracy_score >= 0.7:
            return ValidationStatus.ACCURATE
        elif accuracy_score >= 0.4:
            return ValidationStatus.PARTIALLY_ACCURATE
        else:
            return ValidationStatus.INACCURATE
    
    def generate_outcome_summary(
        self,
        recommendation: Recommendation,
        price_change_percent: float,
        accuracy_score: float
    ) -> str:
        """
        Generate human-readable outcome summary
        
        Args:
            recommendation: Recommendation object
            price_change_percent: Actual price change
            accuracy_score: Calculated accuracy score
            
        Returns:
            Summary text
        """
        rec_type = recommendation.recommendation
        confidence = recommendation.confidence
        
        outcome = f"{rec_type} recommendation with {confidence} confidence. "
        outcome += f"Stock price changed {price_change_percent:+.2f}% over {recommendation.time_horizon}. "
        
        if accuracy_score >= 0.7:
            outcome += "Recommendation was accurate."
        elif accuracy_score >= 0.4:
            outcome += "Recommendation was partially accurate."
        else:
            outcome += "Recommendation was inaccurate."
        
        return outcome
    
    def validate_recommendation(
        self, 
        recommendation: Recommendation
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a single recommendation
        
        Args:
            recommendation: Recommendation model instance
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get current stock price
            stock_data, error = self.data_collector.get_stock_data(recommendation.ticker)
            
            if not stock_data:
                return False, f"Failed to fetch price data: {error}"
            
            current_price = stock_data.current_price
            original_price = recommendation.price_at_analysis
            
            if not original_price:
                return False, "No original price recorded"
            
            # Calculate price change
            price_change_percent = (
                (current_price - original_price) / original_price * 100
            )
            
            # Calculate accuracy score
            accuracy_score = self.calculate_accuracy_score(
                recommendation.recommendation,
                price_change_percent
            )
            
            # Determine validation status
            validation_status = self.determine_validation_status(accuracy_score)
            
            # Generate outcome summary
            outcome_summary = self.generate_outcome_summary(
                recommendation,
                price_change_percent,
                accuracy_score
            )
            
            # Update recommendation
            recommendation.validation_date = datetime.now()
            recommendation.validation_status = validation_status
            recommendation.price_at_validation = current_price
            recommendation.price_change_percent = price_change_percent
            recommendation.accuracy_score = accuracy_score
            recommendation.actual_outcome = outcome_summary
            
            self.db.commit()
            
            logger.info(
                f"Validated recommendation {recommendation.id} for {recommendation.ticker}: "
                f"{validation_status} (score: {accuracy_score:.2f})"
            )
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating recommendation {recommendation.id}: {e}")
            self.db.rollback()
            return False, str(e)
    
    def validate_pending_recommendations(self) -> int:
        """
        Find and validate all recommendations that are due for validation
        
        Returns:
            Number of recommendations validated
        """
        validated_count = 0
        
        # Get pending recommendations
        pending = self.db.query(Recommendation).filter(
            Recommendation.validation_status == ValidationStatus.PENDING
        ).all()
        
        logger.info(f"Found {len(pending)} pending recommendations")
        
        for rec in pending:
            # Check if validation window has passed
            if not rec.time_horizon or not rec.analysis_date:
                continue
            
            window_days = VALIDATION_WINDOWS.get(rec.time_horizon, 7)
            validation_due_date = rec.analysis_date + timedelta(days=window_days)
            
            if datetime.now() >= validation_due_date:
                success, error = self.validate_recommendation(rec)
                if success:
                    validated_count += 1
                else:
                    logger.warning(
                        f"Failed to validate recommendation {rec.id}: {error}"
                    )
        
        logger.info(f"Validated {validated_count} recommendations")
        
        # Update daily metrics if any were validated
        if validated_count > 0:
            self.update_daily_metrics()
        
        return validated_count
    
    def update_daily_metrics(self):
        """Update daily validation metrics"""
        try:
            today = datetime.now().date()
            
            # Get all validated recommendations
            validated = self.db.query(Recommendation).filter(
                Recommendation.validation_status != ValidationStatus.PENDING
            ).all()
            
            if not validated:
                return
            
            # Calculate metrics
            total = len(validated)
            accurate = len([r for r in validated if r.validation_status == ValidationStatus.ACCURATE])
            partially = len([r for r in validated if r.validation_status == ValidationStatus.PARTIALLY_ACCURATE])
            inaccurate = len([r for r in validated if r.validation_status == ValidationStatus.INACCURATE])
            
            avg_score = sum(r.accuracy_score for r in validated if r.accuracy_score) / total
            
            # Breakdown by confidence
            by_confidence = {}
            for conf in ["HIGH", "MEDIUM", "LOW"]:
                conf_recs = [r for r in validated if r.confidence == conf]
                if conf_recs:
                    by_confidence[conf] = {
                        "total": len(conf_recs),
                        "avg_accuracy": sum(r.accuracy_score for r in conf_recs if r.accuracy_score) / len(conf_recs)
                    }
            
            # Update or create metric
            metric = self.db.query(ValidationMetric).filter(
                func.DATE(ValidationMetric.date) == today
            ).first()
            
            if metric:
                metric.total_recommendations = total
                metric.accurate_count = accurate
                metric.partially_accurate_count = partially
                metric.inaccurate_count = inaccurate
                metric.avg_accuracy_score = avg_score
                metric.recommendations_by_confidence = by_confidence
            else:
                metric = ValidationMetric(
                    date=datetime.now(),
                    total_recommendations=total,
                    accurate_count=accurate,
                    partially_accurate_count=partially,
                    inaccurate_count=inaccurate,
                    avg_accuracy_score=avg_score,
                    recommendations_by_confidence=by_confidence
                )
                self.db.add(metric)
            
            self.db.commit()
            logger.info(f"Updated daily metrics: {accurate}/{total} accurate")
            
        except Exception as e:
            logger.error(f"Error updating daily metrics: {e}")
            self.db.rollback()
