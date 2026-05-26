#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ERP Data Entry - Manual Input GUI
Save influencer data and auto-fill ERP form in one click
"""

import sys
# Prevent console encoding crashes on Windows due to emojis/unicode
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='ignore')
except Exception:
    pass

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import shutil
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import threading
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import queue
import time

# ── FastAPI local server (bot agent can control via HTTP) ──
try:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse, FileResponse
    from pydantic import BaseModel
    import uvicorn
    try:
        from PIL import ImageGrab
        PILLOW_AVAILABLE = True
    except ImportError:
        PILLOW_AVAILABLE = False
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("⚠️  FastAPI not installed. Bot-agent API disabled.")
    print("    Run: pip install fastapi uvicorn")

load_dotenv()
ERP_URL = os.getenv("ERP_URL", "https://erp.bx123.pro/admin/main")

def scrape_product_info(url):
    """
    Scrape product information from shopping product pages (tikhubs.ru, colestore.ru, etc.)
    Returns: dict with product_name, product_brand, product_sku, product_images
    """
    try:
        print(f"\n🔍 Scraping product from: {url}")
        
        # Fetch page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract product name from H1, og:title, or title
        product_name = ""
        h1 = soup.find('h1')
        og_title = soup.find('meta', property='og:title')
        title_tag = soup.find('title')

        if h1 and h1.get_text(strip=True):
            product_name = h1.get_text(strip=True)
        elif og_title and og_title.get('content'):
            product_name = og_title.get('content', '').replace('\n', ' ').strip()
        elif title_tag and title_tag.get_text(strip=True):
            product_name = title_tag.get_text(strip=True)

        if product_name:
            print(f"✓ Product Name: {product_name}")
        else:
            print("⚠️ Could not find product name, using fallback")
            product_name = "Unknown Product"
        
        # --- INTELLIGENT BRAND EXTRACTION ---
        # Strategy: Extract shop name from URL and skip it if it's the first word of the product name
        domain_match = re.search(r'https?://(?:www\.)?([^./]+)', url)
        shop_name = domain_match.group(1).lower() if domain_match else ""
        
        words = product_name.split()
        if words:
            # If first word is the shop name, use the second word (or more) as brand
            if words[0].lower() == shop_name and len(words) > 1:
                # If first word was shop name, the second word is usually the brand
                # special case for "Louis Vuitton" (take 2 words if possible)
                if len(words) > 2 and words[1].lower() == "louis" and words[2].lower() == "vuitton":
                    product_brand = "Louis Vuitton"
                else:
                    product_brand = words[1]
            else:
                product_brand = words[0]
        else:
            product_brand = ""
            
        print(f"✓ Brand: {product_brand} (Calculated from shop name: {shop_name})")
        
        # Extract SKU/size from product name
        # Strategy: Look for various patterns like "24cm", "30x20cm", "Size 30", or keywords "Small", "Large"
        product_sku = ""
        
        # 1. Look for explicit dimensions (e.g., 24cm, 30x20cm, 18x16x11cm)
        # Matches: "24cm", "18x16x11 cm", "30 x 20 x 10", "30*20"
        dimension_match = re.search(
            r'(\d+(?:\.\d+)?(?:\s*[x*\xd7]\s*\d+(?:\.\d+)?){1,2}\s*(?:cm|mm|inch|")?)',
            product_name, re.IGNORECASE
        )
        
        if dimension_match:
            product_sku = dimension_match.group(1).strip()
            print(f"✓ Found Size (Dimensions): {product_sku}")
            
        # 2. If no dimensions, look for size keywords (Small, Medium, Large, Mini)
        if not product_sku:
            size_keywords = ['Small', 'Medium', 'Large', 'Mini', 'Maxi', 'Nano', 'Jumbo']
            for kw in size_keywords:
                if re.search(rf'\b{kw}\b', product_name, re.IGNORECASE):
                    product_sku = kw
                    print(f"✓ Found Size (Keyword): {product_sku}")
                    break
                    
        # 3. Fallback
        if not product_sku:
            product_sku = "Size/Color/etc"
            print(f"⚠️ Could not extract size, using default SKU")
        
        # Extract product images
        product_images = []
        
        # === UNIVERSAL IMAGE SCRAPER ===
        # Strategy: Try JSON-LD / og:image first, then fall back to <img> scan
        image_urls = []

        # 1. Try og:image (highest quality, most reliable)
        og_imgs = soup.find_all('meta', property='og:image')
        for m in og_imgs:
            src = m.get('content', '')
            if src:
                full_url = urljoin(url, src)
                if full_url not in image_urls:
                    image_urls.append(full_url)

        # 2. Try JSON-LD structured data (e.g. Shopify, WooCommerce)
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                ld = json.loads(script.string or '')
                # Handle list or single object
                ld_list = ld if isinstance(ld, list) else [ld]
                for item in ld_list:
                    imgs = item.get('image', [])
                    if isinstance(imgs, str): imgs = [imgs]
                    if isinstance(imgs, dict): imgs = [imgs.get('url', '')]
                    for img_url in imgs:
                        if img_url and img_url not in image_urls:
                            image_urls.append(urljoin(url, img_url))
            except:
                pass

        # 3. Scan <img> tags as fallback
        if len(image_urls) < 2:
            thumbnails = soup.find_all('img')
            for img in thumbnails:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or ''
                if not src:
                    continue
                # Skip common non-product images
                if any(skip in src.lower() for skip in ['logo', 'icon', 'banner', 'avatar', 'header', 'sprite']):
                    continue
                # Accept any image with a likely product path OR just any jpeg/png/webp
                if any(x in src.lower() for x in ['upload', '/bag', '/product', '/image', '/photo', '/img']) or \
                   any(src.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    width = img.get('width')
                    height = img.get('height')
                    if width and height:
                        try:
                            if int(str(width).replace('px','')) < 100 or int(str(height).replace('px','')) < 100:
                                continue
                        except:
                            pass
                    full_url = urljoin(url, src)
                    if full_url not in image_urls:
                        image_urls.append(full_url)
        
        print(f"✓ Found {len(image_urls)} product images (after filtering)")
        
        # Download FIRST 5 unique images:
        # images[0] = Main image  (Product Main Image)
        # images[1] = Detail 1
        # images[2] = Detail 2
        # images[3] = Detail 3
        # (We need 5 raw image_urls to safely get 4 unique ones after any dups slip through)
        download_dir = "c:/Trợ lý AI/product_images"
        os.makedirs(download_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Normalize URLs to detect near-duplicate (same path, different query params)
        def normalize_url(u):
            return u.split('?')[0].split('#')[0].rstrip('/')
        
        seen_normalized = set()
        unique_image_urls = []
        for u in image_urls:
            norm = normalize_url(u)
            if norm not in seen_normalized:
                seen_normalized.add(norm)
                unique_image_urls.append(u)
        
        print(f"✓ After normalization dedup: {len(unique_image_urls)} unique product images")
        
        seen_content_hashes = set()  # Track MD5 hashes to skip physically duplicate images
        
        for i, original_url in enumerate(unique_image_urls[:5]):
            try:
                print(f"  Processing image {i+1}/4...")
                
                # generate candidates
                candidates = []
                
                # 1. High Quality Hack (!min -> !large)
                if '!' in original_url:
                    hq_url = re.sub(r'![a-zA-Z0-9_-]+\.(?:jpg|png|webp).*$', '!large.jpg', original_url, flags=re.IGNORECASE)
                    if hq_url != original_url:
                        candidates.append(hq_url)
                
                # 2. Clean URL (Universal "Stripper" to find Original)
                # We apply a series of cleanups to try and get the raw URL
                
                clean_url = original_url
                
                # A. Remove !suffix (e.g. !min.jpg, !thumb.jpg)
                clean_url = re.sub(r'![^/]+$', '', clean_url)
                
                # B. Remove query parameters (e.g. ?width=500, ?q=90)
                clean_url = clean_url.split('?')[0]
                
                # C. Remove dimension suffixes before extension (e.g. _800x800.jpg, _50x50.jpg)
                # Matches _123x123 or -123x123 right before the dot of extension
                clean_url = re.sub(r'[_-]\d+[xX]\d+(?=\.[a-zA-Z]+$)', '', clean_url)
                
                # D. Remove generic size/quality suffixes (e.g. _tn, _small, _opt, _optimized)
                common_suffixes = ['_tn', '_small', '_medium', '_large', '_opt', '_optimized', '_thumb', '_min']
                for suffix in common_suffixes:
                    clean_url = re.sub(fr'{suffix}(?=\.[a-zA-Z]+$)', '', clean_url, flags=re.IGNORECASE)
                
                # E. Remove path-based resizing (e.g. /w_500/, /s640/, /h_300/)
                # Cloudinary/Google style: .../image/upload/w_500,h_500/v123...
                clean_url = re.sub(r'/(?:w|h|s|c|q)[_-]?\d+[^/]*/', '/', clean_url)
                
                if clean_url != original_url and clean_url not in candidates:
                    candidates.append(clean_url)
                
                # 3. Original Fallback
                if original_url not in candidates:
                    candidates.append(original_url)
                
                # Try downloading candidates in order
                success = False
                headers = {'User-Agent': 'Mozilla/5.0'}
                
                filename = f"product_{timestamp}_{i+1}.jpg" # Default extension
                filepath = os.path.join(download_dir, filename)
                
                for attempt_url in candidates:
                    try:
                        print(f"    Trying: {attempt_url if len(attempt_url)<60 else attempt_url[:57]+'...'}")
                        resp = requests.get(attempt_url, headers=headers, timeout=10)
                        
                        if resp.status_code == 200:
                            # Check content type for extension
                            if 'image/png' in resp.headers.get('Content-Type', ''):
                                filename = filename.replace('.jpg', '.png')
                            elif 'image/webp' in resp.headers.get('Content-Type', ''):
                                filename = filename.replace('.jpg', '.webp')
                                
                            filepath = os.path.join(download_dir, filename)
                            
                            # --- CONTENT HASH DEDUP ---
                            import hashlib
                            img_hash = hashlib.md5(resp.content).hexdigest()
                            
                            if img_hash in seen_content_hashes:
                                print(f"    ⚠️ Skipping duplicate image (same content as previous)")
                                success = True  # Mark as "handled", just skip
                                break
                            
                            # New unique image - save it
                            seen_content_hashes.add(img_hash)
                            with open(filepath, 'wb') as f:
                                f.write(resp.content)
                            
                            product_images.append(filepath)
                            print(f"    ✓ Downloaded successfully (hash: {img_hash[:8]}...)")
                            success = True
                            break
                        else:
                            print(f"    ✗ Failed (Status {resp.status_code})")
                    except Exception as e:
                        print(f"    ✗ Error: {e}")
                
                if not success:
                    print(f"  ⚠️ Could not download image {i+1} after trying all variants")
                
            except Exception as e:
                print(f"  ⚠️ Unexpected error processing image {i+1}: {e}")
                continue
        
        if len(product_images) == 0:
            print("⚠️ Warning: No images downloaded")
        
        result = {
            "product_name": product_name,
            "product_brand": product_brand,
            "product_sku": product_sku,
            "product_images": product_images
        }
        
        print(f"\n✅ Scraping complete! Got {len(product_images)} images")
        return result
        
    except requests.RequestException as e:
        raise Exception(f"Network error: {str(e)}")
    except Exception as e:
        raise Exception(f"Scraping failed: {str(e)}")

def scrape_social_media(url):
    """
    Scrape social media profile info from YouTube or TikTok
    Returns: dict with profile_picture, channel_name, followers, followers_unit
    """
    try:
        import re  # Ensure re is locally bound to avoid UnboundLocalError with complex scoping
        print(f"\n🔍 Scraping social media from: {url}")
        
        # Detect platform
        platform = None
        if 'youtube.com' in url or 'youtu.be' in url:
            platform = 'youtube'
        elif 'tiktok.com' in url:
            platform = 'tiktok'
        elif 'instagram.com' in url:
            platform = 'instagram'
        else:
            raise Exception("Unsupported platform. Only YouTube, TikTok, and Instagram are supported.")
        
        print(f"✓ Platform: {platform.upper()}")
        
        # ======= INSTAGRAM: Fresh browser context (like incognito) =======
        if platform == 'instagram':
            print("  → Opening Instagram in fresh browser (no bot detection)...")
            with sync_playwright() as p_ig:
                browser = p_ig.chromium.launch(
                    headless=False,  # Non-headless mimics real user
                    args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
                )
                ctx = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    viewport={'width': 1280, 'height': 900},
                )
                ig_page = ctx.new_page()
                # Hide webdriver property (key anti-detection step)
                ig_page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                # Clean URL
                clean_url = url.strip()
                if not clean_url.startswith('http'):
                    clean_url = 'https://' + clean_url
                
                ig_page.goto(clean_url, wait_until='domcontentloaded', timeout=45000)
                ig_page.wait_for_timeout(3000)  # Wait for Instagram JS to render follower counts
                
                result = {"profile_picture": "", "channel_name": "", "followers": "", "followers_unit": "H"}
                
                # === CHANNEL NAME from og:title ===
                try:
                    raw_title = ig_page.evaluate("""
                        () => {
                            const og = document.querySelector('meta[property="og:title"]');
                            return og ? og.content : null;
                        }
                    """)
                    if raw_title:
                        print(f"  Raw title: {raw_title}")
                        # Remove " • Instagram photos and videos" suffix
                        import re as _re
                        clean = _re.sub(r'\s*[•·]\s*Instagram.*$', '', raw_title, flags=_re.IGNORECASE).strip()
                        # Extract username from "(@username)" format
                        pm = _re.search(r'\(@?([\w.]+)\)\s*$', clean)
                        if pm:
                            clean = pm.group(1)
                        elif clean.startswith('(') and clean.endswith(')'):
                            clean = clean[1:-1].lstrip('@')
                        result['channel_name'] = clean
                        print(f"  ✓ Channel Name: {result['channel_name']}")
                except Exception as e:
                    print(f"  ⚠️ Channel name error: {e}")
                
                # === FOLLOWERS from rendered page ===
                try:
                    import re as _re
                    followers_raw = ig_page.evaluate(r"""
                        () => {
                            const spans = Array.from(document.querySelectorAll('span, a'));
                            for (const el of spans) {
                                const title = el.getAttribute('title') || '';
                                const text = (el.innerText || '').trim();
                                const check = title || text;
                                if (/[\d.,]+[KMBkmb]?\s*followers/i.test(check)) return check;
                                if (/[\d.,]+[KMBkmb]?\s*ng.*theo\s*d/i.test(check)) return check;
                            }
                            // Fallback: meta description
                            const d = document.querySelector('meta[name="description"]');
                            return d ? d.content : null;
                        }
                    """)
                    if followers_raw:
                        print(f"  Followers raw: {followers_raw[:100]}")
                        m = _re.search(r'([\d.,]+)\s*([KMBkmb])?\s*(?:followers|ng.*theo)', followers_raw, _re.IGNORECASE)
                        if m:
                            num = m.group(1).replace(',', '.')
                            mult = (m.group(2) or '').upper()
                            try:
                                val = float(num)
                            except:
                                val = 0
                            if mult == 'K':
                                result['followers'] = num
                                result['followers_unit'] = 'K'
                            elif mult == 'M':
                                result['followers'] = str(round(val * 1000, 1))
                                result['followers_unit'] = 'K'
                            else:
                                if val >= 1000:
                                    result['followers'] = str(round(val / 1000, 1))
                                    result['followers_unit'] = 'K'
                                else:
                                    result['followers'] = str(int(val))
                                    result['followers_unit'] = 'H'
                            print(f"  ✓ Followers: {result['followers']} {result['followers_unit']}")
                        else:
                            print("  ⚠️ Could not parse followers from text")
                    else:
                        print("  ⚠️ Could not find followers on page")
                except Exception as e:
                    print(f"  ⚠️ Followers error: {e}")
                
                # === PROFILE PICTURE from og:image ===
                try:
                    pic_url = ig_page.evaluate("""
                        () => {
                            const og = document.querySelector('meta[property="og:image"]');
                            return og ? og.content : null;
                        }
                    """)
                    if pic_url:
                        if pic_url.startswith('//'):
                            pic_url = 'https:' + pic_url
                        print(f"  → Downloading profile picture...")
                        import requests as _req
                        r = _req.get(pic_url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.instagram.com/'}, timeout=15)
                        r.raise_for_status()
                        dl_dir = "c:/Trợ lý AI/profile_pictures"
                        os.makedirs(dl_dir, exist_ok=True)
                        ts = datetime.now().strftime("%Y%m%d%H%M%S")
                        fpath = os.path.join(dl_dir, f"profile_instagram_{ts}.jpg")
                        with open(fpath, 'wb') as f:
                            f.write(r.content)
                        result['profile_picture'] = fpath
                        print(f"  ✓ Profile Picture saved")
                    else:
                        print("  ⚠️ No profile picture found")
                except Exception as e:
                    print(f"  ⚠️ Profile picture error: {e}")
                
                ctx.close()
                browser.close()
            
            print(f"\n✅ Instagram scraping complete!")
            return result
        # ======= END INSTAGRAM =======
        
        # Use Playwright to scrape (YouTube / TikTok)
        with sync_playwright() as p:
            # === USE PERSISTENT PROFILE ===
            # This saves cookies/cache so you don't get CAPTCHA every time
            user_data_dir = "c:/Trợ lý AI/browser_profile"
            os.makedirs(user_data_dir, exist_ok=True)
            
            print(f"  Using persistent profile: {user_data_dir}")
            
            # Launch persistent context
            context = p.chromium.launch_persistent_context(
                user_data_dir,
                headless=False,
                args=[
                    '--start-maximized',
                    '--disable-blink-features=AutomationControlled'
                ],
                viewport=None, # Use actual window size
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            )
            
            page = context.pages[0] # Get the first page
            
            print(f"  Loading page...")
            
            # Clean URL (remove query parameters)
            if '?' in url:
                url = url.split('?')[0]
                print(f"  → Cleaned URL: {url}")

            # TikTok-specific handling
            if platform == 'tiktok':
                print(f"  ⚠️ TikTok may show CAPTCHA - please solve it manually if it appears!")
                try:
                    # Use domcontentloaded instead of networkidle - faster and less prone to hanging
                    page.goto(url, wait_until='domcontentloaded', timeout=60000)
                    print(f"  ✓ Initial DOM loaded")
                    page.wait_for_timeout(5000) # Wait for hydration
                    
                    # Check for CAPTCHA (Only if VISIBLE)
                    try:
                        # Common TikTok CAPTCHA text patterns
                        captcha_locator = page.locator('text=/slider|puzzle|captcha|verify you are human/i')
                        
                        if captcha_locator.count() > 0 and captcha_locator.first.is_visible():
                            print(f"\n  ⚠️ CAPTCHA DETECTED!")
                            print(f"  → Please solve the CAPTCHA in the browser window")
                            print(f"  → After solving, press ENTER in this terminal to continue...")
                            input()  # Wait for user to solve CAPTCHA
                            print(f"  ✓ User confirmed, waiting for verification...")
                            
                            # Wait for "Verifying..." modal to disappear
                            print(f"  → Waiting for TikTok verification to complete...")
                            try:
                                page.wait_for_selector('text=/verifying/i', state='hidden', timeout=30000)
                                print(f"  ✓ Verification complete!")
                            except:
                                pass
                            
                            # Extra wait for page to stabilize
                            page.wait_for_timeout(3000)
                    except Exception as e:
                        # Ignore CAPTCHA check errors
                        pass
                    
                except Exception as e:
                    print(f"  ⚠️ TikTok loading issue: {e}")
            
            elif platform == 'instagram':
                # Instagram public profiles are accessible WITHOUT login
                try:
                    page.goto(url, wait_until='domcontentloaded', timeout=60000)
                    print(f"  ✓ Instagram page loaded")
                    page.wait_for_timeout(1500)  # Short wait - meta tags load fast
                except Exception as e:
                    print(f"  ⚠️ Instagram loading issue: {e}")
            
            else:
                # YouTube - normal loading
                page.goto(url, wait_until='networkidle', timeout=60000)
                page.wait_for_timeout(5000)
            
            # Take screenshot for debugging
            screenshot_path = f"c:/Trợ lý AI/debug_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            page.screenshot(path=screenshot_path)
            print(f"  ✓ Screenshot saved: {screenshot_path}")
            
            result = {
                "profile_picture": "",
                "channel_name": "",
                "followers": "",
                "followers_unit": "H"
            }
            
            if platform == 'youtube':
                # Extract YouTube channel info
                
                # === CHANNEL NAME ===
                try:
                    print("\n  DEBUG: Finding channel name...")
                    channel_name = None
                    
                    # Method 1: Use JavaScript to get from page title or meta
                    try:
                        js_code = """
                        (() => {
                            // Try meta tags first
                            const metaName = document.querySelector('meta[property="og:title"]');
                            if (metaName) return metaName.content;
                            
                            // Try page title
                            const title = document.title;
                            if (title && !title.includes('YouTube')) {
                                return title.replace(' - YouTube', '').trim();
                            }
                            
                            // Try ytInitialData
                            if (window.ytInitialData) {
                                const header = window.ytInitialData.header?.c4TabbedHeaderRenderer;
                                if (header?.title) return header.title;
                            }
                            
                            return null;
                        })()
                        """
                        channel_name = page.evaluate(js_code)
                        if channel_name:
                            print(f"    ✓ Found via JavaScript")
                    except:
                        pass
                    
                    # Method 2: Try CSS selectors as fallback
                    if not channel_name:
                        selectors_to_try = [
                            'yt-formatted-string#text.ytd-channel-name',
                            'ytd-channel-name yt-formatted-string',
                            '#channel-name #text',
                            'ytd-channel-name #text'
                        ]
                        
                        for selector in selectors_to_try:
                            try:
                                elem = page.locator(selector).first
                                channel_name = elem.inner_text(timeout=2000)
                                if channel_name and channel_name.strip():
                                    print(f"    ✓ Found with selector: {selector}")
                                    break
                            except:
                                pass
                    
                    if channel_name:
                        result['channel_name'] = channel_name.strip()
                        print(f"  ✓ Channel Name: {result['channel_name']}")
                    else:
                        print("  ⚠️ Could not extract channel name")
                except Exception as e:
                    print(f"  ⚠️ Channel name error: {e}")
                
                # Subscribers count - try multiple selectors
                try:
                    # DEBUG: Print all elements containing "người đăng ký" or "subscriber"
                    print("\n  DEBUG: Finding all subscriber elements...")
                    all_sub_elems = page.locator('text=/người đăng ký|subscriber/i').all()
                    for idx, elem in enumerate(all_sub_elems[:5]):  # Only first 5
                        try:
                            elem_text = elem.inner_text(timeout=1000)
                            print(f"    [{idx}] {elem_text}")
                        except:
                            pass
                    
                    sub_text = None
                    try:
                        # Try yt-formatted-string with subscriber info
                        sub_elem = page.locator('yt-formatted-string#subscriber-count').first
                        sub_text = sub_elem.inner_text(timeout=5000)
                    except:
                        try:
                            # Alternative: look for span with id="subscriber-count"
                            sub_elem = page.locator('span#subscriber-count').first
                            sub_text = sub_elem.inner_text(timeout=5000)
                        except:
                            try:
                                # Look for text containing "subscriber" or "người đăng ký" (Vietnamese)
                                sub_elem = page.locator('text=/subscriber|người đăng ký/i').first
                                sub_text = sub_elem.inner_text(timeout=5000)
                            except:
                                pass
                    
                    if sub_text:
                        print(f"\n  ✓ Raw subscriber text: {sub_text}")
                        
                        # Parse "7,16 N người đăng ký" (Vietnamese) or "716K subscribers" (English)
                        import re
                        # Match patterns like: "7,16 N", "716K", "2.62K", "2,62K", etc.
                        match = re.search(r'([\d.,]+)\s*([NKMB])?', sub_text, re.IGNORECASE)
                        if match:
                            count_str = match.group(1).replace(',', '.')
                            multiplier = match.group(2)
                            
                            print(f"  → Parsed: number='{count_str}', multiplier='{multiplier}'")
                            
                            count_val = float(count_str)
                            
                            # Handle multipliers (N = K in Vietnamese)
                            if multiplier:
                                multiplier_upper = multiplier.upper()
                                if multiplier_upper == 'K' or multiplier_upper == 'N':  # N = nghìn = K
                                    result['followers'] = count_str
                                    result['followers_unit'] = 'K'
                                elif multiplier_upper == 'M':
                                    result['followers'] = str(count_val * 1000)
                                    result['followers_unit'] = 'K'
                                elif multiplier_upper == 'B':  # Billion
                                    result['followers'] = str(count_val * 1000000)
                                    result['followers_unit'] = 'K'
                            else:
                                # No multiplier, raw number
                                if count_val < 1000:
                                    result['followers'] = str(int(count_val))
                                    result['followers_unit'] = 'H'
                                else:
                                    result['followers'] = str(round(count_val / 1000, 2))
                                    result['followers_unit'] = 'K'
                            
                            print(f"  ✓ Subscribers: {result['followers']} {result['followers_unit']}")
                        else:
                            print(f"  ⚠️ Could not parse subscriber count from: {sub_text}")
                    else:
                        print("  ⚠️ Could not find subscriber element")
                except Exception as e:
                    print(f"  ⚠️ Subscriber extraction error: {e}")
                
                # === PROFILE PICTURE ===
                try:
                    print("\n  DEBUG: Finding profile picture...")
                    img_url = None
                    
                    # Method 1: Use JavaScript to get from ytInitialData with detailed debugging
                    try:
                        js_code = """
                        (() => {
                            console.log('=== DEBUG: Profile Picture Search ===');
                            
                            // Method 1: Try ytInitialData
                            if (window.ytInitialData) {
                                console.log('✓ ytInitialData exists');
                                const header = window.ytInitialData.header;
                                console.log('Header types:', Object.keys(header || {}));
                                
                                // Try c4TabbedHeaderRenderer
                                if (header?.c4TabbedHeaderRenderer) {
                                    const renderer = header.c4TabbedHeaderRenderer;
                                    console.log('c4TabbedHeaderRenderer keys:', Object.keys(renderer));
                                    
                                    if (renderer.avatar?.thumbnails) {
                                        const thumbnails = renderer.avatar.thumbnails;
                                        console.log('Found thumbnails:', thumbnails.length);
                                        const url = thumbnails[thumbnails.length - 1]?.url;
                                        if (url) {
                                            console.log('✓ Avatar URL from ytInitialData:', url);
                                            return url;
                                        }
                                    }
                                }
                                
                                // Try pageHeaderRenderer
                                if (header?.pageHeaderRenderer) {
                                    const renderer = header.pageHeaderRenderer;
                                    if (renderer.content?.pageHeaderViewModel?.image?.decoratedAvatarViewModel?.avatar?.avatarViewModel?.image?.sources) {
                                        const sources = renderer.content.pageHeaderViewModel.image.decoratedAvatarViewModel.avatar.avatarViewModel.image.sources;
                                        if (sources.length > 0) {
                                            const url = sources[sources.length - 1]?.url;
                                            if (url) {
                                                console.log('✓ Avatar URL from pageHeaderRenderer:', url);
                                                return url;
                                            }
                                        }
                                    }
                                }
                            }
                            
                            // Method 2: Search all images on page
                            console.log('Searching all images...');
                            const imgs = Array.from(document.querySelectorAll('img'));
                            console.log('Total images found:', imgs.length);
                            
                            const ytImages = imgs.filter(img => img.src && img.src.includes('yt3.ggpht.com'));
                            console.log('YouTube CDN images:', ytImages.length);
                            
                            if (ytImages.length > 0) {
                                const url = ytImages[0].src;
                                console.log('✓ Avatar URL from image search:', url);
                                return url;
                            }
                            
                            console.log('✗ No avatar found');
                            return null;
                        })()
                        """
                        img_url = page.evaluate(js_code)
                        if img_url:
                            print(f"    ✓ Found via JavaScript: {img_url[:80]}...")
                    except Exception as e:
                        print(f"    ⚠️ JavaScript error: {e}")
                    
                    # Method 2: Try CSS selectors as fallback
                    if not img_url:
                        print("    → Trying CSS selectors...")
                        selectors_to_try = [
                            'img#img',
                            'yt-img-shadow img',
                            'ytd-c4-tabbed-header-renderer img',
                            'img[src*="yt3.ggpht.com"]',
                            '#avatar img'
                        ]
                        
                        for selector in selectors_to_try:
                            try:
                                img_elem = page.locator(selector).first
                                img_url = img_elem.get_attribute('src', timeout=2000)
                                if img_url and 'http' in img_url:
                                    print(f"    ✓ Found with selector: {selector}")
                                    break
                            except:
                                pass
                    
                    if img_url and 'http' in img_url:
                        # Handle protocol-relative URLs
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        
                        # Download profile picture
                        print(f"  → Downloading from: {img_url[:60]}...")
                        import requests
                        headers = {'User-Agent': 'Mozilla/5.0'}
                        img_response = requests.get(img_url, headers=headers, timeout=10)
                        img_response.raise_for_status()
                        
                        # Save
                        download_dir = "c:/Trợ lý AI/profile_pictures"
                        os.makedirs(download_dir, exist_ok=True)
                        
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        filename = f"profile_{platform}_{timestamp}.jpg"
                        filepath = os.path.join(download_dir, filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(img_response.content)
                        
                        result['profile_picture'] = filepath
                        print(f"  ✓ Profile Picture: {filename}")
                    else:
                        print("  ⚠️ Could not find profile picture URL")
                except Exception as e:
                    print(f"  ⚠️ Profile picture error: {e}")
            
            elif platform == 'tiktok':
                # Extract TikTok profile info
                print("\n  DEBUG: Extracting TikTok data...")
                
                # === CHANNEL NAME ===
                try:
                    print("  → Finding channel name...")
                    channel_name = None
                    selectors = [
                        'h2[data-e2e="user-title"]',
                        'h1[data-e2e="user-title"]',
                        'h2.tiktok-username',
                        '[data-e2e="user-subtitle"]'
                    ]
                    
                    for selector in selectors:
                        try:
                            elem = page.locator(selector).first
                            channel_name = elem.inner_text(timeout=3000)
                            if channel_name:
                                print(f"    ✓ Found with: {selector}")
                                break
                        except:
                            pass
                    
                    if channel_name:
                        result['channel_name'] = channel_name.strip()
                        print(f"  ✓ Channel Name: {result['channel_name']}")
                    else:
                        print("  ⚠️ Could not extract channel name")
                except Exception as e:
                    print(f"  ⚠️ Channel name error: {e}")
                
                # === FOLLOWERS COUNT ===
                try:
                    print("  → Finding followers count...")
                    followers_text = None
                    selectors = [
                        'strong[data-e2e="followers-count"]',
                        'strong[title*="Followers"]',
                        '[data-e2e="followers-count"]'
                    ]
                    
                    for selector in selectors:
                        try:
                            elem = page.locator(selector).first
                            followers_text = elem.inner_text(timeout=3000)
                            if followers_text:
                                print(f"    ✓ Found with: {selector}")
                                break
                        except:
                            pass
                    
                    if followers_text:
                        print(f"    Raw: {followers_text}")
                        # Parse "160.5M" or "2.6K"
                        import re
                        match = re.search(r'([\d.,]+)\s*([KMB])?', followers_text, re.IGNORECASE)
                        if match:
                            count_str = match.group(1).replace(',', '.')
                            multiplier = match.group(2)
                            count_val = float(count_str)
                            
                            if multiplier:
                                if multiplier.upper() == 'K':
                                    result['followers'] = count_str
                                    result['followers_unit'] = 'K'
                                elif multiplier.upper() == 'M':
                                    result['followers'] = str(count_val * 1000)
                                    result['followers_unit'] = 'K'
                                elif multiplier.upper() == 'B':
                                    result['followers'] = str(count_val * 1000000)
                                    result['followers_unit'] = 'K'
                            else:
                                if count_val < 1000:
                                    result['followers'] = str(int(count_val))
                                    result['followers_unit'] = 'H'
                                else:
                                    result['followers'] = str(round(count_val / 1000, 2))
                                    result['followers_unit'] = 'K'
                            
                            print(f"  ✓ Followers: {result['followers']} {result['followers_unit']}")
                    else:
                        print("  ⚠️ Could not find followers count")
                except Exception as e:
                    print(f"  ⚠️ Followers error: {e}")
                
                # === PROFILE PICTURE ===
                try:
                    print("  → Finding profile picture...")
                    img_url = None
                    
                    # Method 1: Meta Tag (Most Reliable)
                    try:
                        js_code = """
                        (() => {
                            // Try Open Graph image first
                            const ogImg = document.querySelector('meta[property="og:image"]');
                            if (ogImg && ogImg.content) return ogImg.content;
                            
                            // Try twitter image
                            const twImg = document.querySelector('meta[name="twitter:image"]');
                            if (twImg && twImg.content) return twImg.content;
                            
                            return null;
                        })()
                        """
                        img_url = page.evaluate(js_code)
                        if img_url:
                            print(f"    ✓ Found via Meta Tag")
                    except:
                        pass
                    
                    # Method 2: Strict CSS selectors (Only if meta tag fails)
                    if not img_url:
                        selectors = [
                            'img[data-e2e="user-avatar"]',  # Best selector
                            'div[data-e2e="user-avatar"] img',
                            'span[data-e2e="user-avatar"] img'
                        ]
                        
                        for selector in selectors:
                            try:
                                elem = page.locator(selector).first
                                if elem.is_visible():
                                    img_url = elem.get_attribute('src', timeout=2000)
                                    if img_url and 'http' in img_url:
                                        print(f"    ✓ Found with: {selector}")
                                        break
                            except:
                                pass
                    
                    if img_url:
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        
                        print(f"  → Downloading from: {img_url[:60]}...")
                        import requests
                        
                        # TikTok CDN requires Referer header usually
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                            'Referer': 'https://www.tiktok.com/'
                        }
                        
                        # Increase timeout to 30s
                        img_response = requests.get(img_url, headers=headers, timeout=30)
                        img_response.raise_for_status()
                        
                        download_dir = "c:/Trợ lý AI/profile_pictures"
                        os.makedirs(download_dir, exist_ok=True)
                        
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        filename = f"profile_{platform}_{timestamp}.jpg"
                        filepath = os.path.join(download_dir, filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(img_response.content)
                        
                        result['profile_picture'] = filepath
                        print(f"  ✓ Profile Picture: {filename}")
                    else:
                        print("  ⚠️ Could not find profile picture")
                except Exception as e:
                    print(f"  ⚠️ Profile picture error: {e}")
            # (Instagram is handled separately above with its own fresh context)
            
            context.close()
        
        print(f"\n✅ Social media scraping complete!")
        return result
        
    except Exception as e:
        raise Exception(f"Social media scraping failed: {str(e)}")

class DataEntryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📝 ERP Data Entry - Manual Input")
        self.root.geometry("700x800")
        self.root.configure(bg="#f0f0f0")
        
        # Main container - split into form (left) and history (right)
        container = tk.Frame(self.root, bg="#f0f0f0")
        container.pack(fill="both", expand=True)
        
        # LEFT SIDE: Form
        main_frame = tk.Frame(container, bg="#f0f0f0")
        main_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        # RIGHT SIDE: History Panel
        history_frame = tk.Frame(container, bg="#E3F2FD", width=300)
        history_frame.pack(side="right", fill="both", padx=10, pady=10)
        history_frame.pack_propagate(False)
        
        # History Title
        tk.Label(
            history_frame,
            text="📜 History",
            font=("Segoe UI", 14, "bold"),
            bg="#E3F2FD",
            fg="#1976D2"
        ).pack(pady=10)
        
        # History Listbox with Scrollbar
        list_frame = tk.Frame(history_frame, bg="#E3F2FD")
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar_hist = tk.Scrollbar(list_frame)
        scrollbar_hist.pack(side="right", fill="y")
        
        self.history_listbox = tk.Listbox(
            list_frame,
            font=("Segoe UI", 9),
            bg="white",
            selectmode=tk.SINGLE,
            yscrollcommand=scrollbar_hist.set
        )
        self.history_listbox.pack(side="left", fill="both", expand=True)
        scrollbar_hist.config(command=self.history_listbox.yview)
        
        # History Buttons
        hist_btn_frame = tk.Frame(history_frame, bg="#E3F2FD")
        hist_btn_frame.pack(pady=10)
        
        tk.Button(
            hist_btn_frame,
            text="📂 Load",
            font=("Segoe UI", 10, "bold"),
            bg="#4CAF50",
            fg="white",
            command=self.load_from_history,
            cursor="hand2"
        ).pack(side="left", padx=5)
        
        tk.Button(
            hist_btn_frame,
            text="🔄 Resubmit",
            font=("Segoe UI", 10, "bold"),
            bg="#FF9800",
            fg="white",
            command=self.resubmit_from_history,
            cursor="hand2"
        ).pack(side="left", padx=5)
        
        tk.Button(
            hist_btn_frame,
            text="🗑️ Delete",
            font=("Segoe UI", 10, "bold"),
            bg="#F44336",
            fg="white",
            command=self.delete_from_history,
            cursor="hand2"
        ).pack(side="left", padx=5)
        
        # Load history
        self.load_history_list()
        
        # Title
        title = tk.Label(
            main_frame,
            text="📝 Influencer Order Data Entry",
            font=("Segoe UI", 18, "bold"),
            bg="#f0f0f0",
            fg="#333"
        )
        title.pack(pady=(0, 20))
        
        # Create scrollable frame
        canvas = tk.Canvas(main_frame, bg="#f0f0f0")
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f0f0f0")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Fields dictionary
        self.fields = {}
        
        # INFLUENCER INFORMATION
        self.create_section(scrollable_frame, "👤 Influencer Information")
        
        self.fields['nickname'] = self.create_field(scrollable_frame, "Nickname / Channel Name *", "Enter channel name")
        # Updated Contact Type list based on user request (Removed WeChat, added others)
        self.fields['contact_type'] = self.create_dropdown(scrollable_frame, "Contact Type *", 
            ["Please select a contact type....", "WhatsApp", "Email", "Phone", "Instagram", "Snapchat", "TikTok", "Other"])
        self.fields['contact_type'].set("Email")
        self.fields['contact_info'] = self.create_field(scrollable_frame, "Contact Information *", "influencer@example.com")
        self.fields['cooperation_date'] = self.create_field(scrollable_frame, "Cooperation Date", datetime.now().strftime("%Y-%m-%d"))
        self.fields['cooperation_status'] = self.create_dropdown(scrollable_frame, "Cooperation Status", 
            ["Please select a cooperation status....", "New Internet Celebrity", "Old Internet Celebrity"])
        self.fields['cooperation_status'].set("New Internet Celebrity")
        self.fields['influencer_quality'] = self.create_dropdown(scrollable_frame, "Influencer Quality",
            ["Unknown", "High", "Medium", "Low"])
        self.fields['contact_email'] = self.create_field(scrollable_frame, "Contact Email *", "influencer@example.com")
        
        # Profile Picture
        self.create_section(scrollable_frame, "🖼️ Profile Picture")
        self.fields['profile_picture'] = self.create_file_picker(scrollable_frame, "Profile Picture", "Choose image file")
        
        # SOCIAL INFORMATION
        self.create_section(scrollable_frame, "📱 Social Media Information")
        
        self.fields['platform'] = self.create_dropdown(scrollable_frame, "Platform *", ["Youtube", "TikTok", "Instagram", "Facebook"])
        self.fields['channel_name'] = self.create_field(scrollable_frame, "Channel Name *", "Enter channel name")
        
        # Channel Link with Auto Fill button
        link_frame = tk.Frame(scrollable_frame, bg="#f0f0f0")
        link_frame.pack(fill="x", pady=5)
        
        tk.Label(
            link_frame,
            text="Channel Link *",
            font=("Segoe UI", 10),
            bg="#f0f0f0",
            fg="#333",
            width=25,
            anchor="w"
        ).pack(side="left")
        
        self.fields['channel_link'] = tk.Entry(
            link_frame,
            font=("Segoe UI", 10)
        )
        self.fields['channel_link'].pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.fields['channel_link'].insert(0, "https://youtube.com/...")
        self.fields['channel_link'].config(fg='gray')
        self.fields['channel_link'].bind('<FocusIn>', lambda e: self._clear_placeholder(e, "https://youtube.com/..."))
        self.fields['channel_link'].bind('<FocusOut>', lambda e: self._restore_placeholder(e, "https://youtube.com/..."))
        
        # Auto Fill Button
        tk.Button(
            link_frame,
            text="🔍 Auto Fill",
            font=("Segoe UI", 9, "bold"),
            bg="#9C27B0",
            fg="white",
            padx=10,
            cursor="hand2",
            command=self.auto_fill_social_info
        ).pack(side="left", padx=(0, 10))
        
        self.fields['followers'] = self.create_field(scrollable_frame, "Followers Count *", "100")
        self.fields['followers_unit'] = self.create_dropdown(scrollable_frame, "Followers Unit *", ["H", "K", "M"])
        
        # SHIPPING INFORMATION
        self.create_section(scrollable_frame, "📦 Delivery Information")
        
        # Email Reader for Auto-Fill
        email_frame = tk.Frame(scrollable_frame, bg="#E3F2FD", padx=10, pady=10)
        email_frame.pack(fill="x", pady=(0, 10))
        
        email_label = tk.Label(
            email_frame,
            text="📧 Auto-fill from Email:",
            font=("Segoe UI", 10, "bold"),
            bg="#E3F2FD",
            fg="#1976D2"
        )
        email_label.pack(anchor="w", pady=(0, 5))
        
        email_input_frame = tk.Frame(email_frame, bg="#E3F2FD")
        email_input_frame.pack(fill="x")
        
        read_btn = tk.Button(
            email_input_frame,
            text="📧 Read Email",
            font=("Segoe UI", 9, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=15,
            cursor="hand2",
            command=self.read_email_and_fill
        )
        read_btn.pack(side="right", padx=5)
        
        self.email_reader_input = tk.Entry(
            email_input_frame,
            font=("Segoe UI", 10),
            width=25
        )
        self.email_reader_input.insert(0, "Enter influencer email and press Enter...")
        self.email_reader_input.pack(side="left", fill="x", expand=True, padx=5)
        
        # Bind Enter key
        self.email_reader_input.bind('<Return>', lambda e: self.read_email_and_fill())
        
        info_label = tk.Label(
            email_frame,
            text="💡 Enter email address and press Enter to auto-fill delivery info",
            font=("Segoe UI", 8, "italic"),
            bg="#E3F2FD",
            fg="#666"
        )
        info_label.pack(anchor="w", pady=(5, 0))
        
        # Delivery fields
        self.fields['consignee'] = self.create_field(scrollable_frame, "Recipient Name *", "Full name")
        self.fields['phone'] = self.create_field(scrollable_frame, "Phone Number *", "0123456789")
        self.fields['country'] = self.create_field(scrollable_frame, "Country *", "Vietnam")
        self.fields['province'] = self.create_field(scrollable_frame, "Province / State *", "Ho Chi Minh")
        self.fields['city'] = self.create_field(scrollable_frame, "City *", "District 1")
        self.fields['address'] = self.create_text_field(scrollable_frame, "Detailed Address *", "Street, building, etc.")
        self.fields['postal_code'] = self.create_field(scrollable_frame, "Postal Code", "700000")
        
        # PRODUCT INFORMATION
        self.create_section(scrollable_frame, "🛍️ Product Information")
        
        # Product Link with Auto Fill button
        link_frame = tk.Frame(scrollable_frame, bg="#f0f0f0")
        link_frame.pack(fill="x", pady=5)
        
        tk.Label(
            link_frame,
            text="Product Link *",
            font=("Segoe UI", 10),
            bg="#f0f0f0",
            fg="#333",
            width=25,
            anchor="w"
        ).pack(side="left")
        
        self.fields['product_link'] = tk.Entry(
            link_frame,
            font=("Segoe UI", 10)
        )
        self.fields['product_link'].pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.fields['product_link'].insert(0, "https://example.com/product")
        self.fields['product_link'].config(fg='gray')
        self.fields['product_link'].bind('<FocusIn>', lambda e: self._clear_placeholder(e, "https://example.com/product"))
        self.fields['product_link'].bind('<FocusOut>', lambda e: self._restore_placeholder(e, "https://example.com/product"))
        
        # Auto Fill Button
        tk.Button(
            link_frame,
            text="🔍 Auto Fill",
            font=("Segoe UI", 9, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=10,
            cursor="hand2",
            command=self.auto_fill_product_info
        ).pack(side="left", padx=(0, 10))
        
        self.fields['product_name'] = self.create_field(scrollable_frame, "Product Name *", "Product title")
        self.fields['product_brand'] = self.create_field(scrollable_frame, "Brand *", "Brand name")
        self.fields['product_type'] = self.create_dropdown(scrollable_frame, "Product Type *", ["bag", "shoes", "accessories"])
        self.fields['product_sku'] = self.create_field(scrollable_frame, "Product SKU *", "Size/Color/etc")
        
        # Product Main Image
        self.fields['product_main_image'] = self.create_file_picker(scrollable_frame, "Product Main Image *", "Select main product image")
        
        # Product Detail Images (up to 3)
        self.fields['product_detail_image_1'] = self.create_file_picker(scrollable_frame, "Detail Image 1", "Optional detail image 1")
        self.fields['product_detail_image_2'] = self.create_file_picker(scrollable_frame, "Detail Image 2", "Optional detail image 2")
        self.fields['product_detail_image_3'] = self.create_file_picker(scrollable_frame, "Detail Image 3", "Optional detail image 3")
        
        # ORDER NOTE (Promotion Effect Note)
        self.create_section(scrollable_frame, "📝 Order Note")
        default_note = "Influ agreed to collaborate and will create a video showcasing the gift on their channel after receiving the package. Our information will also be included in the video description"
        self.fields['order_note'] = self.create_text_field(scrollable_frame, "Order Note (效果备注)", default_note)
        
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # MOUSE WHEEL SCROLLING - Works anywhere in the window
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind to canvas
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Also bind to scrollable_frame and all its children
        def bind_mousewheel(widget):
            widget.bind("<MouseWheel>", on_mousewheel)
            for child in widget.winfo_children():
                bind_mousewheel(child)
        
        bind_mousewheel(scrollable_frame)
        
        # Buttons
        btn_frame = tk.Frame(main_frame, bg="#f0f0f0")
        btn_frame.pack(pady=20)
        
        save_btn = tk.Button(
            btn_frame,
            text="💾 Save Data",
            font=("Segoe UI", 12, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=30,
            pady=10,
            cursor="hand2",
            command=self.save_data
        )
        save_btn.pack(side="left", padx=5)
        
        clear_btn = tk.Button(
            btn_frame,
            text="🗑️ Clear All",
            font=("Segoe UI", 12),
            bg="#f44336",
            fg="white",
            padx=30,
            pady=10,
            cursor="hand2",
            command=self.clear_all
        )
        clear_btn.pack(side="left", padx=5)
        
        load_btn = tk.Button(
            btn_frame,
            text="📂 Load Last",
            font=("Segoe UI", 12),
            bg="#2196F3",
            fg="white",
            padx=30,
            pady=10,
            cursor="hand2",
            command=self.load_data
        )
        load_btn.pack(side="left", padx=5)
        
        # API processing state
        self.active_tasks = 0

        # --- Playwright Thread-Safety Bridge ---
        # All browser commands MUST run in this dedicated thread
        self.browser_queue = queue.Queue()
        self.pw_thread = threading.Thread(target=self._browser_worker_loop, daemon=True)
        self.pw_thread.start()

        # Placeholders for worker thread state
        self.pw_instance = None
        self.browser_ctx = None
        self.active_page = None

    def _browser_worker_loop(self):
        """Dedicated thread for ALL playwright operations to avoid thread safety errors."""
        print("🧵 Browser worker thread started.")
        with sync_playwright() as p:
            self.pw_instance = p
            while True:
                try:
                    # Wait for a command (task)
                    task = self.browser_queue.get()
                    action = task.get('action')
                    
                    if action == 'init':
                        # Launch or return existing page
                        if not self.browser_ctx:
                            print("🚀 Launching persistent browser context...")
                            self.browser_ctx = self.pw_instance.chromium.launch_persistent_context(
                                user_data_dir="C:/erp_profile",
                                headless=False
                            )
                            self.active_page = self.browser_ctx.pages[0] if self.browser_ctx.pages else self.browser_ctx.new_page()
                        task['response_queue'].put(self.active_page)
                        
                    elif action == 'fill_form':
                        # Execute the full form filling logic
                        # (We'll call the original method here, but it's now running in THIS thread)
                        self._execute_fill_form_on_thread(task['data'])
                        task['response_queue'].put(True)
                        
                    elif action == 'screenshot':
                        if self.active_page:
                            print("📷 Worker: Taking live screenshot...")
                            self.active_page.screenshot(path="last_browser_state.png")
                        task['response_queue'].put(True)
                        
                    elif action == 'scrape_social':
                        print(f"🔍 Worker: Scraping social from {task['url']}")
                        result = scrape_social_media(task['url'])
                        task['response_queue'].put(result)
                        
                    elif action == 'close':
                        if self.browser_ctx:
                            self.browser_ctx.close()
                            self.browser_ctx = None
                            self.active_page = None
                            print("🛑 Browser context closed.")
                        task['response_queue'].put(True)
                        
                    self.browser_queue.task_done()
                except Exception as e:
                    print(f"💥 Browser Worker Error: {e}")
                    if 'response_queue' in task:
                        task['response_queue'].put(e)

    def _execute_fill_form_on_thread(self, data):
        """Internal method to fill form, must only be called by the browser worker thread."""
        # This will be the renamed original fill_form logic
        # (I'll move the logic here in the next step)
        pass

    def create_section(self, parent, title):
        """Create section header"""
        frame = tk.Frame(parent, bg="#f0f0f0")
        frame.pack(fill="x", pady=(15, 5))
        
        label = tk.Label(
            frame,
            text=title,
            font=("Segoe UI", 14, "bold"),
            bg="#f0f0f0",
            fg="#1976D2"
        )
        label.pack(anchor="w")
        
        separator = tk.Frame(frame, height=2, bg="#1976D2")
        separator.pack(fill="x", pady=5)
        
    def create_field(self, parent, label_text, placeholder=""):
        """Create input field"""
        frame = tk.Frame(parent, bg="#f0f0f0")
        frame.pack(fill="x", pady=5)
        
        label = tk.Label(
            frame,
            text=label_text,
            font=("Segoe UI", 10),
            bg="#f0f0f0",
            fg="#333",
            width=25,
            anchor="w"
        )
        label.pack(side="left")
        
        entry = tk.Entry(
            frame,
            font=("Segoe UI", 10),
            width=40
        )
        entry.insert(0, placeholder)
        entry.pack(side="left", padx=10, fill="x", expand=True)
        
        return entry
    
    def create_text_field(self, parent, label_text, placeholder=""):
        """Create multi-line text field"""
        frame = tk.Frame(parent, bg="#f0f0f0")
        frame.pack(fill="x", pady=5)
        
        label = tk.Label(
            frame,
            text=label_text,
            font=("Segoe UI", 10),
            bg="#f0f0f0",
            fg="#333",
            width=25,
            anchor="w"
        )
        label.pack(side="left", anchor="n")
        
        text = tk.Text(
            frame,
            font=("Segoe UI", 10),
            width=40,
            height=3
        )
        text.insert("1.0", placeholder)
        text.pack(side="left", padx=10, fill="x", expand=True)
        
        return text
    
    def create_dropdown(self, parent, label_text, options):
        """Create dropdown field"""
        frame = tk.Frame(parent, bg="#f0f0f0")
        frame.pack(fill="x", pady=5)
        
        label = tk.Label(
            frame,
            text=label_text,
            font=("Segoe UI", 10),
            bg="#f0f0f0",
            fg="#333",
            width=25,
            anchor="w"
        )
        label.pack(side="left")
        
        # REMOVED StringVar - it interferes with .set() method
        dropdown = ttk.Combobox(
            frame,
            values=options,
            font=("Segoe UI", 10),
            width=37,
            state="readonly"
        )
        dropdown.current(0)  # Set default to first option
        dropdown.pack(side="left", padx=10, fill="x", expand=True)
        
        return dropdown
    
    def create_file_picker(self, parent, label_text, placeholder=""):
        """Create file picker field"""
        frame = tk.Frame(parent, bg="#f0f0f0")
        frame.pack(fill="x", pady=5)
        
        label = tk.Label(
            frame,
            text=label_text,
            font=("Segoe UI", 10),
            bg="#f0f0f0",
            fg="#333",
            width=25,
            anchor="w"
        )
        label.pack(side="left")
        
        entry = tk.Entry(
            frame,
            font=("Segoe UI", 10),
            width=30
        )
        entry.insert(0, placeholder)
        entry.pack(side="left", padx=5)
        
        def browse_file():
            filename = filedialog.askopenfilename(
                title="Select Profile Picture",
                filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif"), ("All files", "*.*")]
            )
            if filename:
                entry.delete(0, "end")
                entry.insert(0, filename)
        
        browse_btn = tk.Button(
            frame,
            text="📁 Browse",
            font=("Segoe UI", 9),
            bg="#2196F3",
            fg="white",
            padx=10,
            cursor="hand2",
            command=browse_file
        )
        browse_btn.pack(side="left", padx=5)
        
        return entry
    
    def _clear_placeholder(self, event, placeholder):
        """Clear placeholder text on focus"""
        widget = event.widget
        if widget.get() == placeholder:
            widget.delete(0, "end")
            widget.config(fg='black')
    
    def _restore_placeholder(self, event, placeholder):
        """Restore placeholder text if empty"""
        widget = event.widget
        if not widget.get():
            widget.insert(0, placeholder)
            widget.config(fg='gray')
    
    def auto_fill_product_info(self, silent=False):
        """Auto-fill product information from any product URL"""
        try:
            # Get URL
            url = self.fields['product_link'].get().strip()
            
            # Check if placeholder or empty
            if url == "https://example.com/product" or not url or not url.startswith('http'):
                if not silent:
                    messagebox.showerror("Error", "❌ Please enter a valid product URL first!")
                return
            
            # Show loading message (only in manual mode)
            if not silent:
                messagebox.showinfo("Scraping", "🔍 Fetching product information...\n\nPlease wait...")

            # Run scraper in background thread
            self.active_tasks += 1
            thread = threading.Thread(target=self._scrape_and_fill_thread, args=(url, silent))
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            if not silent:
                messagebox.showerror("Error", f"Failed to start scraping:\n{str(e)}")
            else:
                print(f"Failed to start scraping: {e}")
            self.active_tasks -= 1
    
    def _scrape_and_fill_thread(self, url, silent=False):
        """Background thread to scrape product"""
        try:
            # Scrape product info
            info = scrape_product_info(url)
            
            # Update UI in main thread
            self.root.after(0, lambda: self._populate_product_fields(info))
            self.active_tasks -= 1
            
        except Exception as e:
            error_msg = str(e)
            if not silent:
                self.root.after(0, lambda: messagebox.showerror("Scraping Failed", f"❌ {error_msg}\n\nPlease check the URL and try again."))
            else:
                print(f"Scraping Failed for {url}: {error_msg}")
            
            # Clear placeholders so it doesn't submit literally 'Product title' to ERP
            def clear_placeholders():
                for f in ['product_name', 'product_brand', 'product_sku']:
                    if self.fields.get(f) and self.fields[f].get().strip() in ["Product title", "Brand name", "Size/Color/etc"]:
                        self.fields[f].delete(0, 'end')
            self.root.after(0, clear_placeholders)
            self.active_tasks -= 1
    
    def _populate_product_fields(self, info):
        """Populate Product Information fields with scraped data"""
        try:
            # Fill Product Name
            if info.get('product_name'):
                self.fields['product_name'].delete(0, 'end')
                self.fields['product_name'].insert(0, info['product_name'])
                self.fields['product_name'].config(fg='black')
            
            # Fill Brand
            if info.get('product_brand'):
                self.fields['product_brand'].delete(0, 'end')
                self.fields['product_brand'].insert(0, info['product_brand'])
                self.fields['product_brand'].config(fg='black')
            
            # Fill SKU
            if info.get('product_sku'):
                self.fields['product_sku'].delete(0, 'end')
                self.fields['product_sku'].insert(0, info['product_sku'])
                self.fields['product_sku'].config(fg='black')
            
            # Fill images
            images = info.get('product_images', [])
            
            if len(images) >= 1:
                # Main image
                self.fields['product_main_image'].config(state='normal')
                self.fields['product_main_image'].delete(0, 'end')
                self.fields['product_main_image'].insert(0, images[0])
                self.fields['product_main_image'].config(state='disabled')
            
            if len(images) >= 2:
                # Detail image 1
                self.fields['product_detail_image_1'].config(state='normal')
                self.fields['product_detail_image_1'].delete(0, 'end')
                self.fields['product_detail_image_1'].insert(0, images[1])
                self.fields['product_detail_image_1'].config(state='disabled')
            
            if len(images) >= 3:
                # Detail image 2
                self.fields['product_detail_image_2'].config(state='normal')
                self.fields['product_detail_image_2'].delete(0, 'end')
                self.fields['product_detail_image_2'].insert(0, images[2])
                self.fields['product_detail_image_2'].config(state='disabled')
            
            if len(images) >= 4:
                # Detail image 3
                self.fields['product_detail_image_3'].config(state='normal')
                self.fields['product_detail_image_3'].delete(0, 'end')
                self.fields['product_detail_image_3'].insert(0, images[3])
                self.fields['product_detail_image_3'].config(state='disabled')
            
            # Success message
            msg = f"✅ Auto-filled successfully!\n\n"
            msg += f"• Product: {info.get('product_name', 'N/A')}\n"
            msg += f"• Brand: {info.get('product_brand', 'N/A')}\n"
            msg += f"• SKU: {info.get('product_sku', 'N/A')}\n"
            msg += f"• Images: {len(images)}/4 downloaded"
            
            print(f"DEBUG: {msg}")
            # Only show messagebox if NOT in automated flow (though we don't have a silent flag here yet, 
            # we can decide based on context if we really wanted to. For now, popups are okay at the END)
            # messagebox.showinfo("Success", msg)

            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to populate fields:\n{str(e)}")
    
    def auto_fill_social_info(self, silent=False):
        """Auto-fill social media information from YouTube/TikTok URL"""
        try:
            # Get URL
            url = self.fields['channel_link'].get().strip()
            
            # Check if placeholder
            if url == "https://youtube.com/..." or not url:
                if not silent:
                    messagebox.showerror("Error", "❌ Please enter a valid YouTube or TikTok URL first!")
                return
            
            # Validate platform
            if 'youtube.com' not in url and 'youtu.be' not in url and 'tiktok.com' not in url and 'instagram.com' not in url:
                if not silent:
                    messagebox.showwarning("Warning", "⚠️ Only YouTube, TikTok, and Instagram URLs are supported.")
                return
            
            # Show loading message
            if not silent:
                messagebox.showinfo("Scraping", "🔍 Fetching channel information...\n\nThis may take 10-15 seconds.\nPlease wait...")

            
            # Run scraper in background thread
            self.active_tasks += 1
            thread = threading.Thread(target=self._scrape_and_fill_social_thread, args=(url, silent))
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            if not silent:
                messagebox.showerror("Error", f"Failed to start scraping:\n{str(e)}")
            else:
                print(f"Failed to start social scraping: {e}")
            self.active_tasks -= 1
    
    def _scrape_and_fill_social_thread(self, url, silent=False):
        """Background thread to scrape social media - runs in its OWN thread with its own Playwright context.
        IMPORTANT: Do NOT dispatch to browser_queue! That thread already owns a sync_playwright() context.
        Nesting another sync_playwright() inside the same thread causes a fatal crash."""
        try:
            # Run scrape_social_media directly in this thread (not via browser_queue)
            # This gives it its own isolated Playwright context
            info = scrape_social_media(url)
            
            if isinstance(info, Exception):
                raise info
            
            # Update UI in main thread
            self.root.after(0, lambda: self._populate_social_fields(info))
            self.active_tasks -= 1
            
        except Exception as e:
            error_msg = str(e)
            if not silent:
                self.root.after(0, lambda: messagebox.showerror("Scraping Failed", f"❌ {error_msg}\n\nPlease check the URL and try again."))
            else:
                print(f"Social Scraping Failed for {url}: {error_msg}")
            self.active_tasks -= 1
    
    def _populate_social_fields(self, info):
        """Populate Social Media Information fields with scraped data"""
        try:
            # Fill Channel Name
            if info.get('channel_name'):
                self.fields['channel_name'].delete(0, 'end')
                self.fields['channel_name'].insert(0, info['channel_name'])
                self.fields['channel_name'].config(fg='black')
                
                # SYNC TO TOP SECTION: Nickname / Channel Name
                if 'nickname' in self.fields:
                    self.fields['nickname'].delete(0, 'end')
                    self.fields['nickname'].insert(0, info['channel_name'])
            
            # Fill Followers Count
            if info.get('followers'):
                self.fields['followers'].delete(0, 'end')
                self.fields['followers'].insert(0, info['followers'])
                self.fields['followers'].config(fg='black')
            
            # Set Followers Unit
            if info.get('followers_unit'):
                self.fields['followers_unit'].set(info['followers_unit'])
            
            # Fill Profile Picture
            if info.get('profile_picture'):
                self.fields['profile_picture'].config(state='normal')
                self.fields['profile_picture'].delete(0, 'end')
                self.fields['profile_picture'].insert(0, info['profile_picture'])
                self.fields['profile_picture'].config(state='disabled')
            
            # Success message
            print(f"✅ Social Auto-filled: {info.get('channel_name', 'N/A')} ({info.get('followers', 'N/A')} {info.get('followers_unit', '')})")
            
        except Exception as e:
            print(f"Error populating social fields: {e}")
    
    def lookup_influencer_link(self, email_to_find):
        """Lookup social link from 2 fixed Google Sheets by email"""
        if not email_to_find:
            return None
            
        print(f"\n🔍 Searching for email '{email_to_find}' in GSheets...")
        
        # Spreadsheet ID and GIDs from direct links (Case-specific: u vs U)
        SHEET_ID = "1Lx1hyB59VHuLPJBuf_908XIDyhF-JoFG2l95q2Zp0k4"
        GIDS = ["1162923450", "517784804"] 
        
        import csv
        import requests
        from io import StringIO
        
        for gid in GIDS:
            try:
                # Use CSV export URL
                url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                # Parse CSV
                f = StringIO(response.text)
                reader = csv.reader(f)
                
                # Skip header
                header = next(reader, None)
                
                # Column A (index 0) = Email, Column G (index 6) = Link
                for row in reader:
                    if len(row) > 6:
                        row_email = row[0].strip().lower()
                        if row_email == email_to_find.lower():
                            link = row[6].strip()
                            if link:
                                print(f"✅ Found link in GSheet (GID {gid}): {link}")
                                return link
                
            except Exception as e:
                print(f"⚠️ GSheet lookup error (GID {gid}): {e}")
                
        print("❌ Email not found in GSheets.")
        return None

    def verify_and_complete_address(self, shipping_data):
        """Verify and complete address using smart detection"""
        try:
            import re
            from groq import Groq
            
            # Normalize common synonyms to standard keys
            if shipping_data:
                if "state" in shipping_data and not shipping_data.get("province"):
                    shipping_data["province"] = shipping_data["state"]
                if "zip" in shipping_data and not shipping_data.get("postal_code"):
                    shipping_data["postal_code"] = shipping_data["zip"]
                if "zip_code" in shipping_data and not shipping_data.get("postal_code"):
                    shipping_data["postal_code"] = shipping_data["zip_code"]
                if "consignee" in shipping_data and not shipping_data.get("name"):
                    shipping_data["name"] = shipping_data["consignee"]
                if "recipient" in shipping_data and not shipping_data.get("name"):
                    shipping_data["name"] = shipping_data["recipient"]
                if "phone_number" in shipping_data and not shipping_data.get("phone"):
                    shipping_data["phone"] = shipping_data["phone_number"]
                if "contact_number" in shipping_data and not shipping_data.get("phone"):
                    shipping_data["phone"] = shipping_data["contact_number"]
                if "detailed_address" in shipping_data and not shipping_data.get("address"):
                    shipping_data["address"] = shipping_data["detailed_address"]
            
            # US STATE MAPPING (common abbreviations)
            US_STATES = {
                'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
                'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
                'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
                'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
                'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
                'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
                'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
                'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
                'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
                'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
                'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
                'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
                'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia'
            }
            
            CANADA_PROVINCES = {
                'AB': 'Alberta', 'BC': 'British Columbia', 'MB': 'Manitoba', 'NB': 'New Brunswick',
                'NL': 'Newfoundland and Labrador', 'NS': 'Nova Scotia', 'NT': 'Northwest Territories',
                'NU': 'Nunavut', 'ON': 'Ontario', 'PE': 'Prince Edward Island', 'QC': 'Quebec',
                'SK': 'Saskatchewan', 'YT': 'Yukon'
            }
            
            CITY_TO_STATE = {
                'charlotte': 'North Carolina',
                'new york': 'New York',
                'los angeles': 'California',
                'chicago': 'Illinois',
                'houston': 'Texas',
                'phoenix': 'Arizona',
                'philadelphia': 'Pennsylvania',
                'san antonio': 'Texas',
                'san diego': 'California',
                'dallas': 'Texas',
                'miami': 'Florida',
                'atlanta': 'Georgia',
                'boston': 'Massachusetts',
                'seattle': 'Washington',
                'denver': 'Colorado',
                'las vegas': 'Nevada'
            }
            
            postal = str(shipping_data.get('postal_code', '')).strip().upper()
            province = str(shipping_data.get('province', '')).strip()
            city = str(shipping_data.get('city', '')).strip()
            
            # RULE 0: Detect CANADA Postal Code (Format: A1A 1A1 or A1A-1A1)
            # This must take priority over +1 phone code (which defaults to USA)
            is_canada_format = re.match(r'^[A-Z]\d[A-Z][ -]?\d[A-Z]\d$', postal)
            
            if is_canada_format:
                shipping_data['country'] = 'Canada'
                print(f"✓ Detected Country: Canada (via Postal Code format)")
                
                # Expand Province Abbreviation (ON -> Ontario (ON))
                prov_upper = province.upper().strip()
                if prov_upper in CANADA_PROVINCES:
                    full_name = CANADA_PROVINCES[prov_upper]
                    # Format as requested: "Ontario (ON)"
                    shipping_data['province'] = f"{full_name} ({prov_upper})"
                    print(f"✓ Expanded Province: {prov_upper} → {shipping_data['province']}")
            
            # RULE 1: Detect US ZIP code (5 digits or 5+4 format)
            # CAUTION: Many countries use 5 digits (France, Germany, Thailand, etc.)
            # Only default to USA if Country is NOT already detected/set (and not Canada)
            is_us_format = re.match(r'^\d{5}(-?\d{4})?$', postal)
            current_country = shipping_data.get('country', '').lower()
            
            if is_us_format:
                # If country is empty or unknown, assume USA as fallback
                if not current_country or current_country in ['unknown', '']:
                     shipping_data['country'] = 'USA'
                     print(f"✓ Assumed Country: USA (via 5-digit Zip, context was empty)")
                # If it's explicitly NOT USA (e.g. France), do not overwrite!
                
                # Logic for State expansion if we think it is USA
                if shipping_data.get('country') == 'USA':
                    # If province looks wrong (like "Ho Chi Minh"), try to find correct state
                    if province.lower() in ['ho chi minh', 'vietnam', 'hanoi', 'saigon', '']:
                        # Try to find state from city name
                        if city in CITY_TO_STATE:
                            shipping_data['province'] = CITY_TO_STATE[city]
                            print(f"✓ Fixed: {city.title()} → {CITY_TO_STATE[city]}")
                        else:
                            # Use AI to determine state
                            shipping_data = self._ai_verify_us_address(shipping_data, postal, city)
            
            # RULE 2: Check if province is US state abbreviation
            if province.upper() in US_STATES:
                shipping_data['province'] = US_STATES[province.upper()]
                shipping_data['country'] = 'USA'
                print(f"✓ Expanded: {province.upper()} → {US_STATES[province.upper()]}")
            
            # RULE 4: Comprehensive Country Detection via Phone Prefix
            phone = str(shipping_data.get('phone', '')).strip()
            # Remove spaces, dashes, parentheses for checking
            clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
            
            COUNTRY_CODES = {
                '+1': 'USA', '001': 'USA',
                '+44': 'United Kingdom', '0044': 'United Kingdom',
                '+84': 'Vietnam', '0084': 'Vietnam',
                '+86': 'China', '0086': 'China',
                '+81': 'Japan', '0081': 'Japan',
                '+82': 'South Korea', '0082': 'South Korea',
                '+61': 'Australia', '0061': 'Australia',
                '+33': 'France', '0033': 'France',
                '+49': 'Germany', '0049': 'Germany',
                '+39': 'Italy', '0039': 'Italy',
                '+34': 'Spain', '0034': 'Spain',
                '+7': 'Russia',
                '+55': 'Brazil',
                '+91': 'India',
                '+62': 'Indonesia',
                '+60': 'Malaysia',
                '+63': 'Philippines',
                '+65': 'Singapore',
                '+66': 'Thailand'
            }
            
            # Check phone prefix ONLY if country is not already detected
            # (Don't let +1 overwrite 'Canada' if AI already found 'Canada')
            current_country = shipping_data.get('country', '').strip()
            
            if not current_country or current_country.lower() in ['unknown', '']:
                for prefix, country_name in COUNTRY_CODES.items():
                    if clean_phone.startswith(prefix):
                        shipping_data['country'] = country_name
                        print(f"✓ Detected Country: {country_name} (via Phone Prefix {prefix})")
                        break
            
            # RULE 5: UK Postcode format check
            uk_postcode_pattern = r'^[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}$'
            if re.match(uk_postcode_pattern, postal, re.IGNORECASE) and shipping_data.get('country') != 'United Kingdom':
                 shipping_data['country'] = 'United Kingdom'
                 print(f"✓ Detected Country: United Kingdom (via Postcode format)")

            # RULE 6: SAFETY CHECK - Remove US States if Country is UK/Vietnam/etc
            current_country = shipping_data.get('country', '').lower()
            current_province = shipping_data.get('province', '')
            
            # List of specific US states that often get hallucinated
            us_states_names = list(US_STATES.values()) + ['Texas', 'California', 'New York', 'Florida']
            
            if 'united kingdom' in current_country or 'uk' in current_country:
                # If province is a US state name, clear it
                if current_province in us_states_names:
                    print(f"⚠️ Removed invalid Province '{current_province}' for UK address")
                    shipping_data['province'] = '' 
                    # Optional: Could try to infer correct UK county here if we had a map
            
            # RULE 3: Vietnam postal codes
            elif re.match(r'^\d{6}$', postal):
                if not shipping_data.get('country') or shipping_data.get('country').lower() in ['vietnam', 'unknown']:
                    shipping_data['country'] = 'Vietnam'
            
            return shipping_data
            
        except Exception as e:
            print(f"Address verification error: {e}")
            return shipping_data
    
    def _ai_verify_us_address(self, shipping_data, postal, city):
        """Use AI to verify US address when hardcoded rules don't work"""
        try:
            from groq import Groq
            GROQ = os.getenv("GROQ_API_KEY")
            
            if not GROQ:
                return shipping_data
            
            client = Groq(api_key=GROQ)
            
            prompt = f"""
You are a US address expert. Given this US address, determine the correct STATE.

Address info:
- City: {city}
- ZIP Code: {postal}

Return ONLY the state name (full name, not abbreviation).
Example: "North Carolina" NOT "NC"

If you don't know, return "Unknown"
"""
            
            ai = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"user","content":prompt}],
                temperature=0,
                max_tokens=50
            )
            
            state = ai.choices[0].message.content.strip().strip('"\'')
            
            if state and state != "Unknown":
                shipping_data['province'] = state
                print(f"✓ AI found: {city.title()}, {postal} → {state}")
            
        except Exception as e:
            print(f"AI verification error: {e}")
        
        return shipping_data
    
    def read_email_and_fill(self, silent=False):
        """Main entry point to read emails and auto-fill ALL info (Threaded)"""
        email_address = self.email_reader_input.get().strip()
        
        # Clear placeholder text
        if "Enter" in email_address or "press" in email_address:
            if not silent:
                messagebox.showwarning("Email Required", "Please enter an email address!")
            return
            
        if not email_address or "@" not in email_address:
            if not silent:
                messagebox.showwarning("Invalid Email", "Please enter a valid email address!")
            return
            
        # UI Feedback
        self.email_reader_input.config(state="disabled")
        print(f"\n📧 STARTING COMPLETE AUTOMATION FOR: {email_address} (Silent: {silent})")
        self.active_tasks += 1
        
        # Start thread
        thread = threading.Thread(target=self._read_email_thread, args=(email_address, silent))
        thread.daemon = True
        thread.start()

    def _read_email_thread(self, email_address, silent=False):
        """Background thread for the complete email-to-filling workflow"""
        try:
            import imaplib
            import email
            from email.header import decode_header
            
            GMAIL = os.getenv("GMAIL_ADDRESS")
            PASS = os.getenv("GMAIL_APP_PASSWORD")
            GOOGLE_API = os.getenv("GOOGLE_API_KEY")
            
            if not GMAIL or not PASS:
                if not silent:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Gmail credentials not found!"))
                else:
                    print("Error: Gmail credentials not found!")
                return
                
            # 1. READ EMAIL DATA
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(GMAIL, PASS)
            mail.select("inbox")
            
            # Search for emails from the influencer
            status_from, data_from = mail.search(None, f'(FROM "{email_address}")')
            ids_from = data_from[0].split() if data_from[0] else []
            
            # Search for emails sent to the influencer
            status_to, data_to = mail.search(None, f'(TO "{email_address}")')
            ids_to = data_to[0].split() if data_to[0] else []
            
            # Combine, deduplicate, and sort numerically to maintain chronological order
            all_ids = set(ids_from + ids_to)
            ids = sorted(list(all_ids), key=lambda x: int(x))
            
            if not ids:
                msg = f"No emails found from or to {email_address}"
                if not silent:
                    self.root.after(0, lambda: messagebox.showwarning("Not Found", msg))
                else:
                    print(msg)
                self.root.after(0, lambda: self.email_reader_input.config(state="normal"))
                self.active_tasks -= 1
                return
                
            all_body = ""
            email_count = min(len(ids), 35)  # Scan up to 35 emails in the thread
            
            extracted_product_link = ""
            import re as _re
            
            prod_regex = _re.compile(
                r'https?://[^\s<>"]*?(?:colestore\.ru|bags-store\.ru|tikhubs\.ru|bags-store\.com)/[^\s<>"]*?(?:bags|shoes|product|\.html)[^\s<>"]*',
                _re.IGNORECASE
            )
            
            # --- OPTIMIZED CONTENT EXTRACTION ---
            def clean_html(html_content):
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html_content, "html.parser")
                    # Remove script and style elements
                    for script_or_style in soup(["script", "style"]):
                        script_or_style.extract()
                    return soup.get_text(separator=' ', strip=True)
                except:
                    return _re.sub('<[^<]+?>', '', html_content)

            fetched_emails = []
            for email_id in ids[-email_count:]:
                try:
                    status, msg = mail.fetch(email_id, "(RFC822)")
                    raw = msg[0][1]
                    msg = email.message_from_bytes(raw)
                    
                    # Decode subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")
                    
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                try:
                                    body += part.get_payload(decode=True).decode('utf-8', 'ignore')
                                except: pass
                            elif content_type == "text/html" and not body:
                                try:
                                    html_content = part.get_payload(decode=True).decode('utf-8', 'ignore')
                                    body += clean_html(html_content)
                                except: pass
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode('utf-8', 'ignore')
                            if msg.get_content_type() == "text/html":
                                body = clean_html(body)
                        except: pass
                    
                    # Search for detailed product link locally in this email body (scans all 35 emails)
                    if not extracted_product_link:
                        match = prod_regex.search(body)
                        if match:
                            extracted_product_link = match.group(0)
                            print(f"🎯 Local pre-scan found product link: {extracted_product_link}")
                    
                    # Clean up HTML elements in the general text if any slipped through
                    if '<div' in body or '<table' in body or '<body' in body:
                        body = clean_html(body)
                        
                    clean_text = f"\n--- EMAIL SUBJECT: {subject} ---\n{body}\n"
                    fetched_emails.append(clean_text)
                except Exception as e:
                    print(f"Error reading email {email_id}: {e}")
            
            mail.logout()
            
            # Keep only the latest 5 emails for AI shipping extraction to save massive tokens
            ai_emails = fetched_emails[-5:]
            all_body = "".join(ai_emails)
            
            if len(all_body) > 25000:
                all_body = all_body[-25000:]

            print(f"📄 EMAIL BODY (first 2000 chars):\n{all_body[:2000]}\n---")
            
            # 2. AI PARSING
            prompt = f"""
You are an expert logistics coordinator. Extract the shipping/delivery information from the email content below.
Also search for any Product Link (e.g. tikhubs.ru, colestore.ru, bags-store.ru, or any influencer chosen bag link) mentioned in the text.

ALL EMAILS FROM/TO {email_address}:
{all_body}

RULES:
1. Extract: name, phone, address, city, province (state/county), postal_code, country.
2. If province is missing but you know it from the city (e.g. Scranton -> Pennsylvania), fill it in.
3. Do NOT strip domains or protocols from the product link. Extract the absolute URL exactly as written in the email.
4. PRODUCT LINK: Find the specific product details URL (e.g., containing '/bags/', '/shoes/', '/product/', or ending in '.html') chosen by the influencer. NEVER extract the home page URL (e.g., https://www.colestore.ru/ or https://www.tikhubs.ru/) if a specific product details URL is available in any email in the thread.
5. If NO specific product link or product URL is found in the email text, you MUST leave the "product_link" field completely empty (""). DO NOT invent, hallucinate, or make up a product link under any circumstances! DO NOT use generic example URLs.
6. Return ONLY valid JSON.

JSON FORMAT:
{{
  "name": "",
  "phone": "",
  "address": "",
  "city": "",
  "province": "",
  "postal_code": "",
  "country": "",
  "product_link": "",
  "channel_link": ""
}}
"""
            # 2. AI EXTRACTION
            GOOGLE_API = os.getenv("GOOGLE_API_KEY")
            GROQ = os.getenv("GROQ_API_KEY")
            text = ""
            
            if GOOGLE_API:
                # Restored the model name that was working: gemini-flash-latest
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GOOGLE_API}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}], 
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048}
                }
                try:
                    r = requests.post(url, json=payload, timeout=25)
                    data = r.json()
                    if 'candidates' in data:
                        text = data['candidates'][0]['content']['parts'][0]['text']
                    else:
                        print(f"Gemini issue: {data}")
                except Exception as e:
                    print(f"Gemini Request failed: {e}")

            if not text and GROQ:
                print("⚠️ Switching to Groq fallback...")
                try:
                    from groq import Groq
                    client = Groq(api_key=GROQ)
                    ai = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role":"user","content":prompt}],
                        temperature=0.1,
                        max_tokens=2048
                    )
                    text = ai.choices[0].message.content.strip()
                except Exception as e:
                    print(f"Groq failed: {e}")

            if not text:
                raise ValueError("Could not extract data. Please check API keys.")

            # --- ROBUST JSON RECOVERY ---
            import re as _re
            shipping_data = {}
            try:
                # Strip markdown code fences
                text_clean = text
                if "```json" in text_clean:
                    text_clean = text_clean.split("```json")[1].split("```")[0]
                elif "```" in text_clean:
                    text_clean = text_clean.split("```")[1].split("```")[0]
                text_clean = text_clean.strip()

                start = text_clean.find("{")
                end = text_clean.rfind("}") + 1
                if start == -1:
                    raise ValueError("No JSON object found in response")
                json_str = text_clean[start:end]

                # Fix common AI JSON mistakes
                json_str = _re.sub(r",(\s*[}\]])", r"\1", json_str)
                json_str = _re.sub(r":\s*'([^']*)'", r': "\1"', json_str)

                shipping_data = json.loads(json_str, strict=False)
                print(f"JSON parsed OK. Keys: {list(shipping_data.keys())}")

            except Exception as jse:
                print(f"JSON Parse failed ({jse}), using regex fallback.")
                # FIXED REGEX: matches BOTH "key":"string" AND "key": 1234 (unquoted numbers)
                def get_val(key):
                    # Quoted string
                    m = _re.search(r'"' + key + r'"\s*:\s*"([^"]*)"', text)
                    if m: return m.group(1).strip()
                    # Unquoted number (phone, postal_code etc)
                    m = _re.search(r'"' + key + r'"\s*:\s*([0-9][^\s,}\]"]+)', text)
                    if m: return m.group(1).strip()
                    return ""

                shipping_data = {
                    "name":         get_val("name"),
                    "phone":        get_val("phone"),
                    "address":      get_val("address"),
                    "city":         get_val("city"),
                    "province":     get_val("province"),
                    "postal_code":  get_val("postal_code"),
                    "country":      get_val("country"),
                    "product_link": get_val("product_link"),
                    "channel_link": get_val("channel_link"),
                }
                print(f"Regex fallback got: { {k:v for k,v in shipping_data.items() if v} }")

            # ---- DIRECT EMAIL BODY FALLBACK ----
            # If AI/regex missed any shipping field, scan the email body directly
            def _body_find(patterns):
                for pat in patterns:
                    m = _re.search(pat, all_body, _re.IGNORECASE | _re.MULTILINE)
                    if m: return m.group(1).strip()
                return ""

            if not shipping_data.get("phone"):
                shipping_data["phone"] = _body_find([
                    r'(?:phone|mobile|cell|tel)[^\d\n]*[:\-]?\s*\+?([0-9][\d\s\-\(\)\.]{6,18})',
                    r'\b(\+?1?\s*\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4})\b',
                ])

            if not shipping_data.get("name") and not shipping_data.get("consignee"):
                shipping_data["name"] = _body_find([
                    r'(?:name|recipient|consignee|ship\s*to)\s*[:\-]+\s*([A-Z][a-zA-Z\s]{2,40})',
                ])

            if not shipping_data.get("address"):
                shipping_data["address"] = _body_find([
                    r'(?:address|street|addr)\s*[:\-]+\s*([0-9]+[^\n,]{5,80})',
                    r'\b(\d+\s+[A-Z][a-zA-Z\s]{3,50}(?:Dr|St|Ave|Blvd|Rd|Ln|Way|Ct|Pl|Trail)\.?)\b',
                ])

            if not shipping_data.get("city"):
                shipping_data["city"] = _body_find([
                    r'(?:city|town)\s*[:\-]+\s*([A-Za-z][a-zA-Z\s]{2,30})',
                ])

            if not shipping_data.get("province") and not shipping_data.get("state"):
                shipping_data["province"] = _body_find([
                    r'(?:state|province|region)\s*[:\-]+\s*([A-Za-z][a-zA-Z\s]{2,30})',
                ])

            if not shipping_data.get("postal_code") and not shipping_data.get("zip"):
                shipping_data["postal_code"] = _body_find([
                    r'(?:zip|postal|postcode)\s*[:\-]+\s*([0-9]{4,10})',
                    r'\b([0-9]{5}(?:-[0-9]{4})?)\b',
                ])

            if not shipping_data.get("country"):
                shipping_data["country"] = _body_find([
                    r'(?:country)\s*[:\-]+\s*([A-Za-z][a-zA-Z\s]{2,30})',
                ])
                if not shipping_data.get("country"):
                    if _re.search(r'\b\d{5}\b', all_body) and _re.search(r'\b(?:USA|US|United States|America)\b', all_body, _re.I):
                        shipping_data["country"] = "USA"

            missing = [k for k in ["name", "phone", "address", "city", "province", "postal_code", "country"] if not shipping_data.get(k)]
            if missing:
                print(f"  Still missing after body fallback: {missing}")

            # --- REGEX FALLBACK FOR PRODUCT LINK ---
            # If AI missed it, first try restoring the link found in the pre-scan of all 35 emails
            if not shipping_data.get("product_link"):
                if extracted_product_link:
                    shipping_data["product_link"] = extracted_product_link
                    print(f"🎯 Restored product link from 35-email pre-scan: {extracted_product_link}")
                else:
                    import re
                    shopping_patterns_detailed = [
                        r'https?://[^\s<>"]*?(?:colestore\.ru|bags-store\.ru|tikhubs\.ru|bags-store\.com)/[^\s<>"]*?(?:bags|shoes|product|\.html)[^\s<>"]*',
                    ]
                    
                    found_url = None
                    for p in shopping_patterns_detailed:
                        found = re.search(p, all_body, re.IGNORECASE)
                        if found:
                            found_url = found.group(0)
                            print(f"✅ Regex found detailed product link in short body: {found_url}")
                            break
                                
                    if found_url:
                        shipping_data["product_link"] = found_url

            # Clean up generic homepages to prevent useless/hallucinated details
            prod_link = shipping_data.get("product_link") or ""
            if prod_link:
                cleaned_link = prod_link.strip().lower().rstrip("/")
                if cleaned_link in [
                    "https://www.tikhubs.ru", "https://tikhubs.ru", "http://www.tikhubs.ru", "http://tikhubs.ru",
                    "https://www.colestore.ru", "https://colestore.ru", "http://www.colestore.ru", "http://colestore.ru",
                    "https://www.bags-store.ru", "https://bags-store.ru", "http://www.bags-store.ru", "http://bags-store.ru",
                    "https://www.bags-store.com", "https://bags-store.com", "http://www.bags-store.com", "http://bags-store.com"
                ]:
                    print(f"⚠️ Cleaned up generic homepage URL: {prod_link} -> Setting to empty.")
                    shipping_data["product_link"] = ""

            # VERIFY ADDRESS
            shipping_data = self.verify_and_complete_address(shipping_data)
            
            # DEBUG: Print what was extracted
            print(f"🔎 AI EXTRACTED:")
            for k, v in shipping_data.items():
                if v:
                    print(f"   {k}: {v}")
            
            # 3. SCRAPE PRODUCT INFO SYNCHRONOUSLY before updating UI
            # This must happen here (blocking) so data is ready when update_ui() runs
            product_info = {}
            prod_url = shipping_data.get("product_link") or ""
            prod_url = prod_url.strip()
            
            # Robust product URL repair logic
            if prod_url and not prod_url.startswith("http"):
                print(f"WARNING: Extracted product link lacks protocol/domain: {prod_url}")
                # Try finding a full URL in the email body that contains this relative portion
                import re as _re
                # Clean relative URL by stripping common domains to match path
                clean_rel = prod_url.replace("www.", "").replace("colestore.ru", "").replace("tikhubs.ru", "").replace("bags-store.ru", "").replace("bags-store.com", "").lstrip("/")
                if clean_rel:
                    found_url = _re.search(fr'https?://[^\s<>"]*?{_re.escape(clean_rel)}[^\s<>"]*', all_body, _re.IGNORECASE)
                    if found_url:
                        prod_url = found_url.group(0)
                        print(f"SUCCESS: Repaired product URL from email body: {prod_url}")
                
                # If still not fully repaired, check domain prefixing
                if not prod_url.startswith("http"):
                    for domain in ['colestore.ru', 'tikhubs.ru', 'bags-store.ru', 'bags-store.com']:
                        if domain in prod_url:
                            prod_url = "https://www." + prod_url[prod_url.find(domain):]
                            print(f"SUCCESS: Repaired product URL fallback: {prod_url}")
                            break
            
            if prod_url and prod_url.startswith("http"):
                print(f"\n🛍️ Scraping product info from: {prod_url}")
                try:
                    product_info = scrape_product_info(prod_url)
                    print(f"✅ Product scraped: {product_info.get('product_name')} | "
                          f"Brand: {product_info.get('product_brand')} | "
                          f"Images: {len(product_info.get('product_images', []))}")
                except Exception as pe:
                    print(f"⚠️ Product scraping failed ({pe}) - fields will be empty")

            # 4. UI UPDATER - runs in main thread, all data ready
            def update_ui():
                # Clear delivery fields
                for fn in ['consignee', 'phone', 'country', 'province', 'city', 'address', 'postal_code']:
                    if fn in self.fields:
                        f = self.fields[fn]
                        if isinstance(f, tk.Text): f.delete("1.0", "end")
                        else: f.delete(0, "end")
                
                # Fill Delivery
                name_val = shipping_data.get("name") or shipping_data.get("consignee") or shipping_data.get("recipient")
                phone_val = shipping_data.get("phone") or shipping_data.get("phone_number") or shipping_data.get("contact_number")
                country_val = shipping_data.get("country")
                prov_val = shipping_data.get("province") or shipping_data.get("state") or shipping_data.get("region")
                city_val = shipping_data.get("city")
                addr_val = shipping_data.get("address") or shipping_data.get("street") or shipping_data.get("detailed_address")
                zip_val = shipping_data.get("postal_code") or shipping_data.get("zip") or shipping_data.get("zip_code")
                
                if name_val: self.fields['consignee'].insert(0, name_val)
                if phone_val: self.fields['phone'].insert(0, phone_val)
                if country_val: self.fields['country'].insert(0, country_val)
                if prov_val: self.fields['province'].insert(0, prov_val)
                if city_val: self.fields['city'].insert(0, city_val)
                if addr_val: self.fields['address'].insert("1.0", addr_val)
                if zip_val: self.fields['postal_code'].insert(0, zip_val)
                
                # SYNC contact fields
                if email_address:
                    if 'contact_info' in self.fields:
                        self.fields['contact_info'].delete(0, 'end')
                        self.fields['contact_info'].insert(0, email_address)
                    if 'contact_email' in self.fields:
                        self.fields['contact_email'].delete(0, 'end')
                        self.fields['contact_email'].insert(0, email_address)
                
                # Fill Product Link
                self.fields['product_link'].delete(0, "end")
                if prod_url and prod_url.startswith("http"):
                    self.fields['product_link'].insert(0, prod_url)
                    self.fields['product_link'].config(fg='black')
                else:
                    self.fields['product_link'].config(fg='gray')

                # Fill Product Info (from synchronous scrape above)
                if product_info:
                    pname = product_info.get('product_name', '')
                    pbrand = product_info.get('product_brand', '')
                    psku = product_info.get('product_sku', '')
                    images = product_info.get('product_images', [])

                    if pname:
                        self.fields['product_name'].delete(0, 'end')
                        self.fields['product_name'].insert(0, pname)
                        self.fields['product_name'].config(fg='black')
                    if pbrand:
                        self.fields['product_brand'].delete(0, 'end')
                        self.fields['product_brand'].insert(0, pbrand)
                        self.fields['product_brand'].config(fg='black')
                    if psku:
                        self.fields['product_sku'].delete(0, 'end')
                        self.fields['product_sku'].insert(0, psku)
                        self.fields['product_sku'].config(fg='black')
                    if len(images) >= 1:
                        self.fields['product_main_image'].config(state='normal')
                        self.fields['product_main_image'].delete(0, 'end')
                        self.fields['product_main_image'].insert(0, images[0])
                        self.fields['product_main_image'].config(state='disabled')
                    if len(images) >= 2:
                        self.fields['product_detail_image_1'].config(state='normal')
                        self.fields['product_detail_image_1'].delete(0, 'end')
                        self.fields['product_detail_image_1'].insert(0, images[1])
                        self.fields['product_detail_image_1'].config(state='disabled')
                    if len(images) >= 3:
                        self.fields['product_detail_image_2'].config(state='normal')
                        self.fields['product_detail_image_2'].delete(0, 'end')
                        self.fields['product_detail_image_2'].insert(0, images[2])
                        self.fields['product_detail_image_2'].config(state='disabled')
                    if len(images) >= 4:
                        self.fields['product_detail_image_3'].config(state='normal')
                        self.fields['product_detail_image_3'].delete(0, 'end')
                        self.fields['product_detail_image_3'].insert(0, images[3])
                        self.fields['product_detail_image_3'].config(state='disabled')
                    print(f"✅ Product fields filled in GUI: {pname}")
                else:
                    # Clear product details if no link/info was found
                    self.fields['product_name'].delete(0, 'end')
                    self.fields['product_brand'].delete(0, 'end')
                    self.fields['product_sku'].delete(0, 'end')
                    self.fields['product_main_image'].config(state='normal')
                    self.fields['product_main_image'].delete(0, 'end')
                    self.fields['product_main_image'].config(state='disabled')
                    for img_f in ['product_detail_image_1', 'product_detail_image_2', 'product_detail_image_3']:
                        self.fields[img_f].config(state='normal')
                        self.fields[img_f].delete(0, 'end')
                        self.fields[img_f].config(state='disabled')

                # Social Link (GSheet)
                social_url = self.lookup_influencer_link(email_address)
                if social_url:
                    self.fields['channel_link'].delete(0, "end")
                    self.fields['channel_link'].insert(0, social_url)
                    self.fields['channel_link'].config(fg='black')
                else:
                    print("⚠️ Social Link not found in GSheet, trying AI extraction...")
                    social_url = shipping_data.get("channel_link")
                    if social_url:
                        self.fields['channel_link'].delete(0, "end")
                        self.fields['channel_link'].insert(0, social_url)
                
                # Trigger social scraping (still async - doesn't block submit)
                self.auto_fill_social_info(silent=True)
                
                self.email_reader_input.config(state="normal")
                msg = f"✅ Complete automation finished for:\n{email_address}\n\n✓ Delivery info filled\n✓ Product scraped\n✓ GSheet lookup done"
                print(f"Success! {msg.replace(chr(10), ' ')}")
                
                self.active_tasks -= 1
                
                 # Check if we successfully found a product link
                has_product_link = bool(prod_url and prod_url.strip().startswith("http"))
                
                if has_product_link:
                    # Automatically wait for social scraper to finish, then auto-submit (both GUI and API modes)
                    def auto_submit_when_done():
                        print("⏳ Waiting for social scraper to finish before auto-submitting...")
                        while self.active_tasks > 0:
                            time.sleep(1)
                        print("🚀 All scrapers finished! Opening browser to submit form.")
                        self.root.after(0, lambda: self.save_data(silent=True))
                    
                    bg_thread = threading.Thread(target=auto_submit_when_done)
                    bg_thread.daemon = True
                    bg_thread.start()
                else:
                    print("⚠️ Product link is missing. Auto-submit bypassed. Please enter the product link manually in the GUI to continue.")
                    if not silent:
                        self.root.after(0, lambda: messagebox.showinfo("Manual Action Required", "⚠️ Delivery info parsed, but could not find a product link in the email.\n\nPlease enter the product link in the app to continue!"))

            self.root.after(0, update_ui)
            
        except Exception as e:
            print(f"Automation Error: {e}")
            if not silent:
                self.root.after(0, lambda e=e: messagebox.showerror("Error", f"Automation failed:\n{str(e)}"))
            self.root.after(0, lambda: self.email_reader_input.config(state="normal"))
            self.active_tasks -= 1

    
    def get_field_value(self, field):
        """Get value from field (entry, text, or combobox)"""
        if isinstance(field, tk.Text):
            return field.get("1.0", "end-1c").strip()
        elif isinstance(field, ttk.Combobox):
            return field.get()
        else:
            return field.get().strip()
    
    def save_data(self, silent=False):
        """Save data and auto-fill form"""
        data = {}
        
        for key, field in self.fields.items():
            data[key] = self.get_field_value(field)
        
        # Validation
        required_fields = ['nickname', 'contact_info', 'platform', 'channel_name', 'channel_link']
        missing = [f for f in required_fields if not data.get(f)]
        
        if missing and not silent:
            messagebox.showwarning("Missing Fields", f"Please fill required fields:\n{', '.join(missing)}")
            return
        
        # Save to main file
        filename = "influencer_data.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Save to history
        self.save_to_history(data)
        
        # Determine if we should open browser
        should_open = False
        if silent:
            should_open = True
        else:
            should_open = messagebox.askyesno("Saved!", "✅ Data saved!\n\nOpen browser and fill form now?")
            
        if should_open:
            # Run browser automation in separate thread to keep GUI responsive
            thread = threading.Thread(target=self.fill_form, args=(data,))
            thread.daemon = True
            thread.start()
    
    def save_to_history(self, data):
        """Save current entry to history"""
        try:
            history_file = "erp_history.json"
            history = []
            
            # Load existing history
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            # Add timestamp and save
            entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data": data
            }
            
            history.insert(0, entry)  # Add to beginning
            
            # Keep only last 50 entries
            history = history[:50]
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            
            # Refresh history list
            self.load_history_list()
            
        except Exception as e:
            print(f"Failed to save history: {e}")
    
    def load_history_list(self):
        """Load and display history in listbox"""
        try:
            self.history_listbox.delete(0, tk.END)
            
            history_file = "erp_history.json"
            if not os.path.exists(history_file):
                return
            
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            for entry in history:
                timestamp = entry.get("timestamp", "Unknown")
                nickname = entry.get("data", {}).get("nickname", "No Name")
                platform = entry.get("data", {}).get("platform", "")
                
                display = f"{timestamp} - {nickname} ({platform})"
                self.history_listbox.insert(tk.END, display)
                
        except Exception as e:
            print(f"Failed to load history: {e}")
    
    def load_from_history(self):
        """Load selected history entry into form"""
        try:
            selection = self.history_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select an entry from history!")
                return
            
            index = selection[0]
            
            with open("erp_history.json", 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            data = history[index]["data"]
            
            # Fill form UI
            for key, value in data.items():
                if key in self.fields:
                    field = self.fields[key]
                    if isinstance(field, tk.Text):
                        field.delete("1.0", "end")
                        field.insert("1.0", value)
                    elif isinstance(field, ttk.Combobox):
                        field.set(value)
                    else:
                        field.delete(0, "end")
                        field.insert(0, value)
            
            messagebox.showinfo("Loaded!", f"✅ Data loaded from history!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load from history:\n{str(e)}")

    def resubmit_from_history(self):
        """Load from history and immediately submit"""
        try:
            selection = self.history_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select an entry to resubmit!")
                return
            
            index = selection[0]
            
            with open("erp_history.json", 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            data = history[index]["data"]
            
            # Fill form UI (so user can see what is being submitted)
            for key, value in data.items():
                if key in self.fields:
                    field = self.fields[key]
                    if isinstance(field, tk.Text):
                        field.delete("1.0", "end")
                        field.insert("1.0", value)
                    elif isinstance(field, ttk.Combobox):
                        field.set(value)
                    else:
                        field.delete(0, "end")
                        field.insert(0, value)
            
            if messagebox.askyesno("Resubmit", f"🔄 Ready to resubmit:\n\n{data.get('nickname')} ({data.get('platform')})\n\nOpen browser and fill form?"):
                thread = threading.Thread(target=self.fill_form, args=(data,))
                thread.daemon = True
                thread.start()
        except Exception as e:
             messagebox.showerror("Error", f"Failed to resubmit:\n{str(e)}")
    
    def delete_from_history(self):
        """Delete selected entry from history"""
        try:
            selection = self.history_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select an entry to delete!")
                return
            
            index = selection[0]
            
            with open("erp_history.json", 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            entry = history[index]
            
            if messagebox.askyesno("Delete", f"Delete this entry?\n\n{entry['timestamp']} - {entry['data'].get('nickname')}"):
                history.pop(index)
                
                with open("erp_history.json", 'w', encoding='utf-8') as f:
                    json.dump(history, f, indent=2, ensure_ascii=False)
                
                self.load_history_list()
                messagebox.showinfo("Deleted", "✅ Entry deleted from history!")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete:\n{str(e)}")
    
    def _init_browser(self):
        """Request browser initialization from the worker thread."""
        resp_q = queue.Queue()
        self.browser_queue.put({'action': 'init', 'response_queue': resp_q})
        result = resp_q.get()
        if isinstance(result, Exception): raise result
        return result

    def close_browser(self):
        """Request browser closure from the worker thread."""
        resp_q = queue.Queue()
        self.browser_queue.put({'action': 'close', 'response_queue': resp_q})
        result = resp_q.get()
        if isinstance(result, Exception): print(f"Close error: {result}")

    def fill_form(self, data):
        """Enqueue form filling task to the worker thread."""
        resp_q = queue.Queue()
        self.browser_queue.put({'action': 'fill_form', 'data': data, 'response_queue': resp_q})
        # Note: We don't necessarily block the UI thread here, 
        # but the worker will execute it sequentially.
        print("📥 Form filling task enqueued.")

    def _execute_fill_form_on_thread(self, data):
        """INTERNAL: The actual human-like automation logic, executed by the worker thread."""
        try:
            # Check if browser is still alive and responsive. If closed/crashed, reset context.
            browser_alive = False
            if self.browser_ctx and self.active_page:
                try:
                    # Accessing properties forces playwright to verify target is still open
                    _ = self.browser_ctx.pages
                    _ = self.active_page.url
                    browser_alive = True
                except Exception:
                    print("⚠️ Active browser context or page was closed/crashed. Resetting...")
                    try: self.browser_ctx.close()
                    except: pass
                    self.browser_ctx = None
                    self.active_page = None

            # --- 1. INITIALIZE / FIND CORRECT PAGE ---
            if not self.active_page:
                self.browser_ctx = self.pw_instance.chromium.launch_persistent_context(
                    user_data_dir="C:/erp_profile",
                    headless=False
                )
                self.active_page = self.browser_ctx.pages[0] if self.browser_ctx.pages else self.browser_ctx.new_page()

            # Find the best ERP tab among all open tabs
            print(f"🔍 Worker: Scanning {len(self.browser_ctx.pages)} open tabs...")
            target_page = None
            for p in self.browser_ctx.pages:
                try:
                    if any(x in p.url for x in ["/celebrity", "erp.bx123.pro"]):
                        target_page = p; break
                except: pass
            
            if not target_page:
                print("  → No ERP tab found. Using first tab...")
                target_page = self.browser_ctx.pages[0]
            
            self.active_page = target_page
            page = self.active_page
            page.bring_to_front()

            # --- 2. DEFINE INTERNAL HELPERS ---
            def auto_login_if_needed():
                try:
                    current_url = page.url
                    # Detect 401/403 unauthorized or session expired
                    if any(x in current_url for x in ['/401', '/403', '/500']):
                        print("⚠️ Detected unauthorized/error page (401/403). Navigating to login...")
                        page.goto("https://erp.bx123.pro/login", wait_until="domcontentloaded", timeout=15000)
                        page.wait_for_timeout(2000)
                        current_url = page.url

                    # Check for login indicators (URL or Presence of Login Form)
                    if any(x in current_url for x in ['/login', '/admin/login', 'auth']) or page.locator('input[placeholder="账号"], input[name="username"]').count() > 0:
                        print("🔐 Login page detected - Attempting auto-fill...")
                        user_input = page.locator('input[placeholder="账号"], input[name="username"]').first
                        if user_input.count() > 0:
                            user_input.fill("panjinying")
                        pass_input = page.locator('input[placeholder="密码"], input[type="password"]').first
                        if pass_input.count() > 0:
                            pass_input.fill("LIrong2025")
                        page.wait_for_timeout(500)
                        login_btn = page.locator('button:has-text("登陆"), button:has-text("登录"), input[type="submit"]').first
                        if login_btn.count() > 0:
                            login_btn.click()
                            
                            # Wait for login completion to handle slide verification or network delay
                            print("⏳ Waiting for login completion (solve slide verification if present)...")
                            login_success = False
                            for _ in range(45):  # Wait up to 45 seconds
                                page.wait_for_timeout(1000)
                                curr = page.url.lower()
                                # If we are no longer on the login page and not on a 401/403 page
                                if not any(x in curr for x in ['/login', 'auth']) and page.locator('input[placeholder="账号"]').count() == 0:
                                    # Double check we are not on a 401/403 page either
                                    if not any(x in curr for x in ['/401', '/403']):
                                        print(f"🎉 Login successful! Active URL: {page.url}")
                                        login_success = True
                                        break
                            if not login_success:
                                print("⚠️ Login timeout. Please ensure credentials are correct and captcha is solved.")
                            page.wait_for_timeout(2000)
                except Exception as e: print(f"    Auto-login error: {e}")


            def get_target_locator(selector):
                """Search for selector across main page and all nested frames."""
                try:
                    # 1. Check main page
                    loc = page.locator(selector).first
                    if loc.count() > 0: return loc
                    # 2. Check all frames
                    for frame in page.frames:
                        if frame == page.main_frame: continue
                        f_loc = frame.locator(selector).first
                        if f_loc.count() > 0: return f_loc
                except: pass
                return None

            def debug_diagnose():
                """Dumps page state to terminal for troubleshooting failures."""
                try:
                    print("\n" + "="*40 + "\n[DIAGNOSTIC REPORT]")
                    print(f"URL: {page.url}\nTitle: {page.title()}\nFrames: {len(page.frames)}")
                    # Scroll to bottom to force all fields to load
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(1000)
                    inputs = page.locator('input[placeholder]').all()
                    print(f"All Placeholders ({len(inputs)} inputs): {[i.get_attribute('placeholder') for i in inputs[:20]]}")
                    selects = page.locator('.el-select').all()
                    print(f"El-Select dropdowns found: {len(selects)}")
                    labels = page.locator('label').all()
                    print(f"Labels found: {[l.inner_text() for l in labels[:15]]}")
                    print("="*40 + "\n")
                    page.evaluate("window.scrollTo(0, 0)")
                except: pass

            def safe_fill(selector, value, label=""):
                if not value: return False
                try:
                    print(f"  → Filling {label}...")
                    try: page.wait_for_selector('.el-loading-mask', state='hidden', timeout=2000)
                    except: pass
                    loc = get_target_locator(selector)
                    if loc:
                        loc.scroll_into_view_if_needed()
                        loc.click(force=True, timeout=2000)
                        loc.fill(str(value))
                        print(f"    ✅ {label} filled")
                        return True
                    print(f"    ❌ {label} not found (even in frames)")
                    return False
                except Exception as e:
                    print(f"    ❌ {label} error: {str(e)[:80]}")
                    return False

            def fill_by_label(label_text, value, field_label=""):
                """Fill input by finding it via its associated label text."""
                if not value: return False
                try:
                    print(f"  → Filling {field_label} by label '{label_text}'...")
                    # Method 1: Playwright get_by_label
                    loc = page.get_by_label(label_text, exact=False).first
                    if loc.count() > 0:
                        loc.scroll_into_view_if_needed()
                        loc.click(force=True, timeout=2000)
                        loc.fill(str(value))
                        print(f"    ✅ {field_label} filled via get_by_label")
                        return True
                    # Method 2: filter form-item
                    loc2 = page.locator('.el-form-item').filter(
                        has=page.locator('label', has_text=label_text)
                    ).locator('input').first
                    if loc2.count() > 0:
                        loc2.scroll_into_view_if_needed()
                        loc2.click(force=True, timeout=2000)
                        loc2.fill(str(value))
                        print(f"    ✅ {field_label} filled via filter")
                        return True
                except Exception as e:
                    print(f"    ❌ {field_label} label-fill error: {str(e)[:80]}")
                return False

            def translate_to_erp(category, value):
                """Translate AI-extracted values to match EXACT text shown in ERP dropdowns.
                
                IMPORTANT: Options are verified against actual ERP UI screenshots.
                Contact Type options (from screenshot): Email, WhatsApp, Phone, Instagram, Snapchat, Tiktok, Other
                Platform options: tiktok, YouTube, Instagram, Facebook, etc.
                Unit options: H, K, M
                Country options: Chinese text (美国, 英国...)
                Cooperation Status: Chinese text (新网红, 老网红)
                """
                if not value: return ""
                val = str(value).lower().strip()
                mappings = {
                    # ERP Country dropdown uses ENGLISH names (from screenshot)
                    "country": {
                        "usa": "United States", "united states": "United States", "us": "United States",
                        "uk": "United Kingdom (UK)", "united kingdom": "United Kingdom (UK)",
                        "russia": "Russia", "ru": "Russia",
                        "vietnam": "Vietnam", "vn": "Vietnam",
                        "canada": "Canada", "australia": "Australia",
                        "germany": "Germany", "france": "France",
                        "italy": "Italy", "spain": "Spain",
                        "japan": "Japan", "korea": "South Korea",
                        "brazil": "Brazil", "mexico": "Mexico",
                        "dominican republic": "Dominican Republic",
                        "trinidad": "Trinidad and Tobago",
                        "puerto rico": "Puerto Rico",
                    },
                    # ERP shows ENGLISH text for contact type (verified from screenshot)
                    "contact_type": {
                        "email": "Email", "mailbox": "Email", "mail": "Email",
                        "whatsapp": "WhatsApp",
                        "phone": "Phone", "telephone": "Phone",
                        "instagram": "Instagram",
                        "snapchat": "Snapchat",
                        "tiktok": "Tiktok",
                        "other": "Other",
                        # Chinese fallbacks in case AI sends Chinese
                        "邮件": "Email", "电话": "Phone",
                    },
                    # ERP platform dropdown options (verified: tiktok lowercase, YouTube caps)
                    "platform": {
                        "youtube": "YouTube", "tiktok": "tiktok",
                        "instagram": "Instagram", "facebook": "Facebook",
                        "twitter": "Twitter", "pinterest": "Pinterest",
                        "snapchat": "Snapchat",
                    },
                    # ERP unit: H (小于1000), K (千), M (百万) - from hint text in screenshot
                    "unit": {
                        "k": "K", "m": "M", "h": "H",
                        "1000": "K", "1000000": "M",
                        "thousand": "K", "million": "M",
                    },
                    # ERP Cooperation Status options (ENGLISH from screenshot):
                    # "New Internet Celebrity", "Old Internet Celebrity"
                    "cooperation_status": {
                        "new": "New Internet Celebrity",
                        "old": "Old Internet Celebrity",
                        "first": "New Internet Celebrity",
                        "new internet celebrity": "New Internet Celebrity",
                        "old internet celebrity": "Old Internet Celebrity",
                        "existing": "Old Internet Celebrity",
                        "new_internet_celebrity": "New Internet Celebrity",
                        "old_internet_celebrity": "Old Internet Celebrity",
                    },
                    # ERP Influencer Quality options (ENGLISH from screenshot):
                    # "unknown", "ordinary", "high quality", "blacklist"
                    "influencer_quality": {
                        "unknown": "unknown",
                        "normal": "ordinary", "ordinary": "ordinary",
                        "good": "high quality", "excellent": "high quality",
                        "high": "high quality", "high quality": "high quality",
                        "blacklist": "blacklist",
                        "medium": "ordinary",
                    },
                    "product_type": {
                        "bag": "包包", "bags": "包包",
                        "watch": "手表", "watches": "手表",
                        "shoes": "鞋子", "jewelry": "首饰",
                        "accessories": "配饰",
                    }
                }
                # Return original value if already correct Chinese/English
                if val in ["新网红", "老网红", "未知", "普通", "优质",
                           "美国", "英国", "Email", "WhatsApp", "Phone",
                           "YouTube", "tiktok", "Instagram", "K", "M", "H"]:
                    return value

                result = mappings.get(category, {}).get(val, value)
                return result

            def click_dropdown_option(search_text, option_text, label="", by_selector=False):
                """Select from dropdown. Tries native <select> first (ERP), then Element UI."""
                if not option_text: return False
                print(f"  -> Selecting {label}: '{option_text}'...")
                try:
                    page.wait_for_timeout(300)
                    want = str(option_text).lower().strip()
                    q = str(search_text).lower().strip()

                    # Strategy 1: Native HTML <select>
                    js_native = f"""
                    () => {{
                        const q = '{q}';
                        const want = '{want}';
                        const isSocial = q.includes('platform') || q.includes('account') || q.includes('unit') || q.includes('社交') || q.includes('单位');
                        
                        const selects = Array.from(document.querySelectorAll('select'));
                        for (let s of selects) {{
                            // Check if inside a table row
                            const inTable = !!(s.closest('tr') || s.closest('.el-table__row') || s.closest('td'));
                            if (isSocial && !inTable) continue;
                            if (!isSocial && inTable) continue;
                            
                            const ph = (s.options[0]?.text || '').toLowerCase();
                            const fi = s.closest('.el-form-item') || s.closest('td') || s.parentElement;
                            const ctx = fi ? (fi.innerText || '').toLowerCase() : '';
                            
                            // Check if it's the right select
                            let matched = ph.includes(q) || ctx.includes(q);
                            
                            if (!matched) {{
                                for (let o of s.options) {{
                                    const ot = o.text.toLowerCase().trim();
                                    if (ot === want || ot.includes(want)) {{
                                        matched = true;
                                        break;
                                    }}
                                }}
                            }}
                            
                            if (matched) {{
                                for (let o of s.options) {{
                                    const ot = o.text.toLowerCase().trim();
                                    if (ot === want || ot.includes(want) || want.includes(ot) || want.replace(/[^a-z0-9]/g, '') === ot.replace(/[^a-z0-9]/g, '')) {{
                                        s.value = o.value;
                                        s.dispatchEvent(new Event('change', {{bubbles:true}}));
                                        s.dispatchEvent(new Event('input',  {{bubbles:true}}));
                                        return 'OK:' + o.text;
                                    }}
                                }}
                                return 'OPTS:' + Array.from(s.options).map(o=>o.text).slice(1).join('|');
                            }}
                        }}
                        return null;
                    }}
                    """
                    r = page.evaluate(js_native)
                    if r and r.startswith('OK:'):
                        page.wait_for_timeout(300)
                        print(f"    OK {label} = '{r[3:]}' selected (native)")
                        return True
                    elif r and r.startswith('OPTS:'):
                        print(f"    WARNING {label}: options=[{r[5:]}] - '{option_text}' not matched")
                        return False

                    # Strategy 2: Element UI el-select
                    js_find = f"""
                    () => {{
                        const q = '{q}';
                        const byPh = Array.from(document.querySelectorAll('input[placeholder]'))
                            .find(i => i.placeholder.toLowerCase().includes(q));
                        if (byPh) return byPh;
                        for (let l of document.querySelectorAll('.el-form-item__label, label')) {{
                            if ((l.innerText||'').toLowerCase().includes(q)) {{
                                const fi = l.closest('.el-form-item');
                                if (fi) {{ const inp = fi.querySelector('input'); if (inp) return inp; }}
                            }}
                        }}
                        return null;
                    }}
                    """
                    h = page.evaluate_handle(js_find)
                    trig = h.as_element()
                    if trig:
                        trig.scroll_into_view_if_needed()
                        trig.click(force=True)
                        page.wait_for_timeout(800)
                        js_opt = f"""
                        () => {{
                            const want = '{want}';
                            for (let el of document.querySelectorAll('li.el-select-dropdown__item, div[role="option"]')) {{
                                const r = el.getBoundingClientRect();
                                if (r.width > 0 && r.height > 0) {{
                                    const t = (el.innerText||'').toLowerCase().trim();
                                    if (t === want || t.includes(want)) {{ el.click(); return el.innerText.trim(); }}
                                }}
                            }}
                            return JSON.stringify(Array.from(document.querySelectorAll(
                                'li.el-select-dropdown__item'
                            )).filter(e=>e.getBoundingClientRect().width>0).map(e=>e.innerText.trim()).slice(0,10));
                        }}
                        """
                        res = page.evaluate(js_opt)
                        if res and not res.startswith('['):
                            page.wait_for_timeout(300)
                            print(f"    OK {label} = '{res}' selected (el-select)")
                            return True
                        print(f"    X {label}: el-select options found: {res}")
                        try: page.keyboard.press("Escape")
                        except: pass
                    else:
                        print(f"    X {label}: select element not found")
                except Exception as e:
                    print(f"    X {label} error: {e}")
                return False

            def upload_file(btn_text, file_path, label="", slot_index=0):
                """Upload file via hidden file input, then click Upload in same container."""
                if not file_path: return False
                paths = [p for p in (file_path if isinstance(file_path, list) else [file_path])
                         if p and os.path.exists(p)]
                if not paths:
                    print(f"    WARNING {label}: file not found")
                    return False
                try:
                    print(f"  -> Uploading {label}: {[os.path.basename(p) for p in paths]}")
                    page.wait_for_timeout(400)

                    # Find file input
                    js_find = f"""
                    () => {{
                        const containers = Array.from(document.querySelectorAll('.el-upload, .upload-demo'));
                        const matches = containers.filter(c => (c.innerText||'').includes('{btn_text}'));
                        const container = matches[{slot_index}] || matches[0];
                        if (!container) {{
                            const inputs = Array.from(document.querySelectorAll('input[type="file"]'));
                            return inputs[{slot_index}] || inputs[0] || null;
                        }}
                        return container.querySelector('input[type="file"]');
                    }}
                    """
                    h = page.evaluate_handle(js_find)
                    inp = h.as_element()

                    if not inp:
                        print(f"    X {label}: file input not found")
                        return False

                    # Unhide and upload
                    page.evaluate("""
                        inp => {
                            inp.style.cssText = 'display:block!important;opacity:1!important;visibility:visible!important;width:2px;height:2px;position:fixed;left:0;top:0;';
                        }
                    """, inp)
                    inp.set_input_files(paths)
                    page.wait_for_timeout(1500)

                    # Highly robust confirmation click targeting the exact slot container
                    js_up = f"""
                    () => {{
                        const containers = Array.from(document.querySelectorAll('.el-upload, .upload-demo, .btn-file, .file-input, .input-group-btn'));
                        const matches = containers.filter(c => (c.innerText||'').includes('{btn_text}'));
                        const container = matches[{slot_index}] || matches[0];
                        if (container) {{
                            let parent = container;
                            // Search up to the main wrapper (.file-input or similar) to locate the sibling upload button
                            const wrapper = container.closest('.file-input, .upload-demo, .el-upload, .form-group');
                            if (wrapper) parent = wrapper;
                            
                            const upBtn = Array.from(parent.querySelectorAll('button, .btn, .el-button, span'))
                                .find(el => {{
                                    const txt = (el.innerText || '').trim();
                                    const cls = el.className || '';
                                    return (txt.includes('上传') || txt.toLowerCase().includes('upload') || cls.includes('fileinput-upload') || cls.includes('kv-file-upload')) 
                                        && el.getBoundingClientRect().width > 0;
                                }});
                            if (upBtn) {{
                                upBtn.click();
                                return 'container-click';
                            }}
                        }}
                        
                        // Global fallback
                        const anyUp = Array.from(document.querySelectorAll('button, .el-button, span'))
                            .find(el => {{
                                const txt = (el.innerText || '').trim();
                                const cls = el.className || '';
                                return (txt.includes('上传') || txt.toLowerCase().includes('upload') || cls.includes('fileinput-upload')) 
                                    && el.getBoundingClientRect().width > 0;
                            }});
                        if (anyUp) {{
                            anyUp.click();
                            return 'global-click';
                        }}
                        return 'not-found';
                    }}
                    """
                    res = page.evaluate(js_up)
                    page.wait_for_timeout(2500)
                    if res != 'not-found':
                        print(f"    OK {label}: uploaded ({res})")
                        return True
                    else:
                        print(f"    WARNING {label}: file set, but confirmation upload button not found")
                        return False
                except Exception as e:
                    print(f"    X {label} upload error: {e}")
                return False

            def fill_date(value, label, selector_or_text):
                """Fill Element UI datepicker."""
                if not value: return False
                try:
                    print(f"  → Filling {label}: '{value}'...")
                    date_str = str(value).strip()
                    loc = None
                    try:
                        candidate = page.locator(f'input[placeholder*="{selector_or_text}"]').first
                        if candidate.count() > 0:
                            loc = candidate
                    except:
                        pass

                    if not loc:
                        js_find = f"""() => {{
                            const src = '{selector_or_text}'.toLowerCase();
                            for (let l of document.querySelectorAll('.el-form-item__label, label')) {{
                                if ((l.innerText || '').toLowerCase().includes(src)) {{
                                    const fi = l.closest('.el-form-item');
                                    if (fi) {{
                                        const inp = fi.querySelector('input');
                                        if (inp) return inp;
                                    }}
                                }}
                            }}
                            return null;
                        }}"""
                        h = page.evaluate_handle(js_find)
                        if h.as_element():
                            loc = h.as_element()

                    if loc:
                        loc.scroll_into_view_if_needed()
                        loc.click(force=True)
                        page.wait_for_timeout(500)
                        loc.click(force=True, click_count=3)
                        page.keyboard.type(date_str)
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(600)
                        page.keyboard.press("Escape")
                        print(f"    OK {label} = '{date_str}' filled")
                        return True
                    print(f"    X {label} not found")
                    return False
                except Exception as e:
                    print(f"    X {label} error: {e}")
                    return False
            # --- 3. NAVIGATION LOGIC (REDIRECT BUSTER) ---
            print(f"📍 Navigation: Starting at {page.url}")
            
            def attempt_goto(url):
                print(f"  → Goto: {url}")
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(3000)
                    return page.url
                except Exception as e:
                    print(f"    Navigation fail: {e}")
                    return page.url

            # Ensure logged in before navigating
            auto_login_if_needed()

            if "/celebrityOrder/save" not in page.url:
                current_url = attempt_goto("https://erp.bx123.pro/celebrityOrder/save")
                
                # Handle potential redirect to Dashboard, Login, or 401 page
                if any(x in current_url for x in ["/admin/main", "login", "/401", "/403"]):
                    print("  ⚠️ Redirected or unauthorized page. Retrying with login check & alternative URL...")
                    auto_login_if_needed()
                    attempt_goto("https://erp.bx123.pro/admin/celebrityOrder/save")

            # Wait for form to fully load before filling
            print("  ⏳ Waiting for form to fully load...")
            try:
                page.wait_for_selector('input', state='visible', timeout=8000)
                page.wait_for_timeout(2000)  # Extra wait for all Element UI components to render
            except:
                page.wait_for_timeout(3000)

            page.screenshot(path="last_browser_state.png")
            
            # --- 4. FORM FILLING EXECUTION ---
            print("🚀 Starting Form Fill Sequence...")
            
            # Helper to try multiple selectors - returns True on first success
            def try_fill(value, label, *selectors):
                if not value: return False
                for sel in selectors:
                    if safe_fill(sel, value, label):
                        return True
                print(f"    ❌ {label}: all selectors exhausted")
                return False

            def safe_select(selector, value, label=""):
                """Legacy select support for standard HTML <select> boxes."""
                try:
                    loc = get_target_locator(selector)
                    if loc and loc.count() > 0:
                        tag_name = loc.evaluate("el => el.tagName")
                        if tag_name == 'SELECT':
                            loc.scroll_into_view_if_needed()
                            loc.select_option(label=str(value), timeout=2000)
                            print(f"    ✅ {label} native select: '{value}'")
                            return True
                except: pass
                return False

            def try_dropdown(option_text, label, *selectors):
                if not option_text: return False
                for sel in selectors:
                    # 1. Try legacy native <select>
                    if safe_select(sel, option_text, label):
                        return True
                        
                    # 2. Try Element UI dropdown
                    # If the selector is pure Chinese label text (e.g. "联系类型"), by_selector=False
                    # If it's a CSS string like 'select[name="..."]', by_selector=True
                    is_css = ('[' in sel or '.' in sel or '#' in sel)
                    if click_dropdown_option(sel, option_text, label, by_selector=is_css):
                        return True
                        
                print(f"    ❌ {label}: all dropdown selectors exhausted")
                return False

            # ====================================================
            # --- 4. FORM FILLING EXECUTION (v2 - verified field IDs) ---
            # Field IDs confirmed by live browser inspection of ERP form
            # ====================================================
            print("Starting Form Fill Sequence (v2)...")

            # HELPER: Select native <select> by id and option text
            def select_by_id(field_id, option_text, label=""):
                if not option_text: return False
                try:
                    loc = page.locator(f'select#{field_id}').first
                    if loc.count() == 0:
                        print(f"    X {label}: select#{field_id} not found")
                        return False
                    loc.scroll_into_view_if_needed()
                    try:
                        loc.select_option(label=str(option_text), timeout=3000)
                        print(f"    OK {label} = '{option_text}'")
                        return True
                    except: pass
                    # JS partial match fallback
                    r2 = page.evaluate(f"""() => {{
                        const s = document.querySelector('select#{field_id}');
                        if (!s) return 'NOT_FOUND';
                        const want = '{str(option_text).lower()}';
                        for (let o of s.options) {{
                            if (o.text.toLowerCase().includes(want) || want.includes(o.text.toLowerCase())) {{
                                s.value = o.value;
                                s.dispatchEvent(new Event('change', {{bubbles:true}}));
                                return 'OK:' + o.text;
                            }}
                        }}
                        return 'OPTS:' + Array.from(s.options).map(o=>o.text).join('|');
                    }}""")
                    if r2 and r2.startswith('OK:'):
                        print(f"    OK {label} = '{r2[3:]}' (partial)")
                        return True
                    print(f"    X {label}: no match. Options={r2}")
                    return False
                except Exception as e:
                    print(f"    X {label}: {e}")
                    return False

            # HELPER: Fill input/textarea by id
            def fill_by_id(field_id, value, label=""):
                if not value: return False
                try:
                    loc = page.locator(f'#{field_id}').first
                    if loc.count() == 0:
                        print(f"    X {label}: #{field_id} not found")
                        return False
                    loc.scroll_into_view_if_needed()
                    loc.click(force=True, timeout=2000)
                    loc.fill(str(value))
                    print(f"    OK {label} = '{str(value)[:60]}'")
                    return True
                except Exception as e:
                    print(f"    X {label} #{field_id}: {e}")
                    return False

            # HELPER: Fill date picker by id
            # ERP uses Element UI DatePicker - must click date then click 确定 button
            def fill_date_by_id(field_id, date_str, label=""):
                if not date_str: return False
                try:
                    loc = page.locator(f'#{field_id}').first
                    if loc.count() == 0:
                        loc = page.locator('input[placeholder*="\u5408\u4f5c\u65f6\u95f4"], input[placeholder*="\u5408\u4f5c\u65e5\u671f"]').first
                    if loc.count() == 0:
                        print(f"    X {label}: #{field_id} not found")
                        return False
                    loc.scroll_into_view_if_needed()
                    page.wait_for_timeout(300)
                    # Click to open the date picker calendar
                    loc.click(force=True)
                    page.wait_for_timeout(600)
                    # Type the date into the input field (shows at bottom of picker)
                    loc.press('Control+a')
                    loc.press('Delete')
                    page.keyboard.type(str(date_str))
                    page.wait_for_timeout(500)
                    # Click the 确定 (Confirm) button in the date picker panel
                    confirmed = page.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll(
                            '.el-picker-panel__footer button, .el-date-picker__footer button'
                        ));
                        const ok = btns.find(b => b.innerText.trim() === '\u786e\u5b9a');
                        if (ok) { ok.click(); return true; }
                        // Fallback: any visible button with \u786e\u5b9a text
                        const all = Array.from(document.querySelectorAll('button'));
                        const fb = all.find(b => b.innerText.trim() === '\u786e\u5b9a' && b.getBoundingClientRect().width > 0);
                        if (fb) { fb.click(); return true; }
                        return false;
                    }""")
                    page.wait_for_timeout(300)
                    if not confirmed:
                        # If 确定 not found, press Enter as last resort
                        page.keyboard.press('Enter')
                        page.wait_for_timeout(300)
                    print(f"    OK {label} = '{date_str}' (confirmed={confirmed})")
                    return True
                except Exception as e:
                    print(f"    X {label}: {e}")
                    return False

            # HELPER: Upload file - 2-step process (NO CSS visibility hack!)
            # Step 1: set_input_files() on hidden input (Playwright handles hidden inputs natively)
            # Step 2: re-hide the input immediately, then click .fileinput-upload button
            def upload_by_id(input_id, file_path, label=""):
                if not file_path: return False
                paths = [p for p in (file_path if isinstance(file_path, list) else [file_path]) if p and os.path.exists(p)]
                if not paths:
                    print(f"    X {label}: file not found at {file_path}")
                    return False
                try:
                    print(f"  -> Uploading {label}: {[os.path.basename(p) for p in paths]}")

                    # --- STEP 1: Set files directly (Playwright works on hidden inputs) ---
                    inp_loc = page.locator(f'#{input_id}').first
                    if inp_loc.count() == 0:
                        print(f"    X {label}: #{input_id} not found")
                        return False
                    inp_loc.set_input_files(paths)
                    page.wait_for_timeout(1200)
                    print(f"    OK {label}: file(s) set")

                    # --- STEP 2: Click the Upload/上传 button in the same container ---
                    upload_clicked = page.evaluate(f"""() => {{
                        const inp = document.querySelector('#{input_id}');
                        if (!inp) return 'no-input';
                        let container = inp.parentElement;
                        for (let i = 0; i < 8 && container; i++) {{
                            const upBtn = container.querySelector(
                                '.fileinput-upload, .kv-file-upload, .fileinput-upload-button'
                            );
                            if (upBtn && upBtn.getBoundingClientRect().width > 0) {{
                                upBtn.click();
                                return 'clicked:' + upBtn.className.substring(0, 40);
                            }}
                            const allBtns = container.querySelectorAll('a.btn, button');
                            for (let b of allBtns) {{
                                const txt = (b.innerText || '').trim();
                                if ((txt === '\u4e0a\u4f20' || b.className.includes('fileinput-upload'))
                                        && b.getBoundingClientRect().width > 0) {{
                                    b.click();
                                    return 'clicked-text';
                                }}
                            }}
                            container = container.parentElement;
                        }}
                        return 'not-found';
                    }}""")
                    page.wait_for_timeout(2000)
                    print(f"    OK {label}: upload result=({upload_clicked})")
                    return True
                except Exception as e:
                    print(f"    X {label} upload error: {e}")
                    return False

            # ============================================================
            # SECTION 1: Influencer Info
            # ============================================================
            print("  [1/5] Influencer Info...")

            fill_by_id("screenName", data.get('nickname') or data.get('screen_name'), "Nickname")

            contact_type_map = {
                "email": "Email", "mailbox": "Email", "mail": "Email",
                "whatsapp": "WhatsApp", "phone": "Phone", "telephone": "Phone",
                "instagram": "Instagram", "snapchat": "Snapchat",
                "tiktok": "Tiktok", "other": "Other",
            }
            raw_ct = str(data.get('contact_type') or "Email").lower()
            ct_val = contact_type_map.get(raw_ct, "Email")
            select_by_id("contactType", ct_val, "Contact Type")

            fill_by_id("contact", data.get('contact_info') or data.get('email'), "Contact Value")

            coop_date = data.get('cooperation_date') or datetime.now().strftime('%Y-%m-%d')
            fill_date_by_id("cooperationTime", coop_date, "Cooperation Date")

            coop_map = {"new": "\u65b0\u7f51\u7ea2", "old": "\u8001\u7f51\u7ea2", "existing": "\u8001\u7f51\u7ea2",
                        "\u65b0\u7f51\u7ea2": "\u65b0\u7f51\u7ea2", "\u8001\u7f51\u7ea2": "\u8001\u7f51\u7ea2",
                        "new internet celebrity": "\u65b0\u7f51\u7ea2", "old internet celebrity": "\u8001\u7f51\u7ea2"}
            raw_coop = str(data.get('cooperation_status') or "new").lower()
            coop_val = coop_map.get(raw_coop, "\u65b0\u7f51\u7ea2")
            select_by_id("cooperation", coop_val, "Cooperation Status")

            quality_map = {"unknown": "\u672a\u77e5", "normal": "\u666e\u901a", "ordinary": "\u666e\u901a",
                           "good": "\u4f18\u8d28", "high": "\u4f18\u8d28", "excellent": "\u4f18\u8d28",
                           "blacklist": "\u9ed1\u540d\u5355",
                           "\u672a\u77e5": "\u672a\u77e5", "\u666e\u901a": "\u666e\u901a",
                           "\u4f18\u8d28": "\u4f18\u8d28", "\u9ed1\u540d\u5355": "\u9ed1\u540d\u5355"}
            raw_q = str(data.get('influencer_quality') or "unknown").lower()
            q_val = quality_map.get(raw_q, "\u672a\u77e5")
            select_by_id("quality", q_val, "Influencer Quality")

            email_v = data.get('email') or data.get('contact_email')
            if email_v and '@' in str(email_v):
                fill_by_id("email", email_v, "Contact Email")

            avatar = data.get('profile_picture') or data.get('avatar')
            if avatar:
                upload_by_id("avatarUploader", avatar, "Avatar")

            # ============================================================
            # SECTION 2: Social Media
            # ============================================================
            print("  [2/5] Social Media Info...")
            try:
                # Button has id="addCelebritySocial"
                add_btn = page.locator('#addCelebritySocial').first
                if add_btn.count() > 0:
                    add_btn.scroll_into_view_if_needed()
                    add_btn.click(force=True)
                else:
                    page.evaluate("""() => {
                        const btn = document.querySelector('#addCelebritySocial') ||
                            Array.from(document.querySelectorAll('button')).find(b => (b.innerText||'').includes('\u6dfb\u52a0\u793e\u4ea4\u4fe1\u606f'));
                        if (btn) btn.click();
                    }""")
                page.wait_for_timeout(1200)
                print("    OK Clicked addCelebritySocial")
            except Exception as e:
                print(f"    X Social add btn: {e}")

            platform_map = {
                "youtube": "YouTube", "tiktok": "tiktok", "instagram": "Instagram",
                "facebook": "Facebook", "twitter": "Twitter", "snapchat": "Snapchat",
                "pinterest": "Pinterest", "tumblr": "Tumblr", "reddit": "Reddit"
            }
            raw_plat = str(data.get('platform') or "youtube").lower()
            plat_val = platform_map.get(raw_plat, "YouTube")
            page.evaluate(f"""() => {{
                const rows = Array.from(document.querySelectorAll('tr'));
                for (let row of rows) {{
                    const sel = row.querySelector('select');
                    if (sel && sel.options.length > 1) {{
                        const want = '{plat_val.lower()}';
                        for (let o of sel.options) {{
                            if (o.text.toLowerCase() === want) {{
                                sel.value = o.value;
                                sel.dispatchEvent(new Event('change', {{bubbles:true}}));
                                break;
                            }}
                        }}
                        break;
                    }}
                }}
            }}""")
            print(f"    OK Platform = '{plat_val}'")

            ch_name = data.get('channel_name') or data.get('screen_name') or data.get('nickname')
            if ch_name:
                try:
                    page.wait_for_timeout(500)
                    # Find the account name input in the newly added table row
                    inp = page.locator('input[placeholder="\u793e\u4ea4\u8d26\u53f7"]').first
                    if inp.count() == 0:
                        inp = page.locator('.el-table__row input[type="text"]').first
                    if inp.count() > 0:
                        inp.scroll_into_view_if_needed()
                        inp.click(force=True)
                        inp.fill(str(ch_name))
                        print(f"    OK Channel Name = '{ch_name}'")
                    else:
                        print("    X Channel Name: input not found")
                except Exception as e:
                    print(f"    X Channel Name: {e}")

            ch_link = data.get('channel_link') or data.get('social_link')
            if ch_link:
                try:
                    ta = page.locator('textarea[placeholder*="\u793e\u4ea4\u4e3b\u9875"]').first
                    if ta.count() == 0:
                        ta = page.locator('textarea[placeholder*="\u63a8\u5e7f"]').first
                    if ta.count() == 0:
                        ta = page.locator('.el-table__row textarea').first
                    if ta.count() > 0:
                        ta.scroll_into_view_if_needed()
                        ta.click(force=True)
                        ta.fill(str(ch_link))
                        print(f"    OK Channel Link = '{str(ch_link)[:60]}'")
                    else:
                        print("    X Channel Link: textarea not found")
                except Exception as e:
                    print(f"    X Channel Link: {e}")

            followers = str(data.get('followers') or '')
            if followers:
                import re as _re
                num_m = _re.search(r'(\d+(?:\.\d+)?)', followers)
                if num_m:
                    try:
                        inp = page.locator('input[placeholder="\u7c89\u4e1d\u6570"]').first
                        if inp.count() > 0:
                            inp.fill(num_m.group(1))
                            print(f"    OK Followers = '{num_m.group(1)}'")
                    except: pass
                unit_val = "M" if 'M' in followers.upper() else ("H" if 'H' in followers.upper() else "K")
                page.evaluate(f"""() => {{
                    const rows = Array.from(document.querySelectorAll('tr'));
                    for (let row of rows) {{
                        const sels = row.querySelectorAll('select');
                        if (sels.length >= 2) {{
                            for (let o of sels[1].options) {{
                                if (o.text.trim() === '{unit_val}') {{
                                    sels[1].value = o.value;
                                    sels[1].dispatchEvent(new Event('change', {{bubbles:true}}));
                                    break;
                                }}
                            }}
                            break;
                        }}
                    }}
                }}""")
                print(f"    OK Followers Unit = '{unit_val}'")

            # ============================================================
            # SECTION 3: Shipping Info
            # ============================================================
            print("  [3/5] Shipping Info...")

            name_val = (data.get('consignee') or data.get('name') or
                        data.get('recipient') or data.get('full_name'))
            fill_by_id("fullName", name_val, "Full Name")
            fill_by_id("phone", data.get('phone') or data.get('phone_number'), "Phone")

            country_raw = str(data.get('country') or '').strip()
            country_map = {
                "usa": "United States", "us": "United States", "united states": "United States",
                "uk": "United Kingdom", "united kingdom": "United Kingdom",
                "canada": "Canada", "australia": "Australia", "russia": "Russia",
                "germany": "Germany", "france": "France", "italy": "Italy",
                "spain": "Spain", "japan": "Japan", "brazil": "Brazil",
                "mexico": "Mexico", "vietnam": "Vietnam",
            }
            country_val = country_map.get(country_raw.lower(), country_raw)
            if country_val:
                # Country uses Bootstrap Select plugin - NOT native select.
                # Must: (1) click dropdown trigger to open, (2) click li item by text.
                c_result = page.evaluate(f"""() => {{
                    const want = '{country_val.lower()}';

                    // Strategy 1: Bootstrap Select - click the li item in the open dropdown
                    const openItems = Array.from(document.querySelectorAll(
                        '.bootstrap-select .dropdown-menu li a, .selectpicker + .dropdown-menu li a'
                    ));
                    if (openItems.length > 0) {{
                        const item = openItems.find(a => a.innerText.toLowerCase().includes(want));
                        if (item) {{ item.click(); return 'BS-clicked:' + item.innerText.trim(); }}
                    }}

                    // Strategy 2: Click Bootstrap Select button to open, then click option
                    const bsBtn = document.querySelector(
                        'button[data-id="country"], .bootstrap-select button.dropdown-toggle'
                    );
                    if (bsBtn) {{
                        bsBtn.click();
                        return 'BS-opened';
                    }}

                    // Strategy 3: Native select direct value set + trigger change
                    const s = document.querySelector('#country');
                    if (!s) return 'NOT_FOUND';
                    for (let o of s.options) {{
                        const txt = o.text.toLowerCase();
                        if (txt.includes(want)) {{
                            s.value = o.value;
                            s.dispatchEvent(new Event('change', {{bubbles:true}}));
                            s.dispatchEvent(new Event('input', {{bubbles:true}}));
                            // Also try Bootstrap Select refresh
                            try {{ $(s).selectpicker('val', o.value); }} catch(e) {{}}
                            return 'native-OK:' + o.text;
                        }}
                    }}
                    return 'OPTS:' + Array.from(s.options).slice(1,5).map(o=>o.text).join('|');
                }}""")

                # If Bootstrap Select was just opened, wait and click the item
                if c_result == 'BS-opened':
                    page.wait_for_timeout(500)
                    c_result2 = page.evaluate(f"""() => {{
                        const want = '{country_val.lower()}';
                        const items = Array.from(document.querySelectorAll(
                            '.bootstrap-select .dropdown-menu li a, .open .dropdown-menu li a'
                        ));
                        const item = items.find(a => a.innerText.toLowerCase().includes(want)
                                                  && a.getBoundingClientRect().width > 0);
                        if (item) {{ item.click(); return 'clicked:' + item.innerText.trim(); }}
                        return 'no-item. visible=' + items.length;
                    }}""")
                    page.wait_for_timeout(300)
                    c_result = c_result2

                if c_result and ('OK' in c_result or 'clicked' in c_result):
                    print(f"    OK Country = '{c_result}'")
                else:
                    print(f"    X Country: {c_result}")

            prov_val = (data.get('province') or data.get('state') or
                        data.get('address_state') or data.get('region'))
            fill_by_id("state", prov_val, "State/Province")
            fill_by_id("city", data.get('city') or data.get('address_city'), "City")

            addr_val = (data.get('address') or data.get('street') or
                        data.get('detailed_address') or data.get('address_detail'))
            fill_by_id("address", addr_val, "Address")

            zip_val = (data.get('postal_code') or data.get('zip') or
                       data.get('zip_code') or data.get('zipcode'))
            fill_by_id("zipCode", zip_val, "Zip Code")

            # order_note / note from email → goes to 效果备注 (#effectNote)
            # This is the collaboration agreement text ("Influ agreed to...")
            effect_note = (data.get('order_note') or data.get('note') or
                           data.get('effect_note') or data.get('collab_note') or "")
            if effect_note:
                try:
                    ta = page.locator('#effectNote').first
                    if ta.count() > 0:
                        ta.scroll_into_view_if_needed()
                        ta.fill(str(effect_note))
                        print("    OK Effect Note (效果备注) filled")
                    else:
                        print("    X Effect Note: #effectNote not found")
                except Exception as e:
                    print(f"    X Effect Note: {e}")
            # #orderNote (订单备注) is left empty intentionally

            # ============================================================
            # SECTION 4: Product Info
            # ============================================================
            print("  [4/5] Product Info...")

            prod_link = str(data.get('product_link') or '').strip()
            if prod_link and not prod_link.startswith('http'):
                for dom in ['colestore.ru', 'tikhubs.ru', 'bags-store.ru']:
                    if dom in prod_link:
                        prod_link = 'https://www.' + prod_link.lstrip('/'); break
            prod_link = prod_link if prod_link.startswith('http') else ''

            if prod_link:
                fill_by_id("goodsUrl", prod_link, "Product URL")
                page.wait_for_timeout(800)
                try:
                    btn = page.locator('#getGoodsInfo').first
                    if btn.count() > 0:
                        btn.scroll_into_view_if_needed(); btn.click(force=True)
                        print("    OK Clicked getGoodsInfo")
                        page.wait_for_timeout(3000)
                except Exception as e:
                    print(f"    X getGoodsInfo: {e}")

            if data.get('product_name'):
                fill_by_id("goodsName", data.get('product_name'), "Product Name")
            if data.get('product_brand'):
                fill_by_id("goodsBrand", data.get('product_brand'), "Brand")

            type_map = {"bag": "\u5305\u5305", "bags": "\u5305\u5305", "shoes": "\u978b\u5b50",
                        "accessories": "\u914d\u9970", "\u5305\u5305": "\u5305\u5305",
                        "\u978b\u5b50": "\u978b\u5b50", "\u914d\u9970": "\u914d\u9970"}
            type_raw = str(data.get('product_type') or 'bag').lower()
            type_val = type_map.get(type_raw, "\u5305\u5305")
            select_by_id("goodsType", type_val, "Product Type")
            page.wait_for_timeout(500)

            sku_val = data.get('product_sku') or data.get('product_attribute')
            if sku_val:
                sku_set = page.evaluate(f"""() => {{
                    const s = document.querySelector('#goodsSkuList');
                    if (!s) return false;
                    const want = '{str(sku_val).lower()}';
                    for (let o of s.options) {{
                        if (o.text.toLowerCase().includes(want) || want.includes(o.text.toLowerCase())) {{
                            s.value = o.value;
                            s.dispatchEvent(new Event('change', {{bubbles:true}}));
                            return true;
                        }}
                    }}
                    return false;
                }}""")
                if not sku_set:
                    fill_by_id("goodsSku", sku_val, "SKU/Attribute")

            # ============================================================
            # SECTION 5: Upload Images
            # ============================================================
            print("  [5/5] Uploading Images...")

            m_img = data.get('product_main_image')
            if m_img and os.path.exists(m_img):
                upload_by_id("goodsPosterUploader", m_img, "Main Product Image")

            detail_imgs = []
            for i in range(1, 4):
                d_img = data.get(f'product_detail_image_{i}')
                if d_img and os.path.exists(d_img):
                    detail_imgs.append(d_img)
            if detail_imgs:
                upload_by_id("goodsPictureUploader", detail_imgs, "Detail Images")

            page.screenshot(path="last_browser_state.png")
            print("\n Form filling complete!")

        except Exception as e:
            print(f"❌ Worker Automation Error: {e}")
            err_str = str(e).lower()
            if "closed" in err_str or "connection" in err_str or "target" in err_str or "navigating" in err_str:
                print("⚠️ Resetting active page and browser context references due to error.")
                self.browser_ctx = None
                self.active_page = None
            self.root.after(0, lambda: messagebox.showerror("Automation Error", f"❌ Worker Error: {e}"))

    def browser_click(self, selector=None, x=None, y=None, force=False):
        """Dispatch remote click task."""
        resp_q = queue.Queue()
        self.browser_queue.put({'action': 'click', 'selector': selector, 'x': x, 'y': y, 'force': force, 'response_queue': resp_q})
        try:
            result = resp_q.get(timeout=30)
            if isinstance(result, Exception): raise result
        except queue.Empty:
            raise Exception("Browser command timed out")

    def browser_type(self, selector, text):
        """Dispatch remote typing task."""
        resp_q = queue.Queue()
        self.browser_queue.put({'action': 'type', 'selector': selector, 'text': text, 'response_queue': resp_q})
        try:
            result = resp_q.get(timeout=30)
            if isinstance(result, Exception): raise result
        except queue.Empty:
            raise Exception("Browser command timed out")

    def browser_press(self, key):
        """Dispatch remote press task."""
        resp_q = queue.Queue()
        self.browser_queue.put({'action': 'press', 'key': key, 'response_queue': resp_q})
        try:
            result = resp_q.get(timeout=30)
            if isinstance(result, Exception): raise result
        except queue.Empty:
            raise Exception("Browser command timed out")

    def browser_screenshot(self):
        """Dispatch remote screenshot task."""
        resp_q = queue.Queue()
        self.browser_queue.put({'action': 'screenshot', 'response_queue': resp_q})
        try:
            result = resp_q.get(timeout=30)
            if isinstance(result, Exception): raise result
        except queue.Empty:
            raise Exception("Screenshot command timed out")
    
    def clear_all(self):
        """Clear all fields"""
        if messagebox.askyesno("Confirm", "Clear all fields?"):
            for field in self.fields.values():
                if isinstance(field, tk.Text):
                    field.delete("1.0", "end")
                elif isinstance(field, ttk.Combobox):
                    field.set("")
                else:
                    field.delete(0, "end")
    
    def load_data(self):
        """Load data from JSON file"""
        filename = "erp_data.json"
        if not os.path.exists(filename):
            messagebox.showwarning("Not Found", "No saved data found!")
            return
        
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for key, value in data.items():
            if key in self.fields:
                field = self.fields[key]
                if isinstance(field, tk.Text):
                    field.delete("1.0", "end")
                    field.insert("1.0", value)
                elif isinstance(field, ttk.Combobox):
                    field.set(value)
                else:
                    field.delete(0, "end")
                    field.insert(0, value)
        
        messagebox.showinfo("Loaded", "✅ Data loaded successfully!")

# ─────────────────────────────────────────────
# Global pointer – set by main() after app is created
# so that API handlers can safely call app methods
# ─────────────────────────────────────────────
_app_instance = None


def start_api_server():
    """Launch FastAPI server on localhost:8765 in a daemon thread."""
    if not FASTAPI_AVAILABLE:
        return

    api = FastAPI(title="ERP Bot API", version="1.0")

    # ── Request models ──────────────────────────────────────
    class EmailRequest(BaseModel):
        email: str

    class ProductRequest(BaseModel):
        url: str

    class SocialRequest(BaseModel):
        url: str

    class FieldsRequest(BaseModel):
        fields: dict  # {field_key: value}

    # ── Endpoints ───────────────────────────────────────────

    @api.get("/")
    def health():
        """Health check – verify server is running."""
        return {"status": "ok", "message": "ERP Bot API running on localhost:8765"}

    @api.get("/status")
    def get_status():
        """Return current field values from the UI."""
        if _app_instance is None:
            return JSONResponse(status_code=503, content={"error": "App not ready"})
        try:
            data = {}
            for key, field in _app_instance.fields.items():
                if isinstance(field, tk.Text):
                    data[key] = field.get("1.0", "end").strip()
                elif isinstance(field, ttk.Combobox):
                    data[key] = field.get()
                else:
                    data[key] = field.get()
            return {"status": "ok", "is_processing": _app_instance.active_tasks > 0, "active_tasks": _app_instance.active_tasks, "fields": data}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    @api.get("/screenshot")
    def get_screenshot(target: str = "full"):
        """
        Capture and return the current Windows screen.
        target="full": Entire desktop (default)
        target="app": Crop to ERP application window
        target="browser": The last browser automation view
        """
        if not PILLOW_AVAILABLE:
            return JSONResponse(status_code=501, content={"error": "Pillow not installed. Screenshot disabled."})
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f"c:/Trợ lý AI/remote_screenshot_{timestamp}.png"
            
            if target == "browser":
                # Try to trigger a LIVE screenshot via the worker
                if _app_instance:
                    try:
                        _app_instance.browser_screenshot() # This updates 'last_browser_state.png'
                    except:
                        pass # Fallback to existing file if worker busy/timeout
                
                # Return the last browser state
                browser_path = os.path.join(os.getcwd(), "last_browser_state.png")
                if os.path.exists(browser_path):
                    return FileResponse(browser_path, media_type="image/png")
                else:
                    return JSONResponse(status_code=404, content={"error": "No browser screenshot available yet. Run automation first."})

            # Capture screen
            screenshot = ImageGrab.grab()
            
            if target == "app" and _app_instance:
                # Use root geometry to crop
                # root.winfo_rootx() etc. gets screen coordinates
                x = _app_instance.root.winfo_rootx()
                y = _app_instance.root.winfo_rooty()
                w = _app_instance.root.winfo_width()
                h = _app_instance.root.winfo_height()
                
                # Check if visible/mapped
                if _app_instance.root.winfo_ismapped():
                    screenshot = screenshot.crop((x, y, x + w, y + h))
                else:
                    return JSONResponse(status_code=400, content={"error": "App window is currently minimized or hidden."})

            screenshot.save(save_path)
            
            # Return as image file
            return FileResponse(save_path, media_type="image/png")
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Screenshot failed: {str(e)}"})

    @api.post("/browser/close")
    def api_browser_close():
        """Remote close the browser context."""
        if _app_instance is None:
            return JSONResponse(status_code=533, content={"error": "App instance not found"})
        try:
            _app_instance.close_browser()
            return {"status": "ok", "message": "Browser session closed"}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})
    @api.post("/read-email")
    def api_read_email(req: EmailRequest):
        """
        Trigger full email-read automation.
        Same as typing the email and pressing Enter in the UI.
        Body: { "email": "influencer@gmail.com" }
        """
        if _app_instance is None:
            return JSONResponse(status_code=503, content={"error": "App not ready"})
        try:
            def _run():
                # Use the actual widget: email_reader_input (not fields['auto_email'])
                widget = _app_instance.email_reader_input
                widget.config(state='normal')
                widget.delete(0, 'end')
                widget.insert(0, req.email)
                # Call the actual method inside the UI thread context, silently
                _app_instance.read_email_and_fill(silent=True)
            _app_instance.root.after(0, _run)
            return {"status": "ok", "message": f"Started processing email: {req.email}"}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    @api.post("/scrape-product")
    def api_scrape_product(req: ProductRequest):
        """
        Trigger product scraping from a URL.
        Body: { "url": "https://colestore.ru/product/..." }
        """
        if _app_instance is None:
            return JSONResponse(status_code=503, content={"error": "App not ready"})
        try:
            def _run():
                _app_instance.fields['product_link'].delete(0, 'end')
                _app_instance.fields['product_link'].insert(0, req.url)
                _app_instance.auto_fill_product_info(silent=True)
            _app_instance.root.after(0, _run)
            return {"status": "ok", "message": f"Started scraping: {req.url}"}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    @api.post("/scrape-social")
    def api_scrape_social(req: SocialRequest):
        """
        Trigger social media scraping.
        Body: { "url": "https://youtube.com/@channel" }
        """
        if _app_instance is None:
            return JSONResponse(status_code=503, content={"error": "App not ready"})
        try:
            def _run():
                _app_instance.fields['channel_link'].delete(0, 'end')
                _app_instance.fields['channel_link'].insert(0, req.url)
                _app_instance.auto_fill_social_info(silent=True)
            _app_instance.root.after(0, _run)
            return {"status": "ok", "message": f"Started scraping social: {req.url}"}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    @api.post("/set-fields")
    def api_set_fields(req: FieldsRequest):
        """
        Directly set one or more UI fields.
        Body: { "fields": { "nickname": "JaneDoe", "platform": "YouTube" } }
        """
        if _app_instance is None:
            return JSONResponse(status_code=503, content={"error": "App not ready"})
        try:
            updated = []
            def _run():
                for key, value in req.fields.items():
                    if key in _app_instance.fields:
                        field = _app_instance.fields[key]
                        if isinstance(field, tk.Text):
                            field.delete("1.0", "end")
                            field.insert("1.0", str(value))
                        elif isinstance(field, ttk.Combobox):
                            field.set(str(value))
                        else:
                            field.delete(0, 'end')
                            field.insert(0, str(value))
                        updated.append(key)
            _app_instance.root.after(0, _run)
            return {"status": "ok", "updated_fields": list(req.fields.keys())}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    @api.post("/save-and-submit")
    def api_save_and_submit():
        """
        Trigger Save Data → open browser → fill ERP form.
        (Same as clicking the Save Data button.)
        """
        if _app_instance is None:
            return JSONResponse(status_code=503, content={"error": "App not ready"})
        try:
            _app_instance.root.after(0, lambda: _app_instance.save_data(silent=True))
            return {"status": "ok", "message": "Save & Submit triggered (Silent)"}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    @api.post("/browser/save-order")
    def api_browser_save_order():
        """
        Remote click the '保存订单' button in the active browser page.
        """
        if _app_instance is None:
            return JSONResponse(status_code=503, content={"error": "App not ready"})
        try:
            def _click():
                if _app_instance.active_page:
                    # Find the button and click it
                    btn = _app_instance.active_page.locator('button:has-text("保存订单"), button:has-text("保存")').first
                    if btn.count() > 0:
                        btn.click()
                        print("🎉 Save Order button clicked remotely via API!")
                    else:
                        print("❌ Save Order button not found on active page!")
            _app_instance.root.after(0, _click)
            return {"status": "ok", "message": "Save Order command dispatched"}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    # ── Start server in daemon thread ───────────────────────
    def _run_server():
        uvicorn.run(api, host="0.0.0.0", port=8765, log_level="warning")

    t = threading.Thread(target=_run_server, daemon=True)
    t.start()
    print("🌐 Bot API server started → http://localhost:8765")
    print("   Docs available at: http://localhost:8765/docs")


def main():
    global _app_instance
    root = tk.Tk()
    app = DataEntryApp(root)
    _app_instance = app   # expose to API handlers

    # Start API server (runs in background thread, won't block UI)
    start_api_server()

    # Force window to top for first 10 seconds
    def force_top():
        root.attributes('-topmost', True)
        root.lift()
        for i in range(10):
            root.after(i * 1000, lambda: root.attributes('-topmost', True))
            root.after(i * 1000 + 500, lambda: root.lift())
        root.after(10000, lambda: root.attributes('-topmost', False))

    root.after(100, force_top)
    root.mainloop()


if __name__ == "__main__":
    main()
