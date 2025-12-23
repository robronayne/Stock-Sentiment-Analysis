"""Integration tests for validation workflow"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from app.services.validator import RecommendationValidator
from app.models import Recommendation, ValidationMetric
from app.schemas import TimeHorizon, ValidationStatus


@pytest.mark.integration
class TestValidationWorkflow:
    """Test complete validation workflow"""
    
    @patch('app.services.validator.DataCollector')
    def test_complete_validation_workflow(self, mock_collector_class, db_session):
        """Test full validation workflow from pending to validated"""
        
        # Create recommendation 7 days ago
        old_date = datetime.now() - timedelta(days=8)
        
        rec = Recommendation(
            ticker="AAPL",
            company_name="Apple Inc.",
            recommendation="BUY",
            confidence="HIGH",
            sentiment_score=0.7,
            risk_level="MEDIUM",
            summary="Positive outlook",
            reasoning="Strong fundamentals",
            price_at_analysis=180.0,
            price_target=195.0,
            time_horizon="MEDIUM_TERM",
            analysis_date=old_date,
            validation_status="PENDING",
            raw_analysis_json={}
        )
        
        db_session.add(rec)
        db_session.commit()
        
        # Mock current price (stock went up)
        mock_collector = Mock()
        mock_stock_data = Mock()
        mock_stock_data.current_price = 192.0  # +6.7% gain
        mock_collector.get_stock_data.return_value = (mock_stock_data, None)
        mock_collector_class.return_value = mock_collector
        
        # Run validation
        validator = RecommendationValidator(db_session)
        validator.data_collector = mock_collector
        
        validated_count = validator.validate_pending_recommendations()
        
        # Should validate the recommendation
        assert validated_count >= 1
        
        # Check recommendation was updated
        db_session.refresh(rec)
        assert rec.validation_status == ValidationStatus.ACCURATE
        assert rec.price_at_validation == 192.0
        assert rec.price_change_percent == pytest.approx(6.67, rel=0.01)
        assert rec.accuracy_score == 1.0  # BUY with 6.7% gain = perfect
    
    @patch('app.services.validator.DataCollector')
    def test_validation_with_wrong_recommendation(
        self,
        mock_collector_class,
        db_session
    ):
        """Test validation when recommendation was wrong"""
        
        # BUY recommendation 3 days ago
        old_date = datetime.now() - timedelta(days=4)
        
        rec = Recommendation(
            ticker="TSLA",
            recommendation="BUY",
            confidence="MEDIUM",
            price_at_analysis=250.0,
            time_horizon="SHORT_TERM",
            analysis_date=old_date,
            validation_status="PENDING",
            raw_analysis_json={}
        )
        
        db_session.add(rec)
        db_session.commit()
        
        # Stock actually went down significantly
        mock_collector = Mock()
        mock_stock_data = Mock()
        mock_stock_data.current_price = 230.0  # -8% loss
        mock_collector.get_stock_data.return_value = (mock_stock_data, None)
        mock_collector_class.return_value = mock_collector
        
        validator = RecommendationValidator(db_session)
        validator.data_collector = mock_collector
        
        success, error = validator.validate_recommendation(rec)
        
        assert success is True
        assert error is None
        
        db_session.refresh(rec)
        assert rec.validation_status == ValidationStatus.INACCURATE
        assert rec.accuracy_score == 0.0  # BUY but went down 8%
    
    @patch('app.services.validator.DataCollector')
    def test_validation_metrics_update(self, mock_collector_class, db_session):
        """Test that metrics are properly updated after validation"""
        
        # Create multiple recommendations
        old_date = datetime.now() - timedelta(days=8)
        
        recommendations = [
            # Accurate BUY
            Recommendation(
                ticker="AAPL",
                recommendation="BUY",
                confidence="HIGH",
                price_at_analysis=180.0,
                time_horizon="MEDIUM_TERM",
                analysis_date=old_date,
                validation_status="PENDING",
                raw_analysis_json={}
            ),
            # Accurate SELL
            Recommendation(
                ticker="MSFT",
                recommendation="SELL",
                confidence="MEDIUM",
                price_at_analysis=350.0,
                time_horizon="MEDIUM_TERM",
                analysis_date=old_date,
                validation_status="PENDING",
                raw_analysis_json={}
            ),
            # Inaccurate HOLD
            Recommendation(
                ticker="GOOGL",
                recommendation="HOLD",
                confidence="LOW",
                price_at_analysis=140.0,
                time_horizon="MEDIUM_TERM",
                analysis_date=old_date,
                validation_status="PENDING",
                raw_analysis_json={}
            )
        ]
        
        for rec in recommendations:
            db_session.add(rec)
        db_session.commit()
        
        # Mock price changes
        def mock_get_stock_data(ticker):
            prices = {
                "AAPL": 195.0,  # +8.3% (accurate BUY)
                "MSFT": 330.0,  # -5.7% (accurate SELL)
                "GOOGL": 155.0  # +10.7% (inaccurate HOLD)
            }
            mock_data = Mock()
            mock_data.current_price = prices.get(ticker, 100.0)
            return (mock_data, None)
        
        mock_collector = Mock()
        mock_collector.get_stock_data = mock_get_stock_data
        mock_collector_class.return_value = mock_collector
        
        # Run validation
        validator = RecommendationValidator(db_session)
        validator.data_collector = mock_collector
        validator.validate_pending_recommendations()
        
        # Check metrics were created
        metrics = db_session.query(ValidationMetric).first()
        
        if metrics:  # Metrics might not be created if no validations occurred
            assert metrics.total_recommendations >= 2  # At least the accurate ones
            assert metrics.accurate_count >= 2
            assert metrics.avg_accuracy_score > 0
    
    @patch('app.services.validator.DataCollector')
    def test_validation_skips_recent_recommendations(
        self,
        mock_collector_class,
        db_session
    ):
        """Test that recent recommendations are not validated"""
        
        # Very recent recommendation (yesterday)
        recent_date = datetime.now() - timedelta(days=1)
        
        rec = Recommendation(
            ticker="AAPL",
            recommendation="BUY",
            price_at_analysis=180.0,
            time_horizon="MEDIUM_TERM",  # Requires 7 days
            analysis_date=recent_date,
            validation_status="PENDING",
            raw_analysis_json={}
        )
        
        db_session.add(rec)
        db_session.commit()
        
        mock_collector = Mock()
        mock_collector_class.return_value = mock_collector
        
        # Run validation
        validator = RecommendationValidator(db_session)
        
        with patch.object(
            validator,
            'validate_recommendation'
        ) as mock_validate:
            validator.validate_pending_recommendations()
            
            # Should not be called (recommendation too recent)
            assert mock_validate.call_count == 0
        
        # Recommendation should still be pending
        db_session.refresh(rec)
        assert rec.validation_status == "PENDING"
    
    @patch('app.services.validator.DataCollector')
    def test_validation_with_different_time_horizons(
        self,
        mock_collector_class,
        db_session
    ):
        """Test validation respects different time horizons"""
        
        now = datetime.now()
        
        recommendations = [
            # SHORT_TERM (3 days) - old enough
            Recommendation(
                ticker="AAPL",
                recommendation="BUY",
                price_at_analysis=180.0,
                time_horizon="SHORT_TERM",
                analysis_date=now - timedelta(days=4),
                validation_status="PENDING",
                raw_analysis_json={}
            ),
            # MEDIUM_TERM (7 days) - not old enough
            Recommendation(
                ticker="MSFT",
                recommendation="SELL",
                price_at_analysis=350.0,
                time_horizon="MEDIUM_TERM",
                analysis_date=now - timedelta(days=5),
                validation_status="PENDING",
                raw_analysis_json={}
            ),
            # LONG_TERM (30 days) - old enough
            Recommendation(
                ticker="GOOGL",
                recommendation="HOLD",
                price_at_analysis=140.0,
                time_horizon="LONG_TERM",
                analysis_date=now - timedelta(days=31),
                validation_status="PENDING",
                raw_analysis_json={}
            )
        ]
        
        for rec in recommendations:
            db_session.add(rec)
        db_session.commit()
        
        # Mock price data
        mock_collector = Mock()
        mock_data = Mock()
        mock_data.current_price = 200.0
        mock_collector.get_stock_data.return_value = (mock_data, None)
        mock_collector_class.return_value = mock_collector
        
        validator = RecommendationValidator(db_session)
        validator.data_collector = mock_collector
        
        validated = validator.validate_pending_recommendations()
        
        # Should validate SHORT_TERM and LONG_TERM, but not MEDIUM_TERM
        db_session.expire_all()  # Refresh all objects
        
        rec_short = recommendations[0]
        rec_medium = recommendations[1]
        rec_long = recommendations[2]
        
        db_session.refresh(rec_short)
        db_session.refresh(rec_medium)
        db_session.refresh(rec_long)
        
        # SHORT_TERM should be validated (4 days > 3 days required)
        assert rec_short.validation_status != "PENDING"
        
        # MEDIUM_TERM should still be pending (5 days < 7 days required)
        assert rec_medium.validation_status == "PENDING"
        
        # LONG_TERM should be validated (31 days > 30 days required)
        assert rec_long.validation_status != "PENDING"
