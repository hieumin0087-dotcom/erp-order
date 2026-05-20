from cloakbrowser import launch

url='https://www.colestore.ru/bags/colestore-louis-vuitton-neverfull-bandouli-re-inside-out-mm-pink-33-x-27-cm.html'
b=launch(headless=True)
p=b.new_page()
p.goto(url, wait_until='domcontentloaded', timeout=60000)
p.wait_for_timeout(7000)
print('gallery_html_start')
try:
    print(p.locator('.product-gallery').inner_html())
except Exception as e:
    print('galleryerr', repr(e))
print('gallery_html_end')
print('imgs_start')
try:
    print(p.evaluate("""() => Array.from(document.querySelectorAll('.product-gallery img')).map(i => ({src:i.src, alt:i.alt, cls:i.className}))"""))
except Exception as e:
    print('imgserr', repr(e))
print('imgs_end')
print('thumb_links_start')
try:
    print(p.evaluate("""() => Array.from(document.querySelectorAll('.product-gallery a, .product-gallery [data-src], .product-gallery [data-image]')).map(el => ({tag:el.tagName, href:el.href||'', ds:el.getAttribute('data-src')||'', di:el.getAttribute('data-image')||'', os:el.getAttribute('onclick')||''}))"""))
except Exception as e:
    print('linkerr', repr(e))
print('thumb_links_end')
b.close()
