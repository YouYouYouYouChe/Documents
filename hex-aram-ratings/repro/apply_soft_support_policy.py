"""Publish HD-RATING-2.2 from frozen 2.1 details; do not change team calculations."""
from __future__ import annotations

import csv
import json
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
REPRO = Path(__file__).resolve().parent
RULE = json.loads((REPRO / 'soft_support_exclusions_v2.2.json').read_text(encoding='utf-8'))
KEYS = ('游戏日', '场次', '玩家', '英雄')
EXCLUDED = {tuple(entry[key] for key in KEYS): entry for entry in RULE['entries']}
assert len(EXCLUDED) == len(RULE['entries'])
VARIANTS = [f'辅助_{c:.1f}_{lam:.1f}' for c in (.6, .7, .8) for lam in (.8, 1, 1.2)]


def read_rows(day: str) -> list[dict]:
    source = BASE / 'reports' / 'daily' / day / '逐场评分明细_v2.1.csv'
    with source.open(encoding='utf-8-sig', newline='') as handle:
        old = list(csv.DictReader(handle))
    assert old and len(old) == len({(r['场次'], r['玩家']) for r in old}), day
    rows = []
    for row in old:
        row = dict(row)
        key = tuple(row[k] for k in KEYS)
        excluded = EXCLUDED.get(key)
        row['原公式试算分_v2.1'] = row['单局综合分']
        row['是否纳入通用均分'] = '否' if excluded else '是'
        row['处理理由'] = excluded['依据'] if excluded else ''
        if excluded:
            row['单局综合分'] = ''
            for k in VARIANTS:
                row[k] = ''
        # The historic prefix 辅助_ referred to auxiliary sensitivity schemes,
        # not support champions. Clarify it in new published column names.
        for old_key in VARIANTS:
            row['敏感性_' + old_key.removeprefix('辅助_')] = row.pop(old_key)
        rows.append(row)
    target = source.with_name('逐场评分明细_v2.2.csv')
    with target.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    return rows


