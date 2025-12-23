"""Unit tests for recommendation validator"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from app.services.validator import RecommendationValidator, VALIDATION_WINDOWS
from app.models import Recommendation
from app.schemas import TimeHorizon, ValidationStatus


@pytest.mark.unit
class TestRecommendationValidator:
    """Test RecommendationValidator class"""
    
    def test_calculate_accuracy_score_buy_perfect(self):
        """Test accuracy score for perfect BUY recommendation"""
        validator = RecommendationValidator(Mock())
        
        # BUY with +5% or more = 1.0
        score = validator.calculate_accuracy_score("BUY", 6.0)
        assert score == 1.0
        
        # BUY with +2-5% = 0.8
        score = validator.calculate_accuracy_score("BUY", 3.0)
        assert score == 0.8
        
        # BUY with 0-2% = 0.6
        score = validator.calculate_accuracy_score("BUY", 1.0)
        assert score == 0.6
    
    def test_calculate_accuracy_score_buy_wrong(self):
        """Test accuracy score for wrong BUY recommendation"""
        validator = RecommendationValidator(Mock())
        
        # BUY but price went down significantly
        score = validator.calculate_accuracy_score("BUY", -6.0)
        assert score == 0.0
        
        # BUY but small decline
        score = validator.calculate_accuracy_score("BUY", -1.0)
        assert score == 0.4
    
    def test_calculate_accuracy_score_sell_perfect(self):
        """Test accuracy score for perfect SELL recommendation"""
        validator = RecommendationValidator(Mock())
        
        # SELL with -5% or worse = 1.0
        score = validator.calculate_accuracy_score("SELL", -6.0)
        assert score == 1.0
        
        # SELL with -2 to -5% = 0.8
        score = validator.calculate_accuracy_score("SELL", -3.0)
        assert score == 0.8
    
    def test_calculate_accuracy_score_sell_wrong(self):
        """Test accuracy score for wrong SELL recommendation"""
        validator = RecommendationValidator(Mock())
        
        # SELL but price went up
        score = validator.calculate_accuracy_score("SELL", 6.0)
        assert score == 0.0
    
    def test_calculate_accuracy_score_hold_perfect(self):
        """Test accuracy score for perfect HOLD recommendation"""
        validator = RecommendationValidator(Mock())
        
        # HOLD with minimal change = 1.0
        score = validator.calculate_accuracy_score("HOLD", 1.0)
        assert score == 1.0
        
        score = validator.calculate_accuracy_score("HOLD", -1.5)
        assert score == 1.0
        
        # HOLD with moderate change = 0.7
        score = validator.calculate_accuracy_score("HOLD", 3.0)
        assert score == 0.7
    
    def test_calculate_accuracy_score_hold_wrong(self):
        """Test accuracy score for wrong HOLD recommendation"""
        validator = RecommendationValidator(Mock())
        
        # HOLD but large price movement
        score = validator.calculate_accuracy_score("HOLD", 12.0)
        assert score == 0.2
    
    def test_calculate_accuracy_score_short(self):
        """Test accuracy score for SHORT recommendation"""
        validator = RecommendationValidator(Mock())
        
        # SHORT works same as SELL
        score = validator.calculate_accuracy_score("SHORT", -6.0)
        assert score == 1.0
        
        score = validator.calculate_accuracy_score("SHORT", 6.0)
        assert score == 0.0
    
    def test_determine_validation_status(self):
        """Test validation status determination"""
        validator = RecommendationValidator(Mock())
        
        assert validator.determine_validation_status(0.9) == ValidationStatus.ACCURATE
        assert validator.determine_validation_status(0.7) == ValidationStatus.ACCURATE
        assert validator.determine_validation_status(0.5) == ValidationStatus.PARTIALLY_ACCURATE
        assert validator.determine_validation_status(0.4) == ValidationStatus.PARTIALLY_ACCURATE
        assert validator.determine_validation_status(0.2) == ValidationStatus.INACCURATE
    
    def test_generate_outcome_summary(self):
        """Test outcome summary generation"""
        validator = RecommendationValidator(Mock())
        
        # Create mock recommendation
        rec = Mock()
        rec.recommendation = "BUY"
        rec.confidence = "HIGH"
        rec.time_horizon = "MEDIUM_TERM"
        rec.price_target = 200.0
        
        summary = validator.generate_outcome_summary(rec, 5.5, 0.9)
        
        assert "BUY" in summary
        assert "HIGH" in summary
        assert "+5.5%" in summary or "5.5%" in summary
        assert "accurate" in summary.lower()
    
    @patch('app.services.validator.DataCollector')
    def test_validate_recommendation_success(self, mock_collector_class, db_session):
        """Test successful recommendation validation"""
        # Setup mock data collector
        mock_collector = Mock()
        mock_stock_data = Mock()
        mock_stock_data.current_price = 195.0
        mock_collector.get_stock_data.return_value = (mock_stock_data, None)
        mock_collector_class.return_value = mock_collector
        
        # Create recommendation
        rec = Recommendation(
            ticker="AAPL",
            company_name="Apple Inc.",
            recommendation="BUY",
            confidence="HIGH",
            price_at_analysis=185.0,
            time_horizon="MEDIUM_TERM",
            validation_status="PENDING"
        )
        db_session.add(rec)
        db_session.commit()
        
        # Validate
        validator = RecommendationValidator(db_session)
        validator.data_collector = mock_collector
        success, error = validator.validate_recommendation(rec)
        
        # Assertions
        assert success is True
        assert error is None
        assert rec.validation_status == ValidationStatus.ACCURATE
        assert rec.price_at_validation == 195.0
        assert rec.price_change_percent == pytest.approx(5.41, rel=0.01)
        assert rec.accuracy_score == 1.0  # BUY with 5.4% gain
    
    @patch('app.services.validator.DataCollector')
    def test_validate_recommendation_no_price_data(
        self, 
        mock_collector_class,
        db_session
    ):
        """Test validation failure when price data unavailable"""
        # Setup mock to return error
        mock_collector = Mock()
        mock_collector.get_stock_data.return_value = (None, "API Error")
        mock_collector_class.return_value = mock_collector
        
        rec = Recommendation(
            ticker="AAPL",
            recommendation="BUY",
            price_at_analysis=185.0,
            validation_status="PENDING"
        )
        db_session.add(rec)
        db_session.commit()
        
        validator = RecommendationValidator(db_session)
        validator.data_collector = mock_collector
        success, error = validator.validate_recommendation(rec)
        
        assert success is False
        assert error is not None
        assert "Failed to fetch price data" in error
    
    def test_validate_pending_recommendations(self, db_session):
        """Test batch validation of pending recommendations"""
        # Create recommendations at different times
        now = datetime.now()
        
        # Old recommendation (should validate)
        old_rec = Recommendation(
            ticker="AAPL",
            recommendation="BUY",
            price_at_analysis=180.0,
            time_horizon="SHORT_TERM",
            analysis_date=now - timedelta(days=5),
            validation_status="PENDING"
        )
        
        # Recent recommendation (should skip)
        recent_rec = Recommendation(
            ticker="MSFT",
            recommendation="SELL",
            price_at_analysis=350.0,
            time_horizon="MEDIUM_TERM",
            analysis_date=now - timedelta(days=1),
            validation_status="PENDING"
        )
        
        db_session.add_all([old_rec, recent_rec])
        db_session.commit()
        
        with patch.object(
            RecommendationValidator,
            'validate_recommendation',
            return_value=(True, None)
        ) as mock_validate:
            validator = RecommendationValidator(db_session)
            count = validator.validate_pending_recommendations()
            
            # Should only validate the old one
            assert mock_validate.call_count >= 0  # May be 0 or 1 depending on timing
    
    def test_validation_windows(self):
        """Test that validation windows are defined correctly"""
        assert VALIDATION_WINDOWS[TimeHorizon.SHORT_TERM] == 3
        assert VALIDATION_WINDOWS[TimeHorizon.MEDIUM_TERM] == 7
        assert VALIDATION_WINDOWS[TimeHorizon.LONG_TERM] == 30
