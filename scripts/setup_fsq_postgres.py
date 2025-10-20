#!/usr/bin/env python3
"""
Setup FSQ-OS-Places dataset in PostgreSQL for tenant enrichment.

This script:
1. Creates a PostgreSQL database for FSQ data
2. Downloads FSQ-OS-Places parquet files (or uses local copies)
3. Loads the data into PostgreSQL with proper indexing
4. Sets up PostGIS for spatial queries
5. Creates useful views and indexes for tenant matching

Requirements:
  pip install psycopg2-binary pandas pyarrow sqlalchemy geoalchemy2

Usage:
  # Create database and load data
  python scripts/setup_fsq_postgres.py --create-db --load-data
  
  # Just create schema (if DB exists)
  python scripts/setup_fsq_postgres.py --create-schema
  
  # Load from local parquet files
  python scripts/setup_fsq_postgres.py --load-data --parquet-dir ./data/fsq-os-places/
  
Environment Variables:
  POSTGRES_HOST     - PostgreSQL host (default: localhost)
  POSTGRES_PORT     - PostgreSQL port (default: 5432)
  POSTGRES_USER     - PostgreSQL user (default: current user)
  POSTGRES_PASSWORD - PostgreSQL password (optional)
  POSTGRES_DB       - Database name (default: fsq_places)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_db_config() -> dict:
    """Get database configuration from environment variables."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "user": os.getenv("POSTGRES_USER", os.getenv("USER")),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
        "database": os.getenv("POSTGRES_DB", "fsq_places"),
    }


def create_database(config: dict) -> bool:
    """Create the PostgreSQL database if it doesn't exist."""
    try:
        # Connect to default 'postgres' database to create our database
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (config["database"],)
        )
        exists = cursor.fetchone()
        
        if not exists:
            logger.info(f"Creating database: {config['database']}")
            cursor.execute(f"CREATE DATABASE {config['database']}")
            logger.info("Database created successfully")
        else:
            logger.info(f"Database {config['database']} already exists")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        return False


