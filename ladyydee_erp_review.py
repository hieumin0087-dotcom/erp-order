from cloakbrowser import launch
from pathlib import Path
import requests, re, json
from urllib.parse import urljoin
from datetime import datetime
from bs4 import BeautifulSoup

BASE = Path(r'C:\Trợ lý AI\tmp_erp_assets')
BASE.mkdir(exist_ok=True)
AVATAR = BASE / 'ladyydee_avatar.jpg'
POSTER = BASE / 'ladyydee_goods_main.jpg'
DETAIL1 = BASE / 'ladyydee_goods_1.jpg'
DETAIL2 = BASE / 'ladyydee_goods_2.jpg'
DETAIL3 = BASE / 'ladyydee_goods_3.jpg'
OUT = r'C:\Users\Admin\Desktop\ladyydee_erp_review.png'
UA={'User-Agent':'Mozilla/5.0'}
DATA = json.load(open(r'C:\Trợ lý AI\erp_data.json','r',encoding='utf-8'))

def safe(s):
    return str(s).encode('ascii', errors='ignore').decode('ascii')

def download(url, path):
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    path.write_bytes(r.content)

for p in [AVATAR, POSTER, DETAIL1, DETAIL2, DETAIL3]:
    try:
        if p.exists():
            p.unlink()
    except Exception:
        pass

avatar_url = None
try:
    html = requests.get(DATA['channel_link'], headers=UA, timeout=30).text
    m = re.search(r'"avatar":\s*\{.*?"thumbnails":\s*\[(.*?)\]', html, re.S)
    if m:
        thumbs = re.findall(r'"url":"(https:[^\"]+)"', m.group(1))
        if thumbs:
            avatar_url = thumbs[-1].replace('\\u0026', '&')
    if not avatar_url:
        m = re.search(r'<link rel="image_src" href="([^"]+)"', html, re.I)
        if m:
            avatar_url = m.group(1)
except Exception:
    pass
if avatar_url:
    try:
        download(avatar_url, AVATAR)
    except Exception as e:
        print('avatardlerr', safe(repr(e)), flush=True)

html = requests.get(DATA['product_link'], headers=UA, timeout=30).text
soup = BeautifulSoup(html, 'html.parser')
gallery = soup.select_one('.product-gallery')
if not gallery:
    raise RuntimeError('No product gallery found on current product page')
imgs = []
for img in gallery.select('img[src]'):
    src = img.get('src')
    full = urljoin(DATA['product_link'], src)
    base = full.split('!')[0]
    if base not in imgs:
        imgs.append(base)
print('product_gallery_imgs', imgs, flush=True)
if not imgs:
    raise RuntimeError('No product gallery images found on current product page')

download(imgs[0], POSTER)
for i, src in enumerate(imgs[1:4], start=1):
    download(src, [DETAIL1, DETAIL2, DETAIL3][i-1])

browser = launch(headless=True)
page = browser.new_page()
page.set_viewport_size({"width": 1440, "height": 3400})
page.set_default_timeout(40000)

page.goto('https://erp.bx123.pro/admin/login', wait_until='domcontentloaded', timeout=45000)
page.wait_for_timeout(2000)
if page.locator('#userName').count():
    page.fill('#userName', 'panjinying')
if page.locator('#password').count():
    page.fill('#password', 'LIrong2025')
if page.locator('button[type="submit"]').count():
    page.click('button[type="submit"]')
page.wait_for_timeout(4000)

page.goto('https://erp.bx123.pro/celebrityOrder/save', wait_until='domcontentloaded', timeout=45000)
page.wait_for_timeout(5000)

vals = {
    '#screenName': DATA['nickname'],
    '#contact': DATA['contact_info'],
    '#goodsUrl': DATA['product_link'],
    '#goodsName': DATA['product_name'],
    '#goodsBrand': DATA['product_brand'],
    '#goodsSku': DATA['product_sku'],
    '#effectNote': DATA['order_note'],
}
for sel, val in vals.items():
    page.fill(sel, str(val))

for sel, value in [('#contactType','2'),('#cooperation','1'),('#quality','0'),('#country','US'),('#goodsType','accessories')]:
    page.select_option(sel, value=value)

for sel,val in [('input[placeholder*="邮箱"]', DATA['contact_email']),('input[placeholder*="姓名"]', DATA['consignee']),('input[placeholder*="电话"]', DATA['phone']),('input[placeholder*="省"]', DATA['province']),('input[placeholder*="城市"]', DATA['city']),('input[placeholder*="地址"]', DATA['address'])]:
    page.fill(sel, str(val))

for sel in ['input[placeholder*="邮编"]','input[placeholder*="邮政"]']:
    try:
        page.fill(sel, str(DATA['postal_code']))
        break
    except Exception:
        pass

today = datetime.now().strftime('%Y-%m-%d')
page.evaluate("(v)=>{ const el=document.querySelector('#cooperationTime'); if(el){ el.removeAttribute('readonly'); el.value=v; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); } }", today)

page.click('#addCelebritySocial')
page.wait_for_timeout(1000)
page.select_option('select[name="socialList[0].socialType"]', value='4')
page.fill('input[name="socialList[0].socialId"]', DATA['channel_name'])
page.fill('textarea[name="socialList[0].socialUrl"]', DATA['channel_link'])
page.fill('input[name="socialList[0].socialFans"]', str(DATA['followers']))
page.select_option('select[name="socialList[0].socialFansUnit"]', value=DATA['followers_unit'])

def upload_via_plugin(input_sel, files, preview_sel=None):
    page.set_input_files(input_sel, files)
    page.wait_for_timeout(1500)
    page.evaluate("(sel)=>{ const input=document.querySelector(sel); if(!input) return; let root=input.parentElement; for(let i=0;i<8 && root;i++,root=root.parentElement){ const btn=root.querySelector('.fileinput-upload-button, .kv-fileinput-upload, button.fileinput-upload, #ctlBtn, button.btn-default'); if(btn && btn.offsetParent!==null){ btn.click(); return; } } const btn=[...document.querySelectorAll('.fileinput-upload-button, .kv-fileinput-upload, button.fileinput-upload, #ctlBtn, button.btn-default')].find(b=>b.offsetParent!==null); if(btn) btn.click(); }", input_sel)
    page.wait_for_timeout(5000)
    if preview_sel:
        print('preview', preview_sel, page.locator(preview_sel+' img').count(), flush=True)

if AVATAR.exists():
    upload_via_plugin('#avatarUploader', str(AVATAR), '#avatarShow')
upload_via_plugin('#goodsPosterUploader', str(POSTER), '#goodsPosterShow')
detail_files=[str(p) for p in [DETAIL1, DETAIL2, DETAIL3] if p.exists()]
if detail_files:
    upload_via_plugin('#goodsPictureUploader', detail_files, '#goodsPictureShow')

page.wait_for_timeout(4000)
print('avatar imgs', page.locator('#avatarShow img').count(), flush=True)
print('poster imgs', page.locator('#goodsPosterShow img').count(), flush=True)
print('detail imgs', page.locator('#goodsPictureShow img').count(), flush=True)
page.screenshot(path=OUT, full_page=True)
print('shot', OUT, flush=True)
browser.close()
