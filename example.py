#!/usr/bin/env python3
"""Example usage of the tenant scraper."""

from tenant_scraper import TenantScraper

def main():
    """Demonstrate basic scraper usage."""
    # Example Google Maps URL
    maps_url = "https://maps.app.goo.gl/FsGevWWrjvab4tZ9A"

    print("Tenant Scraper Example")
    print(f"URL: {maps_url}")
    print("\nNote: This is a demonstration. Actual scraping requires:")
    print("1. ChromeDriver installation")
    print("2. Internet connection")
    print("3. Valid Google Maps URL")
    print("\nTo run actual scraping:")
    print(f"python -m tenant_scraper.cli '{maps_url}' -o tenants.json")

    # Initialize scraper (would normally scrape if we had a real URL)
    try:
        scraper = TenantScraper(headless=True)
        print("✓ Scraper initialized successfully")

        # Show that methods exist
        assert hasattr(scraper, 'scrape_tenants')
        assert hasattr(scraper, '_handle_consent_page')
        assert hasattr(scraper, '_manipulate_to_directory_view')
        print("✓ All required methods available")

    except Exception as e:
        print(f"✗ Error initializing scraper: {e}")
        return

    print("\nScraper is ready for use!")

if __name__ == "__main__":
    main()
