#!/usr/bin/env python3
"""
Test website extraction with debug logging enabled.
Tests on a small sample to see why websites aren't being extracted.
"""

import asyncio
import logging
import json
from tenant_scraper.scraper import TenantScraper

# Set up debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_website_extraction():
    """Test website extraction on a small sample with debug logging."""
    print("🔍 Testing Website Extraction with Debug Logging\n")
    print("=" * 70)
    
    from tenant_scraper.scraper import ScraperSettings
    
    # Limit to first 5 cards for testing
    settings = ScraperSettings(detail_max_cards=5)
    
    async with TenantScraper(settings=settings) as scraper:
        # Scrape just a few tenants to see debug output
        tenants = await scraper.scrape_tenants(
            'https://maps.app.goo.gl/FsGevWWrjvab4tZ9A',
            fetch_details=True
        )
        
        print("\n" + "=" * 70)
        print("📊 RESULTS SUMMARY")
        print("=" * 70)
        
        total = len(tenants)
        with_phone = sum(1 for t in tenants if t.get('phone'))
        with_website = sum(1 for t in tenants if t.get('website'))
        
        print(f"\nTotal tenants: {total}")
        print(f"With phone: {with_phone}/{total} ({with_phone*100//total if total > 0 else 0}%)")
        print(f"With website: {with_website}/{total} ({with_website*100//total if total > 0 else 0}%)")
        
        print("\n📋 Detailed Results:")
        for i, tenant in enumerate(tenants[:10], 1):
            print(f"\n{i}. {tenant.get('name', 'Unknown')}")
            print(f"   Phone: {tenant.get('phone', 'None')}")
            website = tenant.get('website', 'None')
            if website != 'None':
                print(f"   Website: {website}")
            else:
                print(f"   Website: ❌ NOT FOUND")
        
        # Save results
        with open('outputs/website-extraction-debug-results.json', 'w') as f:
            json.dump(tenants, f, indent=2)
        
        print(f"\n✅ Results saved to: outputs/website-extraction-debug-results.json")
        print("\n💡 Check the debug logs above to see why websites weren't extracted")

if __name__ == "__main__":
    asyncio.run(test_website_extraction())

