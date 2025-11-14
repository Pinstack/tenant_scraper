#!/usr/bin/env python3
"""
Investigate Google Maps tenant card behaviour for Epic 1.

This script captures:
1. DOM structure of tenant cards
2. Event flow for opening cards (scroll, hover, click)
3. Required selectors for automation
4. Timing requirements and retry patterns
5. Screenshots of key interaction states
"""

import argparse
import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

from playwright.async_api import async_playwright, Page, Locator


logger = logging.getLogger(__name__)


@dataclass
class CardInteractionState:
    """Captures state at each interaction point."""
    action: str
    timestamp: float
    selector_used: str
    element_visible: bool
    element_count: int
    screenshot_file: str
    dom_snapshot_file: str
    notes: str


@dataclass
class InvestigationResult:
    """Complete investigation result for a mall."""
    mall_url: str
    mall_name: str
    investigation_timestamp: float
    consent_handling: Dict[str, Any]
    directory_access: Dict[str, Any]
    card_selectors: Dict[str, Any]
    interaction_sequence: List[CardInteractionState]
    timing_observations: Dict[str, Any]
    recommendations: List[str]


async def capture_element_info(page: Page, selector: str, label: str) -> Dict[str, Any]:
    """Capture comprehensive information about elements matching a selector."""
    locator = page.locator(selector)
    count = await locator.count()
    
    info = {
        "selector": selector,
        "label": label,
        "count": count,
        "visible": False,
        "bounding_boxes": [],
        "attributes": [],
    }
    
    if count > 0:
        # Check visibility
        try:
            info["visible"] = await locator.first.is_visible(timeout=1000)
        except Exception:
            pass
        
        # Get bounding boxes for first few elements
        for i in range(min(count, 3)):
            try:
                box = await locator.nth(i).bounding_box(timeout=1000)
                if box:
                    info["bounding_boxes"].append(box)
            except Exception:
                pass
        
        # Get attributes from first element
        try:
            elem = locator.first
            attrs = {}
            for attr in ["class", "role", "aria-label", "data-item-id", "jsaction"]:
                try:
                    val = await elem.get_attribute(attr, timeout=1000)
                    if val:
                        attrs[attr] = val
                except Exception:
                    pass
            info["attributes"].append(attrs)
        except Exception:
            pass
    
    return info


async def investigate_consent_handling(page: Page, output_dir: Path) -> Dict[str, Any]:
    """Investigate consent page handling."""
    logger.info("Investigating consent page...")
    
    consent_info = {
        "consent_detected": False,
        "consent_selectors_tried": [],
        "consent_clicked": False,
        "timing": {},
    }
    
    # Common consent selectors
    consent_selectors = [
        {"selector": "[aria-label*='Accept' i]", "label": "aria-label Accept"},
        {"selector": "button:has-text('Accept')", "label": "button text Accept"},
        {"selector": "button:has-text('Agree')", "label": "button text Agree"},
        {"selector": "#introAgreeButton", "label": "intro agree button"},
        {"selector": "form[action*='consent']", "label": "consent form"},
    ]
    
    start = time.time()
    
    for sel_info in consent_selectors:
        selector = sel_info["selector"]
        label = sel_info["label"]
        
        element_info = await capture_element_info(page, selector, label)
        consent_info["consent_selectors_tried"].append(element_info)
        
        if element_info["count"] > 0:
            consent_info["consent_detected"] = True
            logger.info(f"Consent detected: {label}")
            
            # Try to click
            try:
                await page.locator(selector).first.click(timeout=3000)
                await asyncio.sleep(1)
                consent_info["consent_clicked"] = True
                logger.info(f"Clicked consent: {label}")
                break
            except Exception as e:
                logger.warning(f"Failed to click consent {label}: {e}")
    
    consent_info["timing"]["consent_handling_duration"] = time.time() - start
    
    # Screenshot after consent
    screenshot_path = output_dir / "01_after_consent.png"
    await page.screenshot(path=screenshot_path, full_page=True)
    consent_info["screenshot"] = screenshot_path.name
    
    return consent_info


