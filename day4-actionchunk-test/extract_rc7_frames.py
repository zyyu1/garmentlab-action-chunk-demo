import json
from pathlib import Path

import cv2

ROOT = Path('/root/autodl-tmp')
OUT = ROOT / 'rc7_frames'
OUT.mkdir(exist_ok=True)
cases = {
    's1_4100_single': 'day4-a5-rc2-l1-20261104-210923-025602',
    's2_4100_arc4': 'day4-a5-rc2-l1-20261104-212326-225911',
    's3_4202_single': 'day4-a5-rc2-pfs1-observation-v2-20261104-213547-226507',
    's4_4202_arc4': 'day4-a5-rc2-pfs1-observation-v2-20261104-215152-043317',
    's5_4302_single': 'day4-a5-rc2-pfs1-observation-v2-20261104-220859-844555',
    's6_4302_arc4': 'day4-a5-rc2-pfs1-observation-v2-20261104-222840-723114',
    's7_4201_single': 'day4-a5-rc2-pfs1-observation-v2-20261104-224843-941246',
}
fracs = [0.15, 0.35, 0.55, 0.70, 0.85, 0.97]
for tag, name in cases.items():
    video = ROOT / name / 'evidence' / 'episode.mp4'
    cap = cv2.VideoCapture(str(video))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
    d = OUT / tag
    d.mkdir(exist_ok=True)
    for i, frac in enumerate(fracs):
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int((n - 1) * frac)))
        ok, img = cap.read()
        if not ok:
            print('READ_FAIL', tag, i, flush=True)
            continue
        cv2.imwrite(str(d / ('f%d.png' % i)), img)
    cap.release()
    print('FRAMES', tag, n, round(fps, 2), len(list(d.glob('*.png'))), flush=True)
