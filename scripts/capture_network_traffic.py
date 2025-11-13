#!/usr/bin/env python3
"""
Network traffic capture script for Google Maps places.
Captures HTTP requests and responses for analysis of tenant scraping patterns.
"""

import os
import json
import time
import requests
from urllib.parse import urlparse, parse_qs
import logging
from datetime import datetime
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NetworkTrafficCapture:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.session = requests.Session()
        self.captured_requests = []
        self.start_time = datetime.now()

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    def capture_initial_request(self, url):
        """Capture the initial HTTP request to Google Maps"""
        logger.info(f"Capturing initial request to: {url}")

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            request_data = {
                'timestamp': datetime.now().isoformat(),
                'url': url,
                'method': 'GET',
                'request_headers': dict(response.request.headers),
                'status_code': response.status_code,
                'response_headers': dict(response.headers),
                'response_size': len(response.content),
                'content_type': response.headers.get('content-type', ''),
                'redirect_history': [{'url': r.url, 'status_code': r.status_code} for r in response.history]
            }

            # Save HTML content if it's HTML
            if 'text/html' in response.headers.get('content-type', ''):
                html_file = os.path.join(self.output_dir, 'page.html')
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logger.info(f"Saved HTML content to: {html_file}")

            # Save request metadata
            self.captured_requests.append(request_data)

            return response

        except requests.RequestException as e:
            logger.error(f"Failed to capture initial request: {e}")
            return None

    def extract_google_maps_data(self, html_content):
        """Extract relevant Google Maps data from HTML content"""
        data = {}

        # Look for Google Maps specific data patterns
        if 'Ocean Terminal' in html_content:
            data['location_name'] = 'Ocean Terminal'

        # Extract coordinates from URL parameters
        parsed_url = urlparse(self.captured_requests[0]['url'] if self.captured_requests else '')
        if parsed_url.path.startswith('/maps/place/'):
            path_parts = parsed_url.path.split('/')
            if len(path_parts) > 3:
                data['place_name'] = path_parts[3].replace('+', ' ')

        # Look for data attributes or JSON blobs in the HTML
        import re

        # Look for JSON data in script tags
        json_pattern = r'<script[^>]*>(.*?)</script>'
        scripts = re.findall(json_pattern, html_content, re.DOTALL)

        potential_data = []
        for script in scripts:
            if 'place' in script.lower() or 'ocean' in script.lower():
                potential_data.append(script[:500])  # First 500 chars for analysis

        if potential_data:
            data['potential_data_scripts'] = potential_data

        return data

    def save_metadata(self):
        """Save all captured request metadata"""
        metadata_file = os.path.join(self.output_dir, 'network_metadata.json')

        metadata = {
            'capture_session': {
                'start_time': self.start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'total_requests': len(self.captured_requests)
            },
            'requests': self.captured_requests
        }

        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved network metadata to: {metadata_file}")

    def save_headers(self):
        """Save HTTP headers separately for analysis"""
        headers_file = os.path.join(self.output_dir, 'response_headers.txt')

        with open(headers_file, 'w', encoding='utf-8') as f:
            for i, req in enumerate(self.captured_requests):
                f.write(f"=== Request {i+1} ===\n")
                f.write(f"URL: {req['url']}\n")
                f.write(f"Status: {req['status_code']}\n")
                f.write("Request Headers:\n")
                for key, value in req['request_headers'].items():
                    f.write(f"  {key}: {value}\n")
                f.write("Response Headers:\n")
                for key, value in req['response_headers'].items():
                    f.write(f"  {key}: {value}\n")
                f.write("\n")

        logger.info(f"Saved headers to: {headers_file}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python capture_network_traffic.py <url>")
        sys.exit(1)

    url = sys.argv[1]

    # Create output directory based on URL
    parsed = urlparse(url)
    place_name = parsed.path.split('/')[3] if len(parsed.path.split('/')) > 3 else 'unknown_place'
    output_dir = f"outputs/{place_name.replace('+', '-').lower()}/network-traffic"

    print(f"Capturing network traffic for: {url}")
    print(f"Output directory: {output_dir}")

    # Initialize capture
    capture = NetworkTrafficCapture(output_dir)

    # Capture initial request
    response = capture.capture_initial_request(url)

    if response:
        # Extract Google Maps specific data
        maps_data = capture.extract_google_maps_data(response.text)

        # Save extracted data
        data_file = os.path.join(output_dir, 'extracted_data.json')
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(maps_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved extracted data to: {data_file}")

    # Save all metadata
    capture.save_metadata()
    capture.save_headers()

    print(f"Network traffic capture completed. Files saved in: {output_dir}")

if __name__ == "__main__":
    main()
