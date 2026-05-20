from cloakbrowser import launch
import json, time

url='https://www.colestore.ru/bags/colestore-louis-vuitton-neverfull-bandouli-re-inside-out-mm-pink-33-x-27-cm.html'

b=launch(headless=True)
p=b.new_page()
p.goto(url, wait_until='networkidle', timeout=90000)
p.wait_for_timeout(5000)

js = r"""
async () => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const toAbs = (u) => { try { return new URL(u, location.href).href; } catch { return null; } };
  const clean = (u) => {
    if (!u) return null;
    u = String(u).trim();
    if (!u || u.startsWith('data:') || u === 'javascript:;') return null;
    return toAbs(u.replace(/\\u0026/g, '&').split('!')[0]);
  };
  const gallery = document.querySelector('.product-gallery, .product-carousel');
  if (!gallery) return {error:'no-gallery'};
  const seen = new Set();
  const out = [];
  const add = (u, source) => {
    const x = clean(u);
    if (!x || seen.has(x)) return;
    seen.add(x);
    out.push({url:x, source});
  };
  const posterNode = () => gallery.querySelector('.product-poster img') || gallery.querySelector('img');
  const addPoster = (source) => {
    const img = posterNode();
    if (!img) return;
    add(img.currentSrc || img.src || img.getAttribute('data-src') || img.getAttribute('data-original') || img.getAttribute('data-image'), source);
  };

  addPoster('initial');

  const thumbs = Array.from(gallery.querySelectorAll('.product-thumbnails a, .product-thumbnails img'));
  for (let i = 0; i < thumbs.length; i++) {
    thumbs[i].dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true}));
    if (thumbs[i].click) thumbs[i].click();
    await sleep(1200);
    addPoster('thumb_'+(i+1));
  }

  gallery.querySelectorAll('*').forEach((el, i) => {
    ['src','data-src','data-original','data-image','data-zoom-image','href'].forEach(attr => add(el.getAttribute && el.getAttribute(attr), 'attr_'+attr+'_'+i));
    const bg = getComputedStyle(el).backgroundImage || '';
    const m = bg.match(/url\(["']?(.*?)["']?\)/i);
    if (m) add(m[1], 'bg_'+i);
  });

  return {
    title: document.title,
    thumbs: thumbs.length,
    posterHtml: (gallery.querySelector('.product-poster')||gallery).innerHTML,
    galleryHtml: gallery.innerHTML,
    images: out
  };
}
"""
res = p.evaluate(js)
print(json.dumps(res, ensure_ascii=False))
b.close()
