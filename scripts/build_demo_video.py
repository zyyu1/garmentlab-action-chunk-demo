"""Build the 60-second English-only showcase from existing simulation recordings.
Requires Pillow and ffmpeg. No simulation is run.
"""
from __future__ import annotations
import argparse
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--videos', type=Path, required=True)
ap.add_argument('--out', type=Path, required=True)
ap.add_argument('--ffmpeg', default='ffmpeg')
ap.add_argument('--font', required=True, help='Path to a TrueType font')
args = ap.parse_args()
VID = args.videos.resolve()
OUT = args.out.resolve()
OUT.mkdir(parents=True, exist_ok=False)
ASSETS = OUT / 'video_assets'
ASSETS.mkdir()
FFMPEG = args.ffmpeg

def text(draw, xy, s, size=28, fill='white', bold=False, anchor='ma'):
    f = ImageFont.truetype(args.font, size=size)
    box = draw.textbbox(xy, s, font=f, anchor=anchor)
    if box[0] < 0 or box[2] > 1280:
        raise ValueError('Caption exceeds frame: ' + s)
    draw.text(xy, s, font=f, fill=fill, anchor=anchor)

def intro(path):
    im = Image.new('RGB', (1280, 720), '#101820')
    d = ImageDraw.Draw(im)
    text(d, (640, 80), 'Garment Folding with Action Chunking', 42)
    text(d, (640, 155), 'Stage 8 reduced evaluation | v9.1.3', 26, '#b9c6d2')
    text(d, (640, 255), 'Single-step MLP BC vs H4 action chunking', 32)
    text(d, (640, 340), '15 paired seeds | 30 episodes | 5 pairs per level', 26, '#b9c6d2')
    text(d, (640, 420), 'Simulation state observations | Not an ACT Transformer', 24, '#f0b45a')
    text(d, (640, 500), 'Paired initial states, same backend and evaluation protocol', 24, '#b9c6d2')
    text(d, (640, 650), 'Exploratory small-sample results; no generalization claim', 22, '#8fa3b5')
    im.save(path)

def outro(path):
    im = Image.new('RGB', (1280, 720), '#101820')
    d = ImageDraw.Draw(im)
    text(d, (640, 70), 'Reduced Evaluation Results', 42)
    text(d, (640, 180), 'L1 flat: single 0/5 | H4 2/5', 30)
    text(d, (640, 245), 'L2 perturbed: single 0/5 | H4 0/5', 30)
    text(d, (640, 310), 'L3 crumpled: single 0/5 | H4 0/5', 30)
    text(d, (640, 400), 'Total: single 0/15 | H4 2/15', 34, '#f0b45a')
    text(d, (640, 500), '27/30 episodes lack a complete 331-frame window', 24, '#b9c6d2')
    text(d, (640, 550), 'Original 120-episode plan: 90 episodes remain unexecuted', 24, '#b9c6d2')
    text(d, (640, 650), 'Simulation only | Descriptive results | No real-robot deployment', 22, '#8fa3b5')
    im.save(path)

def overlay_base():
    im = Image.new('RGBA', (1280, 720), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1280, 110), fill=(10, 16, 24, 255))
    d.rectangle((0, 650, 1280, 720), fill=(10, 16, 24, 255))
    return im, d

def pair_overlay(path):
    im, d = overlay_base()
    text(d, (320, 16), 'Single | seed 4113 | 7 actions | rejected', 24)
    text(d, (960, 16), 'H4 | seed 4113 | 7 actions | accepted', 24, '#7fc4ff')
    text(d, (640, 62), 'Same initial state | 30 fps playback | Not synchronized to simulation time', 22, '#b9c6d2')
    text(d, (640, 671), '5 paired states per level | First 26 seconds | Not a speed comparison', 22, '#b9c6d2')
    im.save(path)

def single_overlay(path, title, subtitle):
    im, d = overlay_base()
    text(d, (640, 16), title, 28)
    text(d, (640, 62), subtitle, 23, '#b9c6d2')
    text(d, (640, 671), 'Reduced exploratory evaluation | 5 paired initial states per level', 22, '#b9c6d2')
    im.save(path)

def run(cmd):
    cmd[1:1] = ['-hide_banner', '-loglevel', 'error']
    print('Encoding', Path(cmd[-1]).name, flush=True)
    subprocess.run([str(c) for c in cmd], check=True)


