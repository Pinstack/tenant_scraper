# FSQ-OS-Places Integration Guide

## Overview

This guide explains how to integrate the **Foursquare Open Source Places (FSQ-OS-Places)** dataset with your tenant scraper to enrich Google Maps data with canonical business information, websites, and chain identification.

## What is FSQ-OS-Places?

- **100M+ venues** globally with 22 core attributes
- Updated monthly
- Free and open-source
- Includes: names, addresses, coordinates, categories, websites, phone numbers
- Collaborative AI + human curation

## Why Use PostgreSQL?

### Advantages
1. **Cost**: Free forever, no usage limits
2. **Performance**: Local queries with no network latency
3. **Integration**: Direct Python integration with existing project
4. **Spatial Queries**: PostGIS enables powerful location-based searches
5. **Joins**: Combine FSQ data with your scraped Google Maps data
6. **Control**: Full control over data, indexes, and optimization

### vs Cloud Options
- **MotherDuck/ClickHouse Cloud**: Pay per usage, network latency, vendor lock-in
- **Hugging Face Datasets**: Requires authentication, loads entire dataset into memory
- **Local Parquet**: No indexing, slow queries, manual file management

## Setup Process

### 1. Prerequisites

```bash
# Install PostgreSQL (if not already installed)
brew install postgresql@17  # macOS
# or
sudo apt install postgresql-17  # Ubuntu/Debian

# Install PostGIS
brew install postgis  # macOS
# or
sudo apt install postgis  # Ubuntu/Debian

# Install Python dependencies
pip install psycopg2-binary pandas pyarrow sqlalchemy geoalchemy2
```

### 2. Get FSQ-OS-Places Data

The FSQ-OS-Places dataset is available from multiple sources:

#### Option A: Direct Download from S3 (Requires Access)
```bash
# Dataset is gated - you need to request access
# Visit: https://huggingface.co/datasets/foursquare/fsq-os-places
```

#### Option B: ClickHouse Public Dataset
```bash
# Query directly from ClickHouse Cloud (free tier)
# See: https://clickhouse.com/docs/getting-started/example-datasets/foursquare-places
```

#### Option C: Download Sample for Testing
```bash
# For testing, create a sample dataset from your own scraped data
python scripts/create_sample_fsq_data.py
```

### 3. Create Database and Load Data

```bash
# Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=$USER
export POSTGRES_DB=fsq_places

# Create database and schema
python scripts/setup_fsq_postgres.py --create-db --create-schema

# Load data from parquet files (once you have them)
python scripts/setup_fsq_postgres.py \
  --load-data \
  --parquet-dir ./data/fsq-os-places/ \
  --batch-size 10000
```

### 4. Verify Installation

```bash
# Connect to database
psql -d fsq_places

# Check record count
SELECT COUNT(*) FROM fsq_places;

# Test spatial query
SELECT name, country, locality
FROM fsq_places
WHERE ST_DWithin(
    geom,
    ST_SetSRID(ST_MakePoint(-0.1276, 51.5074), 4326)::geography,
    1000  -- 1km radius
)
LIMIT 10;

# Test fuzzy name search
SELECT name, locality, country
FROM fsq_places
WHERE similarity(LOWER(name), 'starbucks') > 0.5
ORDER BY similarity(LOWER(name), 'starbucks') DESC
LIMIT 10;
```

## Usage

### Enrich Your Tenant Data

```bash
# Enrich scraped tenant data with FSQ information
python scripts/enrich_tenants_with_fsq.py \
  --input outputs/mecsr/complete_tenants_aggregate.json \
  --output outputs/mecsr/tenants_enriched_with_fsq.json \
  --match-threshold 0.8
```

### Matching Strategies

The enrichment script uses multiple strategies to find matches:

1. **Exact Name + Locality**: Normalized exact match in same city
2. **Geographic Proximity**: Within 500m radius (if coordinates available)
3. **Fuzzy + Country**: Similarity matching within same country
4. **Global Fuzzy**: Last resort global search (>60% similarity)

### Output Format

```json
{
  "name": "Starbucks",
  "category": "Coffee Shop",
  "rating": 4.2,
  "fsq_match": {
    "fsq_place_id": "4a0c7b9ef964a520c8b21fe3",
    "fsq_name": "Starbucks",
    "fsq_website": "https://www.starbucks.com",
    "fsq_email": null,
    "fsq_phone": "+1-800-782-7282",
    "fsq_categories": ["Coffee Shop", "Café"],
    "fsq_verified": true,
    "match_type": "exact_locality",
    "match_score": 1.0,
    "similarity": 1.0
  },
  "fsq_confidence": 1.0,
  "website": "https://www.starbucks.com"
}
```

## SQL Query Examples

### Find All Locations of a Chain

```sql
SELECT name, address, locality, country, website
FROM fsq_places
WHERE LOWER(name) LIKE '%zara%'
  AND country IN ('US', 'GB', 'FR')
ORDER BY country, locality;
```

### Find Chains with Most Locations

```sql
SELECT * FROM fsq_chains
WHERE location_count > 100
ORDER BY location_count DESC
LIMIT 20;
```

