#!/usr/bin/env python3
"""
Demo script showing FSQ-OS-Places integration with PostgreSQL.

This script demonstrates:
1. Connecting to PostgreSQL with FSQ data
2. Running spatial queries
3. Finding matches for tenant enrichment
4. Performance benchmarks
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_config():
    """Get database configuration."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "user": os.getenv("POSTGRES_USER", os.getenv("USER")),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
        "database": os.getenv("POSTGRES_DB", "fsq_places"),
    }


def run_query(conn, query: str, description: str = ""):
    """Run a query and return results with timing."""
    print(f"\n{'='*60}")
    print(f"QUERY: {description}")
    print(f"{'='*60}")
    print(query)

    start_time = time.time()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute(query)
        results = cursor.fetchall()
        elapsed = time.time() - start_time

        print(".2f")
        print(f"Rows returned: {len(results)}")

        if results:
            # Show first few results
            for i, row in enumerate(results[:5]):
                print(f"  {i+1}. {dict(row)}")
            if len(results) > 5:
                print(f"  ... and {len(results) - 5} more rows")

        return results, elapsed

    except Exception as e:
        print(f"ERROR: {e}")
        return [], time.time() - start_time
    finally:
        cursor.close()


def demo_basic_queries(conn):
    """Demonstrate basic FSQ queries."""
    print("\n" + "="*80)
    print("FSQ-OS-PLACES POSTGRESQL DEMO")
    print("="*80)

    # 1. Total count
    run_query(
        conn,
        "SELECT COUNT(*) as total_places FROM fsq_places",
        "Total number of places in database"
    )

    # 2. Count by country
    run_query(
        conn,
        """
        SELECT country, COUNT(*) as count
        FROM fsq_places
        WHERE country IS NOT NULL
        GROUP BY country
        ORDER BY count DESC
        LIMIT 10
        """,
        "Places by country (top 10)"
    )

    # 3. Recent places
    run_query(
        conn,
        """
        SELECT name, locality, country, date_created, website
        FROM fsq_places
        WHERE date_created >= '2024-01-01'
        ORDER BY date_created DESC
        LIMIT 5
        """,
        "Recently added places (2024+)"
    )

    # 4. Places with websites
    run_query(
        conn,
        """
        SELECT COUNT(*) as places_with_websites
        FROM fsq_places
        WHERE website IS NOT NULL AND website != ''
        """,
        "Places with website information"
    )


def demo_spatial_queries(conn):
    """Demonstrate spatial queries using PostGIS."""
    print("\n" + "="*80)
    print("SPATIAL QUERIES DEMO")
    print("="*80)

    # 1. Places within radius of London
    run_query(
        conn,
        """
        SELECT name, address, locality, website,
               ST_Distance(geom, ST_SetSRID(ST_MakePoint(-0.1276, 51.5074), 4326)::geography) / 1000.0 as distance_km
        FROM fsq_places
        WHERE ST_DWithin(
            geom,
            ST_SetSRID(ST_MakePoint(-0.1276, 51.5074), 4326)::geography,
            1000  -- 1km radius
        )
        ORDER BY distance_km
        LIMIT 10
        """,
        "Places within 1km of central London"
    )

    # 2. Places near major malls (using some example coordinates)
    mall_locations = [
        (-0.1419, 51.5074, "Westfield London"),
        (-0.1276, 51.5074, "Oxford Street area"),
        (-87.6298, 41.8781, "Magnificent Mile, Chicago"),
    ]

    for lon, lat, location_name in mall_locations:
        results, elapsed = run_query(
            conn,
            f"""
            SELECT name, categories->0->>'label' as category, website,
                   ST_Distance(geom, ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)::geography) / 1000.0 as distance_km
            FROM fsq_places
            WHERE ST_DWithin(
                geom,
                ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)::geography,
                2000  -- 2km radius
            )
              AND categories IS NOT NULL
              AND jsonb_array_length(categories) > 0
            ORDER BY distance_km
            LIMIT 5
            """,
            f"Retail places near {location_name}"
        )


