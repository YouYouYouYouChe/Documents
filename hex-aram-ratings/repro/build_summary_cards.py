"""Build ranked reading cards from published HD-RATING-2.2 match detail.

Run after recalculate_four_days.py. Ranking is descriptive: people who played
different matches are never described as having won a head-to-head comparison.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE = Path(__file__).resolve().parent.parent
DAILY = BASE / 'reports' / 'daily'
MONTHLY = BASE / 'reports' / 'monthly'
HEROES = json.loads((BASE / 'references' / 'riot_ddragon_16.19.1_英雄定位.json').read_text(encoding='utf-8'))['champions']
LABELS = {'Tank': '前排', 'Fighter': '战士', 'Marksman': '射手', 'Mage': '法师', 'Assassin': '刺客', 'Support': '辅助'}
PALETTE = {'前排': '#0A817A', '战士': '#A56719', '射手': '#345DC0', '法师': '#704BC0', '刺客': '#A43B62', '辅助': '#1E836B'}
WIDTH = 1600


def font_file() -> str:
    import os
    candidates = [os.environ.get('HAIDOU_CJK_FONT', ''),
                  str(BASE.parent.parent / 'haido_work' / 'fonts' / 'NotoSansCJKsc-Regular.otf'),
                  '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                  'C:/Windows/Fonts/msyh.ttc',
                  'C:/Windows/Fonts/simhei.ttf']
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise RuntimeError('没有找到中文字体；请设置环境变量 HAIDOU_CJK_FONT 为中文 OTF/TTF 字体路径')


FONT = font_file()
FONTS = {n: ImageFont.truetype(FONT, n) for n in (24, 26, 28, 30, 32, 34, 38, 42, 46, 52, 58, 72)}


def load_rows(days: list[str]) -> list[dict]:
    result = []
    for day in days:
        source = DAILY / day / '逐场评分明细_v2.2.csv'
        if not source.exists():
            raise FileNotFoundError(source)
        with source.open(encoding='utf-8-sig', newline='') as handle:
            for row in csv.DictReader(handle):
                assert row['游戏日'] == day and row['英雄'] in HEROES, (day, row)
                result.append(row)
    return result


def choose_roles(rows: list[dict]) -> tuple[Counter, list[tuple[str, int]], list[str]]:
    roles = Counter(LABELS[HEROES[r['英雄']]['tags'][0]] for r in rows)
    champions = Counter(r['英雄'] for r in rows)
    peak = {h: max((float(r['单局综合分']) for r in rows if r['英雄'] == h and r['单局综合分']), default=-1) for h in champions}
    chosen = sorted(champions, key=lambda h: (-champions[h], -peak[h], h))[:2]
    names = []
    for hero in chosen:
        labels = '/'.join(LABELS[t] for t in HEROES[hero]['tags'])
        names.append(f"{HEROES[hero]['name']}（{labels}）×{champions[hero]}")
    role_order = ['前排', '战士', '射手', '法师', '刺客', '辅助']
    order = sorted(roles.items(), key=lambda item: (-item[1], role_order.index(item[0])))
    return roles, order, names


def profile(name: str, rows: list[dict], period: str) -> dict:
    total = len(rows)
    rated = [r for r in rows if r['是否纳入通用均分'] == '是']
    excluded = total - len(rated)
    n = len(rated)
    roles, ordered_roles, names = choose_roles(rows)
    days = sorted(set(r['游戏日'] for r in rows))
    if n == 0:
        return {'name': name, 'score': None, 'n': 0, 'total': total, 'excluded': excluded, 'days': len(days),
                'roles': ordered_roles, 'heroes': names,
                'comments': ('本期均为软辅局；当前战绩数据无法量化保护效果。', '保留全部原始战绩；本期暂无通用均分和分数序位。'),
                'O': None, 'T': None, 'KP': None, 'V': None}
    avg = lambda key: statistics.mean(float(r[key]) for r in rated)
    scores = [float(r['单局综合分']) for r in rated]
    front = [r for r in rated if HEROES[r['英雄']]['tags'][0] == 'Tank']
    marks = [r for r in rated if HEROES[r['英雄']]['tags'][0] == 'Marksman']
    support = [r for r in rated if HEROES[r['英雄']]['tags'][0] == 'Support']
    dominant, dominant_count = ordered_roles[0]
    if dominant == '前排' and len(front) / total >= .4:
        a = statistics.mean(float(r['真实承伤占比%']) for r in front)
        part1 = f'前排 {len(front)} 场，前排局真实承伤占比均值 {a:.0f}%；占比代表负担，不代表承伤质量。'
    elif dominant == '射手' and len(marks) / total >= .4:
        a = statistics.mean(float(r['输出占比%']) for r in marks)
        part1 = f'射手 {len(marks)} 场，射手局输出占比均值 {a:.0f}%；高输出仍需结合对局环境。'
    elif dominant == '辅助' and len(support) / total >= .4:
        part1 = f'辅助 {len(support)} 场纳入评分；软辅局另列，保护效果尚无法量化。'
    else:
        second = f'；也使用{ordered_roles[1][0]} {ordered_roles[1][1]} 场' if len(ordered_roles) > 1 else ''
        part1 = f'主用{dominant} {dominant_count}/{total} 场{second}；输出分 {avg("输出分O"):.1f}，承伤分 {avg("承伤分T"):.1f}。'
    hi = max(rated, key=lambda r: float(r['单局综合分']))
    lo = min(rated, key=lambda r: float(r['单局综合分']))
    match_label = lambda r: (r['游戏日'][-2:] + '日' if period == 'month' else '') + r['场次']
    if n == 1:
        part2 = f'仅 1 场：{HEROES[hi["英雄"]]["name"]} {scores[0]:.1f}；样本太少，不作长期判断。'
    else:
        part2 = (f'最高 {match_label(hi)} {HEROES[hi["英雄"]]["name"]} {float(hi["单局综合分"]):.1f}；'
                 f'最低 {match_label(lo)} {HEROES[lo["英雄"]]["name"]} {float(lo["单局综合分"]):.1f}。')
        if n == 2:
            part2 += '仅两场。'
    return {'name': name, 'score': statistics.mean(scores), 'n': n, 'total': total, 'excluded': excluded, 'days': len(days),
            'roles': ordered_roles, 'heroes': names, 'comments': (part1, part2),
            'O': avg('输出分O'), 'T': avg('承伤分T'), 'KP': avg('参团分'), 'V': avg('死亡分')}


def sorted_profiles(rows: list[dict], period: str) -> tuple[list[dict], bool]:
    groups = defaultdict(list)
    for row in rows:
        groups[row['玩家']].append(row)
    profiles = sorted((profile(k, v, period) for k, v in groups.items()), key=lambda x: (x['score'] is None, -(x['score'] or 0), x['name']))
    signatures = {name: frozenset((r['游戏日'], r['场次']) for r in rr if r['是否纳入通用均分'] == '是') for name, rr in groups.items()}
    same_games = len(set(signatures.values())) == 1 and all(p['n'] for p in profiles)
    for i, item in enumerate(profiles):
        item['rank'] = i + 1 if item['score'] is not None else '—'
    return profiles, same_games


def draw_card(path: Path, title: str, subtitle: str, players: list[dict], same_games: bool, note: str) -> None:
    height = 365 + 380 * len(players) + 175
    im = Image.new('RGB', (WIDTH, height), '#F0F3F8')
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, WIDTH, 274), fill='#142949')
    d.text((74, 48), title, font=FONTS[72], fill='#FFFFFF')
    d.text((78, 151), subtitle, font=FONTS[34], fill='#BBD2F2')
    d.rounded_rectangle((76, 294, 1523, 360), radius=21, fill='#DFEAFB')
    heading = ('同场次参赛，按均分排列' if same_games else '按各自均分排列；场次不同，序号不代表同条件实力名次')
    d.text((104, 307), heading, font=FONTS[32], fill='#24416E')
    for i, p in enumerate(players):
        y = 386 + i * 380
        d.rounded_rectangle((81, y + 8, 1527, y + 360), radius=29, fill='#E0E6F0')
        d.rounded_rectangle((76, y, 1522, y + 352), radius=29, fill='#FFFFFF')
        d.rounded_rectangle((102, y + 29, 181, y + 106), radius=18, fill='#EBF0FF')
        rank = f"{p['rank']:02}" if isinstance(p['rank'], int) else p['rank']
        d.text((119, y + 37), rank, font=FONTS[46], fill='#3260C8')
        d.text((201, y + 28), p['name'].split('#')[0], font=FONTS[46], fill='#1A2740')
        matchline = f"计分 {p['n']}/{p['total']} 场 · 软辅 {p['excluded']} 场"
        if '月' in title: matchline += f" · {p['days']} 天"
        d.text((201, y + 87), matchline, font=FONTS[28], fill='#68788D')
        d.text((1264, y + 23), f"{p['score']:.2f}" if p['score'] is not None else '—', font=FONTS[58], fill='#284EAD')
        score_label = '阶段均分' if '阶段月评' in title else ('月分' if '月评' in title else '日分')
        d.text((1255, y + 92), score_label if p['score'] is not None else '暂无通用分', font=FONTS[26], fill='#68788D')
        roleline = ' · '.join(f'{name} {count}' for name, count in p['roles'])
        d.text((111, y + 134), '英雄定位：' + roleline, font=FONTS[30], fill='#243650')
        d.text((111, y + 181), '代表英雄：' + '、'.join(p['heroes']), font=FONTS[28], fill='#526888')
        d.text((111, y + 225), p['comments'][0], font=FONTS[28], fill='#2C415D')
        d.text((111, y + 269), p['comments'][1], font=FONTS[28], fill='#2C415D')
        itemline = (f"分项（仅计分场）：输出 {p['O']:.1f} · 承伤 {p['T']:.1f} · 参团 {p['KP']:.1f} · 死亡 {p['V']:.1f}"
                    if p['n'] else '仅参与软辅局；可在逐场明细中查看原始参团和出装。')
        d.text((111, y + 311), itemline, font=FONTS[24], fill='#667897')
    bottom = 393 + len(players) * 380
    d.text((83, bottom), note, font=FONTS[26], fill='#52667E')
    d.text((83, bottom + 49), 'HD-RATING-2.2 · 英雄定位：Riot Data Dragon 16.19.1 静态标签；不等于本局出装或职责。', font=FONTS[24], fill='#52667E')
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.stem + '.pending.png')
    im.save(pending, optimize=True)
    with Image.open(pending) as preview:
        preview.verify()
    pending.replace(path)


START = '<!-- HD-RATING-2.2 SUMMARY START -->'
END = '<!-- HD-RATING-2.2 SUMMARY END -->'


def add_report_section(readme: Path, image_name: str, players: list[dict], same_games: bool, period: str) -> None:
    original = readme.read_text(encoding='utf-8') if readme.exists() else f'# {readme.parent.name} 阶段月评｜HD-RATING-2.2\n'
    for version in ('2.1', '2.2'):
        start = f'<!-- HD-RATING-{version} SUMMARY START -->'
        end = f'<!-- HD-RATING-{version} SUMMARY END -->'
        if start in original:
            a = original.index(start)
            b = original.index(end, a) + len(end)
            original = original[:a].rstrip() + '\n\n' + original[b:].lstrip()
    kind = '月分' if period == 'month-final' else ('阶段均分' if period == 'month' else '日分')
    lines = [START, '', '## 一图流：按分数排序', '', f'![{kind}一图流]({image_name})', '',
             f'**序号说明**：按各自有效单局均分从高到低排序；{"每人参与同一批比赛，可作同场次比较。" if same_games else "参赛场次不同，序号仅代表已收集样本的均分大小，不代表同条件实力排名。"}', '',
             '**软辅处理**：经逐局核验的保护型软辅选手保留战绩，不计该局通用综合分；仍参与同场队友五人团队分母和环境调整。下面英雄分布按实际参赛局，分项点评按纳入评分局。', '',
             f'| 序号 | 队员 | {kind} | 计分 / 实际 | 软辅 | 主要英雄定位 |', '| ---: | --- | ---: | ---: | ---: | --- |']
    for p in players:
        kinds = '／'.join(f'{label}{n}' for label, n in p['roles'])
        score = f"{p['score']:.2f}" if p['score'] is not None else '—'
        lines.append(f"| {p['rank']} | {p['name']} | {score} | {p['n']} / {p['total']} | {p['excluded']} | {kinds} |")
    lines += ['', '### 逐人点评', '']
    for p in players:
        lines += [f"**{p['rank']}. {p['name']}（计分 {p['n']}/{p['total']} 场，软辅 {p['excluded']} 场）**：代表英雄为{'、'.join(p['heroes'])}。{p['comments'][0]}{p['comments'][1]}", '']
    lines += ['英雄定位以 [Riot Data Dragon 16.19.1 静态标签](../../../references/riot_ddragon_16.19.1_英雄定位.json)为准；标签不说明本局出装、单前排状态或实际贡献。' if period == 'day' else '英雄定位以 [Riot Data Dragon 16.19.1 静态标签](../../references/riot_ddragon_16.19.1_英雄定位.json)为准；标签不说明本局出装、单前排状态或实际贡献。', '', END, '']
    heading, separator, body = original.partition('\n')
    if period == 'month-final':
        heading = f'# {readme.parent.name} 月评｜HD-RATING-2.2'
    else:
        heading = heading.replace('HD-RATING-2.1', 'HD-RATING-2.2')
    readme.write_text((heading + '\n\n' + '\n'.join(lines) + '\n' + body.lstrip('\n')).rstrip() + '\n', encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--month', default='2026-09', help='Month with day CSVs, YYYY-MM')
    parser.add_argument('--final', action='store_true', help='Only after all eligible days have been checked; publish full-month result')
    args = parser.parse_args()
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    start = datetime.fromisoformat(args.month + '-01').replace(tzinfo=ZoneInfo('Asia/Shanghai'))
    if args.final:
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1, hour=4)
        if datetime.now(ZoneInfo('Asia/Shanghai')) < next_month:
            raise ValueError('该游戏月尚未结束，不能发布完整月评')
    days = sorted(p.name for p in DAILY.glob(f'{args.month}-*') if (p / '逐场评分明细_v2.2.csv').exists())
    if not days:
        raise ValueError(f'{args.month} 没有 HD-RATING-2.2 逐场明细')
    all_rows = []
    for day in days:
        rows = load_rows([day]); all_rows.extend(rows)
        players, same_games = sorted_profiles(rows, 'day')
        name = '日评一图流_HD-RATING-2.2.png'
        draw_card(DAILY / day / name, f'{day} 海斗日评', f'{len({r["场次"] for r in rows})} 场组排 · 04:00 换日 · 按日分从高到低', players, same_games,
                  '保护型软辅个人局不计通用均分；同场其他人照常。分数是复盘参考。')
        add_report_section(DAILY / day / 'README.md', name, players, same_games, 'day')
        print(day, len(rows), 'records', len(players), 'players')
    players, same_games = sorted_profiles(all_rows, 'month')
    monthdir = MONTHLY / args.month
    name = ('月评' if args.final else '阶段月评') + '一图流_HD-RATING-2.2.png'
    label = '月评' if args.final else '阶段月评'
    subtitle = f'已核对 {len(days)} 个游戏日（{", ".join(d[-2:] for d in days)} 日）' if args.final else f'仅已收集 {len(days)} 个游戏日（{", ".join(d[-2:] for d in days)} 日）· 非整月成绩'
    draw_card(monthdir / name, f'{args.month} {label}', subtitle, players, same_games,
              '按已核对的本月有效单局等权平均；场次不同仅表示分数排序。' if args.final else '只纳入已完整评分的游戏日；其他日期缺失，不代表整月完整排名。')
    add_report_section(monthdir / 'README.md', name, players, same_games, 'month-final' if args.final else 'month')
    print(args.month, len(all_rows), 'records', len(players), 'players ·', 'full month' if args.final else 'incomplete monthly sample')


if __name__ == '__main__':
    main()
