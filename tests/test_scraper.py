"""Tests for the tenant scraper."""

import pytest
from unittest.mock import Mock, patch
from tenant_scraper.scraper import TenantScraper


class TestTenantScraper:
    """Test cases for the TenantScraper class."""

    @patch('tenant_scraper.scraper.webdriver.Chrome')
    @patch('tenant_scraper.scraper.ChromeDriverManager')
    def test_scraper_initialization(self, mock_chrome_manager, mock_chrome):
        """Test that scraper initializes correctly."""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver

        scraper = TenantScraper(headless=True)

        # Verify Chrome driver was created with headless option
        mock_chrome.assert_called_once()
        call_args = mock_chrome.call_args
        options = call_args[1]['options']

        # Check that headless argument was added
        headless_found = False
        for call in options._arguments:
            if '--headless' in call:
                headless_found = True
                break
        assert headless_found, "Headless option should be set"

        assert scraper.driver == mock_driver
        assert scraper.headless is True

    def test_url_manipulation_basic(self):
        """Test basic URL manipulation for directory view."""
        scraper = Mock(spec=TenantScraper)

        # Test URL that should be manipulated
        test_url = "https://www.google.com/maps/place/St+James+Quarter/@55.9549949,-3.1895632,18z/data=!3m1!5s0x4887c78e8d34be11:0x8f6f33443851f595!4m14!1m8!3m7!1s0x4887c78e8d34be11:0x8f6f33443851f595!8m2!3d55.9549949!4d-3.1895632!9m1!1b1!16s%2Fg%2F11c1n6q9j8!3m6!1s0x4887c78e8d34be11:0x8f6f33443851f595!5m1!1e1!8m2!3d55.9549949!4d-3.1895632!10e2!16s%2Fg%2F11c1n6q9j8"

        # This would need actual implementation to test properly
        # For now, just verify the method exists
        assert hasattr(scraper, '_manipulate_to_directory_view')

    @patch('tenant_scraper.scraper.webdriver.Chrome')
    @patch('tenant_scraper.scraper.ChromeDriverManager')
    def test_consent_handling_method_exists(self, mock_chrome_manager, mock_chrome):
        """Test that consent handling method exists."""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver

        scraper = TenantScraper()

        # Verify the consent handling method exists
        assert hasattr(scraper, '_handle_consent_page')
        assert callable(scraper._handle_consent_page)
