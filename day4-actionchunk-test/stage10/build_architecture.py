"""Create the minimal Stage 10 architecture/migration diagram (offline)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(r'E:\learning\project\stage10_showcase_20261109')
FONT = r'C:\Windows\Fonts\msyh.ttc'
FONT_B = r'C:\Windows\Fonts\msyhbd.ttc'
W, H = 1800, 1000
INK = '#173a54'
MUT = '#5d7384'


def f(s, b=False):
    return ImageFont.truetype(FONT_B if b else FONT, s)


def box(d, xy, title, lines, fill='#f4f9fd', outline='#8fb3cc'):
    x0, y0, x1, y1 = xy
    d.rounded_rectangle(xy, radius=18, fill=fill, outline=outline, width=3)
    d.text((x0 + 22, y0 + 18), title, font=f(31, True), fill=INK)
    y = y0 + 66
    for line in lines:
        d.text((x0 + 22, y), line, font=f(22), fill='#29495f')
        y += 34


def arrow(d, xy1, xy2, label=''):
    d.line((xy1, xy2), fill='#3d6f93', width=4)
    # simple arrow head
    x1, y1 = xy1
    x2, y2 = xy2
    if x2 >= x1:
        d.polygon([(x2, y2), (x2 - 16, y2 - 9), (x2 - 16, y2 + 9)], fill='#3d6f93')
    if label:
        d.text(((x1 + x2)//2 - 40, (y1 + y2)//2 - 34), label, font=f(19), fill='#3d6f93')


def main():
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    d.text((50, 35), 'Stage 10 · 最小架构与 sim-to-real 边界', font=f(40, True), fill='#10202d')
    d.text((50, 90), 'Stage 10 · minimal architecture and sim-to-real boundary',
           font=f(24), fill=MUT)

    box(d, (50, 165, 410, 400), '仿真 state-oracle',
        ['布面顶点 / EE / 关节 / holding', '仅仿真、非部署感知'], '#fff7e8', '#d9a441')
    box(d, (500, 165, 890, 400), '训练数据',
        ['70 条示范 / 590 动作', 'H4: 160 chunks / 50 padding'])
    box(d, (980, 165, 1360, 400), '策略',
        ['single-step MLP BC', 'H4 action chunk (k=4)'])
    box(d, (1450, 165, 1750, 400), '公共动作',
        ['[x,y,z,yaw] + gripper', '5 维，不含关节命令'])
    arrow(d, (410, 282), (500, 282), '采集')
    arrow(d, (890, 282), (980, 282), '训练')
    arrow(d, (1360, 282), (1450, 282), '推理')

    box(d, (720, 510, 1120, 690), 'Backend 接口',
        ['get_observation / execute / stop', '策略不直接调用 Isaac'],
        '#eef5fa', '#2f6fb0')
    arrow(d, (1600, 400), (1120, 510), '动作',)
    box(d, (1200, 510, 1740, 690), '仿真执行',
        ['GarmentLab + Isaac Sim 4.0.0.0', '物理 evaluator + 331 帧窗口'], '#eef5fa', '#2f6fb0')
    arrow(d, (1120, 600), (1200, 600), '执行')

    box(d, (60, 760, 560, 940), '迁移目标：真实感知',
        ['RGB-D → 布料关键点/EE/夹爪', '标定、遮挡、噪声：未实现'],
        '#fdf1ef', '#c76b5b')
    box(d, (620, 760, 1120, 940), '真机执行',
        ['IK / 轨迹 / 控制器 / 安全', '动作空间与时序：未实现'],
        '#fdf1ef', '#c76b5b')
    box(d, (1180, 760, 1740, 940), '明确未声明',
        ['RealRobotBackendStub 仅接口占位', '不宣称已支持真机部署'],
        '#fdf1ef', '#c76b5b')
    d.line((610, 700, 610, 760), fill='#c76b5b', width=3)
    d.line((900, 700, 900, 760), fill='#c76b5b', width=3)
    d.text((50, 960), '统一 schema / Backend 边界已存在；真实感知、标定、IK、安全与真机数据仍缺失。',
           font=f(20), fill=MUT)
    im.save(OUT / 'architecture.png')
    print('ARCH_OK', OUT / 'architecture.png')


if __name__ == '__main__':
    main()
