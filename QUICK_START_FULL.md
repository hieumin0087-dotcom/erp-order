# 🚀 ERP Bot - Quick Start Guide

## 📋 Prerequisites

- Python 3.13+
- Gmail account with App Password enabled
- Chrome/Chromium browser

## 🔧 Installation

### Step 1: Install Dependencies

```powershell
cd "c:\Trợ lý AI"
py -m pip install -r requirements.txt
```

### Step 2: Install Playwright Browsers

```powershell
py -m playwright install chromium
```

### Step 3: Configure Environment

1. Copy `.env.example` to `.env`
2. Edit `.env` and fill in your credentials:

```
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
ERP_URL=https://erp.bx123.pro/admin/main
```

## 🎯 Usage

### Basic Usage

```powershell
py bot_erp_full.py
```

Then enter the influencer's email when prompted.

### With Command Line Argument

```powershell
py bot_erp_full.py influencer@example.com
```

## 🔄 Workflow

1. **Email Reading**: Bot connects to Gmail IMAP and reads the latest email from the influencer
2. **Data Extraction**: Parses email content to extract:
   - Channel information (name, platform, link, followers)
   - Contact information (email, phone)
   - Shipping information (name, address, phone)
3. **ERP Automation**: 
   - Opens Chrome to ERP URL
   - Navigates: Influencer Management → Influencer orders → Add
   - Fills all form fields automatically
4. **Manual Review**: Browser stays open for you to review and submit

## 📊 Extracted Data Fields

- `influencer_email` - Email address
- `channel_name` - Channel/account name
- `platform` - youtube/tiktok/instagram
- `channel_link` - Full channel URL
- `followers` - Follower/subscriber count
- `phone` - Phone number (10-12 digits)
- `recipient_name` - Shipping recipient
- `address` - Delivery address
- `city` - City
- `province` - Province/State
- `postal_code` - Postal code
- `country` - Country (default: Vietnam)

## 🎨 Features

✅ **Modular Architecture**: Separate Gmail reader module  
✅ **Robust Parsing**: BeautifulSoup for HTML emails  
✅ **Smart Detection**: Auto-detects platform (YouTube/TikTok/Instagram)  
✅ **Follower Conversion**: Auto-converts to H/K/M units  
✅ **Error Handling**: Detailed logging and graceful failures  
✅ **Manual Fallback**: Prompts for manual input when automation fails  
✅ **Session Persistence**: Saves login session in `user_data/`  

## ⚠️ First Run

On first run, you may need to:
1. Log in to the ERP system manually
2. Complete any 2FA/OTP verification
3. Browser will remember your session for future runs

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'dotenv'"
```powershell
py -m pip install python-dotenv
```

### "ModuleNotFoundError: No module named 'playwright'"
```powershell
py -m pip install playwright
py -m playwright install chromium
```

### "Could not find element"
- The ERP UI may have changed
- Bot will pause and ask you to proceed manually
- Press Enter after completing the step

### Browser doesn't open
```powershell
py -m playwright install chromium
```

## 📁 Project Structure

```
c:\Trợ lý AI\
├── bot_erp_full.py          # Main bot script
├── gmail_reader.py          # Email reading module
├── requirements.txt         # Python dependencies
├── .env                     # Configuration (create from .env.example)
├── .env.example            # Configuration template
├── user_data/              # Browser session data
└── QUICK_START_FULL.md     # This file
```

## 🎓 How It Works

1. **IMAP Connection**: Uses `imaplib` to connect to Gmail
2. **Email Parsing**: Uses `email` + `BeautifulSoup` to extract text from HTML
3. **Regex Extraction**: Finds phone numbers, URLs, follower counts
4. **Browser Automation**: Uses Playwright to control Chrome
5. **Form Filling**: Locates form fields and fills data
6. **Manual Review**: Keeps browser open for final submission

## ✅ Ready to Use!

The bot is production-ready and handles most edge cases gracefully.
