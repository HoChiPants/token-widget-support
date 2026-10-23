#!/usr/bin/env python3
"""Render and check static link previews: --write, --probe, --live."""
import argparse,json,struct,subprocess,re
from pathlib import Path
from html import escape
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
class Tags(HTMLParser):
 def __init__(self):super().__init__();self.meta={};self.links={};self.videos=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='meta' and (k:=a.get('property',a.get('name'))):self.meta.setdefault(k,[]).append(a.get('content',''))
  if tag=='link':self.links.setdefault(a.get('rel'),[]).append(a.get('href',''))
  if tag=='source' and a.get('type')=='video/mp4':self.videos.append(a.get('src'))
def expected(base,a,page):
 video=urljoin(base,a['video']);poster=urljoin(base,a['poster']);url=urljoin(base,page.removesuffix('index.html'))
 return {'og:type':'website','og:site_name':'Studio Minden','og:title':a['app'],'og:description':a['tagline'],'og:url':url,'og:image':poster,'og:image:type':'image/jpeg','og:image:width':str(a['posterWidth']),'og:image:height':str(a['posterHeight']),'og:image:alt':a['app']+' app preview','og:video':video,'og:video:secure_url':video,'og:video:type':'video/mp4','og:video:width':str(a['width']),'og:video:height':str(a['height']),'twitter:card':'summary_large_image','twitter:title':a['app'],'twitter:description':a['tagline'],'twitter:image':poster}
def render(base,a,page):
 p=ROOT/page;s=p.read_text();head,body=s.split('</head>',1)
 head=re.sub(r'\s*<!-- Link preview metadata -->.*?<!-- /Link preview metadata -->','',head,flags=re.S)
 head=re.sub(r'\s*<meta\b(?=[^>]*(?:property|name)=[\"\'](?:og:|twitter:))[^>]*>','',head,flags=re.I)
 head=re.sub(r'\s*<link\b(?=[^>]*rel=[\"\']canonical[\"\'])[^>]*>','',head,flags=re.I)
 meta=expected(base,a,page)
 lines=['<!-- Link preview metadata -->',f'<link rel="canonical" href="{escape(meta["og:url"],quote=True)}">']
 for k,v in meta.items():lines.append(f'<meta {"name" if k.startswith("twitter:") else "property"}="{k}" content="{escape(v,quote=True)}">')
 lines+=['<style>.app-link-preview{margin:36px 0}.app-link-preview video{display:block;width:100%;max-width:360px;height:auto;border-radius:16px;background:#121a18}.app-link-preview video.landscape{max-width:720px}.app-link-preview p{font-size:14px}</style>','<!-- /Link preview metadata -->']
 body=re.sub(r'\s*<!-- App preview player -->.*?<!-- /App preview player -->','',body,flags=re.S)
 label='Screen captures from the app.' if a['kind']=='screenshots' else ('Recorded on iPhone. Names edited; actual recap results.' if a['slug']=='chatrecap' else 'Recorded offline gameplay.')
 video=meta['og:video'];poster=meta['og:image'];land=' class="landscape"' if a['width']>a['height'] else ''
 player=f'''\n<!-- App preview player -->
<section class="app-link-preview" aria-labelledby="app-preview-heading">
<h2 id="app-preview-heading">App preview</h2>
<video{land} controls playsinline preload="none" poster="{poster}" width="{a['width']}" height="{a['height']}" aria-label="{escape(a['app'])} app preview">
<source src="{video}" type="video/mp4">
<a href="{video}">Watch the {escape(a['app'])} preview</a>
</video>
<p>{label}</p>
</section>
<!-- /App preview player -->\n'''
 anchor='</main>' if '</main>' in body else '<footer'
 assert anchor in body,page
 body=body.replace(anchor,player+anchor,1)
 result=head+'\n'+'\n'.join(lines)+'\n</head>'+body
 if 'default-src' in result and "media-src" not in result:result=result.replace("default-src 'none';", "default-src 'none'; img-src 'self'; media-src 'self';")
 result='\n'.join(line.rstrip() for line in result.splitlines())
 result=re.sub(r'\n{2,}','\n',result).rstrip()+'\n'
 p.write_text(result)
