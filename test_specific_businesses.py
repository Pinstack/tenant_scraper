#!/usr/bin/env python3
"""Test website extraction for specific businesses."""

import asyncio
import logging
from tenant_scraper.scraper import TenantScraper

logging.basicConfig(level=logging.INFO)

async def test():
    async with TenantScraper() as scraper:
        # Get all tenants first
        tenants = await scraper.scrape_tenants(
            'https://maps.app.goo.gl/FsGevWWrjvab4tZ9A',
            fetch_details=False
        )
        
        # Find Boots, LEGO, Rituals
        target_names = ['Boots', 'LEGO', 'Rituals']
        targets = []
        
        for tenant in tenants:
            name = tenant.get('name', '')
            for target in target_names:
                if target.lower() in name.lower() and 'opticians' not in name.lower():
                    if not any(t['name'] == name for t in targets):
                        targets.append(tenant)
                        break
        
        print(f"\n🔍 Found {len(targets)} target businesses:")
        for t in targets:
            print(f"  - {t['name']}")
        
        # Now extract details for just these
        print(f"\n📋 Extracting details for target businesses...")
        detailed = await scraper.scrape_tenants(
            'https://maps.app.goo.gl/FsGevWWrjvab4tZ9A',
            fetch_details=True
        )
        
        # Match them up
        print(f"\n📊 Results:")
        print("=" * 70)
        for target in targets:
            target_name = target['name']
            found = next((t for t in detailed if t.get('name') == target_name), None)
            if found:
                website = found.get('website', 'NOT FOUND')
                status = '✅' if website != 'NOT FOUND' else '❌'
                print(f"{status} {target_name}: {website}")
            else:
                print(f"❌ {target_name}: Not found in detailed results")

if __name__ == "__main__":
    asyncio.run(test())

