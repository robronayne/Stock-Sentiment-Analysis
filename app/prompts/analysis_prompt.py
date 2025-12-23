"""Prompt templates for LLM analysis"""
from typing import List, Dict
from datetime import datetime


def format_stock_fundamentals(stock_data) -> str:
    """Format stock fundamental data for prompt"""
    return f"""
Current Price: ${stock_data.current_price:.2f}
Previous Close: ${stock_data.prev_close:.2f}
Day Change: {stock_data.day_change_percent:+.2f}%
Volume: {stock_data.volume:,} (Avg: {stock_data.avg_volume:,})
Market Cap: ${stock_data.market_cap:,} if stock_data.market_cap else 'N/A'
P/E Ratio: {stock_data.pe_ratio:.2f} if stock_data.pe_ratio else 'N/A'
52-Week High: ${stock_data.fifty_two_week_high:.2f} if stock_data.fifty_two_week_high else 'N/A'
52-Week Low: ${stock_data.fifty_two_week_low:.2f} if stock_data.fifty_two_week_low else 'N/A'
Beta: {stock_data.beta:.2f} if stock_data.beta else 'N/A'
""".strip()


def format_news_articles(articles: List, mark_as_new: bool = False) -> str:
    """Format news articles for prompt"""
    if not articles:
        return "No recent news articles available."
    
    formatted = []
    marker = " [NEW]" if mark_as_new else ""
    for i, article in enumerate(articles[:10], 1):  # Limit to 10 most recent
        formatted.append(f"""
Article {i}{marker}:
Title: {article.title}
Source: {article.source}
Date: {article.published_at.strftime('%Y-%m-%d')}
Summary: {article.content[:300]}...
""".strip())
    
    return "\n\n".join(formatted)


def format_price_history(price_history: Dict) -> str:
    """Format historical price data for prompt"""
    if not price_history:
        return "No historical price data available."
    
    closes = price_history.get('close', [])
    if not closes or len(closes) < 2:
        return "Insufficient price history."
    
    # Calculate simple metrics
    week_ago = closes[-7] if len(closes) >= 7 else closes[0]
    month_ago = closes[0]
    current = closes[-1]
    
    week_change = ((current - week_ago) / week_ago * 100) if week_ago else 0
    month_change = ((current - month_ago) / month_ago * 100) if month_ago else 0
    
    # Calculate volatility (simplified)
    volatility = "N/A"
    if len(closes) >= 7:
        recent_closes = closes[-7:]
        avg = sum(recent_closes) / len(recent_closes)
        variance = sum((x - avg) ** 2 for x in recent_closes) / len(recent_closes)
        volatility = f"{(variance ** 0.5 / avg * 100):.2f}%"
    
    return f"""
7-Day Change: {week_change:+.2f}%
30-Day Change: {month_change:+.2f}%
Recent Volatility (7d): {volatility}
""".strip()


