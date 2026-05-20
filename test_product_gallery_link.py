from cloakbrowser import launch
import json, sys

url = sys.argv[1]

browser = launch(headless=True)
page = browser.new_page()
page.goto(url, wait_until='networkidle', timeout=90000)
page.wait_for_timeout(5000)

result = page.evaluate(r"""
async () => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const toAbs = (u) => { try { return new URL(u, location.href).href; } catch { return null; } };
  const clean = (u) => {
    if (!u) return null;
    u = String(u).trim();
    if (!u || u.startsWith('data:') || u === 'javascript:;') return null;
    return toAbs(u.replace(/\\u0026/g, '&').split('!')[0]);
  };

  const gallery = document.querySelector('.product-gallery');
  if (!gallery) return { error: 'no-gallery' };

  const seen = new Set();
  const images = [];
  const add = (u, source) => {
    const x = clean(u);
    if (!x || seen.has(x)) return;
    seen.add(x);
    images.push({ url: x, source });
  };

  const getPoster = () => {
    const img = gallery.querySelector('.product-poster img') || gallery.querySelector('img');
    if (!img) return null;
    return img.currentSrc || img.src || img.getAttribute('data-src') || img.getAttribute('data-original') || img.getAttribute('data-image');
  };

  add(getPoster(), 'initial');

  const thumbs = Array.from(gallery.querySelectorAll('.product-thumbnails a, .product-thumbnails img'));
  for (let i = 0; i < thumbs.length; i++) {
    thumbs[i].dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
    if (thumbs[i].click) thumbs[i].click();
    await sleep(1000);
    add(getPoster(), `thumb_${i + 1}`);
  }

  return {
    title: document.title,
    thumbCount: thumbs.length,
    count: images.length,
    images,
    html: gallery.outerHTML
  };
}
""")

print(json.dumps(result, ensure_ascii=False, indent=2))
browser.close()
