#!/usr/bin/env python3
"""
Example usage of the Stock Sentiment Analysis Bot API

This script demonstrates how to interact with the API programmatically.
"""

import requests
import json
import time
from datetime import datetime

# API configuration
API_BASE_URL = "http://localhost:8000"


def check_health():
    """Check if the API is healthy"""
    response = requests.get(f"{API_BASE_URL}/health")
    data = response.json()
    
    print("=== Health Check ===")
    print(f"Status: {data['status']}")
    print(f"Database: {data['database']}")
    print(f"Ollama: {data['ollama']}")
    print()
    
    return data['status'] == 'healthy'


def analyze_stock(ticker, force_refresh=False):
    """
    Analyze a stock and get recommendation
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        force_refresh: Force new analysis even if recent one exists
    
    Returns:
        dict: Analysis results
    """
    print(f"=== Analyzing {ticker} ===")
    print("This may take 30-60 seconds...")
    
    url = f"{API_BASE_URL}/api/analyze/{ticker}"
    params = {"force_refresh": force_refresh}
    
    response = requests.post(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"\n✓ Analysis Complete")
        print(f"Company: {data['company_name']}")
        print(f"Recommendation: {data['recommendation']}")
        print(f"Confidence: {data['confidence']}")
        print(f"Risk Level: {data['risk_level']}")
        print(f"Sentiment Score: {data['sentiment_score']:.2f}")
        print(f"\nSummary:")
        print(f"  {data['summary']}")
        print(f"\nReasoning:")
        print(f"  {data['reasoning']}")
        
        if data.get('warnings'):
            print(f"\n⚠️  Warnings:")
            for warning in data['warnings']:
                print(f"  • {warning}")
        
        print(f"\nKey Factors:")
        for factor in data.get('key_factors', []):
            impact = factor['impact']
            symbol = "+" if impact == "POSITIVE" else "-" if impact == "NEGATIVE" else "•"
            print(f"  {symbol} {factor['factor']}")
        
        print()
        return data
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)
        return None


def get_latest_recommendation(ticker):
    """Get the latest recommendation for a ticker"""
    response = requests.get(f"{API_BASE_URL}/api/recommendations/{ticker}")
    
    if response.status_code == 200:
        return response.json()
    else:
        return None


def list_all_recommendations(limit=10):
    """List all recommendations"""
    response = requests.get(f"{API_BASE_URL}/api/recommendations", params={"limit": limit})
    
    if response.status_code == 200:
        recommendations = response.json()
        
        print(f"=== Recent Recommendations ({len(recommendations)}) ===")
        for rec in recommendations:
            status_emoji = "⏳" if rec['validation_status'] == "PENDING" else \
                          "✓" if rec['validation_status'] == "ACCURATE" else \
                          "~" if rec['validation_status'] == "PARTIALLY_ACCURATE" else "✗"
            
            print(f"{status_emoji} {rec['ticker']:6s} | {rec['recommendation']:5s} | "
                  f"{rec['confidence']:6s} | {rec['analysis_date'][:10]}")
        
        print()
        return recommendations
    else:
        return []


def get_articles(ticker, limit=5):
    """Get collected articles for a ticker"""
    response = requests.get(f"{API_BASE_URL}/api/articles/{ticker}", params={"limit": limit})
    
    if response.status_code == 200:
        articles = response.json()
        
        print(f"=== Recent Articles for {ticker} ({len(articles)}) ===")
        for article in articles:
            print(f"• {article['title'][:70]}...")
            print(f"  Source: {article['source']} | {article['published_at'][:10]}")
            print()
        
        return articles
    else:
        return []


def get_metrics():
    """Get overall accuracy metrics"""
    response = requests.get(f"{API_BASE_URL}/api/metrics")
    
    if response.status_code == 200:
        metrics = response.json()
        
        print("=== Overall Metrics ===")
        print(f"Total Recommendations: {metrics['total_recommendations']}")
        print(f"Accurate: {metrics['accurate_count']}")
        print(f"Partially Accurate: {metrics['partially_accurate_count']}")
        print(f"Inaccurate: {metrics['inaccurate_count']}")
        print(f"Average Accuracy Score: {metrics['avg_accuracy_score']:.2%}")
        print(f"Accuracy Rate: {metrics['accuracy_percentage']:.1f}%")
        
        if metrics.get('recommendations_by_confidence'):
            print("\nBy Confidence Level:")
            for conf, data in metrics['recommendations_by_confidence'].items():
                print(f"  {conf}: {data['total']} recs, "
                      f"avg accuracy {data['avg_accuracy']:.2%}")
        
        print()
        return metrics
    elif response.status_code == 404:
        print("=== No Metrics Available Yet ===")
        print("Metrics will be available after recommendations are validated.")
        print("Validation happens automatically after the time horizon expires.")
        print()
        return None
    else:
        return None


def validate_recommendation(recommendation_id):
    """Manually trigger validation for a recommendation"""
    response = requests.post(f"{API_BASE_URL}/api/validate/{recommendation_id}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Validation complete")
        print(f"Status: {data['validation_status']}")
        print(f"Accuracy Score: {data['accuracy_score']:.2%}")
        return data
    else:
        print(f"✗ Validation failed: {response.text}")
        return None


def main():
    """Example workflow"""
    print("=" * 60)
    print("Stock Sentiment Analysis Bot - Example Usage")
    print("=" * 60)
    print()
    
    # Check health
    if not check_health():
        print("❌ API is not healthy. Please check the services.")
        return
    
    # Example 1: Analyze a stock
    analysis = analyze_stock("AAPL")
    
    if analysis:
        time.sleep(1)
        
        # Example 2: Get articles
        get_articles("AAPL")
        
        time.sleep(1)
        
        # Example 3: List all recommendations
        list_all_recommendations(limit=5)
        
        time.sleep(1)
        
        # Example 4: Get metrics (if available)
        get_metrics()
    
    # Example 5: Analyze multiple stocks
    print("=== Batch Analysis ===")
    tickers = ["MSFT", "GOOGL", "TSLA"]
    
    for ticker in tickers:
        print(f"\nQueuing analysis for {ticker}...")
        # In production, you might want to add these to a queue
        # and process them asynchronously
    
    print()
    print("=" * 60)
    print("Examples complete!")
    print()
    print("Tips:")
    print("  • Analysis is cached for 1 hour per ticker")
    print("  • Use force_refresh=True to bypass cache")
    print("  • Validation happens automatically via background job")
    print("  • Check /api/metrics after a few days for accuracy data")
    print()
    print("View full API docs at: http://localhost:8000/docs")
    print()


if __name__ == "__main__":
    main()
