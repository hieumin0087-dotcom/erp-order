import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

EMAIL_TEXT = """
PASTE NOI DUNG EMAIL INFLUENCER VO DAY
"""

PROMPT = f"""
You are an expert logistics + ecommerce assistant.

Extract shipping and influencer information from this email.

Return JSON ONLY:

{{
  "full_name": "",
  "address": "",
  "city": "",
  "state": "",
  "zip_code": "",
  "country": "",
  "phone": "",
  "product_link": "",
  "channel_name": "",
  "platform": "",
  "channel_link": ""
}}

Rules:
- Understand meaning, not regex
- Never hallucinate
- Missing field = empty string
- Output raw JSON only

EMAIL:
{EMAIL_TEXT}
"""

resp = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": PROMPT}]
)

print(resp.choices[0].message.content)
