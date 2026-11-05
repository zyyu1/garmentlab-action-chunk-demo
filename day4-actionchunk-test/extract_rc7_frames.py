import cv2
from pathlib import Path

ROOT = Path('/root/autodl-tmp')
RUNS = [
    (1, 4100, 'single', ROOT / 'day4-a5-rc2-l1-20261105-081311-735952'),
    (2, 4100, 'arc4', ROOT / 'day4-a5-rc2-l1-20261105-083859-341524'),
    (3, 4202, 'single', ROOT / 'day4-a5-rc2-pfs1-observation-v2-20261105-085248-353214'),
    (4, 4202, 'arc4', ROOT / 'day4-a5-rc2-pfs1-observation-v2-20261105-091038-643466'),
    (5, 4302, 'single', ROOT / 'day4-a5-rc2-pfs1-observation-v2-20261105-092821-242307'),
    (6, 4302, 'arc4', ROOT / 'day4-a5-rc2-pfs1-observation-v2-20261105-094700-143205'),
    (7, 4201, 'single', ROOT / 'day4-a5-rc2-pfs1-observation-v2-20261105-100445-893957'),
]
OUT = ROOT / 'hold120_rc7_frames'
OUT.mkdir(exist_ok=True)
FRACS = [0.15, 0.35, 0.55, 0.70, 0.85, 0.97]
for slot, seed, mode, run in RUNS:
    tag = 'slot%d_%d_%s' % (slot, seed, mode)
    d = OUT / tag
    d.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(run / 'evidence' / 'episode.mp4'))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    for i, frac in enumerate(FRACS):
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int((n - 1) * frac)))
        ok, img = cap.read()
        if ok:
            cv2.imwrite(str(d / ('f%d.png' % i)), img)
    cap.release()
    print('FRAMES', tag, n, len(list(d.glob('*.png'))), flush=True)
