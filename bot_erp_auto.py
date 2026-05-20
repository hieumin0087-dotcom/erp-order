import imaplib
import email
import json
import os
from dotenv import load_dotenv
from groq import Groq
from playwright.sync_api import sync_playwright

load_dotenv()

GMAIL = os.getenv("GMAIL_ADDRESS")
PASS = os.getenv("GMAIL_APP_PASSWORD")
ERP = os.getenv("ERP_URL")
GROQ = os.getenv("GROQ_API_KEY")

print("=" * 60)
print("🤖 ERP AUTO BOT – AI VERSION v2.0")
print("=" * 60)

target = input("\n📧 Influencer email: ").strip()

### ===== LOAD EMAIL =====

print("\n🔗 Connecting to Gmail...")
mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login(GMAIL, PASS)
mail.select("inbox")

status, data = mail.search(None, f'(FROM "{target}")')
ids = data[0].split()

if not ids:
    print("❌ NO EMAIL FOUND")
    quit()

latest = ids[-1]

status, msg = mail.fetch(latest, "(RFC822)")
raw = msg[0][1]

msg = email.message_from_bytes(raw)

body = ""

if msg.is_multipart():
    for p in msg.walk():
        if p.get_content_type() == "text/plain":
            body += p.get_payload(decode=True).decode(errors='ignore')
else:
    body = msg.get_payload(decode=True).decode(errors='ignore')

mail.logout()

print("✅ EMAIL LOADED")

### ===== AI EXTRACT =====

print("\n🤖 Extracting data with AI...")

client = Groq(api_key=GROQ)

prompt = f"""
Extract shipping + influencer info from this email.
Return ONLY valid JSON, no explanation.

Email:
{body}

JSON FORMAT:
{{
 "shipping": {{
   "full_name":"",
   "address":"",
   "city":"",
   "state":"",
   "zip":"",
   "country":"Vietnam",
   "phone":""
 }},
 "influencer": {{
   "channel_name":"",
   "platform":"youtube",
   "channel_link":"",
   "followers":""
 }}
}}
"""

ai = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role":"user","content":prompt}]
)

text = ai.choices[0].message.content.strip()

# Extract JSON from response
if "```json" in text:
    text = text.split("```json")[1].split("```")[0]
elif "```" in text:
    text = text.split("```")[1].split("```")[0]

text = text.strip()
text = text[text.find("{"):text.rfind("}")+1]

