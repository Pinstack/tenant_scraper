#!/usr/bin/env python3
"""
Test improved website extraction with all enhancements:
- Better scrolling (multiple passes)
- Expansion button clicking
- More fallback selectors
- Button element support
"""

import asyncio
import logging
import json
import sys
from src.tenant_scraper.scraper import TenantScraper, ScraperSettings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def test_improved_extraction():
    print("🔍 Testing Improved Website Extraction\n")
    print("=" * 70)
    print("Enhancements:")
    print("  ✓ Better detail pane scrolling (multiple passes)")
    print("  ✓ Expansion button clicking")
    print("  ✓ Additional fallback selectors (buttons + links)")
    print("  ✓ Better aria-label/text extraction")
    print("=" * 70)
    
    # Test on all cards with no limit
    settings = ScraperSettings(
        detail_max_failures=10,  # Allow more failures before aborting
        detail_max_cards=None  # Process ALL cards
    )
    
    async with TenantScraper(settings=settings) as scraper:
        print(f"\n📍 Scraping: St James Quarter")
        print(f"⚙️  Settings: max_failures={settings.detail_max_failures}, max_cards=unlimited")
        print(f"\n⏳ This will take ~10-15 minutes for ~140 tenants...")
        print(f"   (approx 6 seconds per tenant)")
        
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
        
        extraction_rate = (with_website * 100 / total) if total > 0 else 0
        
        print(f"\n✅ Total tenants processed: {total}")
        print(f"📞 With phone: {with_phone}/{total} ({with_phone*100//total if total > 0 else 0}%)")
        print(f"🌐 With website: {with_website}/{total} ({extraction_rate:.1f}%)")
        
        print(f"\n🎯 TARGET: 90%+ website extraction")
        if extraction_rate >= 90:
            print(f"✅ SUCCESS! Achieved {extraction_rate:.1f}% extraction rate")
        elif extraction_rate >= 50:
            print(f"⚠️  PARTIAL: {extraction_rate:.1f}% (improved but not at target)")
        else:
            print(f"❌ NOT MET: {extraction_rate:.1f}% (still below target)")
        
        # Sample websites
        print(f"\n📋 Sample extracted websites:")
        websites_found = [t for t in tenants if t.get('website')]
        for i, tenant in enumerate(websites_found[:15], 1):
            website = tenant.get('website', '')
            domain = website.replace('https://', '').replace('http://', '').split('/')[0]
            print(f"  {i}. {tenant.get('name', 'Unknown')[:30]:30} → {domain}")
        
        # Check specific known businesses
        print(f"\n🎯 Checking specific known businesses:")
        known_brands = ['Boots', 'LEGO', 'Starbucks', 'Samsung', 'John Lewis']
        for brand in known_brands:
            found = [t for t in tenants if brand.lower() in t.get('name', '').lower()]
            if found:
                t = found[0]
                website = t.get('website', 'NOT FOUND')
                status = '✅' if website != 'NOT FOUND' else '❌'
                print(f"  {status} {t['name']}: {website[:60] if website != 'NOT FOUND' else 'NO WEBSITE'}...")
        
        # Save results
        output_file = 'outputs/improved-website-extraction-results.json'
        with open(output_file, 'w') as f:
            json.dump(tenants, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        
        # Comparison with previous run
        try:
            with open('outputs/full-website-extraction-results.json') as f:
                prev_data = json.load(f)
                prev_with_website = sum(1 for t in prev_data if t.get('website'))
                prev_total = len(prev_data)
                prev_rate = (prev_with_website * 100 / prev_total) if prev_total > 0 else 0
                
                improvement = extraction_rate - prev_rate
                websites_gained = with_website - prev_with_website
                
                print(f"\n📈 IMPROVEMENT vs Previous Run:")
                print(f"   Previous: {prev_with_website}/{prev_total} ({prev_rate:.1f}%)")
                print(f"   Current:  {with_website}/{total} ({extraction_rate:.1f}%)")
                print(f"   Gain:     +{websites_gained} websites (+{improvement:.1f}%)")
        except FileNotFoundError:
            pass
        
        return extraction_rate

if __name__ == "__main__":
    try:
        rate = asyncio.run(test_improved_extraction())
        sys.exit(0 if rate >= 90 else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