def build_analysis_prompt(
    ticker: str,
    company_name: str,
    stock_data,
    articles: List,
    new_articles: List,
    price_history: Dict = None
) -> str:
    """
    Build the complete analysis prompt for the LLM
    
    Args:
        ticker: Stock ticker symbol
        company_name: Company name
        stock_data: StockData object
        articles: List of ALL Article model objects (for context)
        new_articles: List of NEW Article model objects (for recommendation focus)
        price_history: Optional price history dict
        
    Returns:
        Complete prompt string
    """
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    fundamentals = format_stock_fundamentals(stock_data)
    
    # Get IDs of new articles to mark them in the context
    new_article_ids = {a.id for a in new_articles}
    
    # Format all articles with NEW markers
    formatted_articles = []
    for i, article in enumerate(articles[:15], 1):  # Up to 15 for context
        is_new = article.id in new_article_ids
        marker = " [NEW - BREAKING NEWS]" if is_new else " [Previous Context]"
        formatted_articles.append(f"""
Article {i}{marker}:
Title: {article.title}
Source: {article.source}
Date: {article.published_at.strftime('%Y-%m-%d')}
Summary: {article.content[:300]}...
""".strip())
    
    news = "\n\n".join(formatted_articles) if formatted_articles else "No news articles available."
    price_trends = format_price_history(price_history) if price_history else "No price history available."
    
    prompt = f"""You are a professional financial analyst specializing in market sentiment analysis and risk assessment. Your task is to analyze available data and provide an objective, data-driven trading recommendation.

## STOCK INFORMATION
Ticker: {ticker}
Company: {company_name}
Analysis Date: {current_date}

## FUNDAMENTAL DATA
{fundamentals}

## PRICE TRENDS
{price_trends}

## RECENT NEWS & SENTIMENT (Last 7 Days)
{news}

## YOUR TASK
Analyze the provided information and provide a comprehensive trading recommendation.

**CRITICAL INSTRUCTION FOR NEWS ANALYSIS:**
- Articles marked "[NEW - BREAKING NEWS]" are FRESH, RECENT developments that have NOT been analyzed yet
- Articles marked "[Previous Context]" are OLDER news for background context only
- **Your RECOMMENDATION (BUY/SELL/SHORT/HOLD) should be HEAVILY weighted toward NEW articles**
- **Your SUMMARY can include context from previous articles**
- If NEW news contradicts previous context, the NEW news should dominate your recommendation

**Example:**
- Previous Context: "Company beats earnings" (positive)
- NEW Breaking News: "CEO resigns unexpectedly" (negative)
- → Your Recommendation: SELL (driven by new negative development)
- → Your Summary: Can mention earnings beat for context, but emphasize CEO resignation

Consider:
1. **NEW News Impact (70% weight)**: How do the BREAKING NEWS articles affect immediate outlook?
2. **Sentiment Analysis**: What's the sentiment of NEW vs previous context?
3. **Risk Assessment**: Has new information changed the risk profile?
4. **Technical Factors**: Price trends, volume patterns, momentum
5. **Fundamental Factors**: Company health, valuation metrics
6. **Confidence Level**: Higher confidence if new news is clear and significant

## CRITICAL GUIDELINES
- **PRIORITIZE NEW BREAKING NEWS** for your recommendation decision
- Use previous context articles for background/summary only
- Be objective and data-driven. Do not speculate beyond available data.
- If new data is insufficient or conflicting, recommend HOLD with LOW confidence.
- For highly volatile stocks (beta > 1.5 or recent volatility > 5%), clearly flag risks.
- If NEW news is overwhelmingly negative, recommend SELL regardless of previous positive context.
- Base time horizon on the nature of NEW opportunities (breaking news = SHORT_TERM, fundamental shifts = LONG_TERM).

## OUTPUT FORMAT
Respond with ONLY valid JSON in this EXACT structure (no additional text):

{{
  "ticker": "{ticker}",
  "company_name": "{company_name}",
  "analysis_date": "{current_date}",
  "recommendation": "BUY|SELL|SHORT|HOLD",
  "confidence": "HIGH|MEDIUM|LOW",
  "sentiment_score": <float between -1.0 and 1.0>,
  "risk_level": "LOW|MEDIUM|HIGH|VERY_HIGH",
  "volatility_assessment": "<brief assessment of price volatility>",
  "key_factors": [
    {{"factor": "<key factor description>", "impact": "POSITIVE|NEGATIVE|NEUTRAL"}}
  ],
  "summary": "<2-3 sentence executive summary>",
  "reasoning": "<detailed explanation of your recommendation, 3-5 sentences>",
  "price_target": <number or null>,
  "time_horizon": "SHORT_TERM|MEDIUM_TERM|LONG_TERM",
  "warnings": ["<risk warning 1>", "<risk warning 2>"]
}}

Provide ONLY the JSON response, no other text.
"""
    
    return prompt


def build_validation_summary_prompt(
    recommendation,
    price_change: float,
    days_elapsed: int
) -> str:
    """
    Build prompt for LLM to summarize validation outcome
    
    Args:
        recommendation: Recommendation model object
        price_change: Actual price change percentage
        days_elapsed: Days since recommendation
        
    Returns:
        Validation summary prompt
    """
    prompt = f"""Briefly summarize the outcome of this stock recommendation in 1-2 sentences:

Original Recommendation: {recommendation.recommendation}
Confidence: {recommendation.confidence}
Time Horizon: {recommendation.time_horizon}
Price Target: ${recommendation.price_target if recommendation.price_target else 'N/A'}

Actual Outcome:
- Days Elapsed: {days_elapsed}
- Price Change: {price_change:+.2f}%

Was the recommendation accurate? Provide a concise summary.
"""
    
    return prompt