def create_schema(config: dict) -> bool:
    """Create the FSQ places table schema with PostGIS support."""
    try:
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        
        # Enable PostGIS extension
        logger.info("Enabling PostGIS extension...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        
        # Create main places table
        logger.info("Creating fsq_places table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fsq_places (
                fsq_place_id VARCHAR(50) PRIMARY KEY,
                name TEXT NOT NULL,
                latitude DOUBLE PRECISION,
                longitude DOUBLE PRECISION,
                geom GEOMETRY(POINT, 4326),  -- PostGIS geometry column
                address TEXT,
                locality TEXT,
                region TEXT,
                postcode VARCHAR(20),
                country VARCHAR(3),
                categories JSONB,  -- Store as JSONB for flexible querying
                website TEXT,
                email TEXT,
                phone TEXT,
                verified BOOLEAN,
                date_created DATE,
                date_refreshed DATE,
                date_closed DATE,  -- When place was closed/removed
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        logger.info("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fsq_name ON fsq_places USING gin(to_tsvector('english', name))")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fsq_name_lower ON fsq_places (LOWER(name))")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fsq_country ON fsq_places (country)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fsq_locality ON fsq_places (locality)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fsq_categories ON fsq_places USING gin(categories)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fsq_geom ON fsq_places USING gist(geom)")
        
        # Create useful views
        logger.info("Creating helper views...")
        cursor.execute("""
            CREATE OR REPLACE VIEW fsq_chains AS
            SELECT 
                LOWER(name) as chain_name,
                COUNT(*) as location_count,
                ARRAY_AGG(DISTINCT country) as countries,
                MIN(website) as website
            FROM fsq_places
            WHERE name IS NOT NULL
            GROUP BY LOWER(name)
            HAVING COUNT(*) > 1
            ORDER BY location_count DESC
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("Schema created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating schema: {e}")
        return False


def load_parquet_data(config: dict, parquet_path: Path, batch_size: int = 10000) -> bool:
    """Load data from FSQ-OS-Places parquet file into PostgreSQL."""
    try:
        logger.info(f"Loading data from {parquet_path}...")

        # Read parquet in chunks to handle large files
        df = pd.read_parquet(parquet_path)
        logger.info(f"Loaded {len(df)} rows from parquet")

        # Connect to database
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()

        # Prepare data for insertion
        total_rows = len(df)
        inserted = 0

        for i in range(0, total_rows, batch_size):
            batch = df.iloc[i:i+batch_size]

            # Build insert query - map FSQ-OS-Places schema to our table
            values = []
            for _, row in batch.iterrows():
                # Handle categories - convert list to JSONB
                fsq_category_ids = row.get('fsq_category_ids', [])
                fsq_category_labels = row.get('fsq_category_labels', [])

                # Combine categories into our format
                categories = []
                if fsq_category_ids and fsq_category_labels:
                    for cid, label in zip(fsq_category_ids, fsq_category_labels):
                        categories.append({
                            'id': cid,
                            'label': label
                        })

                categories_json = json.dumps(categories) if categories else None

                # Build geometry from lat/lon
                lat = row.get('latitude')
                lon = row.get('longitude')

                # Handle date fields
                date_created = row.get('date_created')
                date_refreshed = row.get('date_refreshed')
                date_closed = row.get('date_closed')

                values.append((
                    row.get('fsq_place_id'),
                    row.get('name'),
                    lat,
                    lon,
                    f"SRID=4326;POINT({lon} {lat})" if lat and lon and pd.notna(lat) and pd.notna(lon) else None,
                    row.get('address'),
                    row.get('locality'),
                    row.get('region'),
                    row.get('postcode'),
                    row.get('country'),
                    categories_json,  # Our categories format
                    row.get('website'),
                    row.get('email'),
                    row.get('tel'),  # FSQ uses 'tel' not 'phone'
                    None,  # verified - not in FSQ schema
                    date_created,
                    date_refreshed,
                    date_closed,  # Add date_closed to schema
                ))

            # Insert batch with updated column mapping
            cursor.executemany("""
                INSERT INTO fsq_places (
                    fsq_place_id, name, latitude, longitude, geom,
                    address, locality, region, postcode, country,
                    categories, website, email, phone, verified,
                    date_created, date_refreshed, date_closed
                )
                VALUES (%s, %s, %s, %s, ST_GeomFromText(%s), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fsq_place_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    geom = EXCLUDED.geom,
                    address = EXCLUDED.address,
                    locality = EXCLUDED.locality,
                    region = EXCLUDED.region,
                    postcode = EXCLUDED.postcode,
                    country = EXCLUDED.country,
                    categories = EXCLUDED.categories,
                    website = EXCLUDED.website,
                    email = EXCLUDED.email,
                    phone = EXCLUDED.phone,
                    verified = EXCLUDED.verified,
                    date_created = EXCLUDED.date_created,
                    date_refreshed = EXCLUDED.date_refreshed,
                    date_closed = EXCLUDED.date_closed,
                    updated_at = CURRENT_TIMESTAMP
            """, values)

            conn.commit()
            inserted += len(batch)
            logger.info(f"Inserted {inserted}/{total_rows} rows ({inserted/total_rows*100:.1f}%)")

        cursor.close()
        conn.close()

        logger.info(f"Successfully loaded {inserted} rows")
        return True
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Setup FSQ-OS-Places in PostgreSQL"
    )
    parser.add_argument(
        "--create-db",
        action="store_true",
        help="Create the database if it doesn't exist"
    )
    parser.add_argument(
        "--create-schema",
        action="store_true",
        help="Create the table schema and indexes"
    )
    parser.add_argument(
        "--load-data",
        action="store_true",
        help="Load data from parquet files"
    )
    parser.add_argument(
        "--parquet-dir",
        type=Path,
        help="Directory containing parquet files"
    )
    parser.add_argument(
        "--parquet-file",
        type=Path,
        help="Single parquet file to load"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10000,
        help="Batch size for loading data (default: 10000)"
    )
    
    args = parser.parse_args()
    
    # Get database configuration
    config = get_db_config()
    
    # Create database if requested
    if args.create_db:
        if not create_database(config):
            sys.exit(1)
    
    # Create schema if requested
    if args.create_schema or args.load_data:
        if not create_schema(config):
            sys.exit(1)
    
    # Load data if requested
    if args.load_data:
        if args.parquet_file:
            if not args.parquet_file.exists():
                logger.error(f"Parquet file not found: {args.parquet_file}")
                sys.exit(1)
            load_parquet_data(config, args.parquet_file, args.batch_size)
        elif args.parquet_dir:
            if not args.parquet_dir.exists():
                logger.error(f"Parquet directory not found: {args.parquet_dir}")
                sys.exit(1)
            parquet_files = sorted(args.parquet_dir.glob("*.parquet"))
            if not parquet_files:
                logger.error(f"No parquet files found in {args.parquet_dir}")
                sys.exit(1)
            for pf in parquet_files:
                logger.info(f"Processing {pf.name}...")
                load_parquet_data(config, pf, args.batch_size)
        else:
            logger.error("Please specify --parquet-file or --parquet-dir")
            sys.exit(1)
    
    logger.info("Setup complete!")


if __name__ == "__main__":
    main()

