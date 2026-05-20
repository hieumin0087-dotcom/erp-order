import json, requests, math
from io import BytesIO
from PIL import Image, ImageDraw

DATA = json.load(open(r'C:\Trợ lý AI\test_gallery_backpack.json','r',encoding='utf-8'))
html = DATA['html']
import re
urls = re.findall(r'src="([^"]+!min\.jpg)"', html, re.I)
urls = [u.split('!')[0] for u in urls]
imgs = []
for u in urls:
    r = requests.get(u, timeout=30, headers={'User-Agent':'Mozilla/5.0'})
    r.raise_for_status()
    img = Image.open(BytesIO(r.content)).convert('RGB')
    imgs.append((u, img))

thumb_w, thumb_h = 260, 260
cols = 2
rows = math.ceil(len(imgs)/cols)
canvas = Image.new('RGB', (cols*thumb_w, rows*(thumb_h+30)), 'white')
draw = ImageDraw.Draw(canvas)
for i, (u, img) in enumerate(imgs):
    r, c = divmod(i, cols)
    x, y = c*thumb_w, r*(thumb_h+30)
    im = img.copy()
    im.thumbnail((thumb_w-10, thumb_h-10))
    px = x + (thumb_w - im.width)//2
    py = y + (thumb_h - im.height)//2
    canvas.paste(im, (px, py))
    draw.text((x+5, y+thumb_h+5), str(i+1), fill='black')

out = r'C:\Users\Admin\Desktop\backpack_gallery_preview.jpg'
canvas.save(out, quality=90)
print(out)
print('\n'.join(urls))
