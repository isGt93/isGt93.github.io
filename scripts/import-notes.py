"""Import the reviewed local Markdown collection into stable Astro post URLs.

published is the source's *recorded* date for theme sorting compatibility. For
edited-only sources, dateKind/dateNote and updated retain that distinction.
"""
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
import hashlib
import json
import os
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from repair_note_svg import repair as repair_svg_copies
from clean_note_ui_icons import clean_markdown_ui_images
from markdown_it import MarkdownIt
from markdown_it.common.utils import unescapeAll

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT.parent/'markdown_articles'
POSTS = ROOT/'src/content/posts'
ASSETS = ROOT/'public/notes-assets'
PARSER = MarkdownIt('commonmark')

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def yaml_text(value):
    return json.dumps(value, ensure_ascii=False)

def blocks(text):
    return [t.content for t in PARSER.parse(text) if t.type in ('fence', 'code_block')]

def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    manifest = load(CORPUS/'_meta/manifest.json')
    sources = {r['id']:r for r in load(ROOT.parent/'reading_memory/manifest.json')}
    summaries = {r['id']:r for r in load(ROOT.parent/'article_summaries/summaries.json')}
    notes = {r['id']:r for r in load(ROOT.parent/'reading_memory/article_notes.json')}
    targets = {(CORPUS/r['output']).resolve():r['id'].lower() for r in manifest}
    POSTS.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    # Remove only known template entries and the importer-owned aNNNN files;
    # preserve future manually authored posts in this collection.
    assert POSTS.resolve().is_relative_to(ROOT.resolve())
    demo_posts = {'content-pipeline-fixture.mdx', 'draft.md', 'encrypted-post.md',
                  'image-grid-demo.md', 'markdown-extended.md', 'markdown-mermaid.md',
                  'markdown-tutorial.md', 'video.md', 'guide/index.md'}
    for p in POSTS.rglob('*'):
        relative = p.relative_to(POSTS).as_posix()
        if p.is_file() and (relative in demo_posts or re.fullmatch(r'a\d{4}\.md', relative)):
            p.unlink()
    used_assets = {}
    output_names = {}
    report = []
    rewritten_links = 0
    removed_ui_icons = 0
    for record in sorted(manifest, key=lambda r:r['id']):
        aid = record['id']; source = CORPUS/record['output']
        original = source.read_text(encoding='utf-8-sig')
        original, removed_icons = clean_markdown_ui_images(original, CORPUS/'assets')
        removed_ui_icons += sum(removed_icons.values())
        summary = summaries[aid]
        title = unescapeAll(original.splitlines()[0].removeprefix('# ').strip())
        body = re.sub(r'\A# [^\n]+\n+', '', original, count=1)
        fenced = set()
        for t in PARSER.parse(body):
            if t.type in ('fence', 'code_block') and t.map:
                fenced.update(range(*t.map))
        def replace_url(match):
            nonlocal rewritten_links
            before, raw_url, after = match.groups()
            u = urlsplit(raw_url)
            if u.scheme or u.netloc or not u.path:
                return match[0]
            local = (source.parent/unquote(u.path)).resolve()
            if local in targets:
                rewritten_links += 1
                return before+'/posts/'+targets[local]+'/'+('#'+u.fragment if u.fragment else '')+after
            if local.is_relative_to((CORPUS/'assets').resolve()):
                if not local.is_file():
                    raise FileNotFoundError(f'{aid}: {raw_url}')
                name = local.name
                if name in used_assets and file_hash(used_assets[name]) != file_hash(local):
                    raise ValueError(f'资产文件名冲突 {name}')
                used_assets[name] = local
                if name not in output_names:
                    if local.suffix.lower()=='.png':
                        with Image.open(local) as image:
                            output_names[name] = local.stem+'.webp' if getattr(image,'n_frames',1)==1 else name
                    else:
                        output_names[name] = name
                return before+'/notes-assets/'+quote(output_names[name])+after
            if u.path.lower().endswith('.md'):
                raise ValueError(f'无法映射文章链接 {aid}: {raw_url}')
            return match[0]
        url_pattern = re.compile(r'(\]\()([^\s)]+)(\))')
        lines = body.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if i in fenced:
                continue
            # Protect literal inline-code examples while rewriting prose links.
            chunks = re.split(r'(`+[^`\n]+`+)', line)
            for j in range(0, len(chunks), 2):
                chunks[j] = url_pattern.sub(replace_url, chunks[j])
            lines[i] = ''.join(chunks)
        body = ''.join(lines)
        if blocks(original) != blocks(body):
            raise ValueError(f'代码在导入时变化 {aid}')
        if not re.match(r'ailx10说：[^\n]+\n\s*\n---\s*\n', body):
            raise ValueError(f'摘要或分隔符缺失 {aid}')
        date = summary['date']
        if not date:
            raise ValueError(f'缺少原始日期 {aid}')
        edited = summary['date_kind']=='编辑于'
        frontmatter = ['---', 'title: '+yaml_text(title), 'published: '+date]
        if edited:
            frontmatter.append('updated: '+date)
        frontmatter += [
            'dateKind: '+yaml_text('edited' if edited else 'published'),
            'dateNote: '+yaml_text('原文最后编辑日期；首次写作日期未单独记录' if edited else '原文发布日期'),
            'description: '+yaml_text(summary['summary'].removeprefix('ailx10说：').strip()),
            'tags: '+yaml_text(list(dict.fromkeys(notes.get(aid,{}).get('tags',[])))[:8]),
            'category: '+yaml_text(sources[aid]['group']),
            'lang: "zh-CN"', 'author: "ailx10"', 'draft: false', 'comment: false',
            'image: ""', '---', '', body.rstrip(), '']
        target = POSTS/(aid.lower()+'.md')
        target.write_text('\n'.join(frontmatter), encoding='utf-8')
        report.append({'id':aid, 'file':target.relative_to(ROOT).as_posix(),
                       'url':'/posts/'+aid.lower()+'/', 'dateKind':'edited' if edited else 'published',
                       'date':date, 'code_blocks':len(blocks(body)),
                       'source_sha256':file_hash(source), 'output_sha256':file_hash(target)})
    def prepare_asset(item):
        name,source=item; target=ASSETS/output_names[name]
        converted = output_names[name] != name
        if converted:
            with Image.open(source) as original:
                pixels=original.convert('RGBA')
                if not target.exists():
                    pixels.save(target,format='WEBP',lossless=True,exact=True,method=4,
                                icc_profile=original.info.get('icc_profile',b''))
                with Image.open(target) as generated:
                    if generated.size != original.size or generated.convert('RGBA').tobytes()!=pixels.tobytes():
                        raise ValueError(f'无损图像像素核对失败 {name}')
        else:
            if target.exists() and os.path.samefile(source,target):
                target.unlink()
                shutil.copy2(source,target)
            elif not target.exists() or file_hash(target)!=file_hash(source):
                if target.exists():target.unlink()
                shutil.copy2(source,target)
        return int(converted)
    with ThreadPoolExecutor(max_workers=4) as pool:
        lossless_count=sum(pool.map(prepare_asset,used_assets.items()))
    svg_repairs=repair_svg_copies(ASSETS)
    (ROOT/'notes-svg-repair-report.json').write_text(json.dumps(svg_repairs,ensure_ascii=False,indent=2),encoding='utf-8')
    # Drop only superseded PNG copies in this importer-owned asset directory.
    # The original Markdown corpus and source images remain untouched.
    assert ASSETS.resolve().is_relative_to((ROOT/'public').resolve())
    for name in used_assets:
        old=ASSETS/name
        if output_names[name]!=name and old.is_file():old.unlink()
    sizes = sorted([((ASSETS/output_names[name]).stat().st_size,output_names[name])
                    for name in used_assets], reverse=True)
    total = sum(s for s,_ in sizes)
    result = {'articles':len(report), 'assets':len(used_assets), 'asset_bytes':total,
              'source_ui_icons_removed':removed_ui_icons,
              'largest_assets':[{'name':name,'bytes':size} for size,name in sizes[:15]],
              'rewritten_article_links':rewritten_links,
              'source_asset_bytes':sum(p.stat().st_size for p in used_assets.values()),
              'lossless_png_webp_verified':lossless_count,
              'svg_xml_repairs':sum(bool(r.get('error')) for r in svg_repairs),
              'svg_root_styles_migrated':sum(bool(r.get('root_style_moved')) for r in svg_repairs),
              'code_blocks_verified':sum(r['code_blocks'] for r in report),
              'dates':{'edited':sum(r['dateKind']=='edited' for r in report),
                       'published':sum(r['dateKind']=='published' for r in report)},
              'excluded_entries':[{'id':'A0026','reason':'只有课程导读与外链，无独立技术正文'},
                                  {'id':'A0171','reason':'原文缺失'},
                                  {'id':'A0699','reason':'历史咨询促销，无独立技术正文'}]}
    (ROOT/'notes-import-report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT/'notes-import-manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    main()
