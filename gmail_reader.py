#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gmail Reader Module
Reads and parses emails from Gmail via IMAP
"""

import imaplib
import email
from email.header import decode_header
import re
from datetime import datetime
from bs4 import BeautifulSoup


class GmailReader:
    def __init__(self, email_address, app_password):
        self.email_address = email_address
        self.app_password = app_password
        self.mail = None
        
    def connect(self):
        """Connect to Gmail IMAP server"""
        try:
            print("🔗 Connecting to Gmail IMAP...")
            self.mail = imaplib.IMAP4_SSL("imap.gmail.com")
            self.mail.login(self.email_address, self.app_password)
            print("✅ Connected successfully!")
            return True
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def get_latest_email_from_sender(self, sender_email):
        """Get the latest email from a specific sender"""
        try:
            self.mail.select("inbox")
            print(f"📧 Searching for latest email from: {sender_email}")
            
            # Search for emails from sender
            status, messages = self.mail.search(None, f'FROM "{sender_email}"')
            email_ids = messages[0].split()
            
            if not email_ids:
                print("⚠️ No emails found from this sender!")
                return None
            
            # Get the latest email (last in the list)
            latest_email_id = email_ids[-1]
            print(f"📬 Found latest email (ID: {latest_email_id.decode()})")
            
            # Fetch the email
            status, msg_data = self.mail.fetch(latest_email_id, "(RFC822)")
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Get subject
                    subject = self.decode_email_subject(msg["Subject"])
                    print(f"📄 Subject: {subject}")
                    
                    # Get body
                    body = self.get_email_body(msg)
                    
                    return {
                        "subject": subject,
                        "body": body,
                        "from": sender_email
                    }
            
            return None
            
        except Exception as e:
            print(f"❌ Error reading email: {e}")
            return None
    
    def decode_email_subject(self, subject):
        """Decode email subject"""
        if subject is None:
            return ""
        decoded_parts = decode_header(subject)
        subject_parts = []
        for content, encoding in decoded_parts:
            if isinstance(content, bytes):
                subject_parts.append(content.decode(encoding or 'utf-8', errors='ignore'))
            else:
                subject_parts.append(content)
        return ''.join(subject_parts)
    
    def get_email_body(self, msg):
        """Extract email body (text and HTML)"""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" or content_type == "text/html":
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        text = payload.decode(charset, errors='ignore')
                        
                        # If HTML, extract text
                        if content_type == "text/html":
                            soup = BeautifulSoup(text, 'html.parser')
                            text = soup.get_text()
                        
                        body += text + "\n"
                    except Exception as e:
                        print(f"⚠️ Error decoding part: {e}")
        else:
            try:
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='ignore')
                
                # If HTML, extract text
                if msg.get_content_type() == "text/html":
                    soup = BeautifulSoup(body, 'html.parser')
                    body = soup.get_text()
            except Exception as e:
                print(f"⚠️ Error decoding body: {e}")
        
        return body
    
    def close(self):
        """Close IMAP connection"""
        if self.mail:
            self.mail.close()
            self.mail.logout()
            print("🔒 Gmail connection closed")


class EmailParser:
    """Parse influencer information from email content"""
    
    @staticmethod
    def extract_email(text):
        """Extract email address"""
        pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        match = re.search(pattern, text)
        return match.group() if match else ""
    
    @staticmethod
    def extract_phone(text):
        """Extract phone number (10-12 digits)"""
        pattern = r'\b\d{10,12}\b'
        match = re.search(pattern, text)
        return match.group() if match else ""
    
    @staticmethod
    def extract_youtube_link(text):
        """Extract YouTube link"""
        pattern = r'(?:https?://)?(?:www\.)?youtube\.com[^\s]+'
        match = re.search(pattern, text)
        return match.group() if match else ""
    
    @staticmethod
    def extract_tiktok_link(text):
        """Extract TikTok link"""
        pattern = r'(?:https?://)?(?:www\.)?tiktok\.com[^\s]+'
        match = re.search(pattern, text)
        return match.group() if match else ""
    
    @staticmethod
    def extract_instagram_link(text):
        """Extract Instagram link"""
        pattern = r'(?:https?://)?(?:www\.)?instagram\.com[^\s]+'
        match = re.search(pattern, text)
        return match.group() if match else ""
    
    @staticmethod
    def detect_platform(text):
        """Detect social media platform from link"""
        text_lower = text.lower()
        if "youtube" in text_lower:
            return "youtube"
        elif "tiktok" in text_lower:
            return "tiktok"
        elif "instagram" in text_lower:
            return "instagram"
        return "youtube"  # default
    
    @staticmethod
    def parse_influencer_data(email_content, sender_email):
        """Parse all influencer data from email"""
        print("\n🔍 Parsing email content...")
        
        data = {
            "influencer_email": sender_email,
            "channel_name": "",
            "platform": "",
            "channel_link": "",
            "followers": "",
            "recipient_name": "",
            "phone": "",
            "address": "",
            "city": "",
            "province": "",
            "postal_code": "",
            "country": "Vietnam"  # default
        }
        
        # Extract phone
        phone = EmailParser.extract_phone(email_content)
        if phone:
            data["phone"] = phone
            print(f"📞 Phone: {phone}")
        
        # Detect platform and extract link
        youtube_link = EmailParser.extract_youtube_link(email_content)
        tiktok_link = EmailParser.extract_tiktok_link(email_content)
        instagram_link = EmailParser.extract_instagram_link(email_content)
        
        if youtube_link:
            data["platform"] = "youtube"
            data["channel_link"] = youtube_link
            print(f"🔗 YouTube: {youtube_link}")
        elif tiktok_link:
            data["platform"] = "tiktok"
            data["channel_link"] = tiktok_link
            print(f"🔗 TikTok: {tiktok_link}")
        elif instagram_link:
            data["platform"] = "instagram"
            data["channel_link"] = instagram_link
            print(f"🔗 Instagram: {instagram_link}")
        
        # Extract channel name from link if available
        if data["channel_link"]:
            # Try to extract channel name from URL
            parts = data["channel_link"].split("/")
            for part in reversed(parts):
                if part and part not in ["www.youtube.com", "youtube.com", "tiktok.com", "instagram.com"]:
                    data["channel_name"] = part.replace("@", "")
                    print(f"📺 Channel: {data['channel_name']}")
                    break
        
        # Try to extract follower count (numbers with K, M, H suffix)
        follower_patterns = [
            r'(\d+(?:\.\d+)?)\s*[KkMmHh]',  # 100K, 1.5M, 500H
            r'(\d{1,3}(?:,\d{3})*)\s*(?:followers|subscribers|fans)',  # 1,000 followers
        ]
        for pattern in follower_patterns:
            match = re.search(pattern, email_content)
            if match:
                data["followers"] = match.group()
                print(f"👥 Followers: {data['followers']}")
                break
        
        print("✅ Parsing complete!")
        return data
