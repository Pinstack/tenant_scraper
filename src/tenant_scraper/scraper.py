"""Main scraper module for extracting tenant information from Google Maps."""

import asyncio
import contextvars
import logging
import re
import time
from dataclasses import dataclass, field
from contextlib import contextmanager
from typing import Dict, List, Optional, Any, Iterable
from urllib.parse import urlparse
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Use module-level logger with a dedicated trace flag for high-volume debug output
logger = logging.getLogger(__name__)
TRACE_BLOCKED_RESOURCES = False
_mall_context: contextvars.ContextVar[str] = contextvars.ContextVar("tenant_scraper_mall", default="")


class MallContextFilter(logging.Filter):
    """Inject mall identifier into log messages when available."""

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        mall = _mall_context.get("")
        if mall and not getattr(record, "_mall_context_applied", False):
            message = record.getMessage()
            record.msg = f"[{mall}] {message}"
            record.args = ()
            setattr(record, "_mall_context_applied", True)
        return True


if not any(isinstance(flt, MallContextFilter) for flt in logger.filters):
    logger.addFilter(MallContextFilter())


@contextmanager
def mall_logging_context(label: Optional[str]):
    """Attach a mall label to log records within the managed scope."""

    token = _mall_context.set(label or "") if label else None
    try:
        yield
    finally:
        if token is not None:
            _mall_context.reset(token)