def demo_tenant_matching(conn):
    """Demonstrate tenant matching capabilities."""
    print("\n" + "="*80)
    print("TENANT MATCHING DEMO")
    print("="*80)

    # Example tenants to match (simulating scraped Google Maps data)
    test_tenants = [
        {
            "name": "Starbucks",
            "locality": "London",
            "latitude": 51.5074,
            "longitude": -0.1276
        },
        {
            "name": "H&M",
            "locality": "London",
            "latitude": 51.5074,
            "longitude": -0.1276
        },
        {
            "name": "Nike Store",
            "locality": "Chicago",
            "latitude": 41.8781,
            "longitude": -87.6298
        }
    ]

    for tenant in test_tenants:
        print(f"\n{'-'*60}")
        print(f"MATCHING: {tenant['name']} in {tenant['locality']}")
        print(f"{'-'*60}")

        # Fuzzy name match in locality
        results, elapsed = run_query(
            conn,
            f"""
            SELECT name, address, locality, website, phone,
                   categories->0->>'label' as primary_category,
                   similarity(LOWER(name), LOWER('{tenant['name']}')) as name_similarity
            FROM fsq_places
            WHERE locality ILIKE '%{tenant['locality'].split()[0]}%'  -- Match first word of locality
              AND similarity(LOWER(name), LOWER('{tenant['name']}')) > 0.3
            ORDER BY name_similarity DESC
            LIMIT 3
            """,
            f"Name matches for '{tenant['name']}' in {tenant['locality']}"
        )

        # Spatial proximity match
        if tenant.get('latitude') and tenant.get('longitude'):
            results, elapsed = run_query(
                conn,
                f"""
                SELECT name, address, locality, website,
                       ST_Distance(geom, ST_SetSRID(ST_MakePoint({tenant['longitude']}, {tenant['latitude']}), 4326)::geography) / 1000.0 as distance_km,
                       categories->0->>'label' as primary_category
                FROM fsq_places
                WHERE ST_DWithin(
                    geom,
                    ST_SetSRID(ST_MakePoint({tenant['longitude']}, {tenant['latitude']}), 4326)::geography,
                    1000  -- 1km radius
                )
                  AND similarity(LOWER(name), LOWER('{tenant['name']}')) > 0.4
                ORDER BY distance_km, similarity(LOWER(name), LOWER('{tenant['name']}')) DESC
                LIMIT 3
                """,
                f"Spatial matches for '{tenant['name']}' within 1km"
            )


def demo_performance_benchmarks(conn):
    """Run performance benchmarks."""
    print("\n" + "="*80)
    print("PERFORMANCE BENCHMARKS")
    print("="*80)

    benchmarks = [
        (
            "SELECT COUNT(*) FROM fsq_places",
            "Simple count query"
        ),
        (
            "SELECT COUNT(*) FROM fsq_places WHERE country = 'US'",
            "Count with country filter"
        ),
        (
            "SELECT COUNT(*) FROM fsq_places WHERE website IS NOT NULL",
            "Count places with websites"
        ),
        (
            "SELECT name FROM fsq_places WHERE LOWER(name) LIKE '%starbucks%' LIMIT 10",
            "Name search (no index)"
        ),
        (
            "SELECT name FROM fsq_places WHERE similarity(LOWER(name), 'starbucks') > 0.5 LIMIT 10",
            "Fuzzy name search (with pg_trgm)"
        ),
        (
            """
            SELECT name, ST_Distance(geom, ST_SetSRID(ST_MakePoint(-0.1276, 51.5074), 4326)::geography) as dist
            FROM fsq_places
            WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(-0.1276, 51.5074), 4326)::geography, 1000)
            ORDER BY dist LIMIT 10
            """,
            "Spatial query (1km radius around London)"
        )
    ]

    for query, description in benchmarks:
        _, elapsed = run_query(conn, query, description)
        print(".4f")


def main():
    """Main demo function."""
    config = get_db_config()

    print("Connecting to PostgreSQL...")
    print(f"Database: {config['database']} on {config['host']}:{config['port']}")

    try:
        conn = psycopg2.connect(**config)
        print("✅ Connected successfully!")

        # Enable pg_trgm for fuzzy text matching
        cursor = conn.cursor()
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        conn.commit()
        cursor.close()

        # Run demos
        demo_basic_queries(conn)
        demo_spatial_queries(conn)
        demo_tenant_matching(conn)
        demo_performance_benchmarks(conn)

        conn.close()
        print("\n" + "="*80)
        print("DEMO COMPLETE!")
        print("="*80)
        print("\nNext steps:")
        print("1. Download full FSQ-OS-Places dataset from Hugging Face")
        print("2. Load all data: python scripts/setup_fsq_postgres.py --load-data --parquet-dir ./data/fsq-os-places/")
        print("3. Enrich your tenants: python scripts/enrich_tenants_with_fsq.py --input your_data.json --output enriched.json")

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running: pg_isready")
        print("2. Check database exists: createdb fsq_places")
        print("3. Load sample data first: python scripts/download_fsq_sample.py")
        print("4. Set environment variables if needed:")
        print("   export POSTGRES_HOST=localhost")
        print("   export POSTGRES_USER=your_user")
        print("   export POSTGRES_DB=fsq_places")


if __name__ == "__main__":
    main()




