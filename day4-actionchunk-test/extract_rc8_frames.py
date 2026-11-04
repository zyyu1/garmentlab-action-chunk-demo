import json
from pathlib import Path

import cv2

ROOT = Path('/root/autodl-tmp')
RUNS = ROOT / 'a5-rc2-pfs1-observation-v2-rc8-runs'
OUT = ROOT / 'rc8_frames'
OUT.mkdir(exist_ok=True)
fracs = [0.15, 0.35, 0.55, 0.70, 0.85, 0.97]
for line in (RUNS / 'batch.jsonl').read_text().splitlines():
    if not line.strip():
        continue
    rec = json.loads(line)
    run = Path(rec['run'])
    tag = 'slot%d_%s_%s' % (rec['slot'], rec['seed'], rec['mode'])
    d = OUT / tag
    d.mkdir(exist_ok=True)
    video = run / 'evidence' / 'episode.mp4'
    cap = cv2.VideoCapture(str(video))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    for i, frac in enumerate(fracs):
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int((n - 1) * frac)))
        ok, img = cap.read()
        if not ok:
            print('READ_FAIL', tag, i, flush=True)
            continue
        cv2.imwrite(str(d / ('f%d.png' % i)), img)
    cap.release()
    print('FRAMES', tag, n, len(list(d.glob('*.png'))), flush=True)
