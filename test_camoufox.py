#!/usr/bin/env python3
"""
Quick test to verify Camoufox can start and navigate
"""

import asyncio
import sys
sys.path.insert(0, '/home/kali/Desktop/env/lib/python3.13/site-packages')

from camoufox import AsyncCamoufox

async def test_camoufox():
    print("Testing Camoufox initialization...")
    
    try:
        # Create Camoufox instance
        camoufox_obj = AsyncCamoufox()
        print("✓ AsyncCamoufox created")
        
        # Start browser
        print("Starting browser...")
        browser = await camoufox_obj.start()
        print("✓ Browser started")
        
        # Create page
        print("Creating page...")
        page = await browser.new_page()
        print("✓ Page created")
        
        # Navigate
        print("Navigating to example.com...")
        await page.goto("https://example.com", timeout=10000)
        print("✓ Navigation successful")
        
        # Get title
        title = await page.title()
        print(f"✓ Page title: {title}")
        
        # Close
        await page.close()
        await browser.stop()
        print("✓ Browser stopped")
        
        print("\n✓✓✓ All tests passed! Camoufox is working correctly! ✓✓✓")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_camoufox())
