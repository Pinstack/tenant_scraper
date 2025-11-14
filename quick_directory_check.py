#!/usr/bin/env python3
"""Quick check of directory navigation without manual pause."""

import asyncio
from playwright.async_api import async_playwright

async def quick_check():
    print("🔍 Quick Directory Navigation Check\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        url = "https://maps.app.goo.gl/FsGevWWrjvab4tZ9A"
        
        print(f"1. Navigating to: {url}")
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        print(f"   URL: {page.url[:100]}")
        
        # Handle consent
        print("\n2. Handling consent...")
        try:
            consent = page.locator("[aria-label*='Accept all' i]").first
            if await consent.count() > 0:
                await consent.click()
                await asyncio.sleep(2)
                print(f"   ✓ Clicked consent")
                print(f"   URL: {page.url[:100]}")
        except:
            print("   No consent needed")
        
        # Check current state
        print("\n3. Checking for !10e3 in URL...")
        if "!10e3" in page.url:
            print("   ✓ Already in directory view")
        else:
            print("   ✗ Not in directory view")
            print(f"   Attempting to add !10e3...")
            
            # Parse URL and add !10e3
            base_url = page.url.split('?')[0].split('#')[0]
            if base_url.endswith('/'):
                base_url = base_url[:-1]
            new_url = base_url + "!10e3"
            
            print(f"   New URL: {new_url[:100]}")
            await page.goto(new_url, wait_until="domcontentloaded")
            await asyncio.sleep(3)
            print(f"   Result: {page.url[:100]}")
        
        # Count a.hfpxzc cards
        print("\n4. Looking for a.hfpxzc cards...")
        cards = page.locator("a.hfpxzc")
        count = await cards.count()
        print(f"   Found: {count} cards")
        
        if count == 0:
            print("\n5. Trying alternative approach - looking for View all button...")
            view_all = page.locator("button:has-text('View all')").first
            if await view_all.count() > 0:
                print("   ✓ Found 'View all' button, clicking...")
                await view_all.click()
                await asyncio.sleep(3)
                
                # Recount cards
                count = await cards.count()
                print(f"   Now found: {count} cards")
        
        # Sample the cards if found
        if count > 0:
            print(f"\n6. Sample of {min(3, count)} cards:")
            for i in range(min(3, count)):
                try:
                    card = cards.nth(i)
                    text = await card.inner_text()
                    print(f"   Card {i+1}: {text[:60]}")
                except Exception as e:
                    print(f"   Card {i+1}: Error - {e}")
        else:
            print("\n6. ❌ NO CARDS FOUND")
            
            # Debug: what selectors DO work?
            print("\n7. Testing alternative selectors...")
            test_selectors = {
                "a[href*='place']": "Links with 'place' in href",
                "div.Nv2PK": "Nv2PK containers",
                "[role='article']": "Article elements",
                "button.hfpxzc": "Buttons with hfpxzc class",
            }
            
            for selector, desc in test_selectors.items():
                try:
                    elems = page.locator(selector)
                    elem_count = await elems.count()
                    print(f"   {desc}: {elem_count}")
                except Exception as e:
                    print(f"   {desc}: Error - {e}")
        
        await browser.close()
        
        print("\n" + "="*60)
        print(f"RESULT: Found {count} tenant cards with a.hfpxzc selector")
        print("="*60)
        
        return count

if __name__ == "__main__":
    count = asyncio.run(quick_check())
    exit(0 if count > 0 else 1)

