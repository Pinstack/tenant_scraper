#!/usr/bin/env python3
"""
Deep investigation of Google Maps tenant card detail extraction for Epic 1.

This script specifically focuses on the card detail pane behavior:
1. Opens directory view
2. Clicks on individual tenant cards
3. Captures detail pane selectors and structure
4. Records network requests for detail data
5. Documents timing requirements
"""

import argparse
import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright, Page, Response


logger = logging.getLogger(__name__)


@dataclass
class DetailPaneCapture:
    """Captures information from a tenant detail pane."""
    tenant_index: int
    tenant_name: str
    card_selector: str
    detail_pane_visible: bool
    detail_pane_selectors: Dict[str, Any]
    extracted_fields: Dict[str, Optional[str]]
    screenshot_file: str
    dom_snapshot_file: str
    url_after_click: str
    timing: Dict[str, float]
    network_requests_during_open: List[Dict[str, Any]]


@dataclass
class CardInvestigationReport:
    """Complete investigation report."""
    mall_url: str
    mall_name: str
    timestamp: float
    
    # Directory view findings
    directory_url: str
    card_container_selector: str
    total_cards_found: int
    sample_cards_investigated: int
    
    # Detail pane findings
    detail_pane_captures: List[DetailPaneCapture]
    
    # Network observations
    protobuf_requests: List[Dict[str, Any]]
    api_endpoints_observed: List[str]
    
    # Timing and throttling
    timing_observations: Dict[str, Any]
    rate_limit_indicators: List[str]
    
    # Recommendations
    recommended_selectors: Dict[str, str]
    recommended_delays: Dict[str, float]
    automation_strategy: List[str]


async def handle_consent(page: Page) -> bool:
    """Handle consent page if present."""
    consent_selectors = [
        "[aria-label*='Accept' i]",
        "button:has-text('Accept')",
        "button:has-text('Agree')",
    ]
    
    for selector in consent_selectors:
        try:
            button = page.locator(selector).first
            if await button.count() > 0:
                await button.click(timeout=3000)
                await asyncio.sleep(1)
                logger.info(f"Clicked consent: {selector}")
                return True
        except Exception:
            continue
    
    return False


async def navigate_to_directory(page: Page) -> bool:
    """Navigate to directory view from mall page."""
    logger.info("Attempting to navigate to directory view...")
    
    # Wait for page to load
    await page.wait_for_load_state("networkidle", timeout=30000)
    await asyncio.sleep(2)
    
    # Check if already in directory view (!10e3 in URL)
    if "!10e3" in page.url:
        logger.info("Already in directory view")
        return True
    
    # Try to click "View all" button
    view_all_selectors = [
        "button:has-text('View all')",
        "[aria-label*='View all' i]",
    ]
    
    for selector in view_all_selectors:
        try:
            button = page.locator(selector).first
            if await button.count() > 0:
                await button.click(timeout=5000)
                await page.wait_for_load_state("networkidle", timeout=10000)
                await asyncio.sleep(2)
                
                if "!10e3" in page.url:
                    logger.info(f"Successfully navigated to directory view via {selector}")
                    return True
        except Exception as e:
            logger.debug(f"Failed with selector {selector}: {e}")
            continue
    
    logger.warning("Could not navigate to directory view")
    return False


async def find_card_selector(page: Page) -> Optional[str]:
    """Find the best selector for tenant cards."""
    logger.info("Finding tenant card selector...")
    
    # Potential selectors ordered by preference
    selectors = [
        "a.hfpxzc",  # Known working selector
        "[role='article']",
        "div[jsaction*='mouseover']",
        "a[href*='/maps/place/']",
    ]
    
    for selector in selectors:
        try:
            count = await page.locator(selector).count()
            if 5 <= count <= 500:  # Reasonable range for tenant cards
                logger.info(f"Found {count} cards with selector: {selector}")
                return selector
        except Exception as e:
            logger.debug(f"Selector {selector} failed: {e}")
            continue
    
    logger.warning("No suitable card selector found")
    return None