async def investigate_directory_access(page: Page, output_dir: Path) -> Dict[str, Any]:
    """Investigate directory view access."""
    logger.info("Investigating directory access...")
    
    directory_info = {
        "view_all_selectors_tried": [],
        "directory_accessed": False,
        "url_before": page.url,
        "url_after": None,
        "timing": {},
    }
    
    # Common "View all" selectors
    view_all_selectors = [
        {"selector": "button:has-text('View all')", "label": "button text 'View all'"},
        {"selector": "[aria-label*='View all' i]", "label": "aria-label View all"},
        {"selector": "a:has-text('View all')", "label": "link text 'View all'"},
        {"selector": "button:has-text('See all')", "label": "button text 'See all'"},
    ]
    
    start = time.time()
    
    for sel_info in view_all_selectors:
        selector = sel_info["selector"]
        label = sel_info["label"]
        
        element_info = await capture_element_info(page, selector, label)
        directory_info["view_all_selectors_tried"].append(element_info)
        
        if element_info["count"] > 0 and element_info["visible"]:
            logger.info(f"View all button found: {label}")
            
            # Try to click
            try:
                await page.locator(selector).first.click(timeout=5000)
                await page.wait_for_load_state("networkidle", timeout=10000)
                await asyncio.sleep(2)
                
                directory_info["directory_accessed"] = True
                directory_info["url_after"] = page.url
                logger.info(f"Clicked view all: {label}")
                break
            except Exception as e:
                logger.warning(f"Failed to click view all {label}: {e}")
    
    directory_info["timing"]["directory_access_duration"] = time.time() - start
    
    # Screenshot after directory access
    screenshot_path = output_dir / "02_directory_view.png"
    await page.screenshot(path=screenshot_path, full_page=True)
    directory_info["screenshot"] = screenshot_path.name
    
    return directory_info


async def investigate_card_selectors(page: Page, output_dir: Path) -> Dict[str, Any]:
    """Investigate tenant card selectors and structure."""
    logger.info("Investigating card selectors...")
    
    card_info = {
        "card_selectors_tried": [],
        "recommended_selector": None,
        "card_structure": {},
    }
    
    # Potential card selectors
    card_selectors = [
        {"selector": "[role='article']", "label": "role=article"},
        {"selector": "div[jsaction*='mouseover']", "label": "div with jsaction mouseover"},
        {"selector": "a[href*='/maps/place/']", "label": "links to place pages"},
        {"selector": "div[data-item-id]", "label": "div with data-item-id"},
        {"selector": ".hfpxzc", "label": "class hfpxzc (observed in DOM)"},
    ]
    
    for sel_info in card_selectors:
        selector = sel_info["selector"]
        label = sel_info["label"]
        
        element_info = await capture_element_info(page, selector, label)
        card_info["card_selectors_tried"].append(element_info)
        
        # If we find a good number of cards, investigate structure
        if 5 <= element_info["count"] <= 500:
            logger.info(f"Promising card selector: {label} (count: {element_info['count']})")
            
            if not card_info["recommended_selector"]:
                card_info["recommended_selector"] = selector
                
                # Investigate first card structure
                try:
                    first_card = page.locator(selector).first
                    
                    # Try to extract structure
                    structure = {
                        "html": await first_card.inner_html() if await first_card.count() > 0 else None,
                        "text": await first_card.inner_text() if await first_card.count() > 0 else None,
                    }
                    
                    card_info["card_structure"] = structure
                    
                    # Save first card HTML to file
                    html_path = output_dir / "card_structure_sample.html"
                    html_path.write_text(structure["html"] or "", encoding="utf-8")
                    
                except Exception as e:
                    logger.warning(f"Failed to extract card structure: {e}")
    
    return card_info


