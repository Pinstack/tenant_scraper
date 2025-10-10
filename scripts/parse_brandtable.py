#!/usr/bin/env python3
"""
Parse the brandtable.html file to extract all tenant information from the fully scrolled directory.
"""

import re
import json
from typing import List, Dict, Any
from bs4 import BeautifulSoup


def parse_brandtable_html(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse the brandtable.html file to extract tenant information.

    Args:
        file_path: Path to the HTML file

    Returns:
        List of tenant dictionaries
    """
    print(f"Reading HTML file: {file_path}")

    # Read the HTML file
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    print(f"HTML file size: {len(html_content)} characters")

    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    tenants = []

    # Method 1: Extract all text content and use improved regex patterns
    all_text = soup.get_text()
    print(f"Total text content length: {len(all_text)}")

    # Look for various tenant patterns in the text
    # Pattern 1: "Name rating(count) · category" - full info
    # Pattern 2: "Order online Name rating(count) · category"
    # Pattern 3: "Reserve a table Name rating(count) · category"
    # Pattern 4: "Name · category" - no rating
    # Pattern 5: Just "Name" - basic

    patterns = [
        # Full pattern with rating and category
        r'([A-Za-z0-9\s&\'\-\(\)]+?)\s+(\d\.\d)\s*\((\d+)\)\s*·\s*([^·\n\r]+)',
        # Pattern with "Order online" prefix
        r'Order online([A-Za-z0-9\s&\'\-\(\)]+?)\s+(\d\.\d)\s*\((\d+)\)\s*·\s*([^·\n\r]+)',
        # Pattern with "Reserve a table" prefix
        r'Reserve a table([A-Za-z0-9\s&\'\-\(\)]+?)\s+(\d\.\d)\s*\((\d+)\)\s*·\s*([^·\n\r]+)',
        # Pattern without rating but with category
        r'([A-Za-z0-9\s&\'\-\(\)]+?)\s*·\s*([^·\n\r]+)',
    ]

    all_matches = []
    for pattern in patterns:
        matches = re.findall(pattern, all_text)
        all_matches.extend(matches)

    print(f"Found {len(all_matches)} regex matches")

    # Process all matches
    for i, match in enumerate(all_matches):
        try:
            if len(match) == 4:  # Name, rating, count, category
                name, rating, count, category = match
                tenant = {
                    'name': clean_tenant_name(name),
                    'rating': float(rating),
                    'review_count': int(count),
                    'category': clean_category(category)
                }
            elif len(match) == 2:  # Name, category (no rating)
                name, category = match
                tenant = {
                    'name': clean_tenant_name(name),
                    'category': clean_category(category)
                }
            else:
                continue

            # Skip invalid entries
            if not tenant['name'] or len(tenant['name']) < 2:
                continue

            # Clean up the name (remove prefixes if present)
            tenant['name'] = re.sub(r'^(Order online|Reserve a table)', '', tenant['name']).strip()

            tenants.append(tenant)

        except Exception as e:
            print(f"Error processing match {i}: {match} - {e}")
            continue

    # Method 2: Extract tenant names from specific HTML elements
    # Look for elements that contain tenant names
    name_selectors = [
        'div.qBF1Pd.fontHeadlineSmall',
        'span.qBF1Pd.fontHeadlineSmall',
        '[aria-label]'
    ]

    html_tenants = []
    for selector in name_selectors:
        elements = soup.select(selector)
        for element in elements:
            name = element.get_text(strip=True) or element.get('aria-label', '')
            if name and len(name) > 2:
                # Clean the name
                clean_name = clean_tenant_name(name)
                if clean_name and not any(t.get('name') == clean_name for t in tenants):
                    html_tenants.append({'name': clean_name})

    # Add HTML-only tenants (those not found by regex)
    tenants.extend(html_tenants)

    print(f"Added {len(html_tenants)} additional tenants from HTML elements")

    # Remove duplicates based on name
    unique_tenants = []
    seen_names = set()
    for tenant in tenants:
        name = tenant.get('name', '').lower().strip()
        if name and name not in seen_names and len(name) > 1:
            unique_tenants.append(tenant)
            seen_names.add(name)

    tenants = unique_tenants

    print(f"\n=== SUMMARY ===")
    print(f"Total unique tenants found: {len(tenants)}")

    # Count data completeness
    with_ratings = sum(1 for t in tenants if 'rating' in t)
    with_reviews = sum(1 for t in tenants if 'review_count' in t)
    with_category = sum(1 for t in tenants if 'category' in t and t['category'])

    print(f"Tenants with ratings: {with_ratings}")
    print(f"Tenants with review counts: {with_reviews}")
    print(f"Tenants with categories: {with_category}")

    # Show sample tenants
    print("\nFirst 15 tenants:")
    for i, tenant in enumerate(tenants[:15]):
        print(f"{i+1}. {tenant}")

    return tenants


def clean_tenant_name(name: str) -> str:
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


def clean_category(category: str) -> str:
    """Clean and normalize category."""
    if not category:
        return ""

    # Remove extra whitespace
    category = re.sub(r'\s+', ' ', category).strip()

    # Remove price indicators and other artifacts
    category = re.sub(r'^£[\d\-]+', '', category).strip()

    return category


def main():
    """Main function to parse the brandtable.html file."""
    file_path = "brandtable.html"

    try:
        tenants = parse_brandtable_html(file_path)

        # Save to JSON
        output_file = "parsed_tenants_from_brandtable.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(tenants, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Saved {len(tenants)} tenants to {output_file}")

    except Exception as e:
        print(f"❌ Error parsing HTML: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
