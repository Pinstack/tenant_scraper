#!/usr/bin/env python3
"""Investigate why directory navigation isn't working properly."""

import asyncio
from playwright.async_api import async_playwright

async def investigate():
    print("🔍 Investigating Directory Navigation Issue")
    print("=" * 70)
    
    async with async_playwright() as p:
        # Use chromium (Chrome) in non-headless mode
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context()
        page = await context.new_page()
        
        url = "https://maps.app.goo.gl/FsGevWWrjvab4tZ9A"
        
        print(f"\n1️⃣  Navigating to: {url}")
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        current_url = page.url
        print(f"   Current URL: {current_url}")
        
        # Check for consent
        print("\n2️⃣  Checking for consent page...")
        try:
            consent_button = page.locator("[aria-label*='Accept all' i]").first
            if await consent_button.count() > 0:
                print("   ✓ Found consent button, clicking...")
                await consent_button.click()
                await asyncio.sleep(2)
                print(f"   New URL: {page.url}")
            else:
                print("   No consent page found")
        except Exception as e:
            print(f"   Consent handling error: {e}")
        
        # Check if we need !10e3
        print("\n3️⃣  Checking URL for !10e3 parameter...")
        if "!10e3" in page.url:
            print("   ✓ Already in directory view (!10e3 present)")
        else:
            print("   ✗ Not in directory view, need to add !10e3")
            print(f"   Current URL: {page.url}")
            
            # Try appending !10e3
            if page.url.startswith("https://www.google.com/maps/place/"):
                new_url = page.url + "!10e3"
                print(f"   Trying modified URL: {new_url[:80]}...")
                await page.goto(new_url, wait_until="domcontentloaded")
                await asyncio.sleep(3)
                print(f"   Result URL: {page.url}")
        
        # Check for "View all" button
        print("\n4️⃣  Looking for 'View all' button...")
        selectors_to_try = [
            "button:has-text('View all')",
            "[aria-label*='View all' i]",
            "button:has-text('view all')",
            "button[aria-label*='view' i]",
        ]
        
        for selector in selectors_to_try:
            try:
                button = page.locator(selector).first
                count = await button.count()
                if count > 0:
                    print(f"   ✓ Found with selector: {selector}")
                    button_text = await button.inner_text()
                    print(f"   Button text: {button_text}")
                    print(f"   Clicking...")
                    await button.click()
                    await asyncio.sleep(3)
                    print(f"   New URL: {page.url}")
                    break
                else:
                    print(f"   ✗ Not found: {selector}")
            except Exception as e:
                print(f"   Error with {selector}: {e}")
        
        # Check for tenant cards with a.hfpxzc
        print("\n5️⃣  Looking for tenant cards with a.hfpxzc...")
        cards = page.locator("a.hfpxzc")
        card_count = await cards.count()
        print(f"   Found {card_count} cards with a.hfpxzc selector")
        
        if card_count > 0:
            print(f"   ✓ Success! Found {card_count} tenant cards")
            # Show first few
            for i in range(min(5, card_count)):
                card = cards.nth(i)
                try:
                    text = await card.inner_text()
                    href = await card.get_attribute('href')
                    print(f"   Card {i+1}: {text[:50]}... -> {href[:50] if href else 'no href'}...")
                except Exception as e:
                    print(f"   Card {i+1}: Error reading - {e}")
        else:
            print("   ✗ No cards found with a.hfpxzc")
            
            # Try alternative selectors
            print("\n   Trying alternative selectors...")
            alt_selectors = [
                "a[href*='/maps/place/']",
                "[role='article']",
                "div.Nv2PK",
                "button.hfpxzc",
            ]
            
            for selector in alt_selectors:
                try:
                    elements = page.locator(selector)
                    count = await elements.count()
                    print(f"   {selector}: {count} elements")
                except Exception as e:
                    print(f"   {selector}: Error - {e}")
        
        # Look at the current page structure
        print("\n6️⃣  Current page structure analysis...")
        try:
            # Check for directory panel
            directory_selectors = [
                "[data-scraper-scroll-target='1']",
                "div[role='feed']",
                "div[role='main']",
            ]
            
            for selector in directory_selectors:
                elements = page.locator(selector)
                count = await elements.count()
                if count > 0:
                    print(f"   ✓ Found {count} elements with: {selector}")
                    # Get first element's aria-label if it exists
                    try:
                        first = elements.first
                        aria_label = await first.get_attribute('aria-label')
                        if aria_label:
                            print(f"     aria-label: {aria_label[:60]}...")
                    except:
                        pass
        except Exception as e:
            print(f"   Error analyzing structure: {e}")
        
        print("\n7️⃣  Pausing for manual inspection...")
        print("   Check the browser window - are you seeing the directory view?")
        print("   Press Ctrl+C when done inspecting...")
        
        try:
            await asyncio.sleep(300)  # 5 minutes for inspection
        except KeyboardInterrupt:
            print("\n   Inspection complete!")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(investigate())

