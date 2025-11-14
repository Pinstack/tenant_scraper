#!/usr/bin/env python3
"""
Full test of website extraction on all tenants.
"""

import asyncio
import json
from tenant_scraper.scraper import TenantScraper

async def test_full_extraction():
    """Test website extraction on all tenants."""
    print("🔍 Full Website Extraction Test\n")
    print("=" * 70)
    
    async with TenantScraper() as scraper:
        tenants = await scraper.scrape_tenants(
            'https://maps.app.goo.gl/FsGevWWrjvab4tZ9A',
            fetch_details=True
        )
        
        print("\n" + "=" * 70)
        print("📊 FINAL RESULTS")
        print("=" * 70)
        
        total = len(tenants)
        with_phone = sum(1 for t in tenants if t.get('phone'))
        with_website = sum(1 for t in tenants if t.get('website'))
        
        print(f"\nTotal tenants: {total}")
        print(f"With phone: {with_phone}/{total} ({with_phone*100//total if total > 0 else 0}%)")
        print(f"With website: {with_website}/{total} ({with_website*100//total if total > 0 else 0}%)")
        
        # Show comparison
        print(f"\n📈 IMPROVEMENT:")
        print(f"  Before fix: 5/140 websites (3.6%)")
        print(f"  After fix: {with_website}/{total} websites ({with_website*100//total if total > 0 else 0}%)")
        improvement = with_website - 5
        print(f"  Improvement: +{improvement} websites ({improvement*100//140 if 140 > 0 else 0}% increase)")
        
        # Show sample websites
        print(f"\n📋 Sample extracted websites:")
        websites_found = [t for t in tenants if t.get('website')]
        for i, tenant in enumerate(websites_found[:10], 1):
            website = tenant.get('website', '')
            print(f"  {i}. {tenant.get('name', 'Unknown')}: {website[:70]}...")
        
        # Save results
        with open('outputs/full-website-extraction-results.json', 'w') as f:
            json.dump(tenants, f, indent=2)
        
        print(f"\n✅ Results saved to: outputs/full-website-extraction-results.json")
        
        return with_website

if __name__ == "__main__":
    websites = asyncio.run(test_full_extraction())
    print(f"\n🎉 Extraction complete! Found {websites} websites.")

