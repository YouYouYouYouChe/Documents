"""Render the exact HD-RATING-2.2 public rules as a reproducible PNG."""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / 'docs' / '海斗评分说明一图流_HD-RATING-2.2.png'


def font_path():
    for path in (os.environ.get('HAIDOU_CJK_FONT'),
                 BASE.parent.parent / 'haido_work/fonts/NotoSansCJKsc-Regular.otf',
                 '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                 'C:/Windows/Fonts/msyh.ttc'):
        if path and Path(path).is_file():
            return str(path)
    raise RuntimeError('缺少中文字体；请通过 HAIDOU_CJK_FONT 指定 OTF / TTF')


FONTS = {n: ImageFont.truetype(font_path(), n) for n in (23, 26, 27, 29, 30, 32, 34, 36, 37, 41, 45, 52, 61, 70)}
W, H = 1600, 3260
BG, NAVY, BLUE, TEAL, INK, SUB = '#F1F5FB', '#16294A', '#3265D0', '#008C83', '#1D2C44', '#61718A'
image = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(image)


def label(x, y, message, size=34, color=INK, max_width=None):
    font = FONTS[size]
    if max_width is not None:
        assert d.textlength(message, font=font) <= max_width, (message, d.textlength(message, font=font), max_width)
    d.text((x, y), message, font=font, fill=color)


def panel(y, height, number, title, hint=None):
    d.rounded_rectangle((63, y + 7, 1537, y + height + 7), radius=30, fill='#DCE5F1')
    d.rounded_rectangle((62, y, 1536, y + height), radius=30, fill='#FFFFFF')
    d.rounded_rectangle((89, y + 24, 157, y + 88), radius=19, fill='#E7EEFF')
    label(103, y + 27, number, 37, BLUE)
    label(181, y + 29, title, 41, INK, 1310)
    if hint:
        label(184, y + 89, hint, 26, SUB, 1294)


def box(x1, y1, x2, y2, color):
    d.rounded_rectangle((x1, y1, x2, y2), radius=21, fill=color)


d.rounded_rectangle((0, -55, W, 290), radius=40, fill=NAVY)
label(77, 53, '海斗评分，一张图看懂', 70, '#FFFFFF')
label(82, 151, 'HD-RATING-2.2  ·  海克斯大乱斗六人轮换组排', 34, '#BFD2F3')
box(81, 220, 720, 268, '#284569')
label(104, 224, '先判断是否计分 → 单局分 → 日分 / 月分', 29, '#FFFFFF')

# 01 Eligibility is evaluated per person, never per whole match.
panel(318, 436, '01', '先看这场：谁进入通用评分？', '判定的是“此人此局”，不是把整场比赛删掉')
label(92, 443, '固定名单中有 3～5 人同场，即纳入组排范围；北京时间 04:00 换日。', 32, INK, 1415)
box(89, 510, 783, 644, '#EAF0FF')
box(803, 510, 1509, 644, '#E0F4F1')
label(108, 525, '普通计分局', 37, BLUE)
label(108, 581, '该人获得单局分，进入本人日 / 月均分。', 29, INK, 665)
label(820, 525, '确认的保护型软辅局', 37, TEAL)
label(820, 581, '该人通用分留空，保留原始战绩。', 29, INK, 670)
label(93, 667, '同场其他人照常计分；软辅和路人仍计入全队五人的计算。', 30, INK, 1410)
label(93, 707, '本批排除：卡尔玛 / 索拉卡 / 烈娜塔 / 悠米各 1 局；输出装赛娜继续计分。', 26, SUB, 1410)

# 02 Two signal families are computed separately for damage and true tanking.
panel(780, 673, '02', '输出与承伤：看同英雄，也看团队份额', '同一套步骤分别算出输出分 O、真实承伤分 T')
box(88, 924, 785, 1288, '#EAF0FF')
box(805, 924, 1509, 1288, '#E0F4F1')
label(109, 946, 'A · 和同英雄参考比', 37, BLUE)
label(109, 1010, '先算“我每分钟多少” ÷ “该英雄参考每分钟”', 27, INK, 664)
label(109, 1058, '本队五人的该倍率取中位数，并且不低于 1', 27, INK, 665)
label(109, 1107, '调整后倍率 ＝ 个人倍率 ÷ 本场环境系数', 27, BLUE, 665)
label(109, 1157, '同英雄发挥分 F(r) ＝ 100r ÷ (1＋r)', 29, INK, 665)
label(109, 1213, '调整后倍率为 1 → 发挥分 50', 26, SUB)
label(827, 946, 'B · 看本场承担多少', 37, TEAL)
label(827, 1010, '个人占比 ＝ 自己的量 ÷ 己方五人的总量', 27, INK, 659)
label(827, 1058, '输出与真实承伤分别求各自的占比', 27, INK)
label(827, 1107, '团队负担分 B(s) ＝ 100s ÷ (s＋0.20)', 29, TEAL, 656)
label(827, 1163, '20% 是五人等分参照，并非英雄达标线', 26, SUB, 654)
label(827, 1213, '占比越高加分越缓，不证明有效贡献', 26, SUB, 654)
box(90, 1310, 1507, 1424, '#F4F7FB')
label(113, 1323, '输出分 O ＝ 60% × 调整后同英雄发挥分 ＋ 40% × 本场输出负担分', 32, BLUE, 1370)
label(113, 1374, '承伤分 T ＝ 60% × 调整后同英雄发挥分 ＋ 40% × 本场承伤负担分', 32, TEAL, 1370)

# 03 Champion weights, participation, deaths, final sum.
panel(1479, 586, '03', '再合成单局分：战斗 70% · 参团 20% · 死亡 10%', '英雄权重只决定“战斗 70%”内部更偏输出还是更偏承伤')
box(89, 1617, 1509, 1737, '#F2F6FB')
label(110, 1634, '英雄输出特点 A ＝ 该英雄参考分均输出 ÷ 全英雄参考分均输出中位数', 29, BLUE, 1370)
label(110, 1687, '英雄承伤特点 B ＝ 该英雄参考分均真实承伤 ÷ 全英雄参考承伤中位数', 29, TEAL, 1370)
label(101, 1764, '英雄输出权重 wO＝A÷(A＋B)；承伤权重 wT＝B÷(A＋B)。', 32, INK, 1375)
label(101, 1818, '参团分：个人参团率与同英雄参考比，再用 F(r) 换算。', 30, INK, 1375)
label(101, 1865, '死亡分：每分钟死亡次数与同英雄参考比；死亡越多，分越低。', 30, INK, 1375)
box(89, 1930, 1509, 2023, NAVY)
label(113, 1945, '单局分 S＝70%×(wO×O＋wT×T)＋20%×参团分＋10%×死亡分', 32, '#FFFFFF', 1370)

# 04 Aggregation explicitly excludes only personal support records.
panel(2090, 533, '04', '日分与月分：只平均“适用的个人场次”', '同一选手各计分局等权，不把全天均分再平均成月分')
box(89, 2223, 1509, 2318, '#EAF0FF')
label(110, 2243, '日分＝当天已计分的单局分之和 ÷ 当天本人计分场数', 36, BLUE, 1370)
box(89, 2337, 1509, 2432, '#E0F4F1')
label(110, 2357, '月分＝本月已计分的单局分之和 ÷ 本月本人计分场数', 36, TEAL, 1370)
label(102, 2460, '例如 9 月 27 日：羊村头目慢羊羊参赛 7 局，烈娜塔局不计通用分，', 30, INK, 1380)
label(102, 2510, '其余 6 局均分 48.86。图里应写“计分 6 / 实际 7 · 软辅 1”。', 30, INK, 1380)
label(102, 2565, '若一个人当天只玩软辅：显示参赛场数，日分及排序留空。', 26, SUB, 1380)

# 05 Reading rules and remaining uncertainty.
panel(2648, 458, '05', '最后：这个分数能说明什么？', '它是公开公式下的战绩复盘参考，不是官方贡献率或玩家实力百分位')
label(101, 2784, '✓  请同时看英雄选择、计分 / 实际 / 软辅场数，以及逐场明细。', 29, INK, 1380)
label(101, 2841, '✓  队员场次不同，只能按各自均分列序位，不作同条件实力排名。', 29, INK, 1380)
label(101, 2899, '✓  真实承伤＝承伤＋自我减伤；第三方参考的跨站口径仍待核实。', 29, INK, 1380)
label(101, 2957, '！  治疗、护盾、控制效果、伤害质量与时长成长仍无法可靠计分。', 29, TEAL, 1380)
label(101, 3015, '！  英雄静态“辅助”标签不等于软辅；须逐局核对职责和截图。', 29, TEAL, 1380)

d.line((74, 3145, 1525, 3145), fill='#DCE6F4', width=2)
label(83, 3163, 'HD-RATING-2.2 · 规则详见 docs/海斗日评与月评评分标准.md · 2026-09-28', 26, SUB, 1415)
label(83, 3204, '本图解释计算流程；逐局软辅核验名单与四天逐场明细在仓库 repro / reports 目录。', 23, SUB, 1415)


def main():
    temp = OUT.with_name(OUT.stem + '.pending.png')
    image.save(temp, optimize=True)
    with Image.open(temp) as check:
        check.verify()
    temp.replace(OUT)
    print(f'{OUT}: {W}x{H}, {OUT.stat().st_size} bytes')


if __name__ == '__main__':
    main()
