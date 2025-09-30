"""Regression tests for the directory HTML parser."""

import asyncio
import os

from tenant_scraper.scraper import TenantScraper


def test_parse_debug_snapshot_returns_expected_tenants():
    """Ensure the parser can recover a large tenant list from saved HTML."""

    snapshot_path = os.path.join(os.path.dirname(__file__), "..", "debug_extracted_dom.html")
    snapshot_path = os.path.abspath(snapshot_path)

    if not os.path.exists(snapshot_path):
        return  # Snapshot not available; skip silently for CI environments

    with open(snapshot_path, "r", encoding="utf-8") as handle:
        html = handle.read()

    scraper = TenantScraper(headless=True, block_resources=False)
    tenants = asyncio.run(scraper._parse_tenant_table_html(html))

    assert len(tenants) >= 120
    assert any(t.get("name", "").lower() == "maki & ramen" for t in tenants)
