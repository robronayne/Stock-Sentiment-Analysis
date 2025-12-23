"""Unit tests for LLM service"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from app.services.llm_service import LLMService


@pytest.mark.unit
@pytest.mark.asyncio
class TestLLMService:
    """Test LLMService class"""
    
    async def test_check_health_success(self):
        """Test successful health check"""
        service = LLMService()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            healthy = await service.check_health()
            
            assert healthy is True
    
    async def test_check_health_failure(self):
        """Test health check when service is down"""
        service = LLMService()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_get = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            healthy = await service.check_health()
            
            assert healthy is False
    
    async def test_generate_completion_success(self, mock_ollama_generate_response):
        """Test successful completion generation"""
        service = LLMService()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_ollama_generate_response
            
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            result = await service.generate_completion("Test prompt")
            
            assert result is not None
            assert isinstance(result, str)
            assert "AAPL" in result
    
    async def test_generate_completion_timeout(self):
        """Test handling of timeout"""
        service = LLMService()
        
        with patch('httpx.AsyncClient') as mock_client:
            import httpx
            mock_post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            result = await service.generate_completion("Test prompt")
            
            assert result is None
    
    async def test_generate_completion_api_error(self):
        """Test handling of API errors"""
        service = LLMService()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            result = await service.generate_completion("Test prompt")
            
            assert result is None
    
    def test_parse_json_response_direct(self):
        """Test parsing clean JSON response"""
        service = LLMService()
        
        json_str = json.dumps({"key": "value", "number": 42})
        result = service.parse_json_response(json_str)
        
        assert result == {"key": "value", "number": 42}
    
    def test_parse_json_response_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks"""
        service = LLMService()
        
        response = """
Here is the analysis:

```json
{
    "recommendation": "BUY",
    "confidence": "HIGH"
}
```

Hope this helps!
"""
        
        result = service.parse_json_response(response)
        
        assert result == {"recommendation": "BUY", "confidence": "HIGH"}
    
    def test_parse_json_response_with_generic_code_block(self):
        """Test parsing JSON in generic code block"""
        service = LLMService()
        
        response = """
```
{
    "ticker": "AAPL",
    "recommendation": "SELL"
}
```
"""
        
        result = service.parse_json_response(response)
        
        assert result == {"ticker": "AAPL", "recommendation": "SELL"}
    
    def test_parse_json_response_with_extra_text(self):
        """Test parsing JSON with surrounding text"""
        service = LLMService()
        
        response = """
Some preamble text...

{"recommendation": "HOLD", "confidence": "MEDIUM"}

Some concluding text...
"""
        
        result = service.parse_json_response(response)
        
        assert result == {"recommendation": "HOLD", "confidence": "MEDIUM"}
    
    def test_parse_json_response_invalid(self):
        """Test handling of invalid JSON"""
        service = LLMService()
        
        result = service.parse_json_response("This is not JSON at all")
        
        assert result is None
    
    async def test_analyze_stock_success(
        self,
        sample_stock_data,
        sample_articles_in_db,
        sample_price_history,
        sample_llm_analysis
    ):
        """Test successful stock analysis"""
        service = LLMService()
        
        # Mock the generate_completion method
        with patch.object(
            service,
            'generate_completion',
            return_value=AsyncMock(return_value=json.dumps(sample_llm_analysis))()
        ):
            result = await service.analyze_stock(
                ticker="AAPL",
                company_name="Apple Inc.",
                stock_data=sample_stock_data,
                articles=sample_articles_in_db,
                price_history=sample_price_history
            )
            
            assert result is not None
            assert result['ticker'] == "AAPL"
            assert result['recommendation'] in ["BUY", "SELL", "SHORT", "HOLD"]
            assert result['confidence'] in ["HIGH", "MEDIUM", "LOW"]
    
    async def test_analyze_stock_missing_fields(
        self,
        sample_stock_data,
        sample_articles_in_db
    ):
        """Test handling of incomplete analysis response"""
        service = LLMService()
        
        # Incomplete analysis (missing required fields)
        incomplete_analysis = {
            "ticker": "AAPL",
            "recommendation": "BUY"
            # Missing: confidence, sentiment_score, etc.
        }
        
        with patch.object(
            service,
            'generate_completion',
            return_value=AsyncMock(return_value=json.dumps(incomplete_analysis))()
        ):
            result = await service.analyze_stock(
                ticker="AAPL",
                company_name="Apple Inc.",
                stock_data=sample_stock_data,
                articles=sample_articles_in_db
            )
            
            # Should return None due to missing fields
            assert result is None
    
    async def test_analyze_stock_generation_failure(
        self,
        sample_stock_data,
        sample_articles_in_db
    ):
        """Test handling of generation failure"""
        service = LLMService()
        
        with patch.object(
            service,
            'generate_completion',
            return_value=AsyncMock(return_value=None)()
        ):
            result = await service.analyze_stock(
                ticker="AAPL",
                company_name="Apple Inc.",
                stock_data=sample_stock_data,
                articles=sample_articles_in_db
            )
            
            assert result is None
