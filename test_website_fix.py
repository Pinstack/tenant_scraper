#!/usr/bin/env python3
"""Test website extraction fix with expansion button clicking."""

import asyncio
import logging
import json
from tenant_scraper.scraper import TenantScraper, ScraperSettings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test():
    print("🔍 Testing Website Extraction Fix\n")
    print("=" * 70)
    
    # Test on first 20 cards to see improvement
    settings = ScraperSettings(detail_max_cards=20)
    
    async with TenantScraper(settings=settings) as scraper:
        tenants = await scraper.scrape_tenants(
            'https://maps.app.goo.gl/FsGevWWrjvab4tZ9A',
            fetch_details=True
        )
        
        total = len(tenants)
        with_website = sum(1 for t in tenants if t.get('website'))
        
        print("\n" + "=" * 70)
        print("📊 RESULTS")
        print("=" * 70)
        print(f"\nTotal tenants: {total}")
        print(f"With websites: {with_website}/{total} ({with_website*100//total if total > 0 else 0}%)")
        
        print(f"\n📋 Sample results:")
        for i, t in enumerate(tenants[:10], 1):
            website = t.get('website', 'NOT FOUND')
            status = '✅' if website != 'NOT FOUND' else '❌'
            print(f"{status} {i}. {t.get('name')}: {website[:50] if website != 'NOT FOUND' else 'NO WEBSITE'}...")
        
        # Check specific known businesses
        print(f"\n🎯 Checking known businesses:")
        known = ['Boots', 'LEGO', 'Starbucks', 'Samsung']
        for name in known:
            found = [t for t in tenants if name.lower() in t.get('name', '').lower()]
            if found:
                t = found[0]
                website = t.get('website', 'NOT FOUND')
                status = '✅' if website != 'NOT FOUND' else '❌'
                print(f"  {status} {t['name']}: {website}")
        
        # Save results
        with open('outputs/website-fix-test-results.json', 'w') as f:
            json.dump(tenants, f, indent=2)
        
        print(f"\n✅ Results saved to: outputs/website-fix-test-results.json")
        
        return with_website, total

if __name__ == "__main__":
    with_website, total = asyncio.run(test())
    improvement = with_website - 1  # Previously had ~1-2 websites in first 20
    print(f"\n📈 IMPROVEMENT: +{improvement} websites extracted vs previous run")

