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
