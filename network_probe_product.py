from cloakbrowser import launch
import json

url='https://www.colestore.ru/bags/colestore-louis-vuitton-neverfull-bandouli-re-inside-out-mm-pink-33-x-27-cm.html'
logs=[]

b=launch(headless=True)
p=b.new_page()

def on_response(resp):
    try:
        u=resp.url
        if any(x in u.lower() for x in ['image','upload/images','.jpg','.jpeg','.png','.webp','gallery','product']):
            logs.append({'url':u,'status':resp.status,'ct':resp.headers.get('content-type','')})
    except Exception:
        pass

p.on('response', on_response)
p.goto(url, wait_until='networkidle', timeout=90000)
p.wait_for_timeout(8000)

try:
    thumbs = p.locator('.product-thumbnails a, .product-thumbnails img').count()
except Exception:
    thumbs = -1

# try clicking visible things inside gallery
try:
    cnt = p.locator('.product-thumbnails a').count()
    for i in range(cnt):
        try:
            p.locator('.product-thumbnails a').nth(i).click(timeout=5000)
            p.wait_for_timeout(1500)
        except Exception:
            pass
except Exception:
    pass

try:
    cnt = p.locator('.product-thumbnails img').count()
    for i in range(cnt):
        try:
            p.locator('.product-thumbnails img').nth(i).click(timeout=5000)
            p.wait_for_timeout(1500)
        except Exception:
            pass
except Exception:
    pass

# scan global JS vars / script text around product
js = p.evaluate("""() => {
  const out = {};
  out.keys = Object.keys(window).filter(k => /product|gallery|image|thumb/i.test(k)).slice(0,200);
  out.scripts = Array.from(document.scripts).map(s=>s.textContent||'').filter(t=>/upload\/images|product|gallery|thumb/i.test(t)).slice(0,20);
  return out;
}""")

print(json.dumps({'thumbs':thumbs,'responses':logs[-300:], 'js':js}, ensure_ascii=False))
b.close()
