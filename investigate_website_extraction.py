#!/usr/bin/env python3
"""
Investigate why website extraction is failing.
This script will:
1. Navigate to a single known business (Boots)
2. Click the card
3. Wait for detail pane
4. Capture screenshots at each step
5. Log all website-related selectors found
6. Save DOM structure for analysis
"""

import asyncio
import logging
from playwright.async_api import async_playwright
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def investigate_single_business():
    """Investigate website extraction for a single business."""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to St James Quarter
            url = 'https://maps.app.goo.gl/FsGevWWrjvab4tZ9A'
            logger.info(f"Navigating to {url}")
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)
            
            # Handle consent if present
            logger.info("Checking for consent page...")
            if 'consent' in page.url.lower():
                logger.info("Consent page detected - accepting")
                accept_button = page.locator("button:has-text('Accept all')")
                if await accept_button.count() > 0:
                    await accept_button.first.click()
                    await asyncio.sleep(2)
            
            # Look for "View all" button
            logger.info("Looking for 'View all' button...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            view_all = page.locator("button:has-text('View all')")
            if await view_all.count() > 0:
                logger.info("Clicking 'View all'")
                await view_all.first.click()
                await asyncio.sleep(3)
            
            # Take screenshot of directory
            await page.screenshot(path="outputs/website-investigation-1-directory.png")
            logger.info("Screenshot saved: directory view")
            
            # Scroll to load all cards
            logger.info("Scrolling to load cards...")
            for i in range(3):
                await page.evaluate("document.querySelector('[role=main]').scrollTop += 500")
                await asyncio.sleep(1)
            
            # Find Boots card using button.hfpxzc selector
            logger.info("Looking for Boots card...")
            cards = page.locator("button.hfpxzc")
            card_count = await cards.count()
            logger.info(f"Found {card_count} cards total")
            
            boots_card = None
            for i in range(card_count):
                card = cards.nth(i)
                aria_label = await card.get_attribute('aria-label')
                if aria_label and 'boots' in aria_label.lower():
                    boots_card = card
                    logger.info(f"Found Boots card: {aria_label}")
                    break
            
            if not boots_card:
                logger.error("Could not find Boots card!")
                return
            
            # Click Boots card
            logger.info("Clicking Boots card...")
            await boots_card.click()
            await asyncio.sleep(2)
            
            # Wait for detail pane
            logger.info("Waiting for detail pane...")
            await page.wait_for_selector("h1", timeout=5000)
            await asyncio.sleep(2)
            
            # Take screenshot of detail pane
            await page.screenshot(path="outputs/website-investigation-2-detail-pane.png")
            logger.info("Screenshot saved: detail pane initial")
            
            # Scroll detail pane to load all content
            logger.info("Scrolling detail pane...")
            pane = page.locator("div[role='main']").first
            if await pane.count() > 0:
                await pane.evaluate("el => el.scrollTop = el.scrollHeight / 2")
                await asyncio.sleep(1)
                await pane.evaluate("el => el.scrollTop = el.scrollHeight")
                await asyncio.sleep(2)
            
            # Take screenshot after scrolling
            await page.screenshot(path="outputs/website-investigation-3-after-scroll.png")
            logger.info("Screenshot saved: after scrolling")
            
            # Try multiple website selectors
            selectors_to_try = [
                "a[data-tooltip='Open website']",
                "a[aria-label*='Website']",
                "a[aria-label*='website']",
                "a[data-tooltip*='website']",
                "a[href^='http']:not([href*='google']):not([href*='maps'])",
                "a[data-item-id*='website']",
                "button[data-tooltip*='website']",
                "button[aria-label*='Website']",
            ]
            
            logger.info("\n" + "="*70)
            logger.info("TESTING WEBSITE SELECTORS")
            logger.info("="*70)
            
            for selector in selectors_to_try:
                try:
                    elem = page.locator(selector).first
                    count = await elem.count()
                    logger.info(f"\nSelector: {selector}")
                    logger.info(f"  Count: {count}")
                    
                    if count > 0:
                        href = await elem.get_attribute('href')
                        aria_label = await elem.get_attribute('aria-label')
                        data_tooltip = await elem.get_attribute('data-tooltip')
                        text = await elem.inner_text()
                        
                        logger.info(f"  href: {href}")
                        logger.info(f"  aria-label: {aria_label}")
                        logger.info(f"  data-tooltip: {data_tooltip}")
                        logger.info(f"  text: {text[:100] if text else None}")
                except Exception as e:
                    logger.info(f"\nSelector: {selector}")
                    logger.info(f"  Error: {e}")
            
            # Find ALL links in detail pane
            logger.info("\n" + "="*70)
            logger.info("ALL LINKS IN DETAIL PANE")
            logger.info("="*70)
            
            all_links = page.locator("div[role='main'] a")
            link_count = await all_links.count()
            logger.info(f"Total links found: {link_count}")
            
            for i in range(min(link_count, 20)):
                link = all_links.nth(i)
                href = await link.get_attribute('href')
                aria_label = await link.get_attribute('aria-label')
                text = await link.inner_text()
                logger.info(f"\nLink {i+1}:")
                logger.info(f"  href: {href}")
                logger.info(f"  aria-label: {aria_label}")
                logger.info(f"  text: {text[:50] if text else None}")
            
            # Save DOM structure
            logger.info("\nSaving DOM structure...")
            detail_pane_html = await page.locator("div[role='main']").first.inner_html()
            Path("outputs/website-investigation-dom.html").write_text(detail_pane_html)
            logger.info("DOM saved to: outputs/website-investigation-dom.html")
            
            logger.info("\n" + "="*70)
            logger.info("INVESTIGATION COMPLETE")
            logger.info("="*70)
            logger.info("Review the following files:")
            logger.info("  - outputs/website-investigation-1-directory.png")
            logger.info("  - outputs/website-investigation-2-detail-pane.png")
            logger.info("  - outputs/website-investigation-3-after-scroll.png")
            logger.info("  - outputs/website-investigation-dom.html")
            
            # Keep browser open for manual inspection
            logger.info("\nKeeping browser open for 60 seconds for manual inspection...")
            await asyncio.sleep(60)
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(investigate_single_business())

