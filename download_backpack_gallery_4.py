import requests, os
urls = [
    'https://static.colestore.ru/upload/images/20220412/2022041209142350800164.jpg',
    'https://static.colestore.ru/upload/images/20220427/2022042716284551902985.jpg',
    'https://static.colestore.ru/upload/images/20220427/2022042716284526104305.jpg',
    'https://static.colestore.ru/upload/images/20220427/2022042716284522900011.jpg',
]
out_dir = r'C:\Users\Admin\Desktop\backpack_gallery_4'
os.makedirs(out_dir, exist_ok=True)
for i, url in enumerate(urls, 1):
    r = requests.get(url, timeout=30, headers={'User-Agent':'Mozilla/5.0'})
    r.raise_for_status()
    path = os.path.join(out_dir, f'backpack_{i}.jpg')
    open(path, 'wb').write(r.content)
    print(path)
