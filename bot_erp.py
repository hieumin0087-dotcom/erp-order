#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ERP Bot - Automated Email to Form Filling
Reads emails from influencers and fills ERP forms automatically
"""

import imaplib
import email
from email.header import decode_header
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

class ERPBot:
    def __init__(self):
        self.email_data = {
            "name": "",
            "contact_info": "",
            "link": "",
            "fans": "",
            "fans_unit": "",
            "consignee": "",
            "phone": "",
            "address": ""
        }
        
    def connect_to_email(self):
        """Connect to Gmail via IMAP"""
        try:
            print("🔗 Đang kết nối với Gmail...")
            self.mail = imaplib.IMAP4_SSL("imap.gmail.com")
            self.mail.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            print("✅ Kết nối thành công!")
            return True
        except Exception as e:
            print(f"❌ Lỗi kết nối email: {e}")
            return False
    
    def read_emails_from_sender(self, sender_email):
        """Read all emails from a specific sender"""
        try:
            self.mail.select("inbox")
            print(f"📧 Đang tìm email từ: {sender_email}")
            
            # Search for emails from sender
            status, messages = self.mail.search(None, f'FROM "{sender_email}"')
            email_ids = messages[0].split()
            
            if not email_ids:
                print("⚠️ Không tìm thấy email nào từ người gửi này!")
                return ""
            
            print(f"📬 Tìm thấy {len(email_ids)} email(s)")
            
            all_content = ""
            
            # Read all emails
            for email_id in email_ids:
                status, msg_data = self.mail.fetch(email_id, "(RFC822)")
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Get email body
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    all_content += body + "\n"
                        else:
                            body = msg.get_payload(decode=True).decode()
                            all_content += body + "\n"
            
            return all_content
            
        except Exception as e:
            print(f"❌ Lỗi đọc email: {e}")
            return ""
    
    def extract_data(self, email_content):
        """Extract phone number and YouTube link from email content"""
        print("🔍 Đang trích xuất dữ liệu...")
        
        # Extract phone number (10-12 digits)
        phone_pattern = r'\b\d{10,12}\b'
        phone_match = re.search(phone_pattern, email_content)
        if phone_match:
            self.email_data["phone"] = phone_match.group()
            print(f"📞 Số điện thoại: {self.email_data['phone']}")
        
        # Extract YouTube link
        youtube_pattern = r'(?:https?://)?(?:www\.)?youtube\.com[^\s]+'
        youtube_match = re.search(youtube_pattern, email_content)
        if youtube_match:
            self.email_data["link"] = youtube_match.group()
            print(f"🔗 Link YouTube: {self.email_data['link']}")
        
        # You can add more extraction logic here based on your needs
        print(f"✅ Trích xuất hoàn tất!")
        
    def fill_erp_form(self, erp_url):
        """Navigate to ERP and fill the form using Playwright"""
        print("🌐 Đang khởi động trình duyệt...")
        
        with sync_playwright() as p:
            # Launch browser with persistent context to save session
            browser = p.chromium.launch_persistent_context(
                user_data_dir="./user_data",
                headless=False,
                channel="chrome"
            )
            
            page = browser.pages[0] if browser.pages else browser.new_page()
            
            # Navigate to ERP
            print(f"🔗 Đang truy cập: {erp_url}")
            page.goto(erp_url)
            page.wait_for_load_state("networkidle")
            
            # Wait for user to login if needed (first time only)
            print("⏳ Chờ đăng nhập (nếu cần)...")
            time.sleep(3)
            
            # Check if login is needed
            try:
                # If username field exists, fill it
                if page.locator('input[name="username"]').is_visible(timeout=2000):
                    print("🔐 Đang điền tài khoản...")
                    page.fill('input[name="username"]', ERP_USERNAME)
                    print("⚠️ Vui lòng hoàn tất đăng nhập thủ công (OTP nếu có)...")
                    input("Nhấn Enter sau khi đăng nhập xong...")
            except:
                print("✅ Đã đăng nhập từ trước!")
            
            # Navigate to Influencer orders
            print("📋 Đang tìm mục 'Influencer orders'...")
            try:
                # Click on User icon
                page.click('text="User"', timeout=5000)
                time.sleep(1)
                
                # Click on Influencer orders
                page.click('text="Influencer orders"', timeout=5000)
                time.sleep(1)
                
                # Click on Add to button
                page.click('text="Add to"', timeout=5000)
                time.sleep(2)
                
                print("✅ Đã vào form điền thông tin!")
            except Exception as e:
                print(f"⚠️ Không tìm thấy đường dẫn tự động. Vui lòng điều hướng thủ công đến form!")
                input("Nhấn Enter khi đã vào form...")
            
            # Fill the form
            print("📝 Đang điền form...")
            
            try:
                # Fill all available fields
                if self.email_data["name"]:
                    page.fill('input[name="name"]', self.email_data["name"])
                    
                if self.email_data["contact_info"]:
                    page.fill('input[name="contact_info"]', self.email_data["contact_info"])
                    
                if self.email_data["link"]:
                    page.fill('input[name="link"]', self.email_data["link"])
                    
                if self.email_data["fans"]:
                    page.fill('input[name="fans"]', self.email_data["fans"])
                    
                if self.email_data["fans_unit"]:
                    page.fill('input[name="fans_unit"]', self.email_data["fans_unit"])
                    
                if self.email_data["consignee"]:
                    page.fill('input[name="consignee"]', self.email_data["consignee"])
                    
                if self.email_data["phone"]:
                    page.fill('input[name="phone"]', self.email_data["phone"])
                    
                if self.email_data["address"]:
                    page.fill('input[name="address"]', self.email_data["address"])
                
                print("✅ Điền form hoàn tất!")
                print("⚠️ Vui lòng kiểm tra và nhấn Submit thủ công!")
                
            except Exception as e:
                print(f"⚠️ Lỗi điền form: {e}")
                print("Vui lòng điền thủ công!")
            
            # Wait for user to review and submit
            input("Nhấn Enter để đóng trình duyệt...")
            browser.close()

def main():
    print("=" * 50)
    print("🤖 ERP BOT - Email to Form Automation")
    print("=" * 50)
    
    bot = ERPBot()
    
    # Connect to email
    if not bot.connect_to_email():
        return
    
    # Get sender email from user
    sender_email = input("\n📧 Nhập email người gửi (Influencer): ").strip()
    
    # Read emails
    email_content = bot.read_emails_from_sender(sender_email)
    
    if email_content:
        # Extract data
        bot.extract_data(email_content)
        
        # Ask for ERP URL
        erp_url = input("\n🌐 Nhập URL trang ERP: ").strip()
        
        # Fill form
        bot.fill_erp_form(erp_url)
    
    print("\n✅ Hoàn tất!")

if __name__ == "__main__":
    main()