"""Build the Stage 9 showcase video (bilingual subtitles) from existing MP4s only."""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r'E:\learning\project')
VID = ROOT / 'stage8_reduced30_20261109' / 'videos'
OUT = ROOT / 'stage9_showcase_20261109'
ASSETS = OUT / 'video_assets'
ASSETS.mkdir(parents=True, exist_ok=True)
FFMPEG = ROOT / '.stage9_deps' / 'imageio_ffmpeg' / 'binaries' / 'ffmpeg-win-x86_64-v9.0.2.exe'
FONT = r'C:\Windows\Fonts\msyh.ttc'
FONT_B = r'C:\Windows\Fonts\msyhbd.ttc'


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size=size)


def text(draw, xy, s, size=28, fill='white', bold=False, anchor='la'):
    draw.text(xy, s, font=font(size, bold), fill=fill, anchor=anchor)


def intro(path):
    im = Image.new('RGB', (1280, 720), '#101820')
    d = ImageDraw.Draw(im)
    text(d, (640, 70), 'Stage 8 缩减版 30 例', 44, bold=True, anchor='ma')
    text(d, (640, 130), 'Stage 8 reduced 30-episode evaluation', 23, '#b9c6d2', anchor='ma')
    text(d, (640, 200), 'single-step MLP BC  vs  H4 action chunk', 30, anchor='ma')
    text(d, (640, 252), '单步 MLP 行为克隆  vs  H4 动作分块', 24, '#dbe7f0', anchor='ma')
    text(d, (640, 315), '15 seeds · 每档 5 个配对初态 · 描述性结果', 22, '#b9c6d2', anchor='ma')
    text(d, (640, 348), '15 seeds · 5 paired initial states per level · descriptive', 19, '#8fa3b5', anchor='ma')
    text(d, (640, 410), '非 ACT Transformer  /  not an ACT Transformer', 22, '#f0b45a', anchor='ma')
    text(d, (640, 475), '同初态配对 · 同 Backend · 同预算/终端/331 帧', 20, '#dbe7f0', anchor='ma')
    text(d, (640, 505), 'Paired initial states · same backend · same budget/terminal/331 window', 17, '#8fa3b5', anchor='ma')
    text(d, (640, 650), '缩减版探索性评估；每档 5 个配对初态', 18, '#8fa3b5', anchor='ma')
    text(d, (640, 678), 'Reduced exploratory evaluation · 5 paired initial states per level', 15, '#708697', anchor='ma')
    im.save(path)


def outro(path):
    im = Image.new('RGB', (1280, 720), '#101820')
    d = ImageDraw.Draw(im)
    text(d, (640, 58), 'Stage 8 缩减版结果', 40, bold=True, anchor='ma')
    text(d, (640, 108), 'Stage 8 reduced results', 21, '#b9c6d2', anchor='ma')
    text(d, (640, 180), 'L1 flat:  single 0/5   ·   H4 2/5', 27, anchor='ma')
    text(d, (640, 230), 'L2 perturbed:  single 0/5   ·   H4 0/5', 27, anchor='ma')
    text(d, (640, 280), 'L3 crumpled:  single 0/5   ·   H4 0/5', 27, anchor='ma')
    text(d, (640, 345), '合计  single 0/15   ·   H4 2/15', 30, '#f0b45a', bold=True, anchor='ma')
    text(d, (640, 385), 'Total  single 0/15   ·   H4 2/15', 20, '#f0b45a', anchor='ma')
    text(d, (640, 485), '原 120 例计划保留；剩余 90 例未执行', 21, '#b9c6d2', anchor='ma')
    text(d, (640, 515), 'Original 120-episode plan retained; 90 episodes remain unexecuted', 17, '#8fa3b5', anchor='ma')
    text(d, (640, 650), '缩减版探索性评估；每档 5 个配对初态', 18, '#8fa3b5', anchor='ma')
    text(d, (640, 678), 'Reduced exploratory evaluation · 5 paired initial states per level', 15, '#708697', anchor='ma')
    im.save(path)


def overlay_base():
    im = Image.new('RGBA', (1280, 720), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1280, 110), fill=(10, 16, 24, 225))
    d.rectangle((0, 650, 1280, 720), fill=(10, 16, 24, 235))
    return im, d


def pair_overlay(path):
    im, d = overlay_base()
    text(d, (320, 8), 'single · seed 4113 · 7 actions · rejected', 23, 'white', True, 'ma')
    text(d, (960, 8), 'H4 · seed 4113 · 7 actions · accepted', 23, '#7fc4ff', True, 'ma')
    text(d, (640, 43), 'Same initial · same 30 fps · no simulation-time resampling', 17, '#b9c6d2', anchor='ma')
    text(d, (640, 70), '同初态并排 · 同速 30 fps · 未按仿真时间同步/重采样', 16, '#8fa3b5', anchor='ma')
    text(d, (640, 659), '缩减版探索性评估；每档 5 个配对初态 · 取共同前 26 s', 17, '#dbe7f0', anchor='ma')
    text(d, (640, 686), 'Reduced exploratory evaluation · 5 paired initial states per level · first 26 s', 14, '#8fa3b5', anchor='ma')
    im.save(path)


def single_overlay(path, title, sub_en, sub_zh):
    im, d = overlay_base()
    text(d, (640, 10), title, 23, 'white', True, 'ma')
    text(d, (640, 44), sub_en, 17, '#b9c6d2', anchor='ma')
    text(d, (640, 70), sub_zh, 16, '#8fa3b5', anchor='ma')
    text(d, (640, 659), '缩减版探索性评估；每档 5 个配对初态', 17, '#dbe7f0', anchor='ma')
    text(d, (640, 686), 'Reduced exploratory evaluation · 5 paired initial states per level', 14, '#8fa3b5', anchor='ma')
    im.save(path)


def run(cmd):
    print('RUN', ' '.join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True)


def main():
    intro(ASSETS / 'intro.png')
    outro(ASSETS / 'outro.png')
    pair_overlay(ASSETS / 'pair.png')
    single_overlay(
        ASSETS / 'h4_4111.png',
        'H4 · seed 4111 · 7 actions · accepted',
        'L1 flat · 331-frame window complete',
        'L1 flat · 331 帧完成')
    single_overlay(
        ASSETS / 'h4_4215.png',
        'H4 · L2 perturbed · seed 4215 · 1 action · execution_error',
        'Failure example; no rerun',
        '失败示例，未补跑')
    single_overlay(
        ASSETS / 'h4_4313.png',
        'H4 · L3 crumpled · seed 4313 · 1 action · execution_error',
        'Failure example; no rerun',
        '失败示例，未补跑')

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
    target = OUT / 'stage9_showcase_bilingual.mp4'
    run([FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', lst,
         '-c', 'copy', '-an', target])
    print('VIDEO_BILINGUAL_OK', target)


if __name__ == '__main__':
    main()
