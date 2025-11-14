#!/usr/bin/env python3
"""Investigate the new card structure - buttons vs links."""

import asyncio
from playwright.async_api import async_playwright

async def investigate():
    print("🔍 Investigating New Card Structure\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        url = "https://maps.app.goo.gl/FsGevWWrjvab4tZ9A"
        
        print(f"1. Navigating to: {url}")
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        # Handle consent
        print("\n2. Handling consent...")
        try:
            consent = page.locator("[aria-label*='Accept all' i]").first
            if await consent.count() > 0:
                await consent.click()
                await asyncio.sleep(2)
                print(f"   ✓ Clicked consent")
        except:
            print("   No consent needed")
        
        # Click View all
        print("\n3. Clicking 'View all' button...")
        view_all = page.locator("button:has-text('View all')").first
        if await view_all.count() > 0:
            await view_all.click()
            await asyncio.sleep(3)
            print("   ✓ Clicked 'View all'")
        
        # Check for buttons
        print("\n4. Analyzing button.hfpxzc elements...")
        buttons = page.locator("button.hfpxzc")
        button_count = await buttons.count()
        print(f"   Found {button_count} button.hfpxzc elements")
        
        if button_count > 0:
            print(f"\n5. Sampling first 5 buttons:")
            for i in range(min(5, button_count)):
                try:
                    button = buttons.nth(i)
                    # Get text content
                    text = await button.inner_text()
                    # Get aria-label
                    aria_label = await button.get_attribute('aria-label')
                    # Get data-item-id if present
                    data_id = await button.get_attribute('data-item-id')
                    # Get jsaction
                    jsaction = await button.get_attribute('jsaction')
                    
                    print(f"\n   Button {i+1}:")
                    print(f"     Text: {text[:80] if text else 'N/A'}")
                    print(f"     aria-label: {aria_label[:80] if aria_label else 'N/A'}")
                    print(f"     data-item-id: {data_id[:80] if data_id else 'N/A'}")
                    print(f"     jsaction: {jsaction[:80] if jsaction else 'N/A'}")
                    
                except Exception as e:
                    print(f"   Button {i+1}: Error - {e}")
        
        # Check the div.Nv2PK containers
        print(f"\n6. Analyzing div.Nv2PK containers...")
        divs = page.locator("div.Nv2PK")
        div_count = await divs.count()
        print(f"   Found {div_count} div.Nv2PK elements")
        
        if div_count > 0:
            print(f"\n7. Sampling first 3 div.Nv2PK containers:")
            for i in range(min(3, div_count)):
                try:
                    div = divs.nth(i)
                    # Get outer HTML (first 200 chars)
                    html = await div.evaluate("el => el.outerHTML")
                    # Look for nested anchor or button
                    nested_a = await div.locator("a").count()
                    nested_button = await div.locator("button").count()
                    
                    print(f"\n   Div {i+1}:")
                    print(f"     Has nested <a>: {nested_a}")
                    print(f"     Has nested <button>: {nested_button}")
                    print(f"     HTML preview: {html[:150]}...")
                    
                except Exception as e:
                    print(f"   Div {i+1}: Error - {e}")
        
        # Try to find if there are any links at all in the directory panel
        print("\n8. Looking for ANY links in the page...")
        all_links = page.locator("a[href*='place']")
        link_count = await all_links.count()
        print(f"   Found {link_count} links with 'place' in href")
        
        if link_count > 0:
            for i in range(min(3, link_count)):
                try:
                    link = all_links.nth(i)
                    text = await link.inner_text()
                    href = await link.get_attribute('href')
                    print(f"   Link {i+1}: {text[:50]} -> {href[:80]}")
                except Exception as e:
                    print(f"   Link {i+1}: Error - {e}")
        
        # Check if we're scrolling the right container
        print("\n9. Looking for scrollable directory panel...")
        scroll_containers = [
            "div[role='feed']",
            "[data-scraper-scroll-target='1']",
            "div.m6QErb.DxyBCb.kA9KIf.dS8AEf",
        ]
        
        for selector in scroll_containers:
            try:
                container = page.locator(selector)
                count = await container.count()
                if count > 0:
                    print(f"   ✓ Found {count} element(s) with: {selector}")
                    # Check if it has scrollable content
                    first = container.first
                    scroll_height = await first.evaluate("el => el.scrollHeight")
                    client_height = await first.evaluate("el => el.clientHeight")
                    print(f"     scrollHeight: {scroll_height}, clientHeight: {client_height}")
            except Exception as e:
                print(f"   Error checking {selector}: {e}")
        
        await browser.close()
        
        print("\n" + "="*70)
        print("ANALYSIS COMPLETE")
        print("="*70)

if __name__ == "__main__":
    asyncio.run(investigate())