def check_faststart(p):
 data=p.read_bytes();pos=0;order=[]
 while pos+8<=len(data):
  size,kind=struct.unpack('>I4s',data[pos:pos+8]);header=8
  if size==1:size=struct.unpack('>Q',data[pos+8:pos+16])[0];header=16
  if size==0:size=len(data)-pos
  assert size>=header and pos+size<=len(data),f'invalid MP4 box: {p}'
  order.append(kind);pos+=size
 assert b'moov' in order and b'mdat' in order and order.index(b'moov')<order.index(b'mdat'),f'MP4 is not fast-start: {p}'
def live(url,mime,size=None,content=None,range_check=False):
 with urlopen(Request(url,method='HEAD'),timeout=30) as r:
  assert r.status==200,(url,r.status)
  assert r.headers.get_content_type()==mime,(url,r.headers.get_content_type())
  if size is not None:assert int(r.headers['Content-Length'])==size,(url,'size mismatch')
 if content is not None:
  with urlopen(url,timeout=30) as r:assert r.read()==content,(url,'HTML mismatch')
 if range_check:
  with urlopen(Request(url,headers={'Range':'bytes=0-1023'}),timeout=30) as r:
   assert r.status==206 and r.headers.get('Content-Range','').startswith('bytes 0-1023/'),(url,'range request failed')
   assert r.read()==content[:1024] if content is not None else len(r.read())==1024
parser=argparse.ArgumentParser(description=__doc__)
for arg in ['write','probe','live']:parser.add_argument('--'+arg,action='store_true')
args=parser.parse_args();config=json.loads((ROOT/'link-previews.json').read_text());base=config['baseUrl'];checked=[]
assert base.startswith('https://')
for a in config['previews']:
 for field in ['video','poster']:
  p=(ROOT/a[field]).resolve();assert p.is_relative_to(ROOT) and p.is_file(),a[field]
 video=ROOT/a['video'];poster=ROOT/a['poster'];check_faststart(video)
 assert video.stat().st_size==a['videoBytes'] and poster.stat().st_size==a['posterBytes']
 assert a['posterWidth']>=900
 assert video.stat().st_size+poster.stat().st_size+100_000<10_000_000,a['slug']+' exceeds Messages resource budget'
 if args.probe:
  probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=codec_name,pix_fmt,width,height:format=duration','-of','json',str(video)]))
  v=probe['streams'][0];assert v['codec_name']=='h264' and v['pix_fmt']=='yuv420p',(a['slug'],v)
  assert (v['width'],v['height'])==(a['width'],a['height'])
  assert abs(float(probe['format']['duration'])-a['duration'])<.1
 for page in a['pages']:
  if args.write:render(base,a,page)
  p=ROOT/page;html=p.read_text();assert p.stat().st_size<1_000_000
  tags=Tags();tags.feed(html)
  for k,v in expected(base,a,page).items():assert tags.meta.get(k)==[v],(page,k,tags.meta.get(k),v)
  assert tags.links.get('canonical')==[urljoin(base,page.removesuffix('index.html'))]
  assert tags.videos==[urljoin(base,a['video'])]
  if args.live:live(urljoin(base,page.removesuffix('index.html')),'text/html',content=p.read_bytes())
  checked.append(page)
 if args.live:
  live(urljoin(base,a['video']),'video/mp4',video.stat().st_size,range_check=True)
  live(urljoin(base,a['poster']),'image/jpeg',poster.stat().st_size)
 print(f"PASS {a['app']}: {a['width']}×{a['height']}, {a['duration']}s, {(a['videoBytes']+a['posterBytes'])/1e6:.2f} MB video + poster")
print(f"Verified {len(config['previews'])} previews across {len(checked)} pages"+(' including live HTTPS and MP4 range requests' if args.live else ' locally'))
