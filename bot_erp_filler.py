#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ERP Form Filler - Reads from saved JSON and fills form accurately
"""

import json
import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

ERP_URL = os.getenv("ERP_URL", "https://erp.bx123.pro/admin/main")

print("=" * 60)
print("🤖 ERP AUTO FILLER - Reading from saved data")
print("=" * 60)

# Load data
data_file = "erp_data.json"

if not os.path.exists(data_file):
    print(f"\n❌ Error: {data_file} not found!")
    print("Please run erp_data_entry.py first to create the data file.")
    input("Press Enter to exit...")
    quit()

with open(data_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("\n📊 Loaded Data:")
print(json.dumps(data, indent=2, ensure_ascii=False))

def safe_fill(page, selector, value, field_name=""):
    """Safely fill a field with error handling"""
    if not value:
        return False
    
    try:
        page.fill(selector, str(value), timeout=3000)
        print(f"  ✅ {field_name}: {value}")
        return True
    except Exception as e:
        print(f"  ⚠️ Failed to fill {field_name}: {selector}")
        return False

def safe_select(page, selector, value, field_name=""):
    """Safely select dropdown option"""
    if not value:
        return False
    
    try:
        page.select_option(selector, value, timeout=3000)
        print(f"  ✅ {field_name}: {value}")
        return True
    except Exception as e:
        print(f"  ⚠️ Failed to select {field_name}: {selector}")
        return False

def safe_click(page, selector, field_name=""):
    """Safely click element"""
    try:
        page.click(selector, timeout=3000)
        print(f"  ✅ Clicked: {field_name}")
        return True
    except Exception as e:
        print(f"  ⚠️ Failed to click {field_name}: {selector}")
        return False

print("\n🌐 Opening browser...")

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir="C:/erp_profile",
        headless=False
    )
    
    page = browser.pages[0] if browser.pages else browser.new_page()
    
    print(f"🔗 Navigating to: {ERP_URL}")
    page.goto(ERP_URL)
    page.wait_for_timeout(3000)
    
    print("\n⏸️  Please LOGIN to ERP if needed...")
    print("Press ENTER when ready to navigate to form...")
    input()
    
    # Navigate directly to form
    print("\n📋 Opening form...")
    page.goto("https://erp.bx123.pro/celebrityOrder/save")
    page.wait_for_timeout(3000)
    
    print("\n📝 Filling form with saved data...\n")
    
    ### INFLUENCER INFORMATION ###
    print("👤 Influencer Information:")
    
    # Try English selectors first, then Chinese
    safe_fill(page, 'input[name="nickname"]', data.get('nickname'), "Nickname")
    safe_fill(page, 'input[name="contact_info"]', data.get('contact_info'), "Contact Info")
    safe_select(page, 'select[name="contact_type"]', data.get('contact_type', 'Email'), "Contact Type")
    safe_fill(page, 'input[name="cooperation_date"]', data.get('cooperation_date'), "Cooperation Date")
    safe_select(page, 'select[name="cooperation_status"]', data.get('cooperation_status'), "Cooperation Status")
    safe_select(page, 'select[name="influencer_quality"]', data.get('influencer_quality'), "Influencer Quality")
    safe_fill(page, 'input[name="contact_email"]', data.get('contact_email'), "Contact Email")
    
    ### SOCIAL MEDIA ###
    print("\n📱 Social Media Information:")
    
    # Click "Add Social Information" if button exists
    try:
        page.click('button:has-text("Add")', timeout=2000)
        page.wait_for_timeout(1000)
    except:
        pass
    
    safe_select(page, 'select[name="platform"]', data.get('platform'), "Platform")
    safe_fill(page, 'input[name="channel_name"]', data.get('channel_name'), "Channel Name")
    safe_fill(page, 'input[name="channel_link"]', data.get('channel_link'), "Channel Link")
    safe_fill(page, 'input[name="fans"]', data.get('followers'), "Followers")
    safe_select(page, 'select[name="fans_unit"]', data.get('followers_unit'), "Unit")
    
    ### DELIVERY INFORMATION ###
    print("\n📦 Delivery Information:")
    
    safe_fill(page, 'input[name="consignee"]', data.get('consignee'), "Recipient Name")
    safe_fill(page, 'input[name="phone"]', data.get('phone'), "Phone")
    safe_fill(page, 'input[name="country"]', data.get('country'), "Country")
    safe_fill(page, 'input[name="province"]', data.get('province'), "Province")
    safe_fill(page, 'input[name="city"]', data.get('city'), "City")
    
    # Address might be textarea
    try:
        page.fill('textarea[name="address"]', data.get('address', ''), timeout=2000)
        print(f"  ✅ Address: {data.get('address')}")
    except:
        safe_fill(page, 'input[name="address"]', data.get('address'), "Address")
    
    safe_fill(page, 'input[name="postal_code"]', data.get('postal_code'), "Postal Code")
    
    print("\n" + "=" * 60)
    print("✅ FORM FILLING COMPLETE!")
    print("=" * 60)
    print("\n👉 Please review the form carefully")
    print("👉 Make any manual adjustments if needed")
    print("👉 Click SUBMIT when ready")
    print("\nBrowser will stay open until you press Enter...")
    
    try:
        input("\nPress ENTER to close browser...")
    except KeyboardInterrupt:
        print("\n\n👋 Closing...")
    
    browser.close()

print("\n✅ DONE!")