try:
    data = json.loads(text)
    print("✅ AI DATA LOADED")
    print("\n📊 Extracted Data:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
except:
    print("\n❌ AI JSON PARSE ERROR")
    print("Raw output:", text)
    quit()

### ===== HELPER FUNCTIONS =====

def smart_fill(page, field_name, value, selectors):
    """Try multiple selectors to fill a field"""
    if not value:
        return False
    
    for selector in selectors:
        try:
            page.fill(selector, str(value), timeout=2000)
            print(f"  ✅ {field_name}: {value}")
            return True
        except:
            continue
    
    print(f"  ⚠️ Could not fill: {field_name}")
    return False

def smart_select(page, field_name, value, selectors):
    """Try multiple selectors for dropdown"""
    if not value:
        return False
    
    for selector in selectors:
        try:
            page.select_option(selector, value, timeout=2000)
            print(f"  ✅ {field_name}: {value}")
            return True
        except:
            continue
    
    print(f"  ⚠️ Could not select: {field_name}")
    return False

def smart_click(page, text):
    """Try to click button/link with text"""
    try:
        page.click(f'text="{text}"', timeout=3000)
        return True
    except:
        try:
            page.click(f'button:has-text("{text}")', timeout=3000)
            return True
        except:
            return False

### ===== OPEN ERP =====

print("\n🌐 Opening browser...")

with sync_playwright() as p:

    browser = p.chromium.launch_persistent_context(
        user_data_dir="C:/erp_profile",
        headless=False
    )

    page = browser.pages[0] if browser.pages else browser.new_page()

    print(f"🔗 Navigating to: {ERP}")
    page.goto(ERP)
    page.wait_for_timeout(3000)

    print("\n⏸️  LOGIN to ERP, then press ENTER in terminal...")
    input()

    # Navigate to form
    print("\n📋 Opening Influencer Order form...")
    page.goto("https://erp.bx123.pro/celebrityOrder/save")
    page.wait_for_timeout(3000)

    print("\n📝 Filling form fields...")

    ### INFLUENCER INFORMATION ###
    
    print("\n👤 Influencer Information:")
    
    # Nickname / Channel Name
    smart_fill(page, "Nickname", data["influencer"]["channel_name"], [
        'input[name="nickname"]',
        'input[placeholder*="昵称"]',
        'input[placeholder*="Nickname"]',
        'input[id*="nickname"]'
    ])
    
    # Contact Email
    smart_fill(page, "Contact Email", target, [
        'input[name="contact_info"]',
        'input[name="email"]',
        'input[placeholder*="邮箱"]',
        'input[placeholder*="Email"]',
        'input[type="email"]'
    ])
    
    # Contact Type
    smart_select(page, "Contact Type", "Email", [
        'select[name="contact_type"]',
        'select[placeholder*="联系方式"]'
    ])
    
    # Platform
    platform_map = {
        "youtube": "Youtube",
        "tiktok": "TikTok", 
        "instagram": "Instagram"
    }
    platform_value = platform_map.get(data["influencer"].get("platform", "").lower(), "Youtube")
    
    smart_select(page, "Platform", platform_value, [
        'select[name="platform"]',
        'select[placeholder*="平台"]'
    ])
    
    # Channel Link
    smart_fill(page, "Channel Link", data["influencer"]["channel_link"], [
        'input[name="link"]',
        'input[name="channel_link"]',
        'input[placeholder*="链接"]',
        'input[placeholder*="Link"]'
    ])
    
    # Followers
    followers = data["influencer"].get("followers", "")
    if followers:
        # Try to extract number
        import re
        num_match = re.search(r'(\d+(?:\.\d+)?)', str(followers))
        if num_match:
            num = num_match.group(1)
            smart_fill(page, "Followers", num, [
                'input[name="fans"]',
                'input[placeholder*="粉丝"]',
                'input[placeholder*="Followers"]'
            ])
            
            # Unit
            unit = "H"
            if "K" in str(followers).upper():
                unit = "K"
            elif "M" in str(followers).upper():
                unit = "M"
            
            smart_select(page, "Unit", unit, [
                'select[name="fans_unit"]',
                'select[name="unit"]'
            ])

    ### SHIPPING INFORMATION ###
    
    print("\n📦 Shipping Information:")
    
    # Recipient Name
    smart_fill(page, "Recipient Name", data["shipping"]["full_name"], [
        'input[name="consignee"]',
        'input[name="recipient"]',
        'input[placeholder*="姓名"]',
        'input[placeholder*="Name"]',
        'input[placeholder*="收件人"]'
    ])
    
    # Phone
    smart_fill(page, "Phone", data["shipping"]["phone"], [
        'input[name="phone"]',
        'input[name="mobile"]',
        'input[placeholder*="电话"]',
        'input[placeholder*="Phone"]',
        'input[type="tel"]'
    ])
    
    # Country
    smart_fill(page, "Country", data["shipping"]["country"], [
        'input[name="country"]',
        'input[placeholder*="国家"]',
        'input[placeholder*="Country"]'
    ])
    
    # Province/State
    smart_fill(page, "Province", data["shipping"]["state"], [
        'input[name="province"]',
        'input[name="state"]',
        'input[placeholder*="省份"]',
        'input[placeholder*="Province"]'
    ])
    
    # City
    smart_fill(page, "City", data["shipping"]["city"], [
        'input[name="city"]',
        'input[placeholder*="城市"]',
        'input[placeholder*="City"]'
    ])
    
    # Address
    smart_fill(page, "Address", data["shipping"]["address"], [
        'input[name="address"]',
        'textarea[name="address"]',
        'input[placeholder*="地址"]',
        'input[placeholder*="Address"]'
    ])
    
    # Postal Code
    smart_fill(page, "Postal Code", data["shipping"]["zip"], [
        'input[name="postal_code"]',
        'input[name="zip"]',
        'input[name="postcode"]',
        'input[placeholder*="邮编"]',
        'input[placeholder*="Postal"]'
    ])

    print("\n✅ FORM FILLING COMPLETE!")
    print("\n👉 Please review the form and click SUBMIT manually")
    print("Browser will stay open until you close it or press Ctrl+C in terminal")
    
    try:
        input("\nPress ENTER to close browser...")
    except KeyboardInterrupt:
        print("\n\n👋 Closing...")
    
    browser.close()

print("\n✅ DONE!")
