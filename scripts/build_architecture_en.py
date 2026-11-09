"""Create the minimal Stage 10 architecture/migration diagram (offline)."""
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / 'assets'
from matplotlib import font_manager
FONT = font_manager.findfont('DejaVu Sans')
FONT_B = font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans', weight='bold'))
W, H = 1800, 1000
INK = '#173a54'
MUT = '#5d7384'


def f(s, b=False):
    return ImageFont.truetype(FONT_B if b else FONT, s)


def box(d, xy, title, lines, fill='#f4f9fd', outline='#8fb3cc'):
    x0, y0, x1, y1 = xy
    d.rounded_rectangle(xy, radius=18, fill=fill, outline=outline, width=3)
    title_size = 26
    while d.textlength(title, font=f(title_size, True)) > x1-x0-44:
        title_size -= 1
    d.text((x0 + 22, y0 + 18), title, font=f(title_size, True), fill=INK)
    y = y0 + 66
    for line in lines:
        line_size = 20
        while d.textlength(line, font=f(line_size)) > x1-x0-44:
            line_size -= 1
        d.text((x0 + 22, y), line, font=f(line_size), fill='#29495f')
        y += 34


def arrow(d, xy1, xy2, label=''):
    d.line((xy1, xy2), fill='#3d6f93', width=4)
    # simple arrow head
    x1, y1 = xy1
    x2, y2 = xy2
    angle = math.atan2(y2-y1, x2-x1)
    d.polygon([(x2, y2),
               (x2-16*math.cos(angle)+9*math.sin(angle), y2-16*math.sin(angle)-9*math.cos(angle)),
               (x2-16*math.cos(angle)-9*math.sin(angle), y2-16*math.sin(angle)+9*math.cos(angle))], fill='#3d6f93')
    if label:
        d.text(((x1 + x2)//2 - 40, (y1 + y2)//2 - 34), label, font=f(19), fill='#3d6f93')


def main():
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    d.text((50, 35), 'Stage 10 | Architecture and Sim-to-Real Boundary', font=f(40, True), fill='#10202d')
    d.text((50, 90), 'State-oracle training and simulation execution; real-robot components remain unimplemented',
           font=f(22), fill=MUT)

    box(d, (50, 165, 410, 400), 'Simulation state oracle',
        ['Cloth vertices / EE / joints', 'Holding state; simulation only'], '#fff7e8', '#d9a441')
    box(d, (500, 165, 890, 400), 'Training data',
        ['70 demos / 590 actions', 'H4: 160 chunks / 50 padding'])
    box(d, (980, 165, 1360, 400), 'Policies',
        ['single-step MLP BC', 'H4 action chunk (k=4)'])
    box(d, (1450, 165, 1750, 400), 'Public action',
        ['[x,y,z,yaw] + gripper', '5-D; no joint commands'])
    arrow(d, (410, 282), (500, 282), 'Collect')
    arrow(d, (890, 282), (980, 282), 'Train')
    arrow(d, (1360, 282), (1450, 282), 'Infer')

    box(d, (720, 510, 1120, 690), 'Backend interface',
        ['get_observation / execute / stop', 'No direct policy-to-Isaac calls'],
        '#eef5fa', '#2f6fb0')
    arrow(d, (1600, 400), (1120, 510), 'Action',)
    box(d, (1200, 510, 1740, 690), 'Simulation execution',
        ['GarmentLab + Isaac Sim 4.0.0.0', 'Physics evaluator + 331-frame window'], '#eef5fa', '#2f6fb0')
    arrow(d, (1120, 600), (1200, 600), 'Execute')

    box(d, (60, 760, 560, 940), 'Migration: real perception',
        ['RGB-D to cloth keypoints / EE / gripper', 'Calibration, occlusion, noise: not implemented'],
        '#fdf1ef', '#c76b5b')
    box(d, (620, 760, 1120, 940), 'Real-robot execution',
        ['IK / trajectories / controller / safety', 'Action space and timing: not implemented'],
        '#fdf1ef', '#c76b5b')
    box(d, (1180, 760, 1740, 940), 'Deployment boundary',
        ['RealRobotBackendStub: interface only', 'No real-robot deployment claimed'],
        '#fdf1ef', '#c76b5b')
    d.text((50, 960), 'Schemas and backend boundaries exist; real perception, calibration, IK, safety and robot data remain missing.',
           font=f(20), fill=MUT)
    im.save(OUT / 'architecture_en.png')
    print('ARCH_OK', OUT / 'architecture_en.png')


if __name__ == '__main__':
    main()