async def investigate_card_interaction(page: Page, output_dir: Path, card_selector: str) -> List[CardInteractionState]:
    """Investigate interaction sequence for opening card details."""
    logger.info("Investigating card interaction sequence...")
    
    states = []
    
    # Step 1: Scroll to first card
    try:
        first_card = page.locator(card_selector).first
        
        state = CardInteractionState(
            action="initial_state",
            timestamp=time.time(),
            selector_used=card_selector,
            element_visible=await first_card.is_visible(timeout=2000),
            element_count=await page.locator(card_selector).count(),
            screenshot_file="03_before_interaction.png",
            dom_snapshot_file="before_interaction_dom.html",
            notes="Initial state before any interaction",
        )
        
        await page.screenshot(path=output_dir / state.screenshot_file)
        dom_html = await page.content()
        (output_dir / state.dom_snapshot_file).write_text(dom_html, encoding="utf-8")
        
        states.append(state)
        
        # Step 2: Scroll into view
        logger.info("Scrolling card into view...")
        await first_card.scroll_into_view_if_needed(timeout=5000)
        await asyncio.sleep(1)
        
        state = CardInteractionState(
            action="scroll_into_view",
            timestamp=time.time(),
            selector_used=card_selector,
            element_visible=await first_card.is_visible(timeout=2000),
            element_count=await page.locator(card_selector).count(),
            screenshot_file="04_after_scroll.png",
            dom_snapshot_file="after_scroll_dom.html",
            notes="After scrolling card into view",
        )
        
        await page.screenshot(path=output_dir / state.screenshot_file)
        dom_html = await page.content()
        (output_dir / state.dom_snapshot_file).write_text(dom_html, encoding="utf-8")
        
        states.append(state)
        
        # Step 3: Hover over card
        logger.info("Hovering over card...")
        try:
            await first_card.hover(timeout=3000)
            await asyncio.sleep(1)
            
            state = CardInteractionState(
                action="hover",
                timestamp=time.time(),
                selector_used=card_selector,
                element_visible=await first_card.is_visible(timeout=2000),
                element_count=await page.locator(card_selector).count(),
                screenshot_file="05_after_hover.png",
                dom_snapshot_file="after_hover_dom.html",
                notes="After hovering over card - check for popups or highlights",
            )
            
            await page.screenshot(path=output_dir / state.screenshot_file)
            dom_html = await page.content()
            (output_dir / state.dom_snapshot_file).write_text(dom_html, encoding="utf-8")
            
            states.append(state)
        except Exception as e:
            logger.warning(f"Hover failed: {e}")
        
        # Step 4: Click card
        logger.info("Clicking card...")
        try:
            await first_card.click(timeout=5000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            await asyncio.sleep(2)
            
            state = CardInteractionState(
                action="click",
                timestamp=time.time(),
                selector_used=card_selector,
                element_visible=True,
                element_count=await page.locator(card_selector).count(),
                screenshot_file="06_after_click.png",
                dom_snapshot_file="after_click_dom.html",
                notes="After clicking card - should show detail view or panel",
            )
            
            await page.screenshot(path=output_dir / state.screenshot_file, full_page=True)
            dom_html = await page.content()
            (output_dir / state.dom_snapshot_file).write_text(dom_html, encoding="utf-8")
            
            states.append(state)
            
            # Check if URL changed
            logger.info(f"URL after click: {page.url}")
            
        except Exception as e:
            logger.warning(f"Click failed: {e}")
    
    except Exception as e:
        logger.error(f"Card interaction failed: {e}")
    
    return states


async def analyze_timing_requirements(interaction_states: List[CardInteractionState]) -> Dict[str, Any]:
    """Analyze timing requirements from interaction states."""
    
    timing = {
        "action_delays": {},
        "recommendations": [],
    }
    
    for i in range(1, len(interaction_states)):
        prev_state = interaction_states[i - 1]
        curr_state = interaction_states[i]
        
        delay = curr_state.timestamp - prev_state.timestamp
        timing["action_delays"][f"{prev_state.action}_to_{curr_state.action}"] = delay
    
    # Generate recommendations
    if timing["action_delays"]:
        avg_delay = sum(timing["action_delays"].values()) / len(timing["action_delays"])
        timing["recommendations"].append(
            f"Average delay between actions: {avg_delay:.2f}s"
        )
        timing["recommendations"].append(
            "Recommend minimum 1s delay between scroll and hover"
        )
        timing["recommendations"].append(
            "Recommend minimum 1s delay between hover and click"
        )
        timing["recommendations"].append(
            "Recommend 2s wait after click for detail panel to load"
        )
    
    return timing


async def run_investigation(mall_url: str, mall_name: str, output_dir: Path, headless: bool = True) -> InvestigationResult:
    """Run complete investigation for a mall."""
    
    logger.info(f"Starting investigation for: {mall_name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    result = InvestigationResult(
        mall_url=mall_url,
        mall_name=mall_name,
        investigation_timestamp=time.time(),
        consent_handling={},
        directory_access={},
        card_selectors={},
        interaction_sequence=[],
        timing_observations={},
        recommendations=[],
    )
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
        page = await context.new_page()
        
        try:
            # Navigate to mall
            logger.info(f"Navigating to {mall_url}")
            await page.goto(mall_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # Investigate consent
            result.consent_handling = await investigate_consent_handling(page, output_dir)
            
            # Investigate directory access
            result.directory_access = await investigate_directory_access(page, output_dir)
            
            if not result.directory_access["directory_accessed"]:
                logger.warning("Failed to access directory view - investigation incomplete")
                result.recommendations.append("CRITICAL: Could not access directory view - verify URL or selectors")
            else:
                # Investigate card selectors
                result.card_selectors = await investigate_card_selectors(page, output_dir)
                
                if result.card_selectors["recommended_selector"]:
                    # Investigate interaction sequence
                    result.interaction_sequence = await investigate_card_interaction(
                        page, output_dir, result.card_selectors["recommended_selector"]
                    )
                    
                    # Analyze timing
                    result.timing_observations = await analyze_timing_requirements(result.interaction_sequence)
                    result.recommendations.extend(result.timing_observations.get("recommendations", []))
                else:
                    logger.warning("No suitable card selector found")
                    result.recommendations.append("WARNING: No card selector found - may need manual selector discovery")
        
        except Exception as e:
            logger.error(f"Investigation failed: {e}", exc_info=True)
            result.recommendations.append(f"ERROR: Investigation failed - {str(e)}")
        
        finally:
            await browser.close()
    
    # Save investigation result
    result_dict = asdict(result)
    result_path = output_dir / "investigation_result.json"
    with result_path.open("w", encoding="utf-8") as f:
        json.dump(result_dict, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Investigation complete. Results saved to {output_dir}")
    
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Investigate Google Maps tenant card behaviour"
    )
    parser.add_argument("url", help="Google Maps mall URL")
    parser.add_argument("--name", required=True, help="Mall name for output directory")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Base output directory (default: outputs/<mall-name>/investigation)",
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
    output_dir = args.output_dir or Path("outputs") / slug / "investigation"
    
    try:
        result = asyncio.run(run_investigation(args.url, args.name, output_dir, args.headless))
        
        print("\n" + "=" * 80)
        print("INVESTIGATION SUMMARY")
        print("=" * 80)
        print(f"Mall: {result.mall_name}")
        print(f"URL: {result.mall_url}")
        print(f"Consent handled: {result.consent_handling.get('consent_clicked', False)}")
        print(f"Directory accessed: {result.directory_access.get('directory_accessed', False)}")
        print(f"Card selector found: {result.card_selectors.get('recommended_selector', 'None')}")
        print(f"Interaction states captured: {len(result.interaction_sequence)}")
        print(f"\nOutput directory: {output_dir}")
        print("\nRecommendations:")
        for rec in result.recommendations:
            print(f"  - {rec}")
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

