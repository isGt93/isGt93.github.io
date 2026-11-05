"""Apply individually reviewed article corrections after Markdown URL mapping.

Only exact, article-specific passages are changed. Summaries, dates, meaningful
source paragraphs and fenced code are outside the reviewed editing ranges.
"""
from pathlib import Path
import hashlib
import json
import re
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT/'scripts/note-editorial-cleanup.json'
PARSER = MarkdownIt('commonmark')


def fences(text):
    return [(t.type, t.info, t.content) for t in PARSER.parse(text)
            if t.type in ('fence', 'code_block')]


def clean_note_body(body, article_id, policy=None):
    if policy is None:
        policy = json.loads(POLICY_PATH.read_text('utf-8'))['articles']
    plan = policy.get(article_id.upper())
    if not plan:
        return body, {}
    match = re.match(r'\A(\s*ailx10说：[^\n]+\n\s*\n---[ \t]*\n)(.*)\Z', body, re.S)
    if not match:
        raise ValueError(f'Missing protected author summary/divider: {article_id}')
    protected, tail = match.groups()
    before = fences(body)
    ranges = []
    removed = 0
    for span in plan.get('remove_spans', []):
        start = tail.find(span)
        if start < 0:
            continue  # Already cleaned on a previous export/import.
        if tail.find(span, start + len(span)) >= 0:
            raise ValueError(f'Ambiguous editorial passage: {article_id}')
        ranges.append((start, start + len(span)))
        removed += 1
    merged = []
    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    for start, end in reversed(merged):
        tail = tail[:start] + tail[end:]
    replacements = 0
    kinds = {}
    for item in plan.get('replacements', []):
        source, target = item['before'], item['after']
        if source not in tail:
            continue
        if tail.count(source) != 1:
            raise ValueError(f'Ambiguous platform fragment: {article_id}')
        tail = tail.replace(source, target, 1)
        replacements += 1
        kind = item.get('kind', 'reviewed_replacement')
        kinds[kind] = kinds.get(kind, 0) + 1
    embedded = {item['uri_sha256']: item['src'] for item in plan.get('embedded_images', [])}
    if embedded:
        def replace_embedded(match):
            digest = hashlib.sha256(match[2].encode()).hexdigest()
            if digest in embedded:
                kinds['embedded_image_materialized'] = kinds.get('embedded_image_materialized', 0) + 1
            return match[1]+embedded.get(digest, match[2])+match[3]
        tail = re.sub(r'(!\[[^\]\n]*\]\()(data:image/[^\s)]+)(\))', replace_embedded, tail)
    note = plan.get('technical_note', '').strip()
    note_added = 0
    if note and note not in tail:
        after = plan.get('insert_after_anchor')
        before_anchor = plan.get('insert_before_anchor')
        if after and tail.count(after) == 1:
            position = tail.index(after) + len(after)
        elif before_anchor and tail.count(before_anchor) == 1:
            position = tail.index(before_anchor)
        else:
            # Keep context notes inside the article, away from its introduction.
            reference = list(re.finditer(r'^#{1,3} (?:参考(?:资料|文献|链接|阅读)?|资料来源|References)\s*$', tail, re.M | re.I))
            position = reference[-1].start() if reference and reference[-1].start() > len(tail)/2 else len(tail)
        tail = tail[:position].rstrip() + '\n\n' + note + '\n\n' + tail[position:].lstrip()
        note_added = 1
    result = protected + '\n' + tail.lstrip('\n')
    assert before == fences(result), f'Fenced code changed: {article_id}'
    assert result.startswith(protected), f'Author summary changed: {article_id}'
    return result, {'editorial_passages_removed': removed, 'reviewed_replacements_applied': replacements,
                    'technical_notes_retained': note_added, 'replacement_kinds': kinds}
