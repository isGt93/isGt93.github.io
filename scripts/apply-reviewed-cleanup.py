"""Preview or apply reviewed corrections and synchronize both Markdown exports.

Article-specific rules live in note-editorial-cleanup.json. Existing canonical
Markdown must match the website before this command can replace either copy.
"""
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from datetime import datetime
from collections import Counter
import argparse
import hashlib
import json
import os
import re
import zipfile

from markdown_it import MarkdownIt
from clean_note_editorial import clean_note_body, fences, POLICY_PATH

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
CORPUS = WORKSPACE/'markdown_articles'
PUBLISH = WORKSPACE/'publish_markdown'
POSTS = ROOT/'src/content/posts'
PARSER = MarkdownIt('commonmark')


def images(text):
    result = Counter()
    for token in PARSER.parse(text):
        for child in token.children or []:
            if child.type == 'image':
                result[child.attrGet('src')] += 1
    return result


def reverse_urls(body, source, targets):
    protected = set()
    for token in PARSER.parse(body):
        if token.type in ('fence', 'code_block') and token.map:
            protected.update(range(*token.map))

    def rewrite(match):
        parsed = urlsplit(match[2])
        path = parsed.path
        if path.startswith('/notes-assets/'):
            asset = Path(unquote(path)).name
            if not (CORPUS/'assets'/asset).is_file() and asset.endswith('.webp') and (CORPUS/'assets'/(asset[:-5]+'.png')).is_file():
                asset = asset[:-5]+'.png'
            target = CORPUS/'assets'/asset
            if not target.is_file():
                raise FileNotFoundError(target)
        elif re.fullmatch('/posts/a[0-9]{4}/', path):
            target = targets[path.split('/')[2]]
        else:
            return match[0]
        relative = Path(os.path.relpath(target, source.parent)).as_posix()
        return match[1]+quote(relative, safe='/')+('#'+parsed.fragment if parsed.fragment else '')+match[3]

    lines = body.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if index in protected:
            continue
        parts = re.split(r'(`+[^`\n]+`+)', line)
        for part in range(0, len(parts), 2):
            parts[part] = re.sub(r'(\]\()([^\s)]+)(\))', rewrite, parts[part])
        lines[index] = ''.join(parts)
    return ''.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    manifest_path = CORPUS/'_meta/manifest.json'
    manifest = json.loads(manifest_path.read_text('utf-8-sig'))
    targets = {record['id'].lower(): CORPUS/record['output'] for record in manifest}
    policy = json.loads(POLICY_PATH.read_text('utf-8'))['articles']
    changes = {}
    details = []
    image_total = 0
    code_total = 0
    for record in manifest:
        article_id = record['id']
        source = targets[article_id.lower()]
        post = POSTS/(article_id.lower()+'.md')
        original = post.read_text('utf-8-sig')
        front, body = original.split('\n---\n', 1)
        canonical = source.read_text('utf-8-sig')
        heading = canonical.splitlines()[0]
        roundtrip = heading+'\n\n'+reverse_urls(body.lstrip(), source, targets).rstrip()+'\n'
        if roundtrip != canonical:
            raise ValueError(f'Canonical Markdown has independent edits; import first: {article_id}')
        cleaned, counts = clean_note_body(body, article_id, policy)
        updated = front+'\n---\n'+cleaned
        assert fences(original) == fences(updated), article_id
        before_images, after_images = images(body), images(cleaned)
        allowed_removed = Counter()
        allowed_added = Counter()
        for item in policy.get(article_id, {}).get('replacements', []):
            allowed_removed.update(images(item['before'])-images(item['after']))
            allowed_added.update(images(item['after'])-images(item['before']))
        for item in policy.get(article_id, {}).get('embedded_images', []):
            for uri, number in before_images.items():
                if uri.startswith('data:image/') and hashlib.sha256(uri.encode()).hexdigest() == item['uri_sha256']:
                    allowed_removed[uri] += number
                    allowed_added[item['src']] += number
        assert not ((after_images-before_images)-allowed_added), f'Unreviewed new image: {article_id}'
        assert not ((before_images-after_images)-allowed_removed), f'Unreviewed image removal: {article_id}'
        image_total += sum(after_images.values())
        code_total += len(fences(updated))
        for url in after_images:
            if url.startswith('/notes-assets/') and not (ROOT/'public'/unquote(url).lstrip('/')).is_file():
                raise FileNotFoundError(f'{article_id}: {url}')
        canonical_new = heading+'\n\n'+reverse_urls(cleaned.lstrip(), source, targets).rstrip()+'\n'
        publish_target = PUBLISH/record['output']
        if original != updated:
            changes[post] = updated
        if canonical != canonical_new:
            changes[source] = canonical_new
        if publish_target.read_text('utf-8-sig') != canonical_new:
            changes[publish_target] = canonical_new
        if original != updated:
            details.append({'id': article_id, **counts,
                            'removed_images': {(hashlib.sha256(src.encode()).hexdigest() if src.startswith('data:') else src): number for src,number in (before_images-after_images).items()},
                            'sha256_before': hashlib.sha256(original.encode()).hexdigest(),
                            'sha256_after': hashlib.sha256(updated.encode()).hexdigest()})
    # Both exported directories expose the same current article index and format.
    readme = (CORPUS/'README.md').read_text('utf-8-sig')
    if not (PUBLISH/'README.md').is_file() or (PUBLISH/'README.md').read_text('utf-8-sig') != readme:
        changes[PUBLISH/'README.md'] = readme
    backup = None
    if args.apply and changes:
        backup = WORKSPACE/('reviewed-cleanup-apply-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.zip')
        with zipfile.ZipFile(backup, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for path in [*changes, manifest_path]:
                if path.is_file():
                    archive.write(path, path.relative_to(WORKSPACE).as_posix())
        for path, value in changes.items():
            assert path.resolve().is_relative_to(WORKSPACE.resolve())
            path.write_text(value, encoding='utf-8', newline='')
        changed_ids = {entry['id'] for entry in details}
        for record in manifest:
            path = CORPUS/record['output']
            record['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            if record['id'] in changed_ids:
                record['full_publication_cleanup'] = '2026-11-05'
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='')
    report = {'applied': args.apply, 'articles_scanned': len(manifest),
              'website_articles_changed': len(details), 'files_changed': len(changes),
              'editorial_passages_removed': sum(x.get('editorial_passages_removed', 0) for x in details),
              'reviewed_replacements_applied': sum(x.get('reviewed_replacements_applied', 0) for x in details),
              'replacement_kinds': dict(sum((Counter(x.get('replacement_kinds', {})) for x in details), Counter())),
              'technical_notes_retained_in_body': sum(x.get('technical_notes_retained', 0) for x in details),
              'code_blocks_unchanged': code_total, 'image_refs_remaining': image_total,
              'backup': str(backup) if backup else None, 'articles': details}
    filename = 'notes-full-cleanup-result.json' if args.apply else 'notes-full-cleanup-preview.json'
    (ROOT/filename).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'articles'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
