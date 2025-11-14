#!/usr/bin/env python3
"""Find current working selectors for tenant cards."""

import asyncio
from playwright.async_api import async_playwright

async def find_selectors():
    print("🔎 Finding Current Tenant Card Selectors")
    print("=" * 70)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        page = await browser.new_page()
        
        url = "https://maps.app.goo.gl/FsGevWWrjvab4tZ9A"
        
        print(f"\n1. Navigate and setup...")
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        # Consent
        try:
            consent = page.locator("[aria-label*='Accept all' i]").first
            if await consent.count() > 0:
                await consent.click()
                await asyncio.sleep(2)
        except:
            pass
        
        # Click View all
        print("\n2. Clicking 'View all' button...")
        try:
            view_all = page.locator("button:has-text('View all')").first
            if await view_all.count() > 0:
                await view_all.click()
                await asyncio.sleep(4)  # Wait longer
                print("   ✓ Clicked, waiting for directory to load...")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Now let's dump the page HTML to inspect
        print("\n3. Saving page HTML for inspection...")
        html = await page.content()
        with open("outputs/directory_page.html", "w") as f:
            f.write(html)
        print("   ✓ Saved to outputs/directory_page.html")
        
        # Try many different selectors
        print("\n4. Testing various selectors...")
        test_selectors = [
            ("a.hfpxzc", "Original from investigation"),
            ("a[href*='/maps/place/']", "Any place links"),
            ("a[href*='/place/']", "Shorter place links"),
            ("a[class*='hfp']", "Class contains 'hfp'"),
            ("a[class*='zc']", "Class contains 'zc'"),
            ("[data-index]", "Elements with data-index"),
            ("div[role='article']", "Article divs"),
            ("div[role='feed'] a", "Links in feed"),
            ("div.Nv2PK", "Nv2PK containers"),
            ("div.Nv2PK a", "Links in Nv2PK"),
            ("div.Nv2PK button", "Buttons in Nv2PK"),
            ("[jsaction*='mouseover']", "Mouseover actions"),
            ("div[data-item-id]", "Items with data-item-id"),
            ("a[aria-label]", "Links with aria-label"),
        ]
        
        results = []
        for selector, description in test_selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                results.append((selector, description, count))
                print(f"   {selector:40s} {count:4d}  ({description})")
                
                # If we found some elements, show a sample
                if count > 0 and count < 500:  # Reasonable number
                    try:
                        first = elements.first
                        text = await first.inner_text()
                        if text and len(text.strip()) > 0:
                            print(f"      Sample text: {text[:60]}")
                    except:
                        pass
            except Exception as e:
                print(f"   {selector:40s} ERROR: {e}")
        
        # Find the most promising selector
        print("\n5. Analysis:")
        promising = [(s, d, c) for s, d, c in results if 5 < c < 200]
        if promising:
            promising.sort(key=lambda x: x[2], reverse=True)
            print(f"   Most promising selectors (5-200 elements):")
            for selector, desc, count in promising[:5]:
                print(f"     {selector:40s} {count:4d}  ({desc})")
        else:
            print("   ⚠️  No selectors in ideal range (5-200 elements)")
        
        print("\n6. Pausing for 10 seconds - check the browser...")
        print("   Look at the directory view and inspect elements manually")
        await asyncio.sleep(10)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(find_selectors())

