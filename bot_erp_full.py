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

print("ERP AUTO BOT – AI VERSION")

target = input("Influencer email: ").strip()

### ===== LOAD EMAIL =====

mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login(GMAIL, PASS)
mail.select("inbox")

status, data = mail.search(None, f'(FROM "{target}")')
ids = data[0].split()

if not ids:
    print("NO EMAIL FOUND")
    quit()

latest = ids[-1]

status, msg = mail.fetch(latest, "(RFC822)")
raw = msg[0][1]

msg = email.message_from_bytes(raw)

body = ""

if msg.is_multipart():
    for p in msg.walk():
        if p.get_content_type() == "text/plain":
            body += p.get_payload(decode=True).decode()
else:
    body = msg.get_payload(decode=True).decode()

mail.logout()

print("EMAIL LOADED")

### ===== AI EXTRACT =====

client = Groq(api_key=GROQ)

prompt = f"""
Extract shipping + influencer info from email.
Return ONLY valid JSON.

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
   "country":"",
   "phone":""
 }},
 "influencer": {{
   "channel_name":"",
   "platform":"",
   "channel_link":""
 }}
}}
"""

ai = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role":"user","content":prompt}]
)

text = ai.choices[0].message.content.strip()

print("\nAI RAW OUTPUT:\n", text)

text = text[text.find("{"):text.rfind("}")+1]

data = json.loads(text)

print("\nAI DATA LOADED")

### ===== OPEN ERP =====

with sync_playwright() as p:

    browser = p.chromium.launch_persistent_context(
        user_data_dir="C:/erp_profile",
        headless=False
    )

    page = browser.pages[0]

    page.goto(ERP)
    page.wait_for_timeout(3000)

    print("\n👉 LOGIN ERP rồi nhấn ENTER trong terminal")
    input()

    page.goto("https://erp.bx123.pro/celebrityOrder/save")
    page.wait_for_timeout(5000)

    page.fill('input[placeholder*="姓名"]', data["shipping"]["full_name"])
    page.fill('input[placeholder*="电话"]', data["shipping"]["phone"])
    page.fill('input[placeholder*="地址"]', data["shipping"]["address"])
    page.fill('input[placeholder*="城市"]', data["shipping"]["city"])

    print("\n✅ FORM FILLED — bạn kiểm tra rồi submit tay")

    page.wait_for_timeout(60000)
