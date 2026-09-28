"""Recompute four game days with HD-RATING-2.1 from transcriptions and frozen hero table."""
import json,csv,statistics,math,hashlib,subprocess,sys
from collections import defaultdict
from pathlib import Path
P=Path(__file__).resolve().parent
BASE=P.parent
G=json.loads((P/'audited_4days_heroes.json').read_text());REF=json.loads((BASE/'references/aramkit_v16.19_全分段_2026-09-28.json').read_text());CH=REF['champions']
VERIFIED=json.loads((P/'kda_verified.json').read_text())
# Explicit fixes for OCR artifacts, transcribed from the source screenshots.
FIX={('23',1,5,'true_tank_shown'):48000,('23',3,1,'damage_shown'):47000,('23',3,3,'damage_shown'):48000,
     ('23',4,3,'true_tank_shown'):47000,('24',5,1,'true_tank_shown'):44000}
def parse_time(v):
 a,b=map(int,v.split(':'));return a+b/60

def ref(slug):
 s=CH[slug]['stats'];dur=parse_time(s['游戏时长']);n=lambda key:float(s[key].replace(',',''))
 return {'bO':n('对英雄伤害')/dur,'bT':(n('承受伤害')+n('自我减免'))/dur,
         'bK':float(s['参团率'].rstrip('%'))/100,'bV':n('平均死亡')/dur}
R={slug:ref(slug) for slug in CH};MO=statistics.median([v['bO'] for v in R.values()]);MT=statistics.median([v['bT'] for v in R.values()])
def f(x):return 100*x/(1+x)
def b(x):return 100*x/(x+.2)
rows=[]
for g in G:
 day=g['day_folder'];short=day[-2:];game=g['match'];t=parse_time(g['duration']);K=sum(x[0] for x in VERIFIED[short][game-1]);assert K>0
 assert len(g['rows'])==5 and t>4
 for a in g['rows']:
  a['kda']=VERIFIED[short][game-1][a['row']-1]
  for col in ('damage_shown','true_tank_shown','kda'):
   if (short,game,a['row'],col) in FIX:a[col]=FIX[(short,game,a['row'],col)]
 known=sum(a['player']!='非六人名单' for a in g['rows']);assert known>=3
 # The same match's five teammates supply the environment coefficient, including outsiders.
 # If any of the five inputs is absent, no complete score may be reported for that match.
 ratios=[]
 for a in g['rows']:
  assert a['champion'] in R and a['damage_shown'] is not None and a['true_tank_shown'] is not None,(day,game,a)
  r0=R[a['champion']]
  ratios.append((a['damage_shown']/t/r0['bO'],a['true_tank_shown']/t/r0['bT']))
 eO=max(1.0,statistics.median(x[0] for x in ratios))
 eT=max(1.0,statistics.median(x[1] for x in ratios))
 for a in g['rows']:
  if a['player']=='非六人名单':continue
  assert all(a[c] is not None for c in ['damage_shown','true_tank_shown','kda']),(day,game,a)
  hero=a['champion'];r=R[hero];kills,deaths,assists=a['kda'];assert kills+assists<=K+1,(day,game,a['player'],a['kda'],K)
  shareO=a['output_pct']/100;shareT=a['true_tank_pct']/100
  # Screenshots publish whole-percent shares; use them as displayed, including strangers in denominator.
  ro=a['damage_shown']/t/r['bO'];rt=a['true_tank_shown']/t/r['bT'];rk=(kills+assists)/K/r['bK'];
  ro_adj=ro/eO;rt_adj=rt/eT
  O=.6*f(ro_adj)+.4*b(shareO);T=.6*f(rt_adj)+.4*b(shareT);KP=f(rk);V=100*r['bV']/(deaths/t+r['bV']);
  ao=r['bO']/MO;at=r['bT']/MT;wo=ao/(ao+at);wt=1-wo
  variants={}
  for c in [.6,.7,.8]:
   for lam in [.8,1,1.2]:
    wo2=lam*wo/(lam*wo+wt);variants[f'{c:.1f}_{lam:.1f}']=c*(wo2*O+(1-wo2)*T)+(.9-c)*KP+.1*V
  score=variants['0.7_1.0']
  rows.append({'游戏日':day,'场次':f'M{game:02d}','截图':g['file'],'队内熟人数':known,'玩家':a['player'],'英雄':hero,'参考链接':CH[hero]['url'],
               '时长分钟':t,'己方总击杀':K,'击杀':kills,'死亡':deaths,'助攻':assists,
               '输出显示值':a['damage_shown'],'真实承伤显示值':a['true_tank_shown'],
               '输出占比%':a['output_pct'],'真实承伤占比%':a['true_tank_pct'],
               '输出倍率':ro,'承伤倍率':rt,'本场输出环境系数':eO,'本场承伤环境系数':eT,
               '调整后输出倍率':ro_adj,'调整后承伤倍率':rt_adj,
               '参团倍率':rk,'输出权重':wo,'输出分O':O,'承伤分T':T,
               '参团分':KP,'死亡分':V,'单局综合分':score,**{'辅助_'+key:val for key,val in variants.items()}})