async def extract_card_details(page: Page, card_locator) -> Dict[str, Optional[str]]:
    """Extract details from the currently open detail pane."""
    details = {}
    
    # Common field selectors for detail pane
    field_selectors = {
        "name": "h1",
        "category": "button[jsaction*='category']",
        "rating": "div[jsaction*='rating'] span[role='img']",
        "phone": "button[data-tooltip='Copy phone number']",
        "website": "a[data-tooltip='Open website']",
        "address": "button[data-tooltip='Copy address']",
        "hours": "div[aria-label*='Hours']",
    }
    
    for field_name, selector in field_selectors.items():
        try:
            locator = page.locator(selector).first
            if await locator.count() > 0:
                text = await locator.inner_text(timeout=2000)
                details[field_name] = text.strip() if text else None
            else:
                details[field_name] = None
        except Exception:
            details[field_name] = None
    
    return details


async def investigate_card_detail(
    page: Page,
    card_selector: str,
    card_index: int,
    output_dir: Path,
    network_requests: List[Dict[str, Any]]
) -> DetailPaneCapture:
    """Investigate a single tenant card's detail pane."""
    logger.info(f"Investigating card {card_index}...")
    
    start_time = time.time()
    timing = {}
    requests_before = len(network_requests)
    
    try:
        # Get the card
        card = page.locator(card_selector).nth(card_index)
        
        # Get card name before clicking (for identification)
        try:
            tenant_name = await card.inner_text(timeout=2000)
            tenant_name = tenant_name.split('\n')[0][:50]  # First line, truncated
        except Exception:
            tenant_name = f"Unknown_{card_index}"
        
        logger.info(f"Card {card_index}: {tenant_name}")
        
        # Scroll card into view
        await card.scroll_into_view_if_needed(timeout=5000)
        await asyncio.sleep(0.5)
        timing["scroll"] = time.time() - start_time
        
        # Click the card
        click_start = time.time()
        await card.click(timeout=5000)
        await page.wait_for_load_state("networkidle", timeout=10000)
        await asyncio.sleep(2)  # Wait for detail pane to fully render
        timing["click_and_load"] = time.time() - click_start
        
        # Check if detail pane is visible
        # Detail pane typically opens on the right side
        detail_pane_visible = False
        detail_selectors = {}
        
        # Try to find detail pane
        possible_pane_selectors = [
            "div[role='main']",
            "div.m6QErb",  # Known detail pane class
            "div[aria-label*='Information']",
        ]
        
        for sel in possible_pane_selectors:
            try:
                pane = page.locator(sel).first
                if await pane.count() > 0 and await pane.is_visible():
                    detail_pane_visible = True
                    detail_selectors["pane"] = sel
                    break
            except Exception:
                continue
        
        # Extract fields from detail pane
        extracted_fields = await extract_card_details(page, card)
        
        # Get URL after click
        url_after = page.url
        
        # Take screenshot
        screenshot_file = f"card_{card_index:03d}_detail.png"
        await page.screenshot(path=output_dir / screenshot_file, full_page=True)
        
        # Save DOM
        dom_file = f"card_{card_index:03d}_detail_dom.html"
        dom_html = await page.content()
        (output_dir / dom_file).write_text(dom_html, encoding="utf-8")
        
        # Get network requests that occurred during this card opening
        requests_after = len(network_requests)
        new_requests = network_requests[requests_before:requests_after]
        
        timing["total"] = time.time() - start_time
        
        # Go back to directory view
        await page.go_back()
        await page.wait_for_load_state("networkidle", timeout=10000)
        await asyncio.sleep(1)
        
        return DetailPaneCapture(
            tenant_index=card_index,
            tenant_name=tenant_name,
            card_selector=card_selector,
            detail_pane_visible=detail_pane_visible,
            detail_pane_selectors=detail_selectors,
            extracted_fields=extracted_fields,
            screenshot_file=screenshot_file,
            dom_snapshot_file=dom_file,
            url_after_click=url_after,
            timing=timing,
            network_requests_during_open=new_requests,
        )
    
    except Exception as e:
        logger.error(f"Failed to investigate card {card_index}: {e}", exc_info=True)
        return DetailPaneCapture(
            tenant_index=card_index,
            tenant_name=f"Error_{card_index}",
            card_selector=card_selector,
            detail_pane_visible=False,
            detail_pane_selectors={},
            extracted_fields={},
            screenshot_file="",
            dom_snapshot_file="",
            url_after_click=page.url,
            timing=timing,
            network_requests_during_open=[],
        )


