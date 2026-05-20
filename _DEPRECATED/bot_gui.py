#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ERP Bot GUI - Desktop Chat Interface
Modern chat interface for interacting with the ERP automation bot
"""

import customtkinter as ctk
import threading
import imaplib
import email
import re
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import time
from datetime import datetime

# Load environment variables
load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
ERP_USERNAME = os.getenv("ERP_USERNAME")

class ERPBotGUI:
    def __init__(self):
        # Configure theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create main window
        self.root = ctk.CTk()
        self.root.title("🤖 ERP Bot Assistant")
        self.root.geometry("800x600")
        
        # Variables
        self.processing = False
        self.email_data = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Header
        header = ctk.CTkFrame(self.root, height=60, fg_color=("#1a1a1a", "#0d0d0d"))
        header.pack(fill="x", padx=0, pady=0)
        
        title_label = ctk.CTkLabel(
            header, 
            text="🤖 ERP Bot Assistant", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=15)
        
        # Chat area
        chat_frame = ctk.CTkFrame(self.root)
        chat_frame.pack(fill="both", expand=True, padx=20, pady=(10, 0))
        
        # Chat display with scrollbar
        self.chat_display = ctk.CTkTextbox(
            chat_frame,
            font=ctk.CTkFont(size=13),
            wrap="word",
            state="disabled"
        )
        self.chat_display.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Input area
        input_frame = ctk.CTkFrame(self.root)
        input_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.input_field = ctk.CTkEntry(
            input_frame,
            placeholder_text="Nhập lệnh cho bot... (ví dụ: Check mail từ example@mail.com)",
            font=ctk.CTkFont(size=13),
            height=40
        )
        self.input_field.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=10)
        self.input_field.bind("<Return>", lambda e: self.send_message())
        
        self.send_button = ctk.CTkButton(
            input_frame,
            text="Gửi",
            width=100,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.send_message
        )
        self.send_button.pack(side="right", padx=(5, 10), pady=10)
        
        # Welcome message
        self.add_bot_message("Chào bạn! Tôi là ERP Bot Assistant. 🤖\n\nBạn có thể ra lệnh cho tôi như:\n• 'Check mail từ influencer@example.com'\n• 'Điền form ERP với mail từ abc@gmail.com'\n\nTôi sẵn sàng giúp bạn!")
        
    def add_user_message(self, message):
        """Add user message to chat"""
        self.chat_display.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M")
        self.chat_display.insert("end", f"\n[{timestamp}] Bạn:\n{message}\n", "user")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")
        
    def add_bot_message(self, message):
        """Add bot message to chat"""
        self.chat_display.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M")
        self.chat_display.insert("end", f"\n[{timestamp}] Bot:\n{message}\n", "bot")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")
        
    def send_message(self):
        """Handle send button click"""
        message = self.input_field.get().strip()
        
        if not message:
            return
            
        if self.processing:
            self.add_bot_message("⚠️ Tôi đang xử lý yêu cầu trước. Vui lòng đợi...")
            return
        
        # Add user message
        self.add_user_message(message)
        self.input_field.delete(0, "end")
        
        # Process in background thread
        thread = threading.Thread(target=self.process_command, args=(message,))
        thread.daemon = True
        thread.start()
        
    def process_command(self, command):
        """Process user command"""
        self.processing = True
        self.send_button.configure(state="disabled")
        
        try:
            # Parse command
            if "check mail" in command.lower() or "đọc mail" in command.lower():
                # Extract email
                email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
                email_match = re.search(email_pattern, command)
                
                if email_match:
                    sender_email = email_match.group()
                    self.add_bot_message(f"🔍 Đang kiểm tra email từ: {sender_email}")
                    
                    # Read emails
                    content = self.read_emails(sender_email)
                    
                    if content:
                        # Extract data
                        self.extract_data(content)
                        
                        # Ask for ERP URL
                        self.add_bot_message("✅ Đã đọc và trích xuất dữ liệu!\n\nDữ liệu tìm thấy:")
                        if self.email_data.get("phone"):
                            self.add_bot_message(f"📞 Số điện thoại: {self.email_data['phone']}")
                        if self.email_data.get("link"):
                            self.add_bot_message(f"🔗 Link YouTube: {self.email_data['link']}")
                        
                        self.add_bot_message("\nBạn hãy nhập lệnh: 'Điền form ERP tại [URL]' để tôi điền form.")
                    else:
                        self.add_bot_message("❌ Không tìm thấy email nào!")
                else:
                    self.add_bot_message("⚠️ Vui lòng cung cấp địa chỉ email trong lệnh!")
                    
            elif "điền form" in command.lower() or "fill form" in command.lower():
                # Extract URL
                url_pattern = r'https?://[^\s]+'
                url_match = re.search(url_pattern, command)
                
                if url_match:
                    erp_url = url_match.group()
                    self.add_bot_message(f"🌐 Đang mở ERP và điền form tại: {erp_url}")
                    self.fill_form(erp_url)
                else:
                    self.add_bot_message("⚠️ Vui lòng cung cấp URL trong lệnh!")
            else:
                self.add_bot_message("❓ Xin lỗi, tôi chưa hiểu lệnh này. Vui lòng thử:\n• 'Check mail từ [email]'\n• 'Điền form ERP tại [URL]'")
                
        except Exception as e:
            self.add_bot_message(f"❌ Lỗi: {str(e)}")
        finally:
            self.processing = False
            self.send_button.configure(state="normal")
            
    def read_emails(self, sender_email):
        """Read emails from sender"""
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            mail.select("inbox")
            
            status, messages = mail.search(None, f'FROM "{sender_email}"')
            email_ids = messages[0].split()
            
            if not email_ids:
                return ""
            
            all_content = ""
            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    all_content += body + "\n"
                        else:
                            body = msg.get_payload(decode=True).decode()
                            all_content += body + "\n"
            
            mail.close()
            mail.logout()
            return all_content
            
        except Exception as e:
            self.add_bot_message(f"❌ Lỗi kết nối email: {e}")
            return ""
            
    def extract_data(self, email_content):
        """Extract data from email"""
        # Extract phone
        phone_pattern = r'\b\d{10,12}\b'
        phone_match = re.search(phone_pattern, email_content)
        if phone_match:
            self.email_data["phone"] = phone_match.group()
        
        # Extract YouTube link
        youtube_pattern = r'(?:https?://)?(?:www\.)?youtube\.com[^\s]+'
        youtube_match = re.search(youtube_pattern, email_content)
        if youtube_match:
            self.email_data["link"] = youtube_match.group()
            
    def fill_form(self, erp_url):
        """Fill ERP form using Playwright"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir="./user_data",
                    headless=False,
                    channel="chrome"
                )
                
                page = browser.pages[0] if browser.pages else browser.new_page()
                page.goto(erp_url)
                page.wait_for_load_state("networkidle")
                
                time.sleep(2)
                
                # Fill form
                if self.email_data.get("phone"):
                    page.fill('input[name="phone"]', self.email_data["phone"])
                if self.email_data.get("link"):
                    page.fill('input[name="link"]', self.email_data["link"])
                
                self.add_bot_message("✅ Đã điền form! Vui lòng kiểm tra và submit thủ công.")
                
                # Keep browser open
                time.sleep(30)
                browser.close()
                
        except Exception as e:
            self.add_bot_message(f"❌ Lỗi điền form: {e}")
            
    def run(self):
        """Start the application"""
        self.root.mainloop()

def main():
    app = ERPBotGUI()
    app.run()

if __name__ == "__main__":
    main()