class DirectoryTextExtractor:
    """Extracts tenant information from directory view text content."""

    def extract_tenants_from_text(self, page_text: str) -> List[Dict[str, Any]]:
        """
        Extract tenant information from the raw page text content.

        Args:
            page_text: Raw text content from the directory view page

        Returns:
            List of extracted tenant dictionaries
        """
        tenants = []

        # Split text into lines for processing
        lines = page_text.split('\n')
        lines = [line.strip() for line in lines if line.strip()]

        # Process lines to find tenant information
        # Format observed from debug:
        # Business Name (on one line)
        # rating(count) · price_range (on next line)
        # category · address (on next line)
        # Status line (optional)

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for business names (lines that don't contain numbers or special chars)
            # Business names are typically standalone and don't contain ratings or separators
            if (len(line) > 3 and len(line) < 50 and
                not any(char.isdigit() for char in line) and
                '·' not in line and
                not line.startswith('') and  # Skip icons
                line not in ['Directory', 'Search for places', 'Department stores',
                           'Food & Drink', 'Clothing', 'Health & Beauty']):

                # Check if next line contains rating pattern
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()

                    # Look for rating pattern: "4.7(3,575) · £10–20"
                    rating_match = re.search(r'(\d+\.\d+)\((\d+(?:,\d+)*)\)\s+·\s+(.+)', next_line)
                    if rating_match:
                        rating, review_count, price_info = rating_match.groups()

                        # Check for category/address line
                        category = "Business"
                        address = "Unknown"

                        if i + 2 < len(lines):
                            detail_line = lines[i + 2].strip()
                            if '·' in detail_line:
                                parts = detail_line.split('·')
                                if len(parts) >= 2:
                                    category = parts[0].strip()
                                    address = parts[1].strip()

                        tenant = {
                            'name': line,
                            'rating': float(rating),
                            'review_count': int(review_count.replace(',', '')),
                            'category': category,
                            'address': address,
                            'status': 'unknown',
                            'floor_unit': None,
                            'phone': None,
                            'maps_link': None
                        }

                        # Check for status in nearby lines
                        for j in range(i + 1, min(i + 5, len(lines))):
                            status_line = lines[j].lower()
                            if 'closed ⋅ opens' in status_line:
                                tenant['status'] = 'closed'
                                break
                            elif 'opens' in status_line and 'closed' not in status_line:
                                tenant['status'] = 'open'
                                break

                        tenants.append(tenant)
                        i += 3  # Skip the lines we processed
                        continue

            i += 1

        return tenants

    def filter_valid_tenants(self, tenants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out invalid or duplicate tenants."""
        valid_tenants = []

        for tenant in tenants:
            # Basic validation
            if not tenant.get('name') or len(tenant['name']) < 2:
                continue

            # Skip if name looks like UI text
            name_lower = tenant['name'].lower()
            if any(skip in name_lower for skip in [
                'directory', 'search', 'view all', 'floor', 'department',
                'food & drink', 'clothing', 'health & beauty'
            ]):
                continue

            # Skip duplicates
            if not any(t['name'].lower() == tenant['name'].lower() for t in valid_tenants):
                valid_tenants.append(tenant)

        return valid_tenants


@dataclass
class ScraperSettings:
    """Tunable knobs for scraper behaviour."""

    block_resources: bool = True
    aggressive_block: bool = False
    blocked_resource_types: Iterable[str] = field(default_factory=lambda: {"image", "media"})
    blocked_hosts: Iterable[str] = field(
        default_factory=lambda: {
            "lh3.googleusercontent.com",
            "lh4.googleusercontent.com",
            "lh5.googleusercontent.com",
            "lh6.googleusercontent.com",
        }
    )
    aggressive_hosts: Iterable[str] = field(
        default_factory=lambda: {
            "maps.googleapis.com",
            "maps.gstatic.com",
        }
    )
    action_retries: int = 2
    action_retry_backoff: float = 0.5


class TenantScraper:
    """Scraper for extracting tenant information from Google Maps mall listings."""

    def __init__(
        self,
        headless: bool = True,
        *,
        block_resources: Optional[bool] = None,
        aggressive_block: Optional[bool] = None,
        settings: Optional[ScraperSettings] = None,
    ):
        """Initialize the scraper with browser configuration."""
        self.headless = headless
        self.settings = settings or ScraperSettings()

        if block_resources is not None:
            self.settings.block_resources = block_resources
        if aggressive_block is not None:
            self.settings.aggressive_block = aggressive_block
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._setup_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._cleanup()

    async def _setup_browser(self) -> None:
        """Set up Playwright browser with appropriate options."""
        self.playwright = await async_playwright().start()

        # Launch browser
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1920,1080",
                "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            ]
        )

        # Create context and page
        self.context = await self.browser.new_context()
        if self.settings.block_resources:
            await self.context.route("**/*", self._resource_route_interceptor)
        self.page = await self.context.new_page()

        # Set default timeout
        self.page.set_default_timeout(30000)

    async def _perform_with_retries(self, description: str, action_factory) -> Any:
        """Execute a coroutine factory with retries and backoff."""
        retries = max(0, self.settings.action_retries)
        backoff = max(0.0, self.settings.action_retry_backoff)
        attempt = 0
        last_exc = None

        while attempt <= retries:
            try:
                return await action_factory()
            except Exception as exc:  # pylint: disable=broad-except
                last_exc = exc
                if attempt == retries:
                    logger.warning("Action '%s' failed after %d attempts", description, attempt + 1)
                    raise
                delay = backoff * (attempt + 1)
                logger.debug("Retrying '%s' in %.2fs due to %s", description, delay, exc)
                if delay:
                    await asyncio.sleep(delay)
                attempt += 1

        if last_exc:
            raise last_exc  # pragma: no cover
        return None

    async def _resource_route_interceptor(self, route, request) -> None:
        """Lightweight request blocker to speed up scraping while preserving directory functionality."""
        if not self.settings.block_resources:
            await route.continue_()
            return

        try:
            resource_type = request.resource_type
            url = request.url
            hostname = urlparse(url).hostname or ""

            blocked_types = set(self.settings.blocked_resource_types)
            blocked_hosts = set(self.settings.blocked_hosts)

            if self.settings.aggressive_block:
                blocked_hosts.update(self.settings.aggressive_hosts)

            if resource_type in blocked_types or any(hostname.endswith(host) for host in blocked_hosts):
                if TRACE_BLOCKED_RESOURCES:
                    logger.debug(f"Blocking resource: type={resource_type}, url={url}")
                await route.abort()
                return

        except Exception as e:
            logger.debug(f"Resource interceptor fallback due to error: {e}")

        await route.continue_()

    async def _cleanup(self) -> None:
        """Clean up browser resources."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _handle_consent_page(self) -> bool:
        """Handle Google consent page if encountered.

        Returns:
            bool: True if consent was handled or not needed, False if failed
        """
        try:
            # Check if we're on a consent page by looking for consent-related text
            consent_indicators = ["consent", "accept all", "agree", "cookie"]
            page_text = await self.page.inner_text("body")
            page_text_lower = page_text.lower()

            has_consent = any(indicator in page_text_lower for indicator in consent_indicators)

            if not has_consent:
                logger.info("No consent page detected")
                return True

            # Look for consent buttons/inputs - multiple selectors for different regions
            consent_selectors = [
                "[aria-label*='Accept all']",
                "[aria-label*='accept all']",
                "button[data-value='Accept all']",
                "#introAgreeButton",
                ".VtwTSb form + div button",
                "button:has-text('Accept all')",
                "button:has-text('Agree')",
                "input[type='submit'][value*='Accept all']",
                "input[type='submit'][value*='accept all']",
                "input[value*='Accept all']",
                "input[value*='accept all']"
            ]

            for selector in consent_selectors:
                try:
                    element = self.page.locator(selector).first
                    await element.click()
                    logger.info(f"Clicked consent element: {selector}")
                    await asyncio.sleep(2)  # Wait for redirect
                    return True
                except Exception:
                    continue

            logger.warning("Consent page detected but no button found to click")
            return False

        except Exception as e:
            logger.error(f"Error handling consent page: {e}")
            return False

    async def _manipulate_to_directory_view(self, url: str) -> Optional[str]:
        """
        Access the directory panel by simulating user interaction on the current page.
        This method assumes the page is already loaded and handles consent if needed.

        Args:
            url: The current Google Maps URL (for reference only)

        Returns:
            The URL after directory access (should contain !10e3 parameter)
        """
        logger.info("Attempting to access directory via user interaction simulation")

        try:
            # Handle consent page if still present
            await self._handle_consent_page()

            # Check if we're on a Maps page
            current_url = self.page.url
            if 'maps' not in current_url or 'consent' in current_url.lower():
                logger.error("Not on a valid Maps page")
                return None

            logger.info("On Maps page - looking for directory access")

            # Look for directory section and "View all" button
            await asyncio.sleep(2)  # Wait for dynamic content

            directory_section = self.page.locator("h2:has-text('Directory')")
            dir_count = await directory_section.count()

            if dir_count == 0:
                logger.warning("Directory section not found - scrolling to find it")
                # Scroll down to try to find directory section
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                dir_count = await directory_section.count()

            if dir_count == 0:
                logger.warning("Directory section still not found")
                return current_url

            logger.info("Directory section found")

            # Look for "View all" button
            view_all_button = self.page.locator("button:has-text('View all')")
            view_all_count = await view_all_button.count()

            if view_all_count == 0:
                logger.warning("'View all' button not found - directory may already be expanded")
                return current_url

            logger.info("Found 'View all' button - clicking it")
            await view_all_button.first.click()
            await asyncio.sleep(3)

            # Check if directory loaded
            final_url = self.page.url
            if '!10e3' in final_url:
                logger.info("✅ Successfully accessed directory view")
                return final_url
            else:
                logger.warning("Directory may have loaded but URL pattern not detected")
                return final_url

        except Exception as e:
            logger.error(f"Error accessing directory: {e}")
            return None

    async def scrape_tenants(
        self,
        maps_url: str,
        extraction_mode: str = "directory",
        *,
        fetch_details: bool = False,
    ) -> List[Dict[str, Any]]:
        """Main scraping method to extract tenant information.

        Args:
            maps_url: Google Maps URL for the mall
            extraction_mode: "directory" for main directory view, "categories" for category-based extraction

        Returns:
            List of tenant dictionaries with extracted information
        """
        async with self:  # This will setup and cleanup the browser
            try:
                logger.info(f"=== STARTING SCRAPE FOR URL: {maps_url} (mode: {extraction_mode}) ===")

                if extraction_mode == "categories":
                    return await self._scrape_tenants_by_categories(maps_url)
                else:
                    return await self._scrape_tenants_from_directory(
                        maps_url,
                        fetch_details=fetch_details,
                    )

            except Exception as e:
                logger.error(f"Error during scraping: {e}")
                raise

    async def _scrape_tenants_from_directory(
        self,
        maps_url: str,
        *,
        fetch_details: bool = False,
    ) -> List[Dict[str, Any]]:
        """Scrape tenants from the main directory view (original approach)."""
        overall_start = time.perf_counter()

        # Step 1: Handle consent and navigate to URL
        logger.info("Step 1: Navigating to URL...")
        await self._perform_with_retries(
            "navigate to maps URL",
            lambda: self.page.goto(maps_url),
        )
        logger.info(f"Initial page title: {await self.page.title()}")
        logger.info(f"Current URL: {self.page.url}")
        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)
        logger.debug("Navigation completed in %.2fs", time.perf_counter() - overall_start)

        if not await self._handle_consent_page():
            logger.warning("Consent page handling failed or not needed")
        else:
            logger.info("Consent page handled successfully")

        # Step 2: Access and expand directory view
        logger.info("Step 2: Accessing directory view...")
        current_url = self.page.url
        logger.info(f"Current URL: {current_url}")

        # First, scroll down to load content
        logger.info("Scrolling down to load directory content...")
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

        # Look for "View all" button to expand directory
        logger.info("Looking for 'View all' button to expand directory...")
        view_all_button = self.page.locator("button:has-text('View all')")
        view_all_count = await view_all_button.count()

        if view_all_count > 0:
            logger.info("Found 'View all' button - clicking it")
            await self._perform_with_retries(
                "click 'View all'",
                lambda: view_all_button.first.click(),
            )
            try:
                await self.page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                await asyncio.sleep(2)

            # Check if URL changed to include !10e3 parameter (directory view)
            current_url_after_click = self.page.url
            if '!10e3' in current_url_after_click:
                logger.info("✅ Successfully accessed directory view (URL contains !10e3)")
            else:
                logger.warning("Directory view URL pattern not detected after click")
                logger.info(f"URL after click: {current_url_after_click}")

            # Let the deterministic scroller handle loading

        else:
            logger.warning("'View all' button not found - checking if directory is already expanded")
            # Check if we're already in directory view
            if '!10e3' in current_url:
                logger.info("Already in directory view (URL contains !10e3)")
            else:
                logger.warning("Not in directory view and no 'View all' button found")

        # Scroll again to ensure all content is loaded
        logger.info("Scrolling again to load all directory content...")
        scroll_start = time.perf_counter()
        await self._scroll_directory_panel()
        logger.debug("Directory scroll completed in %.2fs", time.perf_counter() - scroll_start)

        # Check if we're in directory view (look for individual tenant names)
        # In directory view (!10e3), individual tenants like "Maki & Ramen" are visible
        test_tenants = ["Maki & Ramen", "John Lewis", "Costa", "Starbucks"]
        found_individual_tenants = False

        page_text = await self.page.inner_text("body")
        for tenant in test_tenants:
            if tenant.lower() in page_text.lower():
                found_individual_tenants = True
                break

        if found_individual_tenants:
            logger.info("✅ Directory view successfully loaded with individual tenants visible")
        else:
            logger.warning("Directory view loaded but individual tenants not visible yet")

        # Step 3: Extract the tenant table element directly from DOM
        logger.info("Step 3: Extracting tenant table element from DOM...")
        tenant_table_html = await self._extract_tenant_table_html()

        if not tenant_table_html:
            logger.error("Failed to extract tenant table HTML from DOM")
            return []

        # Step 4: Parse the extracted HTML using our parsing logic
        logger.info("Step 4: Parsing extracted tenant table HTML...")
        parse_start = time.perf_counter()
        tenants = await self._parse_tenant_table_html(tenant_table_html)
        logger.debug("HTML parsing completed in %.2fs", time.perf_counter() - parse_start)

        if fetch_details:
            logger.info("Fetching detailed tenant information using existing session...")
            detail_start = time.perf_counter()
            tenants = await self._extract_detailed_tenant_data(tenants)
            logger.debug("Detail extraction completed in %.2fs", time.perf_counter() - detail_start)

        logger.info(
            "=== DIRECTORY SCRAPING COMPLETE: Successfully extracted %d tenants from DOM table (total %.2fs) ===",
            len(tenants),
            time.perf_counter() - overall_start,
        )
        return tenants

    async def _scrape_tenants_by_categories(self, maps_url: str) -> List[Dict[str, Any]]:
        """Scrape tenants by processing each category individually (advanced approach)."""
        logger.info("=== STARTING CATEGORY-BASED EXTRACTION ===")

        # Step 1: Navigate and set up directory view
        await self.page.goto(maps_url)
        await asyncio.sleep(3)

        if not await self._handle_consent_page():
            logger.warning("Consent page handling failed or not needed")
        else:
            logger.info("Consent page handled successfully")

        # Access directory view - scroll down first to load content
        logger.info("Scrolling down to load directory content...")
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

        view_all_button = self.page.locator("button:has-text('View all')")
        if await view_all_button.count() > 0:
            await view_all_button.first.click()
            await asyncio.sleep(5)
            logger.info("Successfully accessed directory view")
        else:
            logger.warning("Could not find 'View all' button")

        # Step 2: Extract category information
        category_info = await self._extract_category_info()
        total_expected = sum(cat['count'] for cat in category_info)
        logger.info(f"Found {len(category_info)} categories with {total_expected} total expected businesses")

        # Step 3: Process each category sequentially
        all_tenants = await self._extract_all_categories_sequential(category_info)

        logger.info(f"=== CATEGORY SCRAPING COMPLETE: Successfully extracted {len(all_tenants)} tenants from all categories ===")
        return all_tenants

    async def _extract_all_categories_sequential(self, category_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract tenants from all categories sequentially."""
        all_results = []

        for idx, cat_info in enumerate(category_info):
            logger.info(f"Processing category {idx + 1}: {cat_info['name']}")

            try:
                # Navigate back to directory if needed
                current_url = self.page.url
                if not ('place' in current_url and 'search' in current_url):
                    await self.page.go_back(timeout=5000)
                    await self.page.wait_for_timeout(2000)

                # Click category button
                success = await self._click_category_button_robust(cat_info)
                if success:
                    # Extract tenants from category page
                    category_tenants = await self._extract_tenants_from_category_page(cat_info['name'])
                    all_results.extend(category_tenants)
                    logger.info(f"Extracted {len(category_tenants)} tenants from {cat_info['name']}")

                await self.page.wait_for_timeout(500)

            except Exception as e:
                logger.warning(f"Error processing category {cat_info['name']}: {e}")

        # Remove duplicates
        unique_tenants = []
        seen_names = set()
        for tenant in all_results:
            name = tenant.get('name', '').lower().strip()
            if name and name not in seen_names:
                unique_tenants.append(tenant)
                seen_names.add(name)

        return unique_tenants

    async def _click_category_button_robust(self, cat_info: Dict[str, Any]) -> bool:
        """Click category button."""
        try:
            buttons = self.page.locator(".e2moi")
            count = await buttons.count()

            for i in range(count):
                button = buttons.nth(i)
                text = await button.inner_text()
                if cat_info['name'] in text and str(cat_info['count']) in text:
                    await button.click()
                    await self.page.wait_for_timeout(3000)
                    return True
        except Exception:
            pass
        return False

    async def _extract_tenants_from_category_page(self, category_name: str) -> List[Dict[str, Any]]:
        """Extract tenants from category page."""
        tenants = []

        try:
            # Scroll to load content
            await self._perform_category_scroll()

            # Extract elements
            elements = await self.page.locator("div:has-text('·')").all()

            for element in elements:
                try:
                    text = await element.inner_text()
                    tenant = self._parse_tenant_from_text_improved(text)
                    if tenant and tenant.get('name'):
                        tenant['source_category'] = category_name
                        tenants.append(tenant)
                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"Error extracting from {category_name}: {e}")

        return tenants

    async def _perform_category_scroll(self) -> None:
        """Perform scrolling on category page."""
        for i in range(3):
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.page.wait_for_timeout(1500)

    def _parse_tenant_from_text_improved(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse tenant from text."""
        tenant = {}

        rating_match = re.search(r'(\d\.\d)\s*\((\d+(?:,\d+)?)\)', text)
        if rating_match:
            tenant['rating'] = float(rating_match.group(1))
            tenant['review_count'] = int(rating_match.group(2).replace(',', ''))

            name_part = text[:rating_match.start()].strip()
            if name_part and len(name_part) > 2:
                tenant['name'] = self._clean_tenant_name(name_part)

        return tenant if tenant.get('name') else None

    async def _extract_tenant_data(self) -> List[Dict[str, Any]]:
        """Extract tenant information from the directory view.

        Returns:
            List of tenant data dictionaries
        """
        tenants = []
        logger.info("=== EXTRACTING TENANT DATA ===")

        try:
            # Wait for page to load
            logger.info("Waiting for directory view to load...")
            await self.page.wait_for_selector("[role='main']")
            logger.info("Page loaded successfully")

            # Scroll to reveal more tenants
            logger.info("Scrolling to reveal more directory content...")
            await self._scroll_directory_panel()

            # In directory view (!10e3), individual tenants are directly accessible as buttons
            tenant_buttons = []
            logger.info("Searching for tenant buttons in directory view...")

            # Check if we're in directory view by looking for !10e3 in URL
            current_url = self.page.url
            is_directory_view = '!10e3' in current_url

            if is_directory_view:
                logger.info("Detected directory view (!10e3) - waiting for tenant content to load")
                await asyncio.sleep(3)  # Extra wait for dynamic content

                # In directory view, look for buttons with tenant names and ratings
                all_buttons = self.page.locator("button")
                total_buttons = await all_buttons.count()
                logger.info(f"Total buttons on page: {total_buttons}")

                # Look for buttons that contain individual tenant information
                # Debug: Log all buttons to understand the structure
                logger.info("DEBUG: Logging all buttons to understand structure...")
                for i in range(min(total_buttons, 20)):  # Check first 20 buttons
                    button = all_buttons.nth(i)
                    try:
                        button_text = await button.inner_text()
                        button_text = button_text.strip()
                        if button_text:
                            logger.info(f"  Button {i}: '{button_text[:100]}...'")
                    except Exception:
                        continue

                # Now look for tenant buttons with known patterns
                for i in range(total_buttons):
                    button = all_buttons.nth(i)
                    try:
                        button_text = await button.inner_text()
                        button_text = button_text.strip()

                        # Check if this contains known tenant names or patterns
                        if any(name in button_text for name in ['Maki & Ramen', 'John Lewis', 'Costa', 'Starbucks', 'H&M']):
                            tenant_buttons.append(button)
                            logger.info(f"  ✅ Found known tenant button: '{button_text[:80]}...'")
                        elif '·' in button_text and '(' in button_text and ')' in button_text:
                            # Pattern: "Name rating(count) · details"
                            tenant_buttons.append(button)
                            logger.info(f"  ✅ Found pattern tenant button: '{button_text[:80]}...'")

                    except Exception:
                        continue

                logger.info(f"Found {len(tenant_buttons)} individual tenant buttons in directory view")
            else:
                logger.info("Not in directory view - falling back to category extraction")

                # Fallback: Look for category buttons (like before)
                all_buttons = self.page.locator("button")
                total_buttons = await all_buttons.count()
                logger.info(f"Total buttons on page: {total_buttons}")

                for i in range(total_buttons):
                    button = all_buttons.nth(i)
                    try:
                        button_text = await button.inner_text()
                        button_text = button_text.strip()

                        # Look for tenant-like patterns (categories)
                        if self._is_tenant_button(button_text):
                            tenant_buttons.append(button)
                    except Exception:
                        continue

                logger.info(f"Found {len(tenant_buttons)} category-like buttons as fallback")

            # Process tenant data - use text extraction from page content
            logger.info("Extracting tenant data from page content...")

            try:
                # Get the full page text content
                page_text = await self.page.inner_text("body")

                # Use the directory text extractor (from this module)
                text_extractor = DirectoryTextExtractor()

                # Extract tenants from the text
                extracted_tenants = text_extractor.extract_tenants_from_text(page_text)

                # Filter valid tenants
                valid_tenants = text_extractor.filter_valid_tenants(extracted_tenants)

                tenants.extend(valid_tenants)

                logger.info(f"✅ Extracted {len(valid_tenants)} individual tenants from page text")
                for tenant in valid_tenants:
                    logger.info(f"  ✓ {tenant['name']} ({tenant['category']}) - {tenant['rating']}⭐")

            except Exception as e:
                logger.error(f"Error extracting tenants from page text: {e}")

            logger.info(f"Final result: Extracted {len(tenants)} unique tenants")

        except Exception as e:
            logger.error(f"Error during tenant data extraction: {e}")
            return []

        return tenants

    async def _scroll_directory_panel(self) -> None:
        """Scroll the directory panel to reveal ALL tenants using true infinite scroll."""
        try:
            logger.info("Starting deterministic infinite scroll to reveal ALL tenants...")

            # Small settle to allow initial DOM/JS to attach
            await asyncio.sleep(2)

            # Do not rely on category chips; scroll full directory
            expected_total = None

            # Determine the best scroll container selector
            container_selector = await self._find_results_container_selector()
            logger.info(f"Using scroll container selector: {container_selector}")

            # Optional: derive expected total just for logging/expectation (do not gate scrolling)
            expected_total = None
            try:
                category_info = await self._extract_category_info()
                if category_info:
                    total_expected = sum(
                        cat.get('count', 0)
                        for cat in category_info
                        if isinstance(cat.get('count'), int)
                    )
                    if total_expected:
                        expected_total = total_expected
                        logger.info(
                            "Category chips indicate ~%d total tenants (used as soft target)",
                            expected_total,
                        )
            except Exception as _e:
                logger.debug(f"Could not derive expected total from categories: {_e}")

            # Deterministic scroll without fixed loop counts
            final_count = await self._scroll_until_done(
                container_selector,
                expected_total=expected_total,
            )
            logger.info(f"Infinite scroll complete: {final_count} total tenants loaded")
            return

            # Legacy loop removed: rely on generic deterministic scroller

        except Exception as e:
            logger.warning(f"Error during infinite scroll: {e}")

    async def _find_results_container_selector(self) -> str:
        """Detect the scrollable results container for the directory pane.

        Returns a CSS selector string for the container, or "window" to use window scrolling.
        The detector scores candidates by scrollability and presence of feed-like content.
        """
        # First, quick known patterns
        quick_candidates = [
            "div[role='feed']",
            "[role='main'] div[role='feed']",
            "div[aria-label*='Results' i]",
            "div[aria-label*='Directory' i]",
            "div.m6QErb[aria-label]",
            "[role='main'] .m6QErb[aria-label]",
        ]

        try:
            for sel in quick_candidates:
                try:
                    if await self.page.locator(sel).count() > 0:
                        is_scrollable = await self.page.evaluate(
                            "(s) => { const el = document.querySelector(s); if (!el) return false; const cs = getComputedStyle(el); return (el.scrollHeight - el.clientHeight) > 20 && (cs.overflowY === 'auto' || cs.overflowY === 'scroll'); }",
                            sel,
                        )
                        if is_scrollable:
                            return sel
                except Exception:
                    continue

            # Deep scan: find best scrollable element by score and tag it
            best = await self.page.evaluate(
                "() => {\n"
                "  const nodes = Array.from(document.querySelectorAll('*'));\n"
                "  let best = null; let bestScore = 0;\n"
                "  for (const el of nodes) {\n"
                "    const cs = getComputedStyle(el);\n"
                "    const scrollable = (el.scrollHeight - el.clientHeight) > 20 && (cs.overflowY === 'auto' || cs.overflowY === 'scroll');\n"
                "    if (!scrollable) continue;\n"
                "    const text = (el.innerText || '').toLowerCase();\n"
                "    const dotCount = (text.match(/\u00b7/g) || []).length; // '·' occurrences\n"
                "    const feedCount = el.querySelectorAll('[role=feed], [role=article]').length;\n"
                "    const btnCount = el.querySelectorAll('button').length;\n"
                "    const score = feedCount * 10 + dotCount + Math.min(btnCount, 50);\n"
                "    if (score > bestScore) { bestScore = score; best = el; }\n"
                "  }\n"
                "  if (best) { best.setAttribute('data-scraper-scroll-target','1'); return true; }\n"
                "  return false;\n"
                "}"
            )
            if best:
                return "[data-scraper-scroll-target='1']"
        except Exception:
            pass

        return "window"

    async def _scroll_until_done(
        self,
        container_selector: str,
        *,
        expected_total: Optional[int] = None,
        max_idle_ms: int = 4000,
        max_duration_ms: int = 120000,
    ) -> int:
        """Generic deterministic infinite scroll against a container or window.

        - No fixed iteration count. Stops when:
          - End-of-results sentinel text is visible, or
          - At bottom, no spinner, scrollHeight stable across checks, and idle for a short window, or
          - Reaches expected_total (if provided), or
          - Overall time cap is hit (safety only).

        Returns:
            Final visible tenant count
        """
        loop = asyncio.get_event_loop()
        start = loop.time()
        prev_height = -1
        last_change_ts = start
        stable_checks = 0
        last_growth_ts = start
        last_count = -1
        stagnant_checks = 0

        while True:
            now = loop.time()
            if (now - start) * 1000 > max_duration_ms:
                logger.warning("Stopping scroll due to overall duration cap")
                break

            await self._perform_scroll_step(container_selector)
            current_count = await self._count_visible_tenants()
            logger.info(f"Scrolled: {current_count} tenants visible")

            if current_count > last_count:
                last_growth_ts = now
                stagnant_checks = 0
            else:
                stagnant_checks += 1
            last_count = current_count

            if expected_total and current_count >= expected_total:
                logger.info("Reached expected total tenants; stopping scroll")
                break

            metrics = await self.page.evaluate(
                "(sel) => {\n                    const el = sel === 'window' ? null : document.querySelector(sel);\n                    const c = el || document.scrollingElement || document.body;\n                    const top = c.scrollTop;\n                    const height = c.scrollHeight;\n                    const clientH = c.clientHeight;\n                    const atBottom = Math.abs(height - (top + clientH)) < 2;\n                    return {height, clientH, top, atBottom};\n                }",
                container_selector,
            )

            loading_visible = await self.page.evaluate(
                '''() => !!(document.querySelector('[role="progressbar"], [aria-label*="Loading" i], .loading, .spinner'))'''
            )

            end_text_visible = await self.page.evaluate(
                "() => {\n                    const texts = ['end of results', 'you\\'ve reached the end', 'no more results'];\n                    const bodyText = document.body.innerText.toLowerCase();\n                    return texts.some(t => bodyText.includes(t));\n                }"
            )

            height = metrics.get("height", 0)

            if metrics.get("atBottom") and not loading_visible:
                if height == prev_height:
                    stable_checks += 1
                else:
                    stable_checks = 0
                if height != prev_height:
                    last_change_ts = now
            else:
                stable_checks = 0
                last_change_ts = now

            prev_height = height

            idle_elapsed = (now - last_change_ts) * 1000
            if end_text_visible or (metrics.get("atBottom") and not loading_visible and stable_checks >= 2 and idle_elapsed >= max_idle_ms):
                logger.info("Detected end-of-results via stabilization or sentinel text; stopping")
                break

            no_growth_elapsed = (now - last_growth_ts) * 1000
            soft_target_reached = (
                expected_total is not None
                and current_count >= max(20, int(expected_total * 0.9))
            )

            if (
                stagnant_checks >= 5
                and no_growth_elapsed >= max_idle_ms
                and (not loading_visible or no_growth_elapsed >= max_idle_ms * 3)
            ):
                logger.info(
                    "Tenant count unchanged for %.1fs across %d checks; assuming end of list",
                    no_growth_elapsed / 1000,
                    stagnant_checks,
                )
                break

            if soft_target_reached and no_growth_elapsed >= max_idle_ms * 2:
                logger.info(
                    "Reached %.0f%% of expected tenants with no growth for %.1fs; stopping",
                    (current_count / expected_total) * 100 if expected_total else 0,
                    no_growth_elapsed / 1000,
                )
                break

        final_count = await self._count_visible_tenants()
        return final_count

    async def _perform_scroll_step(self, container_selector: str) -> None:
        """Scroll once and wait for new content using a MutationObserver in the page."""

        await self.page.evaluate(
            "(sel) => {\n                const container = sel === 'window' ? document.scrollingElement || document.body : document.querySelector(sel);\n                if (!container) {\n                    window.scrollTo(0, document.body.scrollHeight);\n                    return;\n                }\n\n                const target = container === document.body ? document.documentElement : container;\n                if (!target._scraperObserver) {\n                    target._scraperObserver = { pending: [] };\n                    const observer = new MutationObserver((mutations) => {\n                        if (!target._scraperObserver) return;\n                        const added = mutations.some(m => m.addedNodes && m.addedNodes.length);\n                        if (added) {\n                            const callbacks = target._scraperObserver.pending.splice(0);\n                            callbacks.forEach(cb => cb());\n                        }\n                    });\n                    observer.observe(target, { childList: true, subtree: true });\n                    target._scraperObserver.observer = observer;\n                }\n\n                target.scrollTop = target.scrollHeight;\n            }",
            container_selector,
        )

    async def _get_expected_total_tenants(self) -> Optional[int]:
        """Try to derive a deterministic expected total tenant count from category chips.

        Returns the sum of per-category counts if available, otherwise None.
        """
        try:
            category_info = await self._extract_category_info()
            if not category_info:
                return None
            total = sum(cat.get('count', 0) for cat in category_info if isinstance(cat.get('count'), int))
            return total if total > 0 else None
        except Exception:
            return None

    async def _count_visible_tenants(self) -> int:
        """Count the number of visible tenant entries in the directory."""
        try:
            # Prefer direct DOM counting within the scroll container for speed
            count = await self.page.evaluate(
                """
                () => {
                    const elements = Array.from(
                        document.querySelectorAll('div.bfdHYd, [data-result-index], div[data-item-id]')
                    );
                    const meaningful = elements.filter(el => (el.innerText || '').trim().length > 0);
                    return meaningful.length;
                }
                """
            )

            if count and count > 0:
                return int(count)

            # Fallback to text-based heuristic if DOM counting fails
            page_text = await self.page.inner_text("body")
            lines = page_text.split('\n')

            tenant_lines = sum(
                1
                for line in lines
                if (len(line.strip()) > 10
                    and ('·' in line or '(' in line and ')' in line))
            )

            return tenant_lines // 3

        except Exception as e:
            logger.warning(f"Error counting visible tenants: {e}")
            return 0

    async def _extract_detailed_tenant_data(self, basic_tenants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract detailed information from individual tenant cards by clicking on each one.

        Args:
            basic_tenants: List of tenants with basic information from directory view

        Returns:
            List of tenants with detailed information including phone, website, hours
        """
        logger.info(f"Starting detailed extraction for {len(basic_tenants)} tenants...")

        detailed_tenants = []

        # Find all tenant buttons/cards in the directory
        tenant_buttons = await self._find_tenant_buttons()
        logger.info(f"Found {len(tenant_buttons)} tenant buttons to process")

        # NEW APPROACH: Extract business URLs from directory, visit each individually
        logger.info("🔄 NEW APPROACH: Extracting business URLs for individual page scraping")

        # Extract business URLs/Place IDs from the directory view
        business_urls = await self._extract_business_urls_from_directory()
        logger.info(f"Found {len(business_urls)} business URLs in directory")

        if business_urls:
            # Visit each business URL individually to get contact details
            logger.info("Visiting individual business pages for contact details...")
            individual_page_tenants = await self._scrape_individual_business_pages(business_urls)

            # Merge individual page data with basic tenant data
            for page_tenant in individual_page_tenants:
                tenant_name = page_tenant.get('name', '')
                matching_tenant = self._find_matching_tenant(basic_tenants, tenant_name)

                if matching_tenant:
                    merged_tenant = {**matching_tenant, **page_tenant}
                    detailed_tenants.append(merged_tenant)
                    logger.info(f"✓ Enhanced via individual page: {tenant_name}")
                else:
                    detailed_tenants.append(page_tenant)
                    logger.info(f"✓ Added via individual page: {tenant_name}")

        # SIMPLIFIED APPROACH: Extract detailed data for ONLY ONE tenant and STOP on first failure
        # This follows the user's request to "stop on first failure during detailed tenant extraction"
        if tenant_buttons:
            logger.info(f"🔄 STOP-ON-FAILURE APPROACH: Processing ONLY first tenant to identify issues...")

            button_info = tenant_buttons[0]  # Only process the first tenant
            logger.info(f"Processing FIRST tenant only: {button_info['text'][:50]}...")

            try:
                button_element = button_info['element']

                # Step 1: Scroll into view
                logger.info("Step 1: Scrolling button into view...")
                await button_element.scroll_into_view_if_needed(timeout=5000)

                # Step 2: Hover over button
                logger.info("Step 2: Hovering over button...")
                await button_element.hover(timeout=2000)

                # Step 3: Click to open card
                logger.info("Step 3: Clicking button to open tenant card...")
                await button_element.click(timeout=5000)

                # Step 4: Wait for card to load
                logger.info("Step 4: Waiting for tenant card to load...")
                await asyncio.sleep(3)

                # Step 5: Extract data from this card
                logger.info("Step 5: Extracting data from tenant card...")
                card_data = await self._extract_card_details()

                if card_data.get('name'):
                    logger.info(f"✅ SUCCESS: Extracted card data for '{card_data.get('name')}'")
                    logger.info(f"   Phone: {card_data.get('phone', 'Not found')}")
                    logger.info(f"   Website: {card_data.get('website', 'Not found')}")
                    logger.info(f"   Address: {card_data.get('address', 'Not found')}")

                    # Match with basic tenant data
                    matching_tenant = self._find_matching_tenant(basic_tenants, card_data.get('name', ''))

                    if matching_tenant:
                        merged_tenant = {**matching_tenant, **card_data}
                        detailed_tenants.append(merged_tenant)
                        logger.info(f"✓ Enhanced: {card_data.get('name')} with detailed info")
                    else:
                        detailed_tenants.append(card_data)
                        logger.info(f"✓ Added: {card_data.get('name')}")
                else:
                    logger.warning("❌ FAILURE: No tenant name found in card data")
                    # Log what we did find
                    logger.info(f"Card data keys: {list(card_data.keys())}")
                    for key, value in card_data.items():
                        logger.info(f"  {key}: {value}")

                # Step 6: Close the card
                logger.info("Step 6: Closing tenant card...")
                await self._close_tenant_card()

                logger.info("✅ FIRST TENANT PROCESSING COMPLETE")

            except Exception as e:
                logger.error(f"❌ FAILURE: Error processing first tenant: {e}")
                logger.error(f"Error type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")

                # Take a screenshot for debugging
                try:
                    await self.page.screenshot(path="debug_failure_screenshot.png")
                    logger.info("📸 Screenshot saved: debug_failure_screenshot.png")
                except Exception:
                    logger.warning("Could not save debug screenshot")

                # Log current page state
                try:
                    current_url = self.page.url
                    page_title = await self.page.title()
                    logger.info(f"Current URL: {current_url}")
                    logger.info(f"Page title: {page_title}")
                except Exception:
                    logger.warning("Could not get page state")

                # STOP HERE as requested by user - do not continue processing
                logger.info("🛑 STOPPING on first failure as requested")
                raise e  # Re-raise to stop execution

            logger.info("Stop-on-failure approach completed: 1 tenant processed (or failed)")

        # Fill in remaining tenants with basic data
        for tenant in basic_tenants:
            tenant_name = tenant.get('name', '')
            if not any(t.get('name') == tenant_name for t in detailed_tenants):
                detailed_tenants.append(tenant)

        logger.info(f"📊 FINAL RESULT: {len(detailed_tenants)} tenants processed")
        contact_count = sum(1 for t in detailed_tenants if t.get('phone') or t.get('website'))
        logger.info(f"📞 CONTACT DETAILS: {contact_count} tenants have phone/website data")

        return detailed_tenants

    async def _find_tenant_buttons(self) -> List[Dict[str, Any]]:
        """Find all tenant buttons/cards in the current directory view.

        Returns:
            List of dictionaries with button elements and their text
        """
        tenant_buttons = []

        try:
            # Look for elements that contain tenant information
            # In directory view, tenants may be clickable divs or spans rather than buttons
            selectors = [
                "div:has-text('·')",  # Divs with the dot separator
                "span:has-text('·')",  # Spans with tenant info
                "[role='button']:has-text('·')",  # Role button elements
                "button:has-text('·')",  # Actual buttons
                "[data-item-id]",  # Elements with item IDs
                ".place-result",  # Place result containers
                "[jsaction]",  # Elements with JS actions
            ]

            for selector in selectors:
                try:
                    elements = self.page.locator(selector)
                    count = await elements.count()

                    for i in range(count):
                        element = elements.nth(i)
                        text = await element.inner_text()
                        text = text.strip()

                        # Filter for tenant-like content - be much more selective
                        if (len(text) > 15 and  # Longer text = more likely to be tenant
                            '·' in text and
                            not text.startswith('') and  # Skip icons
                            'Directory' not in text and
                            'Search' not in text and
                            'View all' not in text.lower() and
                            not text.isupper() and  # Skip category headers
                            not any(category in text.lower() for category in ['restaurants', 'hotels', 'things to do', 'transport', 'parking', 'chemists', 'atms', 'saved', 'recents'])):  # Skip navigation categories

                            # Must have both rating pattern AND business-like content
                            has_rating = '(' in text and ')' in text and any(char.isdigit() for char in text)
                            has_business_words = any(word in text.lower() for word in ['restaurant', 'store', 'shop', 'cafe', 'bar', 'burger', 'pizza', 'food'])

                            if has_rating and (has_business_words or len(text.split('·')) >= 2):
                                # Additional check: ensure element is visible and appears to be a tenant entry
                                try:
                                    is_visible = await element.is_visible()
                                    if is_visible:
                                        # Check if it's in a reasonable position (not navigation)
                                        box = await element.bounding_box()
                                        if box and box['y'] > 200:  # Below the header/navigation area
                                            tenant_buttons.append({
                                                'element': element,
                                                'text': text
                                            })
                                except Exception:
                                    # If visibility check fails, skip this element
                                    pass

                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {e}")
                    continue

            # Remove duplicates based on text content
            seen_texts = set()
            unique_buttons = []
            for button_info in tenant_buttons:
                if button_info['text'] not in seen_texts:
                    seen_texts.add(button_info['text'])
                    unique_buttons.append(button_info)

            logger.info(f"Found {len(unique_buttons)} potential tenant buttons")
            return unique_buttons

        except Exception as e:
            logger.error(f"Error finding tenant buttons: {e}")
            return []

    async def _extract_all_card_details(self, expected_count: int) -> List[Dict[str, Any]]:
        """Extract detailed information from all open tenant cards.

        Args:
            expected_count: Expected number of open cards

        Returns:
            List of dictionaries with detailed tenant information from each card
        """
        card_data_list = []

        try:
            # Wait for all cards to load
            await asyncio.sleep(3)

            # Find all open cards - they typically have specific classes/attributes
            card_selectors = [
                "[role='dialog']",
                ".card",
                "[class*='card']",
                "[class*='popup']",
                "[class*='modal']"
            ]

            all_cards = []
            for selector in card_selectors:
                try:
                    cards = self.page.locator(selector)
                    count = await cards.count()
                    if count > 0:
                        logger.info(f"Found {count} cards with selector: {selector}")
                        # Get all card elements
                        for i in range(count):
                            card_element = cards.nth(i)
                            all_cards.append(card_element)
                except Exception:
                    continue

            logger.info(f"Total card elements found: {len(all_cards)}")

            # Extract data from each card
            for i, card in enumerate(all_cards):
                try:
                    logger.info(f"Extracting data from card {i + 1}/{len(all_cards)}")

                    # Extract data from this specific card
                    card_data = await self._extract_card_details_from_element(card)

                    if card_data.get('name'):  # Only add if we got a name
                        card_data_list.append(card_data)
                        logger.info(f"✅ Extracted: {card_data.get('name', 'Unknown')}")

                except Exception as e:
                    logger.warning(f"Failed to extract from card {i + 1}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error extracting all card details: {e}")

        logger.info(f"Extracted data from {len(card_data_list)} cards")
        return card_data_list

    async def _extract_card_details_from_element(self, card_element) -> Dict[str, Any]:
        """Extract detailed information from a specific card element."""
        details = {
            'name': None,
            'phone': None,
            'website': None,
            'hours': None,
            'address': None,
            'rating': None,
            'review_count': None
        }

        try:
            # Extract business name from this card
            name_selectors = ["h1", "h2", "[class*='title']", "[class*='name']"]
            for selector in name_selectors:
                try:
                    name_elem = card_element.locator(selector).first
                    name_text = await name_elem.inner_text()
                    if name_text and len(name_text.strip()) > 0:
                        details['name'] = name_text.strip()
                        break
                except Exception:
                    continue

            # Extract phone from this card
            phone_selectors = ["a[href^='tel:']", "[class*='phone']", "span:has-text('+44')"]
            for selector in phone_selectors:
                try:
                    phone_elem = card_element.locator(selector).first
                    if await phone_elem.count() > 0:
                        phone_href = await phone_elem.get_attribute('href')
                        phone_text = await phone_elem.inner_text()

                        if phone_href and phone_href.startswith('tel:'):
                            details['phone'] = phone_href.replace('tel:', '')
                        elif phone_text:
                            import re
                            phone_match = re.search(r'[\+]?[\d\s\-\(\)]{10,}', phone_text)
                            if phone_match:
                                details['phone'] = phone_match.group(0).strip()
                        break
                except Exception:
                    continue

            # Extract website from this card
            website_selectors = ["a[href^='http']:not([href*='google'])", "[class*='website']", "a:has-text('.com')"]
            for selector in website_selectors:
                try:
                    website_elem = card_element.locator(selector).first
                    if await website_elem.count() > 0:
                        website_href = await website_elem.get_attribute('href')
                        website_text = await website_elem.inner_text()

                        if website_href and website_href.startswith('http'):
                            details['website'] = website_href
                        elif website_text and ('.com' in website_text or '.co.uk' in website_text):
                            details['website'] = website_text.strip()
                        break
                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"Error extracting card details from element: {e}")

        return details

    async def _close_all_cards(self) -> None:
        """Close all open tenant cards."""
        try:
            logger.info("Closing all open cards...")

            # Try multiple approaches to close cards
            close_attempts = [
                # Press Escape multiple times
                lambda: self.page.keyboard.press('Escape'),
                # Click empty space
                lambda: self.page.mouse.click(10, 10),
                # Look for close buttons and click them
                lambda: self._close_cards_with_buttons()
            ]

            for attempt in close_attempts:
                try:
                    if callable(attempt):
                        await attempt()
                    await asyncio.sleep(1)
                except Exception:
                    continue

            logger.info("Card closing attempts completed")

        except Exception as e:
            logger.warning(f"Error closing all cards: {e}")

    async def _extract_business_urls_from_directory(self) -> List[str]:
        """Extract business URLs from the Google Maps directory view.

        Returns:
            List of Google Maps business URLs
        """
        business_urls = []

        try:
            # Look for business URLs in various places:
            # 1. data-url attributes
            # 2. href attributes on links
            # 3. Google Maps place URLs in the page source
            # 4. JavaScript data structures

            # Get all elements that might contain business URLs
            url_elements = self.page.locator('[data-url], a[href*="maps"], [jsaction], [data-place-id]')

            count = await url_elements.count()
            logger.info(f"Found {count} elements that might contain business URLs")

            # Extract URLs from these elements
            for i in range(count):
                try:
                    element = url_elements.nth(i)

                    # Check data-url attribute
                    data_url = await element.get_attribute('data-url')
                    if data_url and ('maps' in data_url or 'place' in data_url):
                        if data_url not in business_urls:
                            business_urls.append(data_url)
                        continue

                    # Check href attribute
                    href = await element.get_attribute('href')
                    if href and ('maps' in href or 'place' in href):
                        if href not in business_urls:
                            business_urls.append(href)
                        continue

                    # Check data-place-id for constructing URLs
                    place_id = await element.get_attribute('data-place-id')
                    if place_id:
                        constructed_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
                        if constructed_url not in business_urls:
                            business_urls.append(constructed_url)

                except Exception:
                    continue

            # Extract from page source for various Google Maps URL patterns
            page_content = await self.page.content()
            import re

            # Look for various Google Maps URL patterns
            url_patterns = [
                r'https://www\.google\.com/maps/place/[^"\'\s]+',
                r'https://maps\.app\.goo\.gl/[^"\'\s]+',
                r'"/maps/place/[^"]*"',
                r'"/maps/_/js/k=maps.m.\w+\.en\.\w+/[^"]*"'
            ]

            for pattern in url_patterns:
                matches = re.findall(pattern, page_content)
                for match in matches:
                    # Clean up the match (remove quotes if present)
                    url = match.strip('"\'')
                    if url and 'place' in url and url not in business_urls:
                        # Convert relative URLs to absolute if needed
                        if url.startswith('/maps/place/'):
                            url = f"https://www.google.com{url}"
                        business_urls.append(url)

            # Look for business data in JavaScript objects
            # Google Maps often stores business data in window.APP_INITIALIZATION_STATE or similar
            try:
                js_data = await self.page.evaluate("""
                    () => {
                        const urls = [];
                        // Look for business URLs in various JavaScript objects
                        if (window.APP_INITIALIZATION_STATE) {
                            JSON.stringify(window.APP_INITIALIZATION_STATE).split('"').forEach(part => {
                                if (part.includes('/maps/place/') || part.includes('maps.app.goo.gl')) {
                                    urls.push(part);
                                }
                            });
                        }
                        return urls;
                    }
                """)

                for url in js_data:
                    if url and url not in business_urls:
                        business_urls.append(url)

            except Exception as e:
                logger.debug(f"JavaScript data extraction failed: {e}")

            # Filter to unique URLs and limit to reasonable number
            unique_urls = list(set(business_urls))
            # Filter out obviously wrong URLs (sign-in pages, etc.)
            filtered_urls = [url for url in unique_urls if
                           'ServiceLogin' not in url and
                           'signin' not in url and
                           'accounts.google' not in url and
                           len(url) > 20]  # Must be a substantial URL

            # Limit to first 20 to avoid excessive processing
            limited_urls = filtered_urls[:20]

            logger.info(f"Extracted {len(limited_urls)} unique business URLs from directory")
            for i, url in enumerate(limited_urls[:5]):  # Log first 5 for debugging
                logger.info(f"  URL {i+1}: {url[:80]}...")

            return limited_urls

        except Exception as e:
            logger.error(f"Error extracting business URLs: {e}")
            return []

    async def _scrape_individual_business_pages(self, business_urls: List[str]) -> List[Dict[str, Any]]:
        """Scrape individual business pages for contact details.

        Args:
            business_urls: List of Google Maps business URLs

        Returns:
            List of business data with contact details
        """
        detailed_businesses = []
        semaphore = asyncio.Semaphore(5)

        async def process_business(idx: int, url: str) -> None:
            try:
                async with semaphore:
                    logger.info(f"Scraping business {idx + 1}/{len(business_urls)}: {url[:50]}...")
                    context = await self.browser.new_context()
                    page = await context.new_page()
                    try:
                        await page.goto(url, timeout=30000)
                        await page.wait_for_load_state('networkidle', timeout=10000)

                        try:
                            consent_result = await self._handle_consent_on_page(page)
                            if consent_result:
                                logger.debug("Handled consent on business page")
                        except Exception:
                            pass

                        business_data = await self._extract_business_details_from_page(page)
                        if business_data.get('name'):
                            detailed_businesses.append(business_data)
                            logger.info(f"✅ Extracted: {business_data.get('name', 'Unknown')}")
                        else:
                            logger.warning(f"No business name found for URL: {url[:50]}...")
                    finally:
                        await page.close()
                        await context.close()
            except Exception as e:
                logger.error(f"❌ Failed to scrape business {idx + 1}: {e}")

        await asyncio.gather(*(process_business(i, url) for i, url in enumerate(business_urls)))

        logger.info(f"Successfully scraped {len(detailed_businesses)} business pages")
        return detailed_businesses

    async def _handle_consent_on_page(self, page) -> bool:
        """Handle consent page on a specific page."""
        try:
            # Check for consent indicators
            page_text = await page.inner_text('body')
            if 'consent' in page_text.lower() or 'accept all' in page_text.lower():
                # Try to accept consent
                accept_selectors = [
                    "[aria-label*='Accept all']",
                    "button:has-text('Accept all')",
                    "#introAgreeButton"
                ]

                for selector in accept_selectors:
                    try:
                        accept_button = page.locator(selector).first
                        if await accept_button.count() > 0:
                            await accept_button.click()
                            await page.wait_for_load_state('networkidle', timeout=5000)
                            return True
                    except Exception:
                        continue

        except Exception:
            pass

        return False

    async def _extract_business_details_from_page(self, page) -> Dict[str, Any]:
        """Extract business details from an individual business page."""
        details = {
            'name': None,
            'phone': None,
            'website': None,
            'address': None,
            'rating': None,
            'review_count': None
        }

        try:
            # Extract business name
            name_selectors = ["h1", "[role='main'] h1", ".business-name", "[class*='title']"]
            for selector in name_selectors:
                try:
                    name_elem = page.locator(selector).first
                    if await name_elem.count() > 0:
                        name = await name_elem.inner_text()
                        if name and len(name.strip()) > 0:
                            details['name'] = name.strip()
                    break
                except Exception:
                    continue

            # Extract phone number
            phone_selectors = ["a[href^='tel:']", "[class*='phone']", "span:has-text('+44')"]
            for selector in phone_selectors:
                try:
                    phone_elem = page.locator(selector).first
                    if await phone_elem.count() > 0:
                        phone_href = await phone_elem.get_attribute('href')
                        phone_text = await phone_elem.inner_text()

                        if phone_href and phone_href.startswith('tel:'):
                            details['phone'] = phone_href.replace('tel:', '').strip()
                        elif phone_text:
                            import re
                            phone_match = re.search(r'[\+]?[\d\s\-\(\)]{10,}', phone_text)
                            if phone_match:
                                details['phone'] = phone_match.group(0).strip()

                        if details['phone']:
                            break
                except Exception:
                    continue

            # Extract website
            website_selectors = ["a[href^='http']:not([href*='google'])", "[class*='website']", "a:has-text('.com')"]
            for selector in website_selectors:
                try:
                    website_elem = page.locator(selector).first
                    if await website_elem.count() > 0:
                        website_href = await website_elem.get_attribute('href')
                        website_text = await website_elem.inner_text()

                        if website_href and website_href.startswith('http') and 'google' not in website_href:
                            details['website'] = website_href.strip()
                        elif website_text and ('.com' in website_text or '.co.uk' in website_text):
                            details['website'] = website_text.strip()

                        if details['website']:
                            break
                except Exception:
                    continue

            # Extract address
            address_selectors = ["[class*='address']", "span:has-text('Located in')", "[data-address]"]
            for selector in address_selectors:
                try:
                    address_elem = page.locator(selector).first
                    if await address_elem.count() > 0:
                        address = await address_elem.inner_text()
                        if address and len(address.strip()) > 10:
                            details['address'] = address.strip()
                            break
                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"Error extracting business details from page: {e}")

        return details

    async def _close_cards_with_buttons(self) -> None:
        """Try to close cards by finding and clicking close buttons."""
        close_selectors = [
            "button[aria-label*='Close']",
            "button:has-text('×')",
            "button:has-text('Close')",
            ".close-button",
            "[role='button'][aria-label*='close']"
        ]

        for selector in close_selectors:
            try:
                close_buttons = self.page.locator(selector)
                count = await close_buttons.count()
                if count > 0:
                    logger.info(f"Found {count} close buttons with selector: {selector}")
                    # Click all close buttons
                    for i in range(count):
                        try:
                            await close_buttons.nth(i).click()
                            await asyncio.sleep(0.5)
                        except Exception:
                            continue
                break
            except Exception:
                continue

    async def _extract_card_details(self) -> Dict[str, Any]:
        """Extract detailed information from an opened tenant card.

        When multiple cards are open, this targets the most recently opened/topmost card.
        """
        details = {
            'name': None,
            'phone': None,
            'website': None,
            'hours': None,
            'address': None,
            'rating': None,
            'review_count': None
        }

        try:
            # Wait for the card to fully load
            await asyncio.sleep(2)

            # When multiple cards are open, target the topmost/most recent card
            # This is typically the last card in the DOM or has higher z-index

            # Extract business name (usually the most prominent heading)
            name_selectors = [
                "h1",
                "[role='main'] h1",
                ".business-name",
                "h2:first-of-type"
            ]

            for selector in name_selectors:
                try:
                    name_element = self.page.locator(selector).first
                    name_text = await name_element.inner_text()
                    if name_text and len(name_text.strip()) > 0:
                        details['name'] = name_text.strip()
                        break
                except Exception:
                    continue

            # Extract phone number
            phone_selectors = [
                "a[href^='tel:']",
                "span:has-text('Phone') + *",
                "[data-phone]",
                "a:has-text('+'):has-text('0')"
            ]

            for selector in phone_selectors:
                try:
                    phone_element = self.page.locator(selector).first
                    if await phone_element.count() > 0:
                        phone_text = await phone_element.inner_text()
                        phone_href = await phone_element.get_attribute('href')

                        # Use href if available (more reliable), otherwise text
                        if phone_href and phone_href.startswith('tel:'):
                            details['phone'] = phone_href.replace('tel:', '')
                        elif phone_text:
                            # Clean up phone text (remove extra characters)
                            phone_text = phone_text.strip()
                            # Basic phone number pattern
                            import re
                            phone_match = re.search(r'[\+]?[\d\s\-\(\)]{10,}', phone_text)
                            if phone_match:
                                details['phone'] = phone_match.group(0).strip()
                        break
                except Exception:
                    continue

            # Extract website URL
            website_selectors = [
                "a[href^='http']:not([href*='google']):not([href*='maps'])",
                "a:has-text('.com')",
                "a:has-text('www.')",
                "[data-website]"
            ]

            for selector in website_selectors:
                try:
                    website_element = self.page.locator(selector).first
                    if await website_element.count() > 0:
                        website_href = await website_element.get_attribute('href')
                        website_text = await website_element.inner_text()

                        if website_href and website_href.startswith('http'):
                            details['website'] = website_href
                        elif website_text and ('www.' in website_text or '.com' in website_text):
                            details['website'] = website_text.strip()
                    break
                except Exception:
                    continue

            # Extract operating hours
            hours_selectors = [
                "table[data-day]",
                "[data-hours]",
                "span:has-text('Monday'):has-text('Tuesday')",
                "div:has-text('Hours') + *"
            ]

            for selector in hours_selectors:
                try:
                    hours_element = self.page.locator(selector).first
                    if await hours_element.count() > 0:
                        hours_text = await hours_element.inner_text()
                        if hours_text and len(hours_text) > 20:  # Substantial hours information
                            details['hours'] = hours_text.strip()
                        break
                except Exception:
                    continue

            # Extract address (if not already captured from directory)
            if not details.get('address'):
                address_selectors = [
                    "[data-address]",
                    "span:has-text('Address') + *",
                    "div:has-text('Located in')"
                ]

                for selector in address_selectors:
                    try:
                        address_element = self.page.locator(selector).first
                        if await address_element.count() > 0:
                            address_text = await address_element.inner_text()
                            if address_text and len(address_text) > 10:
                                details['address'] = address_text.strip()
                                break
                    except Exception:
                        continue

            logger.info(f"Extracted card details - Name: {details.get('name')}, Phone: {details.get('phone')}, Website: {details.get('website')}")

        except Exception as e:
            logger.warning(f"Error extracting card details: {e}")

        return details

    async def _close_tenant_card(self) -> None:
        """Close the currently opened tenant card."""
        try:
            logger.info("Attempting to close tenant card...")

            # Look for close button - try multiple approaches
            close_selectors = [
                "button[aria-label*='Close']",
                "button:has-text('×')",
                "button:has-text('Close')",
                ".close-button",
                "[role='button'][aria-label*='close']",
                "[aria-label='Close']",
                "button[aria-label='Close']"
            ]

            for selector in close_selectors:
                try:
                    close_button = self.page.locator(selector).first
                    count = await close_button.count()
                    logger.info(f"Trying close selector '{selector}': {count} found")
                    if count > 0:
                        logger.info(f"Clicking close button with selector: {selector}")
                        await close_button.click()
                        await asyncio.sleep(2)  # Wait longer for close animation
                        return
                except Exception as e:
                    logger.warning(f"Close selector '{selector}' failed: {e}")
                    continue

            # Fallback: press Escape
            logger.info("Trying Escape key to close card")
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(2)

            # Final fallback: click on empty space
            logger.info("Trying to click empty space to close card")
            await self.page.mouse.click(10, 10)  # Click top-left corner
            await asyncio.sleep(2)

        except Exception as e:
            logger.warning(f"Error closing tenant card: {e}")

    def _find_matching_tenant(self, tenants: List[Dict[str, Any]], target_name: str) -> Optional[Dict[str, Any]]:
        """Find a tenant from the basic list that matches the detailed card name.

        Args:
            tenants: List of basic tenant dictionaries
            target_name: Name from the detailed card

        Returns:
            Matching tenant dictionary or None
        """
        if not target_name:
            return None

        target_name_lower = target_name.lower().strip()

        # First try exact match
        for tenant in tenants:
            if tenant.get('name', '').lower().strip() == target_name_lower:
                return tenant

        # Then try partial match (first few words)
        target_words = target_name_lower.split()[:3]  # First 3 words
        for tenant in tenants:
            tenant_name_lower = tenant.get('name', '').lower().strip()
            tenant_words = tenant_name_lower.split()[:3]
            if tenant_words == target_words:
                return tenant

        # Try fuzzy matching (contains most words)
        target_words_set = set(target_words)
        for tenant in tenants:
            tenant_name_lower = tenant.get('name', '').lower().strip()
            tenant_words_set = set(tenant_name_lower.split()[:4])  # First 4 words
            if len(target_words_set.intersection(tenant_words_set)) >= 2:
                return tenant

        return None

    async def _extract_tenant_from_button(self, button_element) -> Optional[Dict[str, Any]]:
        """Extract tenant information from a button element and surrounding content.

        Args:
            button_element: The button element containing tenant name

        Returns:
            Dictionary with tenant data or None if extraction fails
        """
        try:
            tenant = {
                "name": None,
                "category": None,
                "rating": None,
                "floor_unit": None,
                "status": "unknown",
                "phone": None,
                "maps_link": None
            }

            # Get the button text (usually the tenant name)
            button_text = await button_element.inner_text()
            button_text = button_text.strip()
            if button_text and len(button_text) > 2:  # Avoid very short texts
                tenant["name"] = button_text

            # Try to get the container that holds all tenant info
            # Look for parent elements that might contain the full tenant data
            container = button_element
            max_depth = 5
            for _ in range(max_depth):
                try:
                    parent = container.locator("xpath=..")
                    count = await parent.count()
                    if count == 0:
                        break
                    container = parent.first
                    # Check if this container has multiple text elements
                    # (indicating it contains tenant data)
                    all_text = await container.inner_text()
                    if len(all_text.split('\n')) > 3:  # Multiple lines of text
                        break
                except Exception:
                    break

            # Extract information from the container text
            container_text = await container.inner_text()

            # Look for rating (e.g., "4.7 stars 3,573 reviews")
            try:
                # Find rating patterns in the text
                rating_patterns = [
                    r'(\d+\.?\d*)\s+stars?\s+(\d+(?:,\d+)?)\s+reviews?',
                    r'(\d+\.?\d*)\s+stars?',
                ]
                for pattern in rating_patterns:
                    match = re.search(pattern, container_text, re.IGNORECASE)
                    if match:
                        tenant["rating"] = float(match.group(1))
                        break
            except Exception:
                pass

            # Look for category (common business types)
            try:
                category_keywords = [
                    "restaurant", "store", "shop", "cafe", "clothing", "department store",
                    "supermarket", "bank", "pharmacy", "bookstore", "electronics",
                    "jewelry", "shoes", "beauty", "salon", "bar", "pub",
                ]
                for keyword in category_keywords:
                    if keyword in container_text.lower():
                        # Find the word that contains this keyword
                        words = container_text.split()
                        for word in words:
                            if keyword.lower() in word.lower():
                                tenant["category"] = word.strip()
                                break
                        if tenant["category"]:
                            break
            except Exception:
                pass

            # Look for floor information
            try:
                floor_patterns = [
                    r"Floor\s+[A-Z0-9\-]+",
                    r"Level\s+[A-Z0-9\-]+",
                    r"Floors?\s+[A-Z0-9\-]+"
                ]
                for pattern in floor_patterns:
                    match = re.search(pattern, container_text, re.IGNORECASE)
                    if match:
                        tenant["floor_unit"] = match.group(0)
                        break
            except Exception:
                pass

            # Look for status information
            try:
                status_indicators = ["Open", "Closed", "Closes soon", "Opens", "Temporarily closed"]
                for status in status_indicators:
                    if status in container_text:
                        tenant["status"] = status.lower().replace(" ", "_")
                        break
            except Exception:
                pass

            # For detailed information, we could try clicking, but for now let's skip
            # to avoid complications. The basic info should be sufficient.
            # tenant["maps_link"] = self.driver.current_url  # Could add mall URL

            return tenant

        except Exception as e:
            logger.error("Error extracting tenant from button: %s", e)
            return None

    def _extract_single_tenant(self, element) -> Optional[Dict[str, Any]]:
        """Extract information for a single tenant.

        Args:
            element: WebElement containing tenant information

        Returns:
            Dictionary with tenant data or None if extraction fails
        """
        try:
            # This is a placeholder implementation - actual selectors will need
            # to be determined by inspecting the actual Google Maps DOM
            tenant = {
                "name": "Placeholder Name",
                "category": "Placeholder Category",
                "rating": None,
                "floor_unit": None,
                "status": "unknown",
                "phone": None,
                "maps_link": None
            }

            # TODO: Implement actual data extraction
            logger.info("Extracted tenant placeholder data")

            return tenant

        except Exception as e:
            logger.error(f"Error extracting single tenant: {e}")
            return None

    def _validate_and_clean_tenant_data(self, tenants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate and clean extracted tenant data.

        Args:
            tenants: List of raw tenant dictionaries

        Returns:
            List of validated and cleaned tenant dictionaries
        """
        logger.info(f"Validating and cleaning {len(tenants)} tenant records")
        cleaned_tenants = []

        for tenant in tenants:
            try:
                # Skip if no name
                if not tenant.get('name'):
                    logger.debug("Skipping tenant with no name")
                    continue

                name = tenant['name'].strip()

                # Skip obvious UI elements and invalid entries
                invalid_indicators = [
                    # Single characters or very short
                    len(name) < 3,
                    # Just numbers
                    name.isdigit(),
                    # UI elements
                    name in ['Menu', 'Save', 'Share', 'Directions', 'View all'],
                    name.startswith(''),  # Navigation icons
                    # Map UI elements
                    name in ['Terrain', 'Travel time', 'Measure', 'Default', 'Satellite',
                             'Globe view', 'Labels', 'Public transport', 'Traffic', 'Cycling',
                             'Street View', 'Wildfires', 'Air Quality'],
                    # Footer elements
                    name in ['Terms', 'Privacy', 'Send product feedback', 'United Kingdom'],
                    # Mall name itself
                    'St James' in name and len(name.split()) <= 3,  # Skip just "St James Quarter"
                ]

                if any(invalid_indicators):
                    logger.debug(f"Skipping invalid tenant: '{name}'")
                    continue

                # Clean the name - remove newlines and extra whitespace
                cleaned_name = ' '.join(name.split()).strip()

                # For category entries, extract the category name and count separately
                category_name = None
                business_count = None

                if '\n' in name or any(char.isdigit() for char in name):
                    # This looks like a category entry like "Food & Drink\n40"
                    lines = name.split('\n')
                    if len(lines) >= 1:
                        category_name = lines[0].strip()
                        if len(lines) >= 2:
                            # Try to extract count
                            count_part = lines[1].strip()
                            try:
                                business_count = int(count_part)
                            except ValueError:
                                pass  # Count not parseable, leave as None

                # Create cleaned tenant record
                cleaned_tenant = {
                    'name': cleaned_name,
                    'category': tenant.get('category'),
                    'business_count': business_count,
                    'rating': tenant.get('rating'),
                    'floor_unit': tenant.get('floor_unit'),
                    'status': tenant.get('status'),
                    'phone': tenant.get('phone'),
                    'maps_link': tenant.get('maps_link'),
                    'is_category_summary': business_count is not None
                }

                # Additional validation
                if category_name and business_count and business_count > 0:
                    # This is a valid category summary
                    cleaned_tenant['category_name'] = category_name
                    logger.debug(f"✅ Valid category: {category_name} ({business_count} businesses)")
                elif len(cleaned_name) >= 3 and any(char.isalpha() for char in cleaned_name):
                    # This is a valid individual business
                    logger.debug(f"✅ Valid business: {cleaned_name}")

                cleaned_tenants.append(cleaned_tenant)

            except Exception as e:
                logger.warning(f"Error validating tenant {tenant.get('name', 'unknown')}: {e}")
                continue

        logger.info(f"Validation complete: {len(cleaned_tenants)} valid tenants from {len(tenants)} raw records")
        return cleaned_tenants

    async def _extract_tenant_table_html(self) -> Optional[str]:
        """Extract all tenant elements directly from the DOM using the same logic as tenant counting.

        Returns:
            Combined HTML content of all detected tenant elements
        """
        try:
            logger.info("Extracting all tenant elements using the same detection logic...")

            # Use the same selectors as the counting method to find ALL tenant elements
            tenant_selectors = [
                "div:has-text('·')",  # Elements with the dot separator used in tenant listings
                "[role='button']:has-text('·')",  # Button elements with tenant info
                "div[data-item-id]",  # Elements with data-item-id attributes
            ]

            all_tenant_html = []

            for selector in tenant_selectors:
                try:
                    logger.info(f"Trying selector: {selector}")
                    elements = self.page.locator(selector)

                    count = await elements.count()
                    logger.info(f"Found {count} elements with selector: {selector}")

                    concurrency = 20
                    semaphore = asyncio.Semaphore(concurrency)

                    async def fetch_html(idx: int) -> None:
                        async with semaphore:
                            try:
                                element = elements.nth(idx)
                                html_content = await element.inner_html()
                                if html_content and len(html_content) > 50:
                                    all_tenant_html.append(f'<tenant-element-{idx}>{html_content}</tenant-element-{idx}>')
                            except Exception as e:
                                logger.debug(f"Error extracting element {idx}: {e}")

                    await asyncio.gather(*(fetch_html(i) for i in range(count)))

                    logger.info(f"Extracted {len(all_tenant_html)} tenant elements so far")

                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue

            if all_tenant_html:
                combined_html = '<all-tenant-elements>' + ''.join(all_tenant_html) + '</all-tenant-elements>'
                logger.info(f"✅ Successfully extracted HTML from {len(all_tenant_html)} tenant elements")
                logger.info(f"Combined HTML content length: {len(combined_html)} characters")

                # Debug: Save the extracted HTML for analysis
                with open("debug_extracted_dom.html", "w", encoding="utf-8") as f:
                    f.write(combined_html)
                logger.info("📄 Saved extracted DOM HTML to debug_extracted_dom.html")

                return combined_html
            else:
                logger.error("❌ No tenant elements found with any selector")
                return None

        except Exception as e:
            logger.error(f"Error extracting tenant elements: {e}")
            return None

    async def _parse_tenant_table_html(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse the extracted tenant table HTML using simplified logic.

        Args:
            html_content: The HTML content of the tenant table element

        Returns:
            List of tenant dictionaries
        """
        try:
            logger.info("Parsing extracted tenant table HTML...")

            from bs4 import BeautifulSoup
            import re

            soup = BeautifulSoup(html_content, 'html.parser')

            tenants = []
            seen_names = set()

            cards = soup.select('div.bfdHYd')
            if not cards:
                logger.debug("No .bfdHYd cards found; falling back to attribute-based lookup")
                fallback_cards = []
                for name_el in soup.select('.qBF1Pd.fontHeadlineSmall'):
                    parent = name_el.find_parent('div', attrs={'data-result-index': True})
                    if parent and parent not in fallback_cards:
                        fallback_cards.append(parent)
                cards = fallback_cards

            logger.info(f"Found {len(cards)} potential tenant cards in HTML")

            for card in cards:
                try:
                    name_el = card.select_one('.qBF1Pd.fontHeadlineSmall')
                    if not name_el:
                        continue

                    raw_name = name_el.get_text(strip=True)
                    name = self._clean_tenant_name(raw_name)
                    if not name:
                        continue

                    name_key = name.lower()
                    if name_key in seen_names:
                        continue

                    tenant: Dict[str, Any] = {
                        'name': name,
                        'category': None,
                        'address': None,
                        'rating': None,
                        'review_count': None,
                        'status': None,
                        'price_range': None,
                    }

                    rating_el = card.select_one('[aria-label*="stars" i]')
                    if rating_el:
                        aria = rating_el.get('aria-label', '')
                        rating_match = re.search(r'([0-9]+\.?[0-9]*)\s+stars', aria)
                        reviews_match = re.search(r'([0-9,]+)\s+reviews', aria)
                        if rating_match:
                            try:
                                tenant['rating'] = float(rating_match.group(1))
                            except ValueError:
                                pass
                        if reviews_match:
                            tenant['review_count'] = int(reviews_match.group(1).replace(',', ''))

                    price_el = card.select_one('.AJB7ye span span:last-of-type')
                    if price_el:
                        price_text = price_el.get_text(strip=True)
                        if price_text and self._looks_like_price(price_text):
                            tenant['price_range'] = price_text

                    detail_block = card.select_one('div.W4Efsd div.W4Efsd')
                    if detail_block:
                        parts = [p for p in detail_block.stripped_strings if p != '·']
                        if parts:
                            tenant['category'] = self._clean_category(parts[0]) if parts[0] else None
                        if len(parts) > 1:
                            tenant['address'] = parts[1]

                    status_block = card.select('div.W4Efsd div.W4Efsd')
                    if len(status_block) > 1:
                        status_text = ' '.join(status_block[1].stripped_strings)
                        if status_text:
                            tenant['status'] = self._normalize_status_ui_text(status_text)

                    seen_names.add(name_key)
                    tenants.append(tenant)

                except Exception as inner_e:
                    logger.debug(f"Error parsing tenant card: {inner_e}")
                    continue

            logger.info(f"Structured parsing produced {len(tenants)} unique tenants")
            return tenants

        except Exception as e:
            logger.error(f"Error parsing tenant table HTML: {e}")
            return []

    def _clean_tenant_name(self, name: str) -> str:
        """Clean and normalize tenant name."""
        if not name:
            return ""

        # Remove common prefixes
        prefixes_to_remove = [
            r'^Order online',
            r'^Reserve a table',
            r'^Book online',
            r'^Delivery',
            r'^Dine-in',
            r'^Takeaway',
            r'^Opens',
            r'^No reviews',
            r'^\d+\)\s*\(',  # Remove patterns like "575) ("
            r'^\d+\s*\(',     # Remove patterns like "112) ("
        ]

        for prefix in prefixes_to_remove:
            name = re.sub(prefix, '', name, flags=re.IGNORECASE).strip()

        # Remove surrounding and embedded double-quote characters (keep apostrophes)
        # Handles ASCII and common Unicode double-quote variants (e.g., “ ” „ « »)
        name = re.sub(r'[\"“”„‟«»]+', '', name).strip()

        # Remove extra whitespace
        name = re.sub(r'\s+', ' ', name).strip()

        # Remove trailing/leading punctuation
        name = name.strip('·- ')

        # Skip if it's just a number or too short
        if len(name) < 2 or name.isdigit():
            return ""

        # Skip if it looks like just a category or malformed data
        if name.startswith('£') or name.startswith('(') or name.endswith(')') and not '(' in name[:-1]:
            return ""

        return name

    def _clean_category(self, category: str) -> str:
        """Clean and normalize category."""
        if not category:
            return ""

        # Remove extra whitespace
        category = re.sub(r'\s+', ' ', category).strip()

        # Remove price indicators and other artifacts
        category = re.sub(r'^£[\d\-]+', '', category).strip()

        return category

    def _looks_like_price(self, text: str) -> bool:
        """Heuristic to decide if a metadata token is a price range, not a rating blob.

        Accepts typical currency-based ranges (e.g., ££, $$, €€) or price words,
        and rejects rating-like strings such as "4.7(3,575)".
        """
        if not text:
            return False

        s = text.strip()

        # Reject rating blobs like "4.7(3,575)" or "5.0(4)"
        if re.match(r'^\d+(?:\.\d+)?\s*\(\d+(?:,\d+)?\)$', s):
            return False

        # Accept repeated currency signs (e.g., ££, $$, €€)
        if re.fullmatch(r'[€£$¥₽₹₪₩₺₫₴₦₱]{1,5}', s):
            return True

        # Accept if it contains any currency symbol
        if re.search(r'[€£$¥₽₹₪₩₺₫₴₦₱]', s):
            return True

        # Accept common verbal scales Google sometimes uses
        if s.lower() in {"inexpensive", "moderate", "expensive"}:
            return True

        # Otherwise, treat as not a price
        return False

    def _normalize_status_ui_text(self, text: str) -> str:
        """Normalize the status line from the UI to a concise phrase.

        Removes phone numbers and keeps the primary status fragment
        (e.g., "Closed ⋅ Opens 10 am", "Open ⋅ Closes 9 pm", "Temporarily closed").
        """
        if not text:
            return text

        s = text.strip()

        # Prefer well-known phrases bounded before any middle dot delimiter
        patterns = [
            r'(Temporarily\s+closed)',
            r'(Closed\s*⋅\s*Opens[^·]+)',
            r'(Open\s*⋅\s*Closes[^·]+)',
            r'(Closes\s+soon)'
        ]

        for pat in patterns:
            m = re.search(pat, s, flags=re.IGNORECASE)
            if m:
                s = m.group(1).strip()
                break
        else:
            # Fallback: keep text up to the first middle dot '·'
            if '·' in s:
                s = s.split('·', 1)[0].strip()

        # Strip any trailing phone number fragments just in case
        s = re.sub(r'\s*·\s*\+?\d[\d\s\-()]{6,}$', '', s).strip()
        s = re.sub(r'\s*\+?\d[\d\s\-()]{6,}$', '', s).strip()

        return s

    async def _extract_category_info(self) -> List[Dict[str, Any]]:
        """Extract category information using multiple selector strategies."""
        category_info = []

        # Try multiple selector strategies to find category buttons
        selector_strategies = [
            # Original strategy - direct text matching
            "button:has-text('Department stores'), button:has-text('Food & Drink'), button:has-text('Clothing'), button:has-text('Health & Beauty'), button:has-text('Home & Kitchen'), button:has-text('Shoes'), button:has-text('Jewellery'), button:has-text('Electronics'), button:has-text('Toys & Sports'), button:has-text('Other')",

            # Strategy 2: Look for buttons with specific classes
            ".e2moi",

            # Strategy 3: Look for buttons containing numbers (category counts)
            "button:has-text('1'), button:has-text('40'), button:has-text('28'), button:has-text('22'), button:has-text('44'), button:has-text('3')",
        ]

        for strategy_idx, selector in enumerate(selector_strategies):
            try:
                logger.info(f"Trying category selector strategy {strategy_idx + 1}")
                buttons = self.page.locator(selector)

                count = await buttons.count()
                if count > 0:
                    logger.info(f"Found {count} buttons with strategy {strategy_idx + 1}")

                    # Extract information from these buttons
                    for i in range(count):
                        try:
                            button = buttons.nth(i)
                            button_text = await button.inner_text()

                            # Parse category name and count
                            lines = button_text.strip().split('\n')
                            if len(lines) >= 1:
                                category_name = lines[0].strip()

                                # Look for count in the text
                                count_match = re.search(r'(\d+)', button_text)
                                count_val = int(count_match.group(1)) if count_match else 0

                                # Skip if we already have this category or if it's not a real category
                                existing_names = [cat['name'] for cat in category_info]
                                if (category_name not in existing_names and
                                    category_name not in ['Directory', 'Search for places', '+6'] and
                                    count_val > 0):

                                    category_info.append({
                                        'name': category_name,
                                        'count': count_val,
                                        'selector_strategy': strategy_idx,
                                        'button_index': i
                                    })

                                    logger.info(f"  Found category: {category_name} ({count_val} businesses)")

                        except Exception as e:
                            logger.debug(f"Error parsing button {i}: {e}")
                            continue

                    # If we found categories, break out of strategy loop
                    if category_info:
                        break

            except Exception as e:
                logger.debug(f"Strategy {strategy_idx + 1} failed: {e}")
                continue

        logger.info(f"Successfully extracted {len(category_info)} categories")
        return category_info

    # Category navigation and extraction helpers removed (deprecated)

    # _click_category_button_robust removed (deprecated)

    # _extract_tenants_from_category_page removed (deprecated)

    # _perform_category_scroll removed (deprecated)

    # _parse_tenant_from_text_improved removed (deprecated)

    # _parse_tenants_from_page_text removed (deprecated)
