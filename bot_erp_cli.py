#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ERP Bot - CLI Version (No blocking, accepts arguments)
Usage: py bot_erp_cli.py <sender_email> <erp_url>
"""

import sys
import imaplib
import email
import re
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import time

# Load environment variables
load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
ERP_USERNAME = os.getenv("ERP_USERNAME")

def read_emails(sender_email):
    """Read emails from sender"""
    try:
        print(f"🔗 Connecting to Gmail...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        mail.select("inbox")
        
        print(f"📧 Searching emails from: {sender_email}")
        status, messages = mail.search(None, f'FROM "{sender_email}"')
        email_ids = messages[0].split()
        
        if not email_ids:
            print("⚠️ No emails found!")
            return ""
        
        print(f"📬 Found {len(email_ids)} email(s)")
        
        all_content = ""
        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors='ignore')
                                all_content += body + "\n"
                    else:
                        body = msg.get_payload(decode=True).decode(errors='ignore')
                        all_content += body + "\n"
        
        mail.close()
        mail.logout()
        return all_content
        
    except Exception as e:
        print(f"❌ Email error: {e}")
        return ""

def extract_data(email_content):
    """Extract phone and YouTube link"""
    data = {}
    
    # Extract phone
    phone_pattern = r'\b\d{10,12}\b'
    phone_match = re.search(phone_pattern, email_content)
    if phone_match:
        data["phone"] = phone_match.group()
        print(f"📞 Phone: {data['phone']}")
    
    # Extract YouTube link
    youtube_pattern = r'(?:https?://)?(?:www\.)?youtube\.com[^\s]+'
    youtube_match = re.search(youtube_pattern, email_content)
    if youtube_match:
        data["link"] = youtube_match.group()
        print(f"🔗 YouTube: {data['link']}")
    
    return data

def fill_form(erp_url, data):
    """Fill ERP form"""
    try:
        print("🌐 Opening browser...")
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir="./user_data",
                headless=False,
                channel="chrome"
            )
            
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto(erp_url)
            page.wait_for_load_state("networkidle")
            
            print("📝 Filling form...")
            time.sleep(2)
            
            # Fill form
            if data.get("phone"):
                try:
                    page.fill('input[name="phone"]', data["phone"])
                except:
                    pass
            
            if data.get("link"):
                try:
                    page.fill('input[name="link"]', data["link"])
                except:
                    pass
            
            print("✅ Form filled! Check and submit manually.")
            print("Browser will auto-close in 30 seconds...")
            
            time.sleep(30)
            browser.close()
            
    except Exception as e:
        print(f"❌ Browser error: {e}")

def main():
    print("=" * 50)
    print("🤖 ERP BOT - CLI Version")
    print("=" * 50)
    
    # Check arguments
    if len(sys.argv) < 3:
        print("\n❌ Missing arguments!")
        print("Usage: py bot_erp_cli.py <sender_email> <erp_url>")
        print("\nExample:")
        print("py bot_erp_cli.py influencer@gmail.com https://erp.example.com")
        sys.exit(1)
    
    sender_email = sys.argv[1]
    erp_url = sys.argv[2]
    
    # Read emails
    content = read_emails(sender_email)
    
    if not content:
        print("❌ No content to process!")
        sys.exit(1)
    
    # Extract data
    print("\n🔍 Extracting data...")
    data = extract_data(content)
    
    # Fill form
    print(f"\n🌐 Opening ERP: {erp_url}")
    fill_form(erp_url, data)
    
    print("\n✅ Done! Exiting...")
    sys.exit(0)

if __name__ == "__main__":
    main()
