"""Remove verified archive UI glyphs without changing prose or code.

Dry-run by default. --apply updates the website and local Markdown exports,
backing up every changed file outside the website repository first.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime
from functools import lru_cache
import argparse
import hashlib
import json
import re
import shutil

from lxml import etree
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT/'scripts/note-ui-icon-signatures.json').read_text('utf-8'))
SHAPES = {(s['viewBox'], s['path_sha256']): s['kind'] for s in POLICY['shapes']}
PARSER = MarkdownIt('commonmark')
IMAGE = re.compile(r'!\[[^\]\n]*\]\((?P<src>(?:\.\./assets/|/notes-assets/)[a-f0-9]{20}\.svg)\)')
SEARCH_LINK = re.compile(r'\[([^\[\]\n]*)\]\(https?://(?:zhida\.|www\.)?zhihu\.com/search\?[^\s)]+\)')


@lru_cache(maxsize=None)
def ui_icon_kind(path):
    path = Path(path)
    if not path.is_file() or path.suffix.lower() != '.svg':
        return None
    raw = path.read_bytes()
    xml = etree.fromstring(raw, etree.XMLParser(resolve_entities=False, no_network=True))
    paths = [re.sub(r'\s+', '', node.get('d', '')) for node in xml.iter()
             if isinstance(node.tag, str) and etree.QName(node).localname == 'path']
    digest = hashlib.sha256('\n'.join(paths).encode()).hexdigest()
    return SHAPES.get((xml.get('viewBox'), digest))


def snapshot(text):
    tokens = PARSER.parse(text)
    code = [(t.type, t.info, t.content) for t in tokens if t.type in ('fence', 'code_block')]
    inline_code = []
    prose = []
    images = Counter()
    for token in tokens:
        for child in token.children or []:
            if child.type == 'image':
                images[child.attrGet('src')] += 1
            elif child.type == 'code_inline':
                inline_code.append(child.content)
                prose.append(child.content)
            elif child.type == 'text':
                prose.append(child.content)
    return code, inline_code, ''.join(prose), images


def clean_markdown_ui_images(text, assets):
    """Return cleaned text and per-kind counts; protect fences and inline code."""
    assets = Path(assets)
    before = snapshot(text)
    removable = {src: ui_icon_kind(assets/Path(src).name) for src in before[3]}
    removable = {src: kind for src, kind in removable.items() if kind}
    if not removable and not SEARCH_LINK.search(text):
        return text, {}
    fenced = set()
    for token in PARSER.parse(text):
        if token.type in ('fence', 'code_block') and token.map:
            fenced.update(range(*token.map))
    counts = Counter()

    def remove(match):
        kind = removable.get(match['src'])
        if not kind:
            return match[0]
        counts[kind] += 1
        return ''

    def unwrap_search(match):
        counts['keyword-search-link'] += 1
        return match[1]

    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if index in fenced:
            continue
        chunks = re.split(r'(`+[^`\n]+`+)', line)
        for part in range(0, len(chunks), 2):
            chunks[part] = SEARCH_LINK.sub(unwrap_search, IMAGE.sub(remove, chunks[part]))
        cleaned = ''.join(chunks)
        lines[index] = '' if line.strip() and not cleaned.strip() else cleaned
    result = ''.join(lines)
    after = snapshot(result)
    assert before[:3] == after[:3], 'Cleanup changed article prose or code'
    expected_images = before[3].copy()
    for src in removable:
        del expected_images[src]
    assert expected_images == after[3], 'Cleanup changed a retained image or left a UI glyph'
    assert sum(n for kind, n in counts.items() if kind != 'keyword-search-link') == sum(before[3][src] for src in removable)
    return result, dict(counts)


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--apply', action='store_true')
    options = args.parse_args()
    corpus = ROOT.parent
    collections = [(ROOT/'src/content/posts', ROOT/'public/notes-assets'),
                   (corpus/'markdown_articles', corpus/'markdown_articles/assets'),
                   (corpus/'publish_markdown', corpus/'publish_markdown/assets')]
    plans = []
    for folder, assets in collections:
        for path in sorted(folder.rglob('*.md')):
            if 'assets' in path.relative_to(folder).parts or '_meta' in path.relative_to(folder).parts:
                continue
            original = path.read_text('utf-8-sig')
            result, counts = clean_markdown_ui_images(original, assets)
            if result != original:
                plans.append((path, result, counts))
    backup = corpus/('note-ui-cleanup-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    details = []
    for path, result, counts in plans:
        before_bytes = path.read_bytes()
        if options.apply:
            saved = backup/path.relative_to(corpus)
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, saved)
            path.write_text(result, encoding='utf-8', newline='')
        details.append({'file': path.relative_to(corpus).as_posix(), 'removed': counts,
                        'sha256_before': hashlib.sha256(before_bytes).hexdigest(),
                        'sha256_after': hashlib.sha256(path.read_bytes() if options.apply else result.encode()).hexdigest()})
    if options.apply:
        manifest_path = corpus/'markdown_articles/_meta/manifest.json'
        manifest = json.loads(manifest_path.read_text('utf-8-sig'))
        changes = {str(path.resolve()): counts for path, _, counts in plans}
        for record in manifest:
            path = corpus/'markdown_articles'/record['output']
            if str(path.resolve()) in changes:
                record['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
                record['platform_ui_icons_removed'] = record.get('platform_ui_icons_removed', 0) + sum(n for kind, n in changes[str(path.resolve())].items() if kind != 'keyword-search-link')
                record['platform_keyword_links_removed'] = changes[str(path.resolve())].get('keyword-search-link', 0)
        saved = backup/manifest_path.relative_to(corpus)
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(manifest_path, saved)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    counts = Counter()
    for _, _, kinds in plans:
        counts.update(kinds)
    report = {'applied': options.apply, 'changed_files': len(plans),
              'removed_references_across_copies': sum(counts.values()), 'by_kind': dict(counts),
              'backup': str(backup) if options.apply else None, 'details': details}
    output = ROOT/('notes-ui-icon-cleanup.json' if options.apply else 'notes-ui-icon-preview.json')
    if options.apply:
        (backup/'cleanup-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'details'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
