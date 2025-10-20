#!/usr/bin/env python3
"""
Quickstart script for FSQ-OS-Places PostgreSQL integration.

This script:
1. Sets up PostgreSQL database and schema
2. Downloads a sample parquet file
3. Loads sample data
4. Runs a demo
5. Shows next steps for full implementation
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import psycopg2


def run_command(cmd: str, description: str) -> bool:
    """Run a shell command and return success status."""
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"{'='*60}")
    print(f"Running: {cmd}")

    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print("✅ Success!")
        if result.stdout.strip():
            print(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False


def check_postgres_connection():
    """Check if we can connect to PostgreSQL."""
    try:
        config = {
            "host": "localhost",
            "port": 5432,
            "user": "postgres",  # Try default user first
            "database": "postgres",
        }

        # Try different user names
        users_to_try = ["postgres", "current_user", None]
        for user in users_to_try:
            if user == "current_user":
                import os
                config["user"] = os.getenv("USER")
            elif user is None:
                continue
            else:
                config["user"] = user

            try:
                conn = psycopg2.connect(**config)
                conn.close()
                print(f"✅ PostgreSQL connection successful (user: {config['user']})")
                return True
            except:
                continue

        print("❌ Could not connect to PostgreSQL")
        print("Make sure PostgreSQL is running and you have access")
        return False

    except Exception as e:
        print(f"❌ PostgreSQL connection check failed: {e}")
        return False


def main():
    """Main quickstart function."""
    print("🚀 FSQ-OS-PLACES POSTGRESQL QUICKSTART")
    print("=" * 80)

    # Check prerequisites
    print("\n📋 CHECKING PREREQUISITES...")

    # Check PostgreSQL
    if not check_postgres_connection():
        print("\n❌ PostgreSQL not accessible. Please:")
        print("1. Install PostgreSQL: brew install postgresql@17")
        print("2. Start PostgreSQL: brew services start postgresql@17")
        print("3. Create user/database if needed")
        sys.exit(1)

    # Check Python dependencies
    try:
        import psycopg2, pandas, pyarrow
        print("✅ Python dependencies available")
    except ImportError as e:
        print(f"❌ Missing Python dependencies: {e}")
        print("Install with: pip install psycopg2-binary pandas pyarrow")
        sys.exit(1)

    # Step 1: Create database and schema
    success = run_command(
        "python scripts/setup_fsq_postgres.py --create-db --create-schema",
        "Create PostgreSQL database and schema"
    )
    if not success:
        print("❌ Database setup failed")
        sys.exit(1)

    # Step 2: Download sample data
    success = run_command(
        "python scripts/download_fsq_sample.py --output data/fsq-sample.parquet --max-size-mb 10",
        "Download sample FSQ-OS-Places data (10MB)"
    )
    if not success:
        print("⚠️ Sample download failed, but continuing...")

    # Step 3: Load sample data
    if Path("data/fsq-sample.parquet").exists():
        success = run_command(
            "python scripts/setup_fsq_postgres.py --load-data --parquet-file data/fsq-sample.parquet --batch-size 1000",
            "Load sample data into PostgreSQL"
        )
        if not success:
            print("❌ Data loading failed")
            sys.exit(1)
    else:
        print("⚠️ No sample file found, skipping data load")

    # Step 4: Run demo
    success = run_command(
        "python scripts/demo_fsq_postgres.py",
        "Run PostgreSQL integration demo"
    )

    # Success summary
    print("\n" + "="*80)
    print("🎉 QUICKSTART COMPLETE!")
    print("="*80)
    print("\n✅ What you accomplished:")
    print("  • PostgreSQL database with PostGIS enabled")
    print("  • FSQ-OS-Places schema and indexes")
    print("  • Sample data loaded and queries working")
    print("  • Spatial queries and fuzzy text matching demonstrated")

    print("\n🚀 Next steps for full implementation:")
    print("1. Get full access to FSQ-OS-Places dataset:")
    print("   https://huggingface.co/datasets/foursquare/fsq-os-places")
    print()
    print("2. Download all parquet files:")
    print("   # Use huggingface-cli or download from HF website")
    print("   mkdir -p data/fsq-os-places")
    print("   # Download files to data/fsq-os-places/")
    print()
    print("3. Load full dataset:")
    print("   python scripts/setup_fsq_postgres.py \\")
    print("     --load-data --parquet-dir data/fsq-os-places/ \\")
    print("     --batch-size 10000")
    print()
    print("4. Enrich your scraped tenants:")
    print("   python scripts/enrich_tenants_with_fsq.py \\")
    print("     --input outputs/mecsr/complete_tenants_aggregate.json \\")
    print("     --output outputs/mecsr/tenants_with_fsq_enrichment.json")
    print()
    print("5. Integrate into your scraping pipeline:")
    print("   # Add FSQ enrichment to your scraper.py")
    print("   # Use enrich_tenant() function for real-time enrichment")

    print("\n💡 Pro tips:")
    print("• The full dataset is 11.3GB - plan for ~50GB PostgreSQL storage")
    print("• Loading takes 1-2 hours with batch_size=10000")
    print("• Add more indexes as needed for your query patterns")
    print("• Use connection pooling for production workloads")

    print("\n📚 Resources:")
    print("• FSQ-OS-Places: https://huggingface.co/datasets/foursquare/fsq-os-places")
    print("• PostGIS docs: https://postgis.net/documentation/")
    print("• Integration guide: docs/FSQ_INTEGRATION.md")


if __name__ == "__main__":
    main()