### Find Tenants Near a Mall

```sql
-- Find all businesses within 1km of a mall
SELECT 
    f.name,
    f.categories,
    f.website,
    ST_Distance(
        f.geom,
        ST_SetSRID(ST_MakePoint(-0.1419, 51.5074), 4326)::geography
    ) / 1000.0 as distance_km
FROM fsq_places f
WHERE ST_DWithin(
    f.geom,
    ST_SetSRID(ST_MakePoint(-0.1419, 51.5074), 4326)::geography,
    1000  -- meters
)
ORDER BY distance_km;
```

### Match Tenants by Name and Location

```sql
-- Fuzzy name matching with location
SELECT 
    f.name as fsq_name,
    f.locality,
    f.website,
    similarity(LOWER(f.name), 'h&m') as name_similarity
FROM fsq_places f
WHERE similarity(LOWER(f.name), 'h&m') > 0.5
  AND f.locality ILIKE '%london%'
ORDER BY name_similarity DESC
LIMIT 10;
```

## Integration with Existing Pipeline

### Option 1: Post-Processing Enrichment

```python
# After scraping all tenants
from scripts.enrich_tenants_with_fsq import enrich_tenant
import psycopg2

conn = psycopg2.connect(...)

for tenant in tenants:
    enriched_tenant = enrich_tenant(conn, tenant)
    # Save enriched data
```

### Option 2: Real-Time Enrichment

```python
# During scraping
from tenant_scraper import TenantScraper
from scripts.enrich_tenants_with_fsq import find_fsq_matches

async with TenantScraper() as scraper:
    tenants = await scraper.scrape_tenants(url)
    
    for tenant in tenants:
        # Enrich in real-time
        fsq_matches = find_fsq_matches(conn, tenant["name"])
        tenant["fsq_match"] = fsq_matches[0] if fsq_matches else None
```

## Performance Optimization

### Indexes

The setup script creates these indexes automatically:
- Full-text search on names (`gin`)
- Lowercase name for exact matching
- Country, locality for filtering
- JSONB categories for category queries
- Spatial index on geometry (`gist`)

### Query Optimization Tips

1. **Use Indexes**: Always filter by indexed columns first
2. **Limit Results**: Use `LIMIT` for large result sets
3. **Batch Processing**: Process tenants in batches of 100-1000
4. **Connection Pooling**: Reuse database connections
5. **Prepare Statements**: Use prepared statements for repeated queries

### Expected Performance

- **Single tenant lookup**: <10ms
- **Batch of 100 tenants**: <1 second
- **Full dataset load**: 1-2 hours for 100M records

## Data Updates

FSQ-OS-Places is updated monthly. To update your local database:

```bash
# Download new parquet files
# Then reload (this will upsert based on fsq_place_id)
python scripts/setup_fsq_postgres.py \
  --load-data \
  --parquet-dir ./data/fsq-os-places-2025-05/ \
  --batch-size 10000
```

## Troubleshooting

### Connection Issues

```bash
# Check PostgreSQL is running
pg_isready

# Check connection
psql -h localhost -U $USER -d fsq_places -c "SELECT 1"
```

### PostGIS Not Available

```bash
# Install PostGIS extension
psql -d fsq_places -c "CREATE EXTENSION postgis"
```

### Memory Issues During Load

```bash
# Reduce batch size
python scripts/setup_fsq_postgres.py \
  --load-data \
  --parquet-file ./data/fsq-os-places-0001.parquet \
  --batch-size 1000  # Smaller batch
```

### Slow Queries

```sql
-- Check if indexes are being used
EXPLAIN ANALYZE
SELECT * FROM fsq_places
WHERE LOWER(name) LIKE '%starbucks%'
LIMIT 10;

-- Rebuild indexes if needed
REINDEX TABLE fsq_places;

-- Update statistics
ANALYZE fsq_places;
```

## Cost Comparison

| Solution | Setup | Storage | Queries | Total/Month |
|----------|-------|---------|---------|-------------|
| PostgreSQL (Local) | Free | ~50GB disk | Free | **$0** |
| MotherDuck | Free tier | $0.08/GB | $0.01/GB scan | ~$5-20 |
| ClickHouse Cloud | Free tier | $0.08/GB | Pay per query | ~$5-15 |
| Hugging Face + Memory | Free | RAM only | Free | **$0*** |

*Requires 16GB+ RAM for full dataset

## Next Steps

1. **Get Access**: Request access to FSQ-OS-Places dataset
2. **Setup Database**: Run setup script to create schema
3. **Load Sample**: Start with small sample to test
4. **Enrich Data**: Run enrichment on your scraped tenants
5. **Analyze Results**: Compare FSQ data with Google Maps data
6. **Optimize**: Tune queries and indexes for your use case

## Resources

- **FSQ-OS-Places Dataset**: https://huggingface.co/datasets/foursquare/fsq-os-places
- **ClickHouse Example**: https://clickhouse.com/blog/fsq
- **PostGIS Documentation**: https://postgis.net/documentation/
- **Foursquare Blog**: https://foursquare.com/resources/blog/data/




