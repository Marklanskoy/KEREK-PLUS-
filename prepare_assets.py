"""Optional demo-photo download. Requires network and requirements.txt.
Downloads only URLs already listed in the seed. Failed images retain fallbacks.
Photos are illustrations, not verified supplier packshots. See docs/ASSETS.md.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request,io,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
PHOTOS=json.loads((ROOT/'server/seed.json').read_text('utf-8'))['photoIds']
def download(item):
 name,pid=item
 url=f'https://images.unsplash.com/photo-{pid}?auto=format&fit=crop&w={1200 if name=="hero" else 600}&q=82'
 path=ROOT/'public/assets/photos'/f'{name}.webp'
 try:
  with urllib.request.urlopen(url,timeout=12) as response:data=response.read(12_000_000)
  im=Image.open(io.BytesIO(data));im.load();im=im.convert('RGB');im.thumbnail((1200,900) if name=='hero' else (600,600));im.save(path,'WEBP',quality=80)
  return name,f'assets/photos/{name}.webp',None
 except Exception as error:return name,None,str(error)
def main():
 (ROOT/'public/assets/photos').mkdir(parents=True,exist_ok=True)
 with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(download,PHOTOS.items()))
 mapping={name:path for name,path,error in results if path}
 (ROOT/'public/js/photos.js').write_text('window.KEREK_LOCAL_PHOTOS='+json.dumps(mapping)+';\n',encoding='utf-8')
 for name,path,error in results:print(name,':',path or 'not downloaded: '+error)
 print(f'Local images: {len(mapping)}/{len(PHOTOS)}. Rebuild standalone HTML with scripts/build.py.')
if __name__=='__main__':main()
