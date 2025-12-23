-- Migration script to add article usage tracking for day trading approach
-- This adds columns to track which articles have been used in analysis
-- Run this if you already have an existing database

-- Add new columns to articles table
ALTER TABLE articles 
ADD COLUMN used_in_analysis BOOLEAN DEFAULT FALSE AFTER sentiment_score,
ADD COLUMN last_used_date DATETIME NULL AFTER used_in_analysis,
ADD COLUMN used_in_recommendation_id INT NULL AFTER last_used_date;

-- Add index for efficient querying of unused articles
CREATE INDEX idx_ticker_unused ON articles(ticker, used_in_analysis, published_at);

-- Optional: Mark all existing articles as unused
-- (They will be considered fresh for the next analysis)
UPDATE articles SET used_in_analysis = FALSE WHERE used_in_analysis IS NULL;

SELECT 'Migration complete! Article usage tracking enabled.' AS status;
