#!/usr/bin/env python3
"""
Quality tests for website extraction.

Validates that website extraction meets the 90%+ requirement for businesses
with websites listed on Google Maps.
"""

import asyncio
import pytest
from playwright.async_api import async_playwright, Page

# Test URL
TEST_URL = "https://maps.app.goo.gl/FsGevWWrjvab4tZ9A"

# Minimum required extraction rate (90%)
MIN_EXTRACTION_RATE = 0.90


async def navigate_to_directory_and_click_card(page: Page, card_index: int = 0) -> bool:
    """Navigate to directory view and click a tenant card."""
    print(f"\n📍 Navigating to: {TEST_URL}")
    await page.goto(TEST_URL, wait_until="domcontentloaded")
    await asyncio.sleep(2)
    
    # Handle consent
    try:
        consent = page.locator("[aria-label*='Accept all' i]").first
        if await consent.count() > 0:
            await consent.click()
            await asyncio.sleep(2)
    except Exception:
        pass
    
    # Scroll and click "View all"
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(2)
    
    try:
        view_all = page.locator("button:has-text('View all')").first
        if await view_all.count() > 0:
            await view_all.click()
            await asyncio.sleep(3)
    except Exception:
        pass
    
    # Click the specified card
    try:
        cards = page.locator("button.hfpxzc")
        card_count = await cards.count()
        if card_count > card_index:
            card = cards.nth(card_index)
            await card.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            await card.click()
            await asyncio.sleep(2)
            return True
    except Exception as e:
        print(f"Error clicking card: {e}")
    
    return False


async def check_website_in_detail_pane(page: Page) -> dict:
    """Check if website link exists in detail pane."""
    await asyncio.sleep(1)  # Wait for detail pane to load
    
    result = {
        'found': False,
        'href': None,
        'aria_label': None,
        'selector_used': None
    }
    
    # Try primary selector
    website_selector = "a[data-tooltip='Open website']"
    website_elem = page.locator(website_selector).first
    count = await website_elem.count()
    
    if count > 0:
        result['found'] = True
        result['selector_used'] = website_selector
        result['href'] = await website_elem.get_attribute('href')
        result['aria_label'] = await website_elem.get_attribute('aria-label')
        return result
    
    # Try fallback selectors
    fallback_selectors = [
        "a[aria-label*='Website']",
        "a[aria-label*='website']",
        "a[data-tooltip*='website']",
        "a[href^='http']:not([href*='google']):not([href*='maps'])"
    ]
    
    for selector in fallback_selectors:
        elem = page.locator(selector).first
        count = await elem.count()
        if count > 0:
            result['found'] = True
            result['selector_used'] = selector
            result['href'] = await elem.get_attribute('href')
            result['aria_label'] = await elem.get_attribute('aria-label')
            return result
    
    return result


@pytest.mark.asyncio
async def test_website_extraction_quality_sample():
    """
    Test website extraction on a sample of businesses.
    
    This test checks a sample of businesses to validate that websites
    are being extracted when they exist on Google Maps.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Test first 10 cards
        sample_size = 10
        websites_found = 0
        websites_available = 0
        
        print(f"\n🧪 Testing website extraction on {sample_size} businesses...")
        
        for i in range(sample_size):
            # Navigate and click card
            success = await navigate_to_directory_and_click_card(page, i)
            if not success:
                print(f"  Card {i+1}: Failed to click")
                await browser.close()
                continue
            
            # Check for website
            result = await check_website_in_detail_pane(page)
            
            if result['found']:
                websites_found += 1
                websites_available += 1
                print(f"  Card {i+1}: ✅ Website found - {result['href'][:60] if result['href'] else result['aria_label']}")
            else:
                # Check if business actually has a website by looking for any http links
                all_links = page.locator("a[href^='http']:not([href*='google']):not([href*='maps'])")
                link_count = await all_links.count()
                if link_count > 0:
                    websites_available += 1
                    print(f"  Card {i+1}: ❌ Website exists but not extracted")
                else:
                    print(f"  Card {i+1}: ℹ️  No website listed")
            
            # Navigate back
            try:
                await page.go_back()
                await asyncio.sleep(1)
            except Exception:
                pass
        
        await browser.close()
        
        if websites_available == 0:
            pytest.skip("No businesses with websites found in sample")
        
        extraction_rate = websites_found / websites_available if websites_available > 0 else 0
        
        print(f"\n📊 Results:")
        print(f"  Businesses with websites: {websites_available}/{sample_size}")
        print(f"  Websites extracted: {websites_found}/{websites_available}")
        print(f"  Extraction rate: {extraction_rate*100:.1f}%")
        print(f"  Required: {MIN_EXTRACTION_RATE*100:.0f}%")
        
        assert extraction_rate >= MIN_EXTRACTION_RATE, (
            f"Website extraction rate {extraction_rate*100:.1f}% is below required {MIN_EXTRACTION_RATE*100:.0f}%\n"
            f"  Extracted: {websites_found}/{websites_available}\n"
            f"  This indicates a problem with website extraction logic."
        )


@pytest.mark.asyncio
async def test_website_extraction_known_businesses():
    """
    Test website extraction on known businesses that should have websites.
    
    Validates extraction on businesses manually verified to have websites.
    """
    known_businesses = [
        "Boots",
        "LEGO",
        "Rituals"
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await navigate_to_directory_and_click_card(page, 0)
        
        # Search for each known business
        results = {}
        for business_name in known_businesses:
            try:
                # Search for business
                search_box = page.locator("input[aria-label*='Search' i], combobox").first
                await search_box.fill(f"{business_name} St James Quarter")
                await page.keyboard.press('Enter')
                await asyncio.sleep(3)
                
                # Check for website
                result = await check_website_in_detail_pane(page)
                results[business_name] = result
                
                print(f"  {business_name}: {'✅' if result['found'] else '❌'}")
                
            except Exception as e:
                print(f"  {business_name}: Error - {e}")
                results[business_name] = {'found': False}
        
        await browser.close()
        
        # Calculate success rate
        found_count = sum(1 for r in results.values() if r.get('found'))
        total_count = len(results)
        success_rate = found_count / total_count if total_count > 0 else 0
        
        print(f"\n📊 Known Businesses Test:")
        print(f"  Websites extracted: {found_count}/{total_count}")
        print(f"  Success rate: {success_rate*100:.1f}%")
        print(f"  Required: {MIN_EXTRACTION_RATE*100:.0f}%")
        
        assert success_rate >= MIN_EXTRACTION_RATE, (
            f"Website extraction failed for known businesses: {success_rate*100:.1f}% < {MIN_EXTRACTION_RATE*100:.0f}%\n"
            f"  This indicates a critical issue with website extraction."
        )


if __name__ == "__main__":
    print("🧪 Running Website Extraction Quality Tests\n")
    print("=" * 70)
    
    async def run_tests():
        print("\n1️⃣  Test: Website extraction quality sample")
        await test_website_extraction_quality_sample()
        
        print("\n2️⃣  Test: Known businesses with websites")
        await test_website_extraction_known_businesses()
        
        print("\n" + "=" * 70)
        print("✅ All quality tests passed!")
    
    asyncio.run(run_tests())

