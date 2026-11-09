"""Render a compact two-page PDF report with PIL (no browser/LaTeX required)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(r'E:\learning\project\stage9_showcase_20261109')
FONT = r'C:\Windows\Fonts\msyh.ttc'
FONT_B = r'C:\Windows\Fonts\msyhbd.ttc'
W, H = 1240, 1754
M = 62
INK = '#182733'
MUT = '#5b7182'
BLUE = '#2f6fb0'
RED = '#a3372c'
GREEN = '#1d6b3a'


def f(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size=size)


def wrap(draw, text, font, width):
    out = []
    for para in text.split('\n'):
        line = ''
        for ch in para:
            test = line + ch
            if draw.textlength(test, font=font) <= width or not line:
                line = test
            else:
                out.append(line)
                line = ch
        out.append(line)
    return out


def para(draw, xy, text, font, width, lh=24, color=INK):
    x, y = xy
    for line in wrap(draw, text, font, width):
        draw.text((x, y), line, font=font, fill=color)
        y += lh
    return y


def section(draw, y, title):
    draw.text((M, y), title, font=f(21, True), fill='#173a54')
    draw.line((M, y + 30, W - M, y + 30), fill='#c9d8e4', width=1)
    return y + 44


def table(draw, y, headers, rows, widths, fs=15, rh=27):
    x = M
    draw.rectangle((M, y, W - M, y + rh), fill='#eef5fa')
    for h, w in zip(headers, widths):
        draw.text((x + 7, y + 5), h, font=f(fs, True), fill='#173a54')
        x += w
    y += rh
    for row in rows:
        x = M
        for val, w in zip(row, widths):
            draw.text((x + 7, y + 4), str(val), font=f(fs), fill=INK)
            x += w
        draw.line((M, y + rh, W - M, y + rh), fill='#dce6ed', width=1)
        y += rh
    return y + 8


def fit_image(draw, path, x, y, max_w, max_h):
    img = Image.open(path).convert('RGB')
    scale = min(max_w / img.width, max_h / img.height)
    size = (int(img.width * scale), int(img.height * scale))
    img = img.resize(size, Image.LANCZOS)
    draw.rectangle((x - 1, y - 1, x + size[0] + 1, y + size[1] + 1),
                   outline='#dbe5ec', width=1)
    return img, (x, y)


def page1():
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    d.text((M, 45), 'STAGE 8 · REDUCED 30  /  STAGE 9 · SHOWCASE',
           font=f(14, True), fill='#4f6b80')
    d.text((M, 78), 'Stage 8 缩减版 30 例', font=f(40, True), fill='#10202d')
    d.text((M, 134), 'single-step MLP 行为克隆  vs  H4 动作分块（action chunk）',
           font=f(20), fill='#365166')
    d.rectangle((M, 180, W - M, 286), fill='#f2f7fb')
    d.rectangle((M, 180, M + 7, 286), fill=BLUE)
    para(d, (M + 22, 192),
         'Stage 8 缩减版评估完成；Stage 9 展示成果已整理；原 120 例评估尚有 90 例未执行。\n'
         '15 个配对初态 · 30 episodes · 每档 5 个配对初态。结果仅作描述，不作统计显著性声明。',
         f(17), W - M * 2 - 30, 26, '#18364d')
    y = 312
    y = section(d, y, '1. 任务与 state-oracle 输入')
    y = para(d, (M, y),
             '任务是方形布料的三档初态折叠：L1 flat、L2 perturbed、L3 crumpled。专家用仿真状态 oracle 生成示范'
             '（布面顶点、末端位姿/夹爪状态与保持状态），不是部署时可用的感知输入。策略观测固定为 1340 维：'
             '441 个布料顶点 × 3 + EE 3 + 四元数 4 + 7 关节 + 1 holding；动作是 [x,y,z,yaw] + gripper(0/1/2)。'
             '成功由冻结的物理 evaluator、终端释放/退让条件和原 331 帧窗口共同判定，本轮未改阈值。',
             f(16), W - M * 2, 24)
    y += 14
    y = section(d, y, '2. single 与 H4 的执行区别')
    colw = (W - M * 2 - 24) // 2
    d.rectangle((M, y, M + colw, y + 210), fill='#fbfdfe', outline='#d6e1e9')
    d.text((M + 12, y + 9), 'single-step MLP BC', font=f(17, True), fill='#173a54')
    para(d, (M + 12, y + 42),
         '每步 observe → 预测 1 个动作 → 执行。\nL1 预算 7 个公共动作，7 次 policy forward。\n'
         '闭环最充分；训练 2000 optimizer updates。', f(15), colw - 24, 23)
    x2 = M + colw + 24
    d.rectangle((x2, y, x2 + colw, y + 210), fill='#f4f9fd', outline='#c9d8e4')
    d.text((x2 + 12, y + 9), 'H4 action chunk', font=f(17, True), fill='#173a54')
    para(d, (x2 + 12, y + 42),
         'observe → 预测 4 个动作 → 顺序执行。\n固定 execute_k=4；L1 首块 4 个、第二块剩余 3 个。\n'
         'chunk 内不重新预测；第二块第 4 个动作因 terminal 丢弃。训练 500 updates。',
         f(15), colw - 24, 23)
    y += 224
    y = para(d, (M, y),
             '两策略使用相同 Backend、初始化、预算、终端判据、331 帧评价和等待协议；H4 没有额外加入专家 '
             'settle/hold。模型是 MLP 行为克隆，不称 ACT Transformer。', f(15), W - M * 2, 22, MUT)
    y += 8
    y = section(d, y, '3. Stage 5 缩减数据与固定模型')
    y = para(d, (M, y),
             'Stage 5 使用缩减数据 50 / 10 / 10（flat / perturbed / crumpled），70 条示范、590 个动作；'
             'H4 数据为 160 个 chunks、590 个有效动作、50 个 padding。固定候选为 single budget500 best_val '
             'ade60131…（2000 updates）与 H4 best_val epoch 389 ff8c6945…（500 updates）；两者 stats 的'
             '归一化数组逐元素相同，但训练更新数不同，不能称为相同计算预算。',
             f(15), W - M * 2, 22)
    y += 8
    # Figure 1
    img, pos = fit_image(d, OUT / 'fig1_success_rate.png', M, y, W - M * 2, 455)
    im.paste(img, pos)
    y += img.height + 8
    caption = ('图 1. 分档 accepted 率，柱上为成功数/该档 5 个初态。single 总 0/15；'
               'H4 总 2/15（仅 L1 的 4111、4113）。L2/L3 两策略均为 0/5。小样本，描述性结果。')
    para(d, (M, y), caption, f(13), W - M * 2, 19, MUT)
    d.line((M, H - 44, W - M, H - 44), fill='#d7e2ea', width=1)
    d.text((M, H - 35), 'Stage 8 reduced30 · 2026-11-09', font=f(12), fill='#708697')
    d.text((W - M - 70, H - 35), 'Page 1 / 2', font=f(12), fill='#708697')
    return im


def page2():
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    y = 45
    y = section(d, y, '4. 三档结果与逐 seed 配对')
    y = table(d, y,
              ['档', 'single', 'H4', 'H4 成功 seed'],
              [['L1 flat', '0/5', '2/5', '4111, 4113'],
               ['L2 perturbed', '0/5', '0/5', '—'],
               ['L3 crumpled', '0/5', '0/5', '—'],
               ['合计', '0/15', '2/15', '—']],
              [260, 160, 160, 590], fs=16, rh=29)
    y = para(d, (M, y),
             '配对顺序 single/H4：4110 EE/EE；4111 EE/accepted；4112 EE/EE；4113 rejected/accepted；'
             '4114 EE/EE；4215 EE/EE；4216 EE/incomplete；4217 incomplete/incomplete；'
             '4218 EE/incomplete；4219 EE/incomplete；4313 EE/EE；4314 incomplete/EE；'
             '4315 EE/EE；4316 EE/incomplete；4317 EE/EE。',
             f(14), W - M * 2, 20, MUT)
    y += 6
    y = section(d, y, '5. 失败类型与证据')
    img, pos = fit_image(d, OUT / 'fig2_failure_types.png', M, y, W - M * 2, 400)
    im.paste(img, pos)
    y += img.height + 6
    para(d, (M, y),
         '图 2. 沿用已有 result errors/reasons 分类；H4 的 2 个 accepted 不计入失败分布。'
         '状态计数：accepted 2、rejected 1、incomplete 7、execution_error 20。',
         f(13), W - M * 2, 18, MUT)
    y += 40
    y = para(d, (M, y),
             '主要类别：抓取/区域外 4；CLOSE 超出 prepared region 9；waypoint 不收敛 6；'
             '释放顺序错误 1；完整 rejected 1；incomplete/无 331 7。0-action 失败的 evidence audit '
             '出现 “non-BC action label / action count outside budget” 的 fail-closed 警告；对应结果'
             '没有实际执行动作，不能据此推断专家动作注入。', f(14), W - M * 2, 20)
    y += 4
    y = section(d, y, '6. 计时与完整窗口')
    y = table(d, y,
              ['policy', 'cases', 'forward calls', 'first mean ms', '后续 median ms', '后续 P95 ms'],
              [['single', '15', '70', '26.369', '1.168', '1.849'],
               ['H4', '15', '29', '27.493', '1.303', '1.509']],
              [170, 120, 210, 250, 250, 200], fs=15, rh=27)
    y = para(d, (M, y),
             'CUDA 同步，仅计 policy model forward；首次调用单列。每 policy 仅 15 例，P95 仅描述性；'
             'H4 policy calls 较少主要来自失败/截断，不能直接解释为效率收益。完整 331 帧仅 3/30'
             '（single 4113 rejected、H4 4111、H4 4113）；其余 27 例几何/稳定性标记 unavailable，未填 0。',
             f(14), W - M * 2, 20)
    y += 4
    y = section(d, y, '7. 展示视频与复现')
    poster = Image.open(OUT / 'stage9_poster.png').convert('RGB')
    pw = 480
    ph = int(poster.height * pw / poster.width)
    poster = poster.resize((pw, ph), Image.LANCZOS)
    im.paste(poster, (M, y))
    d.rectangle((M, y, M + pw, y + ph), outline='#dbe5ec', width=1)
    x = M + pw + 24
    tmp_y = y
    tmp_y = para(d, (x, tmp_y),
                 '视频 1. 60 s；中英双语字幕；同初态 4113 的 single/H4 并排，同速 30 fps，未做仿真时间重采样；'
                 '另含 H4 4111 成功与 L2/L3 代表失败。画面注明缩减版探索性评估。',
                 f(14), W - M - x, 20, MUT)
    tmp_y += 10
    tmp_y = para(d, (x, tmp_y),
                 '文件：stage9_showcase_bilingual.mp4；raw_results.csv（30 行）；'
                 'STAGE8_REDUCED30_MANIFEST.json；run_reduced30.sh。\n'
                 '复现：使用同一 reduced manifest 与 checkpoint/stats/runner；H4 固定 execute_k=4；'
                 '不要重跑本 30 例来补剩余 90 例。\n'
                 '状态：原 120 例计划保留，剩余 90 例未执行；未重训、未追加采集、未扩容。',
                 f(13), W - M - x, 19)
    y += max(ph, 210) + 12
    y = section(d, y, '8. 限制')
    y = para(d, (M, y),
             '• 缩减版 15 seeds / 30 episodes；H4 2/15、single 0/15 仅描述性，不宣称泛化优势或统计显著性。\n'
             '• 4110–4114、4215、4313–4316 曾用于 Stage 4 专家，不是全新独立 test；未进入 Stage 5 train/val，'
             '也未用于 Stage 6/7 策略调试。\n'
             '• L2/L3 全部失败；27/30 无完整 331 帧，物理几何/稳定性不可用。\n'
             '• 专家与 learned runner 的 recovery settle/hold 等待协议仍有差异，不能把 L2/L3 失败只归因数据量。\n'
             '• 未完成原 120 例；本轮不为改善结果追加实验。',
             f(14), W - M * 2, 21)
    d.line((M, H - 44, W - M, H - 44), fill='#d7e2ea', width=1)
    d.text((M, H - 35), 'Stage 8 reduced30 · 2026-11-09', font=f(12), fill='#708697')
    d.text((W - M - 70, H - 35), 'Page 2 / 2', font=f(12), fill='#708697')
    return im


if __name__ == '__main__':
    p1 = page1()
    p2 = page2()
    p1.save(OUT / 'report_page1.png')
    p2.save(OUT / 'report_page2.png')
    pdf = OUT / 'STAGE9_REPORT.pdf'
    p1.save(pdf, 'PDF', resolution=150.0, save_all=True, append_images=[p2])
    print('PDF_OK', pdf, p1.size, p2.size)
