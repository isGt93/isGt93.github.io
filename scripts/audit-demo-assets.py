"""Read-only inventory of disabled-theme demo resources referenced by built HTML."""
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json
import re
from lxml import html

ROOT=Path(__file__).resolve().parents[1]
CANDIDATES=['assets/anime','assets/desktop-banner','assets/mobile-banner','assets/home',
            'assets/music','assets/projects','images','pio']
DIST=ROOT/'dist'
references={name:[] for name in CANDIDATES}
html_files=list(DIST.rglob('*.html'))
for path in html_files:
    document=html.fromstring(path.read_bytes())
    for element in document.iter():
        for attribute in ('src','href','poster','srcset','data-src','data-srcset','style'):
            value=element.get(attribute)
            if not value:continue
            decoded=unquote(value)
            for candidate in CANDIDATES:
                if re.search(r'(?:^|[\s\"\'(,=]|https?://[^/\s]+)\/?'+re.escape(candidate)+r'/',decoded):
                    references[candidate].append({'html':path.relative_to(DIST).as_posix(),
                                                  'tag':element.tag,'attribute':attribute,'value':value})
        if element.tag=='meta' and element.get('property',element.get('name','')) in ('og:image','twitter:image'):
            value=element.get('content','')
            for candidate in CANDIDATES:
                if '/'+candidate+'/' in unquote(value):
                    references[candidate].append({'html':path.relative_to(DIST).as_posix(),
                                                  'tag':'meta','attribute':'content','value':value})
    # CSS background URLs are actual resources too, rather than code samples.
    for style in document.xpath('//style'):
        for url in re.findall(r'url\(\s*[\"\']?([^\"\')]+)',style.text_content()):
            for candidate in CANDIDATES:
                if '/'+candidate+'/' in unquote(url):
                    references[candidate].append({'html':path.relative_to(DIST).as_posix(),
                                                  'tag':'style','attribute':'url','value':url})
inventory=[]
prefixes=[name+'/' for name in CANDIDATES]
for name in CANDIDATES:
    directory=ROOT/'public'/name
    files=[p for p in directory.rglob('*') if p.is_file()] if directory.exists() else []
    active=[ref for ref in references[name] if not any(ref['html'].startswith(prefix) for prefix in prefixes)]
    inventory.append({'directory':'public/'+name,'absolute_directory':str(directory.resolve()),
                      'files':len(files),'bytes':sum(p.stat().st_size for p in files),
                      'html_resource_references':len(references[name]),
                      'active_page_references':len(active),
                      'self_contained_demo_references':len(references[name])-len(active),
                      'unreferenced_in_current_built_pages':not active,
                      'references':references[name]})
result={'html_files_scanned':len(html_files),
        'generated_page_html_files_scanned':sum(not any(path.relative_to(DIST).as_posix().startswith(prefix) for prefix in prefixes) for path in html_files),
        'candidate_total_bytes':sum(row['bytes'] for row in inventory),
        'scanned_attributes':['src','href','poster','srcset','data-src','data-srcset','style'],
        'also_scanned':['social image meta','inline CSS url'], 'directories':inventory,
        'note':'结合当前已禁用功能配置判断；未删除任何文件，未修改导入素材。'}
(ROOT/'demo-assets-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'html_files':len(html_files),'directories':[{'directory':x['directory'],'bytes':x['bytes'],
                   'references':x['html_resource_references']} for x in inventory]},ensure_ascii=False))
