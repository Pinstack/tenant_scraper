#!/usr/bin/env python3
"""
Capture Google Maps protobuf data by loading pages with JavaScript execution
"""

import asyncio
import json
import time
import base64
from playwright.async_api import async_playwright

async def capture_maps_protobuf():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        protobuf_data = []
        
        async def intercept_response(response):
            url = response.url
            
            # Look for URLs that are likely to contain protobuf data
            if any(keyword in url.lower() for keyword in [
                'maps/_/js', 'photometa', 'search', 'listentities', 
                'placedetails', 'place', 'api', 'protobuf'
            ]) and not any(skip in url.lower() for skip in [
                '.css', '.png', '.jpg', '.svg', '.ico', 'favicon'
            ]):
                
                try:
                    content_type = response.headers.get('content-type', '').lower()
                    body = await response.body()
                    
                    # Check if it's protobuf or binary data
                    is_protobuf_like = (
                        'application/x-protobuf' in content_type or
                        'application/protobuf' in content_type or
                        'application/octet-stream' in content_type or
                        (len(body) > 100 and not body.startswith(b'<') and not body.startswith(b'{'))
                    )
                    
                    if is_protobuf_like or len(body) > 1000:
                        data_info = {
                            'url': url,
                            'method': response.request.method,
                            'status': response.status,
                            'content_type': content_type,
                            'size': len(body),
                            'timestamp': time.time(),
                            'headers': dict(response.headers)
                        }
                        
                        # Save the body if it's substantial
                        if len(body) > 100:
                            filename = f'outputs/ocean-terminal/network-traffic/protobuf_capture_{int(time.time())}.bin'
                            with open(filename, 'wb') as f:
                                f.write(body)
                            
                            data_info['file'] = filename
                            print(f'Captured {len(body)} bytes from {url[:60]}...')
                            
                            # Try to detect if it's actually protobuf
                            if len(body) < 5000:  # Only try on smaller files
                                try:
                                    # Check for protobuf-like patterns
                                    body_str = body.decode('utf-8', errors='ignore')
                                    if '!1m' in body_str or '!2m' in body_str:
                                        data_info['protobuf_detected'] = True
                                        print('  -> Protobuf data detected!')
                                        
                                        # Try to decode with deproto
                                        try:
                                            from outputs.ocean_terminal.protobuf_schemas.deproto.deproto import Protobuf
                                            decoder = Protobuf(body_str)
                                            cluster = decoder.decode()
                                            data_info['decoded'] = True
                                            print('  -> Successfully decoded!')
                                        except:
                                            pass
                                except:
                                    pass
                        
                        protobuf_data.append(data_info)
                        
                except Exception as e:
                    print(f'Error processing response: {e}')
        
        page.on('response', intercept_response)
        
        # Test different Google Maps URLs
        test_urls = [
            'https://www.google.com/maps/search/shops+in+Ocean+Terminal+Edinburgh/@55.980686,-3.177862,17z',
            'https://www.google.com/maps/place/Ocean+Terminal/@55.980686,-3.177862,17z',
            # Try with specific search parameters that might trigger protobuf loading
            'https://www.google.com/maps/search/Ocean+Terminal/@55.980686,-3.177862,15z/data=!3m1!4b1!4m2!2m1!6e5',
        ]
        
        for i, url in enumerate(test_urls):
            print(f'\\nLoading URL {i+1}: {url[:80]}...')
            
            try:
                await page.goto(url, wait_until='domcontentloaded')
                await page.wait_for_load_state('networkidle')
                
                # Wait for potential dynamic content
                await asyncio.sleep(5)
                
                # Try some interactions that might trigger data loading
                try:
                    # Look for search results or place cards
                    results = page.locator('[role="main"] [data-result-index]')
                    count = await results.count()
                    print(f'Found {count} result elements')
                    
                    if count > 0:
                        # Try clicking on first result to trigger detail loading
                        await results.first.click()
                        await asyncio.sleep(3)
                        
                except:
                    pass
                
            except Exception as e:
                print(f'Error loading URL: {e}')
        
        # Save all captured data info
        with open('outputs/ocean-terminal/network-traffic/captured_protobuf_info.json', 'w') as f:
            json.dump(protobuf_data, f, indent=2)
        
        print(f'\\nCaptured {len(protobuf_data)} potential protobuf responses')
        
        await browser.close()
        
        return protobuf_data

if __name__ == '__main__':
    result = asyncio.run(capture_maps_protobuf())
    print(f'Capture complete. Found {len(result)} responses.')