def summarize(day: str, rows: list[dict]) -> None:
    directory = BASE / 'reports' / 'daily' / day
    groups = defaultdict(list)
    for row in rows:
        groups[row['玩家']].append(row)
    summaries = []
    for player, personal in groups.items():
        eligible = [r for r in personal if r['是否纳入通用均分'] == '是']
        removed = [r for r in personal if r['是否纳入通用均分'] == '否']
        assert len(eligible) + len(removed) == len(personal)
        mean = lambda key: statistics.mean(float(r[key]) for r in eligible) if eligible else None
        out = {'序位': '', '玩家': player, '可评分对局均分': mean('单局综合分'),
               '纳入评分场数': len(eligible), '实际参赛场数': len(personal), '软辅场数': len(removed),
               '纳入率': len(eligible) / len(personal),
               '输出分O均值': mean('输出分O'), '承伤分T均值': mean('承伤分T'),
               '参团分均值': mean('参团分'), '死亡分均值': mean('死亡分'),
               '纳入场次': '、'.join(r['场次'] for r in eligible),
               '软辅场次': '、'.join(r['场次'] + ' ' + r['英雄'] for r in removed)}
        summaries.append(out)
    summaries.sort(key=lambda x: (-x['可评分对局均分'] if x['可评分对局均分'] is not None else float('inf'), x['玩家']))
    for n, item in enumerate(summaries, 1):
        if item['可评分对局均分'] is not None:
            item['序位'] = n
    with (directory / '日评汇总_v2.2.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(summaries)
    same = len({frozenset(r['场次'] for r in rows if r['玩家'] == name and r['是否纳入通用均分'] == '是') for name in groups}) == 1
    explanation = ('同一批纳入评分的比赛' if same else '纳入评分的比赛集合不同，序号只表示各自样本的均分大小')
    lines = [f'# {day} 海斗日评｜HD-RATING-2.2', '',
             '**范围**：固定名单至少三人参加的组排；本日全场对局照常保留。仅逐局确认的保护型软辅选手不计算通用综合分，其他队员同场照常计分。路人和软辅仍参与五人占比和环境系数。',
             '**公式**：其余对局沿用 v2.1 的单局公式，输出、承伤、参团、死亡均未改权重。排除名单及证据见 [逐局清单](../../../repro/soft_support_exclusions_v2.2.json)，规则见[评分标准](../../../docs/海斗日评与月评评分标准.md)。',
             f'**样本**：{len({r["场次"] for r in rows})} 场组排；名单队员 {len(rows)} 条实际参赛记录，其中 {sum(r["是否纳入通用均分"] == "否" for r in rows)} 条软辅个人记录不进入通用均分；{explanation}。',
             '**游戏日**：北京时间 04:00 至次日 04:00；部分截图未显示精确钟点，沿用用户给出的截图日期归属。英雄参考及版本推断沿用 v2.1，仍须注意跨站真实承伤口径未经完全核实。', '',
             '| 均分序位 | 队员 | 可评分对局均分 | 纳入 / 实际 | 软辅场数 | 输出分 | 承伤分 | 参团分 | 死亡分 |',
             '| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for item in summaries:
        score = f'{item["可评分对局均分"]:.2f}' if item['可评分对局均分'] is not None else '—'
        parts = [f'{item[k]:.1f}' if item[k] is not None else '—' for k in ('输出分O均值','承伤分T均值','参团分均值','死亡分均值')]
        lines.append(f'| {item["序位"] or "—"} | {item["玩家"]} | {score} | {item["纳入评分场数"]} / {item["实际参赛场数"]} | {item["软辅场数"]} | '+ ' | '.join(parts) + ' |')
    lines += ['', '**判定与复核**：排除记录在 [v2.2 逐场明细](逐场评分明细_v2.2.csv)中以 `是否纳入通用均分=否` 标记，`单局综合分` 留空；`原公式试算分_v2.1` 仅供比较旧规则偏差，不纳入日月总分。v2.1 和 v2.0 历史 CSV 均保留原文件。',
              '**阅读方式**：纳入率表示本版可使用的通用评分覆盖率，并非数据采集完整率；软辅局数据完整，但职责未被通用公式衡量。纳入场数不同或所玩场次不同，均分序位不能解释为同条件实力名次。', '',
              '## 逐场截图', '', '| 场次 | 队内参评者 | 原始截图 |', '| --- | ---: | --- |']
    source = BASE / 'repro' / 'audited_4days_heroes.json'
    games = [g for g in json.loads(source.read_text(encoding='utf-8')) if g['day_folder'] == day]
    for game in games:
        file = Path(game['file']).name
        lines.append(f'| M{game["match"]:02d} | {sum(a["player"] != "非六人名单" for a in game["rows"])} | [查看](../../../screenshots/{day}/{file}) |')
    (directory / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(day, ', '.join(f'{a["玩家"].split("#")[0]} {a["可评分对局均分"]:.2f} ({a["纳入评分场数"]}/{a["实际参赛场数"]})' for a in summaries))


def main():
    all_rows = []
    for day in ('2026-09-23','2026-09-24','2026-09-26','2026-09-27'):
        rows = read_rows(day)
        all_rows.extend(rows)
        summarize(day, rows)
    observed = {tuple(r[k] for k in KEYS) for r in all_rows if r['是否纳入通用均分'] == '否'}
    assert len(all_rows) == 160 and observed == set(EXCLUDED), (len(all_rows), observed ^ set(EXCLUDED))
    for case in RULE['checked_but_included']:
        matched = [r for r in all_rows if all(r[k] == case[k] for k in ('游戏日', '场次', '英雄'))]
        assert len(matched) == 1 and matched[0]['是否纳入通用均分'] == '是', case
    subprocess.run([sys.executable, str(REPRO / 'build_summary_cards.py')], check=True)


if __name__ == '__main__':
    main()