assert len(rows)==160,len(rows)
for day in sorted({r['游戏日'] for r in rows}):
 subset=[r for r in rows if r['游戏日']==day];directory=BASE/'reports/daily'/day;directory.mkdir(exist_ok=True)
 with (directory/'逐场评分明细_v2.1.csv').open('w',encoding='utf-8-sig',newline='') as fp:
  w=csv.DictWriter(fp,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(subset)
 totals=[]
 for name in sorted({r['玩家'] for r in subset}):
  games=[r for r in subset if r['玩家']==name];n=len(games);mean=lambda col:sum(x[col] for x in games)/n
  variants={key:mean('辅助_'+key) for key in ['0.6_0.8','0.6_1.0','0.6_1.2','0.7_0.8','0.7_1.0','0.7_1.2','0.8_0.8','0.8_1.0','0.8_1.2']}
  totals.append({'玩家':name,'日分':mean('单局综合分'),'场数':n,'团队输出占比%':mean('输出占比%'),'团队真实承伤占比%':mean('真实承伤占比%'),
                 '分均输出':sum(x['输出显示值']/x['时长分钟'] for x in games)/n,'分均真实承伤':sum(x['真实承伤显示值']/x['时长分钟'] for x in games)/n,
                 '平均输出倍率':mean('输出倍率'),'平均承伤倍率':mean('承伤倍率'),
                 '平均调整后输出倍率':mean('调整后输出倍率'),'平均调整后承伤倍率':mean('调整后承伤倍率'),
                 '平均输出分':mean('输出分O'),'平均承伤分':mean('承伤分T'),
                 '平均参团分':mean('参团分'),'平均死亡分':mean('死亡分'),'九方案':variants})
 same_matches=len({tuple(sorted(r['场次'] for r in subset if r['玩家']==v['玩家'])) for v in totals})==1
 totals.sort(key=lambda x:-x['日分'])
 for rank,v in enumerate(totals,1):
  # When the sets of games differ this is only a displayed score ordering.
  v['名次']=rank
  if same_matches:
   places=[1+sum(other['九方案'][key]>v['九方案'][key] for other in totals) for key in v['九方案']]
   v['九方案名次范围']=f'{min(places)}～{max(places)}'
  else:v['九方案名次范围']=''
 with (directory/'日评汇总_v2.1.csv').open('w',encoding='utf-8-sig',newline='') as fp:
  fields=['名次','玩家','日分','场数','九方案名次范围','团队输出占比%','团队真实承伤占比%','分均输出','分均真实承伤','平均输出倍率','平均承伤倍率','平均调整后输出倍率','平均调整后承伤倍率','平均输出分','平均承伤分','平均参团分','平均死亡分'];w=csv.DictWriter(fp,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows({k:v[k] for k in fields} for v in totals)
 lines=[f'# {day} 海斗日评｜HD-RATING-2.1', '',f'**版本**：[国服 26.19 更新公告](https://lol.qq.com/gicp/news/410/37097271.html)于 9 月 23 日维护上线，按截图所给日期推断本批比赛处于该版本；ARAMKit 页面标记 v16.19。**游戏日**：北京时间当天 04:00 至次日 04:00，按截图所在游戏日目录归属。',
        '**范围**：六人名单中参加本场 3～5 人组排者记个人单局分；名单外玩家参与五人团队占比分母，不进入榜单。',
        '**本场环境调整**：先将己方五名玩家（含名单外队友）各自的分均输出、分均真实承伤除以对应英雄参考速率，分别取五个倍率的中位数，并各与 1 取大值作为环境系数。个人原倍率除以对应系数后参与发挥分计算；本场占比仍使用截图显示值。系数与调整前后倍率见逐场 CSV。',
        '**参考**：ARAMKit 全分段 173 名英雄的同版本页面冻结于 '+REF['fetched_at_utc']+'；站点未统一展示总样本量。第三方“自我减免”和桌面端“自我减伤”作同义映射，**跨站承伤口径待核实**。',
        f'**样本**：{len([x for x in G if x["day_folder"]==day])} 场，名单队员 {len(subset)} 条单局记录；个人记录完整评分率 100%。04:00 开局归属以所给截图目录为准，未显示钟点的截图不补造精确时间。',
        '', f'**比较范围**：{"本日参评者参与完全相同的比赛，可作同场比较。" if same_matches else "参评者的比赛集合不同，下列序号只表示个人日分大小，不代表同条件实力名次；请连同参赛场数阅读。"}',
        '', '| '+('同场名次' if same_matches else '日分序位')+' | 队员 | 日分 | 场数 | '+('九方案名次范围 | ' if same_matches else '')+'输出分 | 承伤分 | 参团分 | 死亡分 | 占比：输出 / 真实承伤 |',
        '| ---: | --- | ---: | ---: | '+('---: | ' if same_matches else '')+'---: | ---: | ---: | ---: | ---: |']
 for v in totals:
  lines.append(f"| {v['名次']} | {v['玩家']} | {v['日分']:.1f} | {v['场数']} | {str(v['九方案名次范围'])+' | ' if same_matches else ''}{v['平均输出分']:.1f} | {v['平均承伤分']:.1f} | {v['平均参团分']:.1f} | {v['平均死亡分']:.1f} | {v['团队输出占比%']:.1f}% / {v['团队真实承伤占比%']:.1f}% |")
 if day=='2026-09-27':
  shared=[r for r in subset if r['场次'] in ('M10','M11')]
  assert len(shared)==10 and len({r['玩家'] for r in shared})==5
  lines+=['','## Let325544 参加的两场：相同比赛对比','',
          '这两场五位名单队员共同参加，下面的均分只代表 M10、M11，不是全天排名。',
          '', '| 队员 | M10 | M11 | 两场均分 |','| --- | ---: | ---: | ---: |']
  common=[]
  for name in {r['玩家'] for r in shared}:
   s=sorted((r for r in shared if r['玩家']==name),key=lambda x:x['场次'])
   common.append((name,s[0]['单局综合分'],s[1]['单局综合分']))
  for name,a,c in sorted(common,key=lambda x:-(x[1]+x[2])):
   lines.append(f'| {name} | {a:.1f} | {c:.1f} | {(a+c)/2:.1f} |')
 lines+=['','**阅读方式**：输出／承伤的调整后倍率或参团倍率等于 1 时，发挥分为 50，不是及格线；本场占比 20% 是数学参照，不是输出或承伤的英雄门槛。日分是每位队员当天参与的所有合格单局的等权平均；参赛场次不一致时分数序位不代表同条件实力名次。九方案名次范围只在同场比较时展示，不是统计置信区间。',
         '','**核对方法**：打开 [逐场评分明细](逐场评分明细_v2.1.csv) 查看英雄、五人中位数环境系数、调整前后倍率、原始显示值、占比、时长、击杀和九组参数分数。单局 `S＝0.70×(wO×O＋wT×T)＋0.20×参团分＋0.10×死亡分`。英雄参考见 [冻结快照](../../../references/aramkit_v16.19_全分段_2026-09-28.json)，定义见[评分标准](../../../docs/海斗日评与月评评分标准.md)。','',
         '## 逐场截图','', '| 场次 | 己方名单人数 | 时长 | 参评人数 | 截图 |','| --- | ---: | ---: | ---: | --- |']
 for g in [v for v in G if v['day_folder']==day]:
  path=Path(g['file']).name;lines.append(f"| M{g['match']:02d} | {sum(a['player']!='非六人名单' for a in g['rows'])} | {g['duration']} | {sum(a['player']!='非六人名单' for a in g['rows'])} | [查看](../../../screenshots/{day}/{path}) |")
 lines+=['','分均输出和分均真实承伤均以截图保留的“万／k”精度计算；占比使用截图显示的整数百分比，所以五人的占比之和可能为 99%—101%。未根据这些取整值倒推精确总量。',
         '','英雄参考是 2026-09-28 取得的同版本公开聚合页面，并非比赛当时冻结的网页快照；网站没有提供逐场分布与所有字段的完整口径。日分只适合作为这套公开公式下的复盘参考。','']
 (directory/'README.md').write_text('\n'.join(lines),encoding='utf-8')
 print(day,' '.join(f"{v['玩家'].split('#')[0]}:{v['日分']:.2f}/{v['场数']}" for v in totals),flush=True)
# Preserve exact source evidence and reproducibility; screenshot hashes already in screenshot READMEs.
refdir=BASE/'references';refdir.mkdir(exist_ok=True)
(refdir/'aramkit_v16.19_全分段_2026-09-28.json').write_text(json.dumps(REF,ensure_ascii=False,indent=2),encoding='utf-8')
(refdir/'英雄基准_中位数.json').write_text(json.dumps({'英雄数':len(R),'参考输出分均中位数':MO,'参考真实承伤分均中位数':MT,'英雄列表':sorted(R)},ensure_ascii=False,indent=2),encoding='utf-8')
print('MO/MT',MO,MT,'rows',len(rows))
# Produce role-aware, ranked reading cards from the just-written detail CSVs.
subprocess.run([sys.executable, str(P/'build_summary_cards.py')], check=True)
