from cloakbrowser import launch
import json

url='https://www.colestore.ru/bags/colestore-louis-vuitton-neverfull-bandouli-re-inside-out-mm-pink-33-x-27-cm.html'

b=launch(headless=True)
p=b.new_page()
p.goto(url, wait_until='networkidle', timeout=90000)
p.wait_for_timeout(5000)

# click main product image
try:
    p.locator('.product-poster img').click(timeout=10000)
    p.wait_for_timeout(3000)
except Exception:
    pass

res = p.evaluate(r"""
() => {
  const all = Array.from(document.querySelectorAll('body *')).map((el,i)=>{
    const r = el.getBoundingClientRect();
    const txt = ((el.innerText||'')+' '+(el.className||'')+' '+(el.getAttribute('aria-label')||'')+' '+(el.getAttribute('title')||'')).toLowerCase();
    return {
      i,
      tag: el.tagName,
      cls: el.className || '',
      text: (el.innerText || '').trim().slice(0,80),
      href: el.getAttribute('href') || '',
      src: el.getAttribute('src') || '',
      visible: !!(r.width && r.height),
      x:r.x,y:r.y,w:r.width,h:r.height,
      nextish: /next|right|arrow-right|chevron-right|icon-right|slick-next|owl-next|swiper-button-next|fancybox-button--arrow_right|mfp-arrow-right/.test(txt),
      prevish: /prev|left|arrow-left|chevron-left|icon-left|slick-prev|owl-prev|swiper-button-prev|fancybox-button--arrow_left|mfp-arrow-left/.test(txt),
      closeish: /close|icon-close|fancybox-button--close|mfp-close/.test(txt)
    }
  });
  return {
    title: document.title,
    modalish: all.filter(x => x.visible && (x.nextish || x.prevish || x.closeish || /modal|popup|lightbox|fancybox|magnific|mfp|viewer|zoom/.test(x.cls.toLowerCase()))).slice(0,200),
    imgs: Array.from(document.querySelectorAll('img')).map((img,i)=>({i,src:img.currentSrc||img.src,cls:img.className||'',w:img.getBoundingClientRect().width,h:img.getBoundingClientRect().height})).filter(x=>x.w>50 && x.h>50).slice(0,200)
  };
}
""")
print(json.dumps(res, ensure_ascii=False))
b.close()
