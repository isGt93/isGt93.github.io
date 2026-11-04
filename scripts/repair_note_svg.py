"""Repair only structurally invalid imported SVG copies; never touch sources."""
from pathlib import Path
import hashlib
import json
from lxml import etree

def repair(directory):
    changed=[]
    for path in sorted(directory.glob('*.svg')):
        raw=path.read_bytes()
        original_error=None
        try:
            document=etree.fromstring(raw,parser=etree.XMLParser(resolve_entities=False,no_network=True))
        except etree.XMLSyntaxError as exc:
            original_error=str(exc)
            document=etree.fromstring(raw,parser=etree.XMLParser(recover=True,resolve_entities=False,no_network=True))
        if document is None or etree.QName(document).localname!='svg':
            raise ValueError(f'无法恢复SVG根节点 {path.name}')
        opening_before=len(etree.tostring(document,encoding='utf-8').split(b'>',1)[0])+1
        moved_style=False
        if opening_before>=900 and document.get('style'):
            css=document.attrib.pop('style')
            namespace=etree.QName(document).namespace
            style=etree.Element(f'{{{namespace}}}style' if namespace else 'style')
            style.text=':root{'+css+'}'
            document.insert(0,style)
            moved_style=True
        if not original_error and not moved_style:
            continue
        restored=etree.tostring(document,encoding='utf-8',xml_declaration=False)
        etree.fromstring(restored,parser=etree.XMLParser(resolve_entities=False,no_network=True))
        opening_after=len(restored.split(b'>',1)[0])+1
        if opening_after>=1000:
            raise ValueError(f'SVG根开标签仍过长 {path.name}: {opening_after}')
        path.write_bytes(restored)
        changed.append({'file':path.name,'original_sha256':hashlib.sha256(raw).hexdigest(),
                        'repaired_sha256':hashlib.sha256(restored).hexdigest(),'error':original_error,
                        'root_style_moved':moved_style,'opening_bytes_before':opening_before,
                        'opening_bytes_after':opening_after})
    return changed

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    changed=repair(root/'public/notes-assets')
    (root/'notes-svg-repair-report.json').write_text(json.dumps(changed,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'已修复{len(changed)}个SVG，原始素材未修改')
