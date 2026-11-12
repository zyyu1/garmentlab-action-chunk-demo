import os
import re
import subprocess
import urllib.parse
from pathlib import Path

ROOT = Path(r'E:\learning\project\garmentlab-action-chunk-demo')
JOURNAL = ROOT / 'docs' / 'journal'


def tracked(pattern='*.md'):
    return subprocess.run(['git', '-C', str(ROOT), '-c', 'core.quotepath=false',
                           'ls-files', pattern], capture_output=True, text=True,
                          encoding='utf-8').stdout.splitlines()


reports = [f for f in tracked() if '/' not in f and ('GarmentLab日报' in f or '环境安装交接日志' in f)]
JOURNAL.mkdir(parents=True, exist_ok=True)
for f in reports:
    subprocess.run(['git', '-C', str(ROOT), 'mv', f, str(JOURNAL / f)], check=True)
print('MOVED', len(reports))

moved = {Path(f).name for f in reports}

# rewrite links to moved reports, computing the relative path per file
link_re = re.compile(r'\]\(([^)]+)\)')
changed = 0
for f in tracked():
    p = ROOT / f
    text = p.read_text(encoding='utf-8-sig')
    orig = text

    def fix(m):
        raw = m.group(1)
        if raw.startswith(('http', 'mailto', '#')):
            return m.group(0)
        target, _, anchor = raw.partition('#')
        name = Path(urllib.parse.unquote(target)).name
        if name not in moved:
            return m.group(0)
        rel = os.path.relpath(JOURNAL / name, p.parent if str(p.parent) != str(ROOT) else ROOT)
        rel = rel.replace(os.sep, '/')
        return '](' + rel + (('#' + anchor) if anchor else '') + ')'

    text = link_re.sub(fix, text)
    if text != orig:
        p.write_text(text, encoding='utf-8')
        changed += 1
print('RELINKED', changed)

# scrub infrastructure details in journal files only
scrubs = [
    (re.compile(r'root@[a-z0-9.\-]*seetacloud\.com(?::\d+)?', re.I), '<server>'),
    (re.compile(r'[a-z0-9.\-]*seetacloud\.com(?::\d+)?', re.I), '<server>'),
    (re.compile(r'/root/autodl-tmp'), '<remote-root>'),
    (re.compile(r'\bautodl-tmp/'), '<remote-root>/'),
]
n = 0
for name in sorted(moved):
    p = JOURNAL / name
    t = p.read_text(encoding='utf-8')
    o = t
    for pat, rep in scrubs:
        t = pat.sub(rep, t)
    if t != o:
        p.write_text(t, encoding='utf-8')
        n += 1
print('SCRUBBED', n)

# index
rows = []
for name in sorted(moved):
    t = (JOURNAL / name).read_text(encoding='utf-8')
    title = next((l.lstrip('# ').strip() for l in t.splitlines() if l.startswith('# ')), name)
    rows.append((name, title))
out = ['# 开发日志索引 / Project log', '',
       '按日期归档的日报与交接日志。原始内容保留，仅对服务器地址与远端口令做脱敏。', '']
for name, title in rows:
    out.append(f'- [{title}]({name})')
(JOURNAL / 'INDEX.md').write_text('\n'.join(out) + '\n', encoding='utf-8')
print('INDEX', len(rows))
