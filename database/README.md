# Database

This directory contains all SQL files for database schema and migrations.

## 📁 Files in This Directory

### `schema.sql`
**Main database schema**
- Defines all tables and indexes
- Used for initial database setup
- Contains the complete database structure

**Tables:**
- `articles` - News articles with deduplication and usage tracking
- `recommendations` - AI recommendations and validation results
- `validation_metrics` - Daily accuracy aggregation
- `rate_limits` - API rate limiting (future use)

**Usage:**
```bash
# Initialize database manually
docker compose exec mysql mysql -u sentimentbot -p sentiment_analysis < database/schema.sql

# Or let setup.sh handle it automatically
scripts/setup.sh
```

### `migrations/`
**Database migrations**
- Incremental schema changes
- Numbered for order: `001_*.sql`, `002_*.sql`, etc.
- Applied to update existing databases

**Current migrations:**
- `001_add_article_tracking.sql` - Adds article usage tracking fields

**Usage:**
```bash
# Run a specific migration
docker compose exec mysql mysql -u sentimentbot -p sentiment_analysis < database/migrations/001_add_article_tracking.sql
```

---

## 🗄️ Database Information

### **Connection Details**
- **Host:** localhost
- **Port:** 3306
- **Database:** sentiment_analysis
- **User:** sentimentbot
- **Password:** Set in `.env` file

### **Access Database**
```bash
# Connect to MySQL
docker compose exec mysql mysql -u sentimentbot -p sentiment_analysis

# View tables
mysql> SHOW TABLES;

# Check articles
mysql> SELECT COUNT(*) FROM articles;

# Check recommendations
mysql> SELECT ticker, recommendation, confidence, analysis_date 
       FROM recommendations 
       ORDER BY analysis_date DESC 
       LIMIT 5;
```

---

## 📊 Schema Overview

### **articles Table**
Stores news articles with deduplication
- Primary key: `id`
- Unique keys: `article_hash`, `url`
- Tracking: `used_in_analysis`, `last_used_date`

### **recommendations Table**
Stores AI recommendations
- Primary key: `id`
- Status: PENDING → ACCURATE/PARTIALLY_ACCURATE/INACCURATE
- Links: `article_ids` (JSON array)

### **validation_metrics Table**
Daily accuracy statistics
- One row per date
- Aggregates all validated recommendations
- Breakdown by confidence level

---

## 🔄 Adding New Migrations

When making schema changes:

1. **Create numbered migration file:**
   ```bash
   # Next number in sequence
   touch database/migrations/002_add_new_feature.sql
   ```

2. **Write migration SQL:**
   ```sql
   -- Add description comment
   ALTER TABLE articles ADD COLUMN new_field VARCHAR(255);
   
   -- Update models.py accordingly
   ```

3. **Update this README** with migration description

4. **Test migration:**
   ```bash
   docker compose exec mysql mysql -u sentimentbot -p < database/migrations/002_add_new_feature.sql
   ```

---

## ⚠️ Important Notes

- **Backup before migrations:** Always backup production data
- **Test migrations:** Test on development database first
- **Update models:** Keep `app/models.py` in sync with schema
- **Document changes:** Update this README and schema comments

---

**All database definitions in one place! 🗄️**
