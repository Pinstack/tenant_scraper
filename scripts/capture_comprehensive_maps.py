
import asyncio
import json
import time
from playwright.async_api import async_playwright

async def capture_maps_data():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        network_data = []
        protobuf_responses = []
        
        async def log_request(request):
            network_data.append({
                'url': request.url,
                'method': request.method,
                'headers': dict(request.headers),
                'timestamp': time.time()
            })
        
        async def log_response(response):
            url = response.url
            # Look for Google Maps API calls that might contain protobuf
            if any(keyword in url for keyword in ['maps/_/js', 'photometa', 'listentities', 'search', 'place']):
                try:
                    body = await response.body()
                    if body and len(body) > 100:  # Only save substantial responses
                        protobuf_responses.append({
                            'url': url,
                            'size': len(body),
                            'content_type': response.headers.get('content-type', ''),
                            'body_preview': body[:200].decode('utf-8', errors='ignore') if body else ''
                        })
                        
                        # Save the full response
                        filename = f'outputs/ocean-terminal/network-traffic/api_response_{int(time.time())}.bin'
                        with open(filename, 'wb') as f:
                            f.write(body)
                        print(f'Saved API response: {filename} ({len(body)} bytes)')
                        
                except Exception as e:
                    print(f'Error capturing response: {e}')
        
        page.on('request', log_request)
        page.on('response', log_response)
        
        print('Navigating to Google Maps...')
        await page.goto('https://www.google.com/maps/place/Ocean+Terminal/@55.980686,-3.177862,17z/data=!3m1!5s0x4887b800fef7712d:0x7edf0a3a5cef023c!4m7!3m6!1s0x4887b801aa0388b7:0xf48f1fec04e6a48c!8m2!3d55.980686!4d-3.177862!10e3!16zL20vMDJuZ3Q2?entry=ttu&g_ep=EgoyMDI1MTAxNC4wIKXMDSoASAFQAw%3D%3D', wait_until='domcontentloaded')
        
        # Wait for dynamic content to load
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(5)  # Wait for AJAX calls
        
        # Try to trigger some interactions that might load more data
        try:
            # Look for and click on elements that might load more data
            await page.wait_for_selector('[role="main"]', timeout=10000)
            await asyncio.sleep(3)
        except:
            pass
        
        # Save network data
        with open('outputs/ocean-terminal/network-traffic/comprehensive_requests.json', 'w') as f:
            json.dump(network_data, f, indent=2)
        
        with open('outputs/ocean-terminal/network-traffic/protobuf_responses.json', 'w') as f:
            json.dump(protobuf_responses, f, indent=2)
        
        print(f'Captured {len(network_data)} network requests')
        print(f'Found {len(protobuf_responses)} potential protobuf responses')
        
        await browser.close()

# Run the async function
asyncio.run(capture_maps_data())
