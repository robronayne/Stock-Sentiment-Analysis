-- MySQL Schema for Sentiment Analysis Bot

-- News articles with deduplication and usage tracking
CREATE TABLE IF NOT EXISTS articles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    article_hash VARCHAR(64) NOT NULL UNIQUE,
    url VARCHAR(1024) UNIQUE,
    ticker VARCHAR(10) NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    source VARCHAR(100),
    published_at DATETIME NOT NULL,
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    sentiment_score FLOAT,
    
    -- Usage tracking for day trading approach
    used_in_analysis BOOLEAN DEFAULT FALSE,
    last_used_date DATETIME NULL,
    used_in_recommendation_id INT NULL,
    
    INDEX idx_ticker_date (ticker, published_at),
    INDEX idx_article_hash (article_hash),
    INDEX idx_collected_at (collected_at),
    INDEX idx_ticker_unused (ticker, used_in_analysis, published_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Stock analysis recommendations
CREATE TABLE IF NOT EXISTS recommendations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(255),
    analysis_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    recommendation VARCHAR(20) NOT NULL,
    confidence VARCHAR(20) NOT NULL,
    sentiment_score FLOAT,
    risk_level VARCHAR(20),
    summary TEXT,
    reasoning TEXT,
    price_at_analysis FLOAT,
    price_target FLOAT,
    time_horizon VARCHAR(20),
    raw_analysis_json JSON,
    article_ids JSON,
    
    -- Validation fields
    validation_date DATETIME,
    validation_status VARCHAR(20) DEFAULT 'PENDING',
    price_at_validation FLOAT,
    price_change_percent FLOAT,
    actual_outcome TEXT,
    accuracy_score FLOAT,
    
    INDEX idx_ticker_date (ticker, analysis_date),
    INDEX idx_validation_pending (validation_status, analysis_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Validation metrics for model improvement
CREATE TABLE IF NOT EXISTS validation_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_recommendations INT,
    accurate_count INT,
    partially_accurate_count INT,
    inaccurate_count INT,
    avg_accuracy_score FLOAT,
    recommendations_by_confidence JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Request rate limiting table
CREATE TABLE IF NOT EXISTS rate_limits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(255) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    request_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_identifier_time (identifier, request_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