def main():
    intro(ASSETS / 'intro.png')
    outro(ASSETS / 'outro.png')
    pair_overlay(ASSETS / 'pair.png')
    single_overlay(ASSETS / 'h4_4111.png',
                   'H4 | L1 flat | seed 4111 | 7 actions | accepted',
                   'Complete 331-frame evaluation window')
    single_overlay(ASSETS / 'h4_4215.png',
                   'H4 | L2 perturbed | seed 4215 | 1 action | execution error',
                   'Failure example from the frozen evaluation; no rerun')
    single_overlay(ASSETS / 'h4_4313.png',
                   'H4 | L3 crumpled | seed 4313 | 1 action | execution error',
                   'Failure example from the frozen evaluation; no rerun')

    segs = []
    p = ASSETS / '01_intro.mp4'
    run([FFMPEG, '-y', '-loop', '1', '-i', ASSETS / 'intro.png', '-t', '3',
         '-r', '30', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', p])
    segs.append(p)
    p = ASSETS / '02_pair_4113.mp4'
    run([FFMPEG, '-y', '-i', VID / 'single_flat_4113_rejected.mp4',
         '-i', VID / 'H4_flat_4113_success.mp4',
         '-loop', '1', '-i', ASSETS / 'pair.png',
         '-filter_complex',
         '[0:v]scale=640:480,setsar=1[l];'
         '[1:v]scale=640:480,setsar=1[r];'
         '[l][r]hstack=inputs=2,pad=1280:720:0:120:black[base];'
         '[2:v]format=rgba[ov];'
         '[base][ov]overlay=0:0:format=auto,format=yuv420p[v]',
         '-map', '[v]', '-t', '26', '-r', '30', '-an',
         '-c:v', 'libx264', '-pix_fmt', 'yuv420p', p])
    segs.append(p)
    p = ASSETS / '03_h4_4111.mp4'
    run([FFMPEG, '-y', '-ss', '14.4', '-i', VID / 'H4_flat_4111_success.mp4',
         '-loop', '1', '-i', ASSETS / 'h4_4111.png',
         '-filter_complex',
         '[0:v]scale=640:480,setsar=1,pad=1280:720:320:120:black[base];'
         '[1:v]format=rgba[ov];[base][ov]overlay=0:0:format=auto,format=yuv420p[v]',
         '-map', '[v]', '-t', '14', '-r', '30', '-an',
         '-c:v', 'libx264', '-pix_fmt', 'yuv420p', p])
    segs.append(p)
    p = ASSETS / '04_h4_4215.mp4'
    run([FFMPEG, '-y', '-i', VID / 'H4_perturbed_4215_failure.mp4',
         '-loop', '1', '-i', ASSETS / 'h4_4215.png',
         '-filter_complex',
         '[0:v]scale=640:480,setsar=1,pad=1280:720:320:120:black[base];'
         '[1:v]format=rgba[ov];[base][ov]overlay=0:0:format=auto,format=yuv420p[v]',
         '-map', '[v]', '-t', '7', '-r', '30', '-an',
         '-c:v', 'libx264', '-pix_fmt', 'yuv420p', p])
    segs.append(p)
    p = ASSETS / '05_h4_4313.mp4'
    run([FFMPEG, '-y', '-i', VID / 'H4_crumpled_4313_failure.mp4',
         '-loop', '1', '-i', ASSETS / 'h4_4313.png',
         '-filter_complex',
         '[0:v]scale=640:480,setsar=1,pad=1280:720:320:120:black[base];'
         '[1:v]format=rgba[ov];[base][ov]overlay=0:0:format=auto,format=yuv420p[v]',
         '-map', '[v]', '-t', '6', '-r', '30', '-an',
         '-c:v', 'libx264', '-pix_fmt', 'yuv420p', p])
    segs.append(p)
    p = ASSETS / '06_outro.mp4'
    run([FFMPEG, '-y', '-loop', '1', '-i', ASSETS / 'outro.png', '-t', '4',
         '-r', '30', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', p])
    segs.append(p)

    lst = ASSETS / 'concat.txt'
    lst.write_text(''.join("file '%s'\n" % p.as_posix() for p in segs), encoding='utf-8')
    target = OUT / 'stage9_showcase_english.mp4'
    run([FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', lst,
         '-c', 'copy', '-an', '-movflags', '+faststart', target])
    print('VIDEO_ENGLISH_OK', target)


if __name__ == '__main__':
    main()
