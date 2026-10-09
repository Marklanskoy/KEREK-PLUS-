"""Package source and a self-contained static preview; exclude all runtime data.
Usage: python scripts/build.py [--output /path/to/output]
No Node.js, third-party bundler or internet is required.
"""
from pathlib import Path
import argparse,base64,json,re,zipfile,hashlib
ROOT=Path(__file__).resolve().parents[1]

def standalone():
 html=(ROOT/'public/index.html').read_text('utf-8')
 css=(ROOT/'public/styles.css').read_text('utf-8')
 icon='data:image/svg+xml;base64,'+base64.b64encode((ROOT/'public/assets/icon.svg').read_bytes()).decode()
 html=html.replace('<link rel="stylesheet" href="styles.css">','<style>'+css+'</style>')
 html=html.replace('<link rel="manifest" href="manifest.webmanifest">','').replace('href="assets/icon.svg"','href="'+icon+'"')
 flag='<script>window.KEREK_STANDALONE=true;window.KEREK_ICON_DATA='+json.dumps(icon)+';</script>'
 html=html.replace('<script src="js/photos.js">',flag+'<script src="js/photos.js">')
 def inline(m):
  name=m.group(1);js=(ROOT/'public/js'/name).read_text('utf-8')
  if name=='photos.js':
   try:mapping=json.loads(re.search(r'window.KEREK_LOCAL_PHOTOS\s*=\s*(\{.*\})',js,re.S).group(1))
   except (AttributeError,json.JSONDecodeError):mapping={}
   embedded={}
   for key,path in mapping.items():
    source=(ROOT/'public'/path).resolve()
    if source.is_relative_to(ROOT/'public/assets/photos') and source.is_file():embedded[key]='data:image/webp;base64,'+base64.b64encode(source.read_bytes()).decode()
   js='window.KEREK_LOCAL_PHOTOS='+json.dumps(embedded)+';'
  return '<script>'+js.replace('</script','<\\/script')+'</script>'
 return re.sub(r'<script src="js/([^\"]+\.js)"></script>',inline,html)

def source_files():
 blocked={'.git','.venv','__pycache__','.pytest_cache','build','node_modules'}
 for path in sorted(ROOT.rglob('*')):
  rel=path.relative_to(ROOT)
  if not path.is_file() or any(part in blocked for part in rel.parts):continue
  if str(rel).startswith('server/data/') or str(rel).startswith('public/assets/uploads/'):continue
  if path.name=='.env' or path.suffix in {'.pyc','.sqlite3','.zip'} or path.name.startswith('.DS_Store'):continue
  yield path,rel.as_posix()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'build');args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
 html=standalone();preview=out/'KEREK_3_0.html';preview.write_text(html,'utf-8')
 archive=out/'KEREK_3_0.zip';manifest=[]
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for path,rel in source_files():
   if path.resolve() in {preview,archive}:continue
   data=path.read_bytes();z.writestr('KEREK_3_0/'+rel,data);manifest.append(hashlib.sha256(data).hexdigest()+'  '+rel)
  z.writestr('KEREK_3_0/KEREK_3_0.html',html.encode());z.writestr('KEREK_3_0/SOURCE_SHA256SUMS.txt','\n'.join(manifest)+'\n')
 with zipfile.ZipFile(archive) as z:
  if z.testzip():raise RuntimeError('Archive CRC validation failed')
 print(f'{preview} — {preview.stat().st_size:,} bytes')
 print(f'{archive} — {archive.stat().st_size:,} bytes; {len(manifest)} source files')
if __name__=='__main__':main()
