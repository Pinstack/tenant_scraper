#!/usr/bin/env python3
"""
Capture Google Maps protobuf data with consent handling
"""

import asyncio
import json
import time
from playwright.async_api import async_playwright

async def capture_maps_with_consent():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        captured_responses = []
        
        async def log_response(response):
            try:
                url = response.url
                body = await response.body()
                
                # Capture substantial responses that might contain protobuf
                if len(body) > 1000 and not any(skip in url for skip in ['.css', '.png', '.jpg', '.svg', '.ico']):
                    response_info = {
                        'url': url,
                        'status': response.status,
                        'content_type': response.headers.get('content-type', ''),
                        'size': len(body),
                        'timestamp': time.time()
                    }
                    
                    # Save the response
                    filename = f'outputs/ocean-terminal/network-traffic/consent_response_{int(time.time())}.bin'
                    with open(filename, 'wb') as f:
                        f.write(body)
                    
                    response_info['file'] = filename
                    
                    # Check for protobuf indicators
                    try:
                        body_str = body.decode('utf-8', errors='ignore')
                        if '!1m' in body_str or '!2m' in body_str:
                            response_info['protobuf_like'] = True
                            print(f'*** PROTOBUF DETECTED in {len(body)} byte response ***')
                        elif 'place' in body_str.lower() and ('name' in body_str.lower() or 'id' in body_str.lower()):
                            response_info['place_data_like'] = True
                            print(f'*** PLACE DATA DETECTED in {len(body)} byte response ***')
                    except:
                        pass
                    
                    captured_responses.append(response_info)
                    print(f'Captured {len(body)} bytes: {url[:80]}...')
                    
            except Exception as e:
                print(f'Error capturing response: {e}')
        
        page.on('response', log_response)
        
        # Navigate to Google Maps - this will likely hit consent page first
        print('Navigating to Google Maps...')
        await page.goto('https://www.google.com/maps/search/shops+in+Ocean+Terminal+Edinburgh/@55.980686,-3.177862,17z', 
                       wait_until='domcontentloaded')
        
        # Wait for and handle consent page
        try:
            # Look for consent buttons
            consent_selectors = [
                '[aria-label*="Accept"]',
                '[aria-label*="Agree"]', 
                'button:has-text("Accept")',
                'button:has-text("Agree")',
                '.consent-button',
                '#consent-button'
            ]
            
            consent_clicked = False
            for selector in consent_selectors:
                try:
                    button = page.locator(selector).first
                    if await button.is_visible(timeout=2000):
                        await button.click()
                        print(f'Clicked consent button: {selector}')
                        consent_clicked = True
                        await asyncio.sleep(2)
                        break
                except:
                    continue
            
            if not consent_clicked:
                print('No consent button found, proceeding anyway...')
        
        except Exception as e:
            print(f'Consent handling error: {e}')
        
        # Wait for map to load
        await page.wait_for_load_state('networkidle', timeout=10000)
        await asyncio.sleep(5)
        
        # Try to interact with the map to trigger data loading
        try:
            # Wait for map canvas
            await page.wait_for_selector('canvas', timeout=5000)
            print('Map canvas loaded')
            
            # Try clicking on the map or search results
            await page.mouse.click(400, 300)  # Click in center of map
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f'Map interaction error: {e}')
        
        # Additional wait for any delayed loading
        await asyncio.sleep(3)
        
        # Save capture summary
        with open('outputs/ocean-terminal/network-traffic/consent_capture_summary.json', 'w') as f:
            json.dump(captured_responses, f, indent=2)
        
        print(f'\\nCapture complete. Saved {len(captured_responses)} responses.')
        
        # Try to decode any protobuf-like responses
        protobuf_files = [r for r in captured_responses if r.get('protobuf_like')]
        if protobuf_files:
            print(f'\\nFound {len(protobuf_files)} protobuf-like responses!')
            for pb_file in protobuf_files[:3]:  # Try first 3
                try:
                    with open(pb_file['file'], 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Extract protobuf strings
                    import re
                    pb_strings = re.findall(r'!1m\d+![^!]*', content)
                    if pb_strings:
                        print(f'Found {len(pb_strings)} protobuf strings in {pb_file["file"]}')
                        
                        # Try decoding first one
                        try:
                            from outputs.ocean_terminal.protobuf_schemas.deproto.deproto import Protobuf
                            decoder = Protobuf(pb_strings[0])
                            cluster = decoder.decode()
                            print(f'Successfully decoded protobuf!')
                            decoder.print_tree()
                        except Exception as e:
                            print(f'Decode error: {e}')
                except Exception as e:
                    print(f'Error processing {pb_file["file"]}: {e}')
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(capture_maps_with_consent())
