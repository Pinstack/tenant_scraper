#!/usr/bin/env python3
"""Quick test of detail extraction on a small set of tenants."""

import asyncio
import json
from tenant_scraper.scraper import TenantScraper

async def main():
    # Test with a smaller mall or just a few cards
    url = "https://maps.app.goo.gl/FsGevWWrjvab4tZ9A"  # St James Quarter
    
    print("🧪 Testing Detail Extraction Pipeline")
    print("=" * 60)
    
    async with TenantScraper(headless=False) as scraper:
        # First get basic tenants
        print("\n1️⃣  Extracting basic tenant data...")
        basic_tenants = await scraper.scrape_tenants(url, extraction_mode="directory")
        print(f"   Found {len(basic_tenants)} basic tenants")
        
        if not basic_tenants:
            print("   ❌ No tenants found in basic extraction")
            return
        
        # Display first few
        for i, t in enumerate(basic_tenants[:3], 1):
            print(f"   {i}. {t.get('name')} - {t.get('category')}")
        
        # Now test detail extraction on the same session
        print(f"\n2️⃣  Testing detail extraction on {len(basic_tenants)} tenants...")
        print("   (This will click each card and extract phone/website/hours)")
        
        # Use the _extract_detailed_tenant_data method directly
        detailed_tenants = await scraper._extract_detailed_tenant_data(basic_tenants)
        
        print(f"\n3️⃣  Results:")
        print(f"   Total tenants: {len(detailed_tenants)}")
        
        # Count how many have contact details
        with_phone = sum(1 for t in detailed_tenants if t.get('phone'))
        with_website = sum(1 for t in detailed_tenants if t.get('website'))
        with_hours = sum(1 for t in detailed_tenants if t.get('hours'))
        
        print(f"   With phone: {with_phone}")
        print(f"   With website: {with_website}")
        print(f"   With hours: {with_hours}")
        
        # Show details for first few
        print(f"\n4️⃣  Sample enriched data:")
        for i, tenant in enumerate(detailed_tenants[:3], 1):
            print(f"\n   Tenant {i}: {tenant.get('name')}")
            print(f"     Category: {tenant.get('category')}")
            print(f"     Phone: {tenant.get('phone') or 'Not found'}")
            print(f"     Website: {tenant.get('website') or 'Not found'}")
            print(f"     Hours: {tenant.get('hours', 'Not found')[:50] if tenant.get('hours') else 'Not found'}...")
        
        # Save results
        output_file = "outputs/detail-extraction-test-results.json"
        with open(output_file, 'w') as f:
            json.dump(detailed_tenants, f, indent=2)
        print(f"\n✅ Full results saved to: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())

