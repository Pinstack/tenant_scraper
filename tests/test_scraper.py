"""Unit tests for TenantScraper helpers."""

import asyncio

import pytest

from tenant_scraper.scraper import ScraperSettings, TenantScraper


@pytest.mark.parametrize(
    "block, aggressive, expected_hosts",
    [
        (True, False, {"lh3.googleusercontent.com"}),
        (True, True, {"lh3.googleusercontent.com", "maps.googleapis.com"}),
    ],
)
def test_settings_apply_host_overrides(block, aggressive, expected_hosts):
    settings = ScraperSettings(block_resources=block, aggressive_block=aggressive)
    scraper = TenantScraper(settings=settings)

    if aggressive:
        assert scraper.settings.aggressive_block is True
    else:
        assert scraper.settings.aggressive_block is False

    blocked = set(scraper.settings.blocked_hosts)
    assert any(host in blocked for host in expected_hosts)


def test_resource_interceptor_blocks_configured_hosts():
    settings = ScraperSettings(block_resources=True)
    scraper = TenantScraper(settings=settings)

    class DummyRoute:
        def __init__(self):
            self.aborted = False
            self.continued = False

        async def abort(self):
            self.aborted = True

        async def continue_(self):
            self.continued = True

    class DummyRequest:
        def __init__(self, resource_type, url):
            self.resource_type = resource_type
            self.url = url

    route = DummyRoute()
    request = DummyRequest("image", "https://lh3.googleusercontent.com/foo")

    asyncio.run(scraper._resource_route_interceptor(route, request))

    assert route.aborted is True
    assert route.continued is False


def test_perform_with_retries_retries_then_succeeds():
    settings = ScraperSettings(action_retries=2, action_retry_backoff=0.01)
    scraper = TenantScraper(settings=settings)

    attempts = {'count': 0}

    async def flaky_action():
        attempts['count'] += 1
        if attempts['count'] < 2:
            raise RuntimeError("temporary failure")
        return "ok"

    result = asyncio.run(scraper._perform_with_retries("flaky", flaky_action))
    assert result == "ok"
    assert attempts['count'] == 2


# Story 1.2: Detail Extraction Tests


def test_scraper_settings_detail_extraction_defaults():
    """Test that detail extraction settings have correct defaults."""
    settings = ScraperSettings()
    
    assert settings.enable_detail_extraction is False
    assert settings.detail_per_card_delay == 2.0
    assert settings.detail_scroll_settle_delay == 0.5
    assert settings.detail_after_click_delay == 2.0
    assert settings.detail_after_back_delay == 1.0
    assert settings.detail_extraction_timeout == 5.0
    assert settings.detail_max_failures == 3
    assert settings.detail_max_cards is None


def test_scraper_settings_detail_extraction_custom():
    """Test that detail extraction settings can be customized."""
    settings = ScraperSettings(
        enable_detail_extraction=True,
        detail_per_card_delay=3.0,
        detail_max_failures=5,
        detail_max_cards=10
    )
    
    assert settings.enable_detail_extraction is True
    assert settings.detail_per_card_delay == 3.0
    assert settings.detail_max_failures == 5
    assert settings.detail_max_cards == 10


@pytest.mark.asyncio
async def test_throttle_delay():
    """Test that throttle delay waits for the specified duration."""
    import time
    
    settings = ScraperSettings()
    scraper = TenantScraper(settings=settings)
    
    start = time.time()
    await scraper._throttle_delay(0.1)
    elapsed = time.time() - start
    
    assert elapsed >= 0.1
    assert elapsed < 0.2  # Should not wait much longer


@pytest.mark.asyncio
async def test_throttle_delay_zero():
    """Test that throttle delay with 0 seconds completes immediately."""
    import time
    
    settings = ScraperSettings()
    scraper = TenantScraper(settings=settings)
    
    start = time.time()
    await scraper._throttle_delay(0.0)
    elapsed = time.time() - start
    
    assert elapsed < 0.05  # Should complete almost immediately


def test_find_matching_tenant_exact_match():
    """Test that _find_matching_tenant finds exact name matches."""
    scraper = TenantScraper()
    
    tenants = [
        {'name': 'Apple Store', 'category': 'Electronics'},
        {'name': 'Nike', 'category': 'Clothing'},
        {'name': 'Starbucks', 'category': 'Coffee'},
    ]
    
    match = scraper._find_matching_tenant(tenants, 'Nike')
    assert match is not None
    assert match['name'] == 'Nike'
    assert match['category'] == 'Clothing'


def test_find_matching_tenant_case_insensitive():
    """Test that _find_matching_tenant is case-insensitive."""
    scraper = TenantScraper()
    
    tenants = [
        {'name': 'Apple Store', 'category': 'Electronics'},
    ]
    
    match = scraper._find_matching_tenant(tenants, 'apple store')
    assert match is not None
    assert match['name'] == 'Apple Store'


def test_find_matching_tenant_partial_match():
    """Test that _find_matching_tenant finds partial matches."""
    scraper = TenantScraper()
    
    tenants = [
        {'name': 'The Apple Store Edinburgh', 'category': 'Electronics'},
    ]
    
    match = scraper._find_matching_tenant(tenants, 'The Apple Store')
    assert match is not None
    assert match['name'] == 'The Apple Store Edinburgh'


def test_find_matching_tenant_no_match():
    """Test that _find_matching_tenant returns None when no match found."""
    scraper = TenantScraper()
    
    tenants = [
        {'name': 'Apple Store', 'category': 'Electronics'},
    ]
    
    match = scraper._find_matching_tenant(tenants, 'Nonexistent Store')
    assert match is None


def test_normalize_phone_number():
    """Test phone number normalization."""
    scraper = TenantScraper()
    
    # Test various formats
    assert scraper._normalize_phone_number('+44 131 123 4567') == '+44 131 123 4567'
    assert scraper._normalize_phone_number('(131) 123-4567') is not None
    assert scraper._normalize_phone_number('tel:+441311234567') == '+441311234567'
    
    # Test invalid input
    assert scraper._normalize_phone_number(None) is None
    assert scraper._normalize_phone_number('') is None


# Integration tests (require fixtures)
# TODO: Add fixture-based tests using captured HTML/protobuf data
# See docs/stories/1-2-card-detail-extraction.md for test ideas