async def run_investigation(
    mall_url: str,
    mall_name: str,
    output_dir: Path,
    sample_size: int = 5,
    headless: bool = True
) -> CardInvestigationReport:
    """Run complete card detail investigation."""
    logger.info(f"Starting card detail investigation for: {mall_name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    network_requests = []
    protobuf_requests = []
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
        page = await context.new_page()
        
        # Set up network monitoring
        async def on_response(response: Response):
            try:
                req_info = {
                    "url": response.url,
                    "status": response.status,
                    "method": response.request.method,
                    "timestamp": time.time(),
                }
                network_requests.append(req_info)
                
                # Check for protobuf responses
                content_type = response.headers.get("content-type", "").lower()
                if "protobuf" in content_type or "octet-stream" in content_type:
                    try:
                        body = await response.body()
                        if len(body) > 100:
                            filename = f"protobuf_{int(time.time()*1000)}.bin"
                            (output_dir / filename).write_bytes(body)
                            req_info["protobuf_file"] = filename
                            req_info["size"] = len(body)
                            protobuf_requests.append(req_info)
                            logger.info(f"Captured protobuf: {filename} ({len(body)} bytes)")
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"Error in response handler: {e}")
        
        page.on("response", on_response)
        
        try:
            # Navigate to mall
            logger.info(f"Navigating to {mall_url}")
            await page.goto(mall_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # Handle consent
            await handle_consent(page)
            
            # Navigate to directory
            directory_success = await navigate_to_directory(page)
            if not directory_success:
                logger.error("Failed to access directory view")
                await browser.close()
                return CardInvestigationReport(
                    mall_url=mall_url,
                    mall_name=mall_name,
                    timestamp=time.time(),
                    directory_url=page.url,
                    card_container_selector="",
                    total_cards_found=0,
                    sample_cards_investigated=0,
                    detail_pane_captures=[],
                    protobuf_requests=[],
                    api_endpoints_observed=[],
                    timing_observations={},
                    rate_limit_indicators=["CRITICAL: Could not access directory view"],
                    recommended_selectors={},
                    recommended_delays={},
                    automation_strategy=["ERROR: Investigation incomplete - directory not accessible"],
                )
            
            directory_url = page.url
            logger.info(f"Directory URL: {directory_url}")
            
            # Find card selector
            card_selector = await find_card_selector(page)
            if not card_selector:
                logger.error("No card selector found")
                await browser.close()
                return CardInvestigationReport(
                    mall_url=mall_url,
                    mall_name=mall_name,
                    timestamp=time.time(),
                    directory_url=directory_url,
                    card_container_selector="",
                    total_cards_found=0,
                    sample_cards_investigated=0,
                    detail_pane_captures=[],
                    protobuf_requests=[],
                    api_endpoints_observed=[],
                    timing_observations={},
                    rate_limit_indicators=["WARNING: No tenant cards found"],
                    recommended_selectors={},
                    recommended_delays={},
                    automation_strategy=["ERROR: Investigation incomplete - no cards found"],
                )
            
            total_cards = await page.locator(card_selector).count()
            logger.info(f"Found {total_cards} tenant cards")
            
            # Investigate sample cards
            sample_size = min(sample_size, total_cards)
            detail_captures = []
            
            for i in range(sample_size):
                capture = await investigate_card_detail(
                    page, card_selector, i, output_dir, network_requests
                )
                detail_captures.append(capture)
                
                # Delay between cards to avoid rate limiting
                await asyncio.sleep(2)
            
            # Analyze results
            api_endpoints = list(set([
                req["url"] for req in network_requests
                if "google" in req["url"] and "/maps" in req["url"]
            ]))
            
            avg_timing = {}
            if detail_captures:
                for key in ["scroll", "click_and_load", "total"]:
                    times = [c.timing.get(key, 0) for c in detail_captures if c.timing.get(key)]
                    if times:
                        avg_timing[f"avg_{key}"] = sum(times) / len(times)
            
            # Generate recommendations
            recommended_selectors = {
                "card": card_selector,
                "detail_pane": detail_captures[0].detail_pane_selectors.get("pane", "") if detail_captures else "",
            }
            
            recommended_delays = {
                "after_scroll": 0.5,
                "after_click": 2.0,
                "between_cards": 2.0,
            }
            
            automation_strategy = [
                "1. Navigate to directory view (append !10e3 to URL or click View all)",
                f"2. Use selector '{card_selector}' to find tenant cards",
                "3. For each card: scroll into view, wait 0.5s, click, wait 2s",
                "4. Extract details from detail pane",
                "5. Use browser back() to return to directory",
                "6. Wait 2s between cards to avoid rate limiting",
            ]
            
            # Check for rate limiting indicators
            rate_limit_indicators = []
            if any(req["status"] == 429 for req in network_requests):
                rate_limit_indicators.append("HTTP 429 Too Many Requests detected")
            if any(req["status"] >= 500 for req in network_requests):
                rate_limit_indicators.append("Server errors (5xx) detected")
            
            report = CardInvestigationReport(
                mall_url=mall_url,
                mall_name=mall_name,
                timestamp=time.time(),
                directory_url=directory_url,
                card_container_selector=card_selector,
                total_cards_found=total_cards,
                sample_cards_investigated=len(detail_captures),
                detail_pane_captures=detail_captures,
                protobuf_requests=protobuf_requests,
                api_endpoints_observed=api_endpoints,
                timing_observations=avg_timing,
                rate_limit_indicators=rate_limit_indicators or ["No rate limiting detected"],
                recommended_selectors=recommended_selectors,
                recommended_delays=recommended_delays,
                automation_strategy=automation_strategy,
            )
            
            # Save report
            report_path = output_dir / "card_investigation_report.json"
            with report_path.open("w", encoding="utf-8") as f:
                json.dump(asdict(report), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Investigation complete. Report saved to {report_path}")
            
            await browser.close()
            return report
            
        except Exception as e:
            logger.error(f"Investigation failed: {e}", exc_info=True)
            await browser.close()
            raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Investigate Google Maps tenant card detail extraction"
    )
    parser.add_argument("url", help="Google Maps mall URL")
    parser.add_argument("--name", required=True, help="Mall name for output directory")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Base output directory (default: outputs/<mall-name>/card-investigation)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=5,
        help="Number of cards to investigate (default: 5)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run in headless mode (default)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Run with visible browser",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    
    # Slugify mall name for directory
    import re
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", args.name).strip("-").lower()
    output_dir = args.output_dir or Path("outputs") / slug / "card-investigation"
    
    try:
        report = asyncio.run(run_investigation(
            args.url, args.name, output_dir, args.sample_size, args.headless
        ))
        
        print("\n" + "=" * 80)
        print("CARD DETAIL INVESTIGATION SUMMARY")
        print("=" * 80)
        print(f"Mall: {report.mall_name}")
        print(f"URL: {report.mall_url}")
        print(f"Directory URL: {report.directory_url}")
        print(f"Total cards found: {report.total_cards_found}")
        print(f"Cards investigated: {report.sample_cards_investigated}")
        print(f"Card selector: {report.card_container_selector}")
        print(f"Protobuf captures: {len(report.protobuf_requests)}")
        print(f"API endpoints observed: {len(report.api_endpoints_observed)}")
        print(f"\nTiming (averages):")
        for key, value in report.timing_observations.items():
            print(f"  {key}: {value:.2f}s")
        print(f"\nRate limiting:")
        for indicator in report.rate_limit_indicators:
            print(f"  - {indicator}")
        print(f"\nAutomation strategy:")
        for step in report.automation_strategy:
            print(f"  {step}")
        print(f"\nOutput directory: {output_dir}")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\nInvestigation interrupted")
        return 1
    except Exception as e:
        logger.error(f"Investigation failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

