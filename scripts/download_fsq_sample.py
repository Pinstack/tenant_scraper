#!/usr/bin/env python3
"""
Download a sample of FSQ-OS-Places data for testing.

This script downloads a small sample parquet file from the Hugging Face
dataset to test our PostgreSQL loading pipeline.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests
from huggingface_hub import HfApi


def download_sample_parquet(output_path: Path, max_size_mb: int = 50) -> bool:
    """Download a sample parquet file from FSQ-OS-Places dataset."""
    try:
        # Initialize HuggingFace API
        api = HfApi()

        # Get dataset info
        dataset_info = api.dataset_info("foursquare/fsq-os-places")
        print(f"Dataset: {dataset_info.id}")
        print(f"Size: {dataset_info.size_in_bytes / (1024**3):.1f} GB")
        print(f"Files: {len(dataset_info.siblings)}")

        # Find parquet files
        parquet_files = [
            sibling for sibling in dataset_info.siblings
            if sibling.rfilename.endswith('.parquet') and 'places' in sibling.rfilename
        ]

        if not parquet_files:
            print("No parquet files found!")
            return False

        # Sort by size (smallest first)
        parquet_files.sort(key=lambda x: x.size if x.size else 0)

        print(f"\nFound {len(parquet_files)} parquet files:")
        for i, pf in enumerate(parquet_files[:5]):  # Show first 5
            size_mb = pf.size / (1024**2) if pf.size else 0
            print(".1f")

        # Download the smallest file
        smallest_file = parquet_files[0]
        size_mb = smallest_file.size / (1024**2) if smallest_file.size else 0

        if size_mb > max_size_mb:
            print(f"Smallest file ({size_mb:.1f} MB) is larger than max_size_mb ({max_size_mb} MB)")
            print("Consider increasing max_size_mb or downloading manually")
            return False

        print(f"\nDownloading {smallest_file.rfilename} ({size_mb:.1f} MB)...")

        # Download file
        url = f"https://huggingface.co/datasets/foursquare/fsq-os-places/resolve/main/{smallest_file.rfilename}"
        response = requests.get(url, stream=True)

        if response.status_code == 200:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"Downloaded to: {output_path}")
            print(f"Size: {output_path.stat().st_size / (1024**2):.1f} MB")
            return True
        else:
            print(f"Failed to download: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"Error downloading sample: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Download FSQ-OS-Places sample data"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/fsq-os-places-sample.parquet"),
        help="Output path for sample parquet file"
    )
    parser.add_argument(
        "--max-size-mb",
        type=int,
        default=50,
        help="Maximum file size to download in MB"
    )

    args = parser.parse_args()

    success = download_sample_parquet(args.output, args.max_size_mb)

    if success:
        print(f"\nSuccess! Sample downloaded to {args.output}")
        print(f"You can now load it with:")
        print(f"python scripts/setup_fsq_postgres.py --load-data --parquet-file {args.output}")
    else:
        print("\nFailed to download sample. Try downloading manually from:")
        print("https://huggingface.co/datasets/foursquare/fsq-os-places")
        sys.exit(1)


if __name__ == "__main__":
    main()




