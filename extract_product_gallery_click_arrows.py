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
  if (!gallery) return {error:'no-gallery'};
  const rect = gallery.getBoundingClientRect();
  const nodes = Array.from(gallery.querySelectorAll('*')).map((el, i) => {
    const r = el.getBoundingClientRect();
    return {
      i,
      tag: el.tagName,
      cls: el.className || '',
      text: (el.innerText || '').trim(),
      aria: el.getAttribute('aria-label') || '',
      title: el.getAttribute('title') || '',
      href: el.getAttribute('href') || '',
      src: el.getAttribute('src') || '',
      w: r.width, h: r.height, x: r.x, y: r.y
    };
  });
  return {gallery:{x:rect.x,y:rect.y,w:rect.width,h:rect.height}, nodes};
}
""")
print(json.dumps(res, ensure_ascii=False))
b.close()
