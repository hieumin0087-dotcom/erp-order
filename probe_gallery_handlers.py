from cloakbrowser import launch
import json

url='https://www.colestore.ru/bags/colestore-louis-vuitton-neverfull-bandouli-re-inside-out-mm-pink-33-x-27-cm.html'

b=launch(headless=True)
p=b.new_page()
p.goto(url, wait_until='networkidle', timeout=90000)
p.wait_for_timeout(5000)

res = p.evaluate(r"""
() => {
  const gallery = document.querySelector('.product-gallery');
  const poster = document.querySelector('.product-poster img');
  const thumbA = document.querySelector('.product-thumbnails a');
  const thumbImg = document.querySelector('.product-thumbnails img');
  const dump = (el) => {
    if (!el) return null;
    const attrs = {};
    for (const a of el.attributes) attrs[a.name] = a.value;
    const keys = [];
    for (const k in el) {
      try {
        const v = el[k];
        if ((k.startsWith('on') && v) || /slick|owl|swiper|gallery|image|thumb|click/i.test(k)) keys.push(k);
      } catch {}
    }
    return {tag: el.tagName, attrs, outer: el.outerHTML, keys: keys.slice(0,200)};
  };
  return {
    gallery: dump(gallery),
    poster: dump(poster),
    thumbA: dump(thumbA),
    thumbImg: dump(thumbImg),
    jquery: !!window.jQuery,
    bodyScripts: Array.from(document.scripts).map(s=>s.src||s.textContent||'').filter(x=>/owl|slick|swiper|gallery|product|thumb/i.test(x)).slice(0,50)
  };
}
""")
print(json.dumps(res, ensure_ascii=False))
b.close()
