"""LLM service for analysis using Ollama"""
import httpx
import json
import logging
from typing import Optional, Dict, Any

from app.config import get_settings
from app.prompts.analysis_prompt import build_analysis_prompt

settings = get_settings()
logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with Ollama LLM"""
    
    def __init__(self):
        self.base_url = settings.ollama_url
        self.model = settings.ollama_model
        self.timeout = 300.0  # 5 minutes timeout for analysis
    
    async def check_health(self) -> bool:
        """Check if Ollama service is available"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    async def ensure_model_pulled(self) -> bool:
        """Ensure the model is pulled and available"""
        try:
            async with httpx.AsyncClient() as client:
                # Check if model exists
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    models = [m['name'] for m in data.get('models', [])]
                    
                    if self.model in models:
                        logger.info(f"Model {self.model} is available")
                        return True
                
                # Pull model if not available
                logger.info(f"Pulling model {self.model}...")
                pull_response = await client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": self.model},
                    timeout=600.0  # 10 minutes for model pull
                )
                
                return pull_response.status_code == 200
                
        except Exception as e:
            logger.error(f"Error ensuring model availability: {e}")
            return False
    
    async def generate_completion(
        self, 
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """
        Generate completion from Ollama
        
        Args:
            prompt: The prompt to send to the LLM
            temperature: Sampling temperature (lower = more focused)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text or None on error
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        }
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get('response', '')
                else:
                    logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                    return None
                    
        except httpx.TimeoutException:
            logger.error("Ollama request timed out")
            return None
        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            return None
    
    def parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON from LLM response, handling common formatting issues
        
        Args:
            response: Raw LLM response text
            
        Returns:
            Parsed JSON dict or None on error
        """
        try:
            # Try direct parsing first
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                # Try to find JSON object boundaries
                start = response.find('{')
                end = response.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = response[start:end]
                else:
                    logger.error("Could not find JSON in response")
                    return None
            
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse extracted JSON: {e}")
                logger.debug(f"Attempted to parse: {json_str[:500]}")
                return None
    async def analyze_stock(
        self,
        ticker: str,
        company_name: str,
        stock_data,
        articles: List[Article],
        new_articles: List[Article],
        price_history: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze stock and generate recommendation
        
        Args:
            ticker: Stock ticker
            company_name: Company name
            stock_data: StockData object
            articles: List of Article models
            price_history: Optional price history
            
        Returns:
            Parsed analysis dict or None on error
        """
        # Build prompt with context and new articles distinction
        prompt = build_analysis_prompt(
            ticker=ticker,
            company_name=company_name,
            stock_data=stock_data,
            articles=articles,
            new_articles=new_articles,
            price_history=price_history
        )
        
        logger.info(f"Generating analysis for {ticker}...")
        
        # Generate completion
        response = await self.generate_completion(
            prompt=prompt,
            temperature=0.3,  # Low temperature for more consistent analysis
            max_tokens=2000
        )
        
        if not response:
            logger.error(f"Failed to generate analysis for {ticker}")
            return None
        
        # Parse JSON response
        analysis = self.parse_json_response(response)
        
        if not analysis:
            logger.error(f"Failed to parse analysis JSON for {ticker}")
            logger.debug(f"Raw response: {response[:500]}")
            return None
        
        # Validate required fields
        required_fields = [
            'ticker', 'recommendation', 'confidence', 'sentiment_score',
            'risk_level', 'summary', 'reasoning', 'time_horizon'
        ]
        
        missing_fields = [f for f in required_fields if f not in analysis]
        if missing_fields:
            logger.error(f"Analysis missing required fields: {missing_fields}")
            return None
        
        logger.info(
            f"Analysis complete for {ticker}: "
            f"{analysis['recommendation']} ({analysis['confidence']} confidence)"
        )
        
        return analysis
