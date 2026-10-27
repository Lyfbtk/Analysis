# -*- coding: utf-8 -*-
"""
生成单文件交互看板：经营总览 + 月度趋势
数据源：metrics/out/*.csv
输出：dashboard/经营总览.html（自包含，无外部依赖）
"""
import json
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
DASH = os.path.join(HERE, 'dashboard')
os.makedirs(DASH, exist_ok=True)

# ---------- 数据准备 ----------
mt = pd.read_csv(f'{OUT}/指标总表.csv')
kpi_raw = dict(zip(mt['指标'], mt['显示值']))

m = pd.read_csv(f'{OUT}/月度经营表.csv').sort_values('month')
pay = pd.read_csv(f'{OUT}/支付结构.csv')
inst = pd.read_csv(f'{OUT}/分期期数分布.csv')
sellers = pd.read_csv(f'{OUT}/卖家Top50.csv')
coh = pd.read_csv(f'{OUT}/cohort_留存矩阵.csv', index_col=0)
coh.columns = [int(c) for c in coh.columns]

# 月表转百分数
monthly = []
for _, r in m.iterrows():
    monthly.append({
        'month': r['month'],
        'gmv': round(r['gmv_all'] / 1e4, 1),          # 万 BRL
        'orders': int(r['orders']),
        'aov': round(r['aov'], 1),
        'attach': round(r['attach'], 3),
        'freight': round(r['freight_rate'] * 100, 2),
        'cancel': round(r['cancel_rate'] * 100, 2),
        'inst': round(r['installment_rate'] * 100, 1),
        'customers': int(r['customers']),
        'new_c': int(r['new_customers']),
        'rep_c': int(r['repeat_customers']),
        'score': round(r['avg_score'], 3),
    })

# 分期分桶
def bucket(x):
    if x <= 1: return '1 期'
    if x <= 10: return f'{int(x)} 期'
    if x <= 12: return '11-12 期'
    return '13 期以上'
inst['bucket'] = inst['inst_max'].apply(bucket)
order_b = ['1 期', '2 期', '3 期', '4 期', '5 期', '6 期', '7 期', '8 期', '9 期', '10 期', '11-12 期', '13 期以上']
inst_b = inst.groupby('bucket')['share'].sum().reindex(order_b).fillna(0)
inst_data = [{'k': k, 'v': round(float(v) * 100, 2)} for k, v in inst_b.items()]

# cohort 矩阵（转百分数，保留两位）
cohort_rows, cohort_cols = [], []
if len(coh):
    cohort_cols = [int(c) for c in coh.columns]
    for idx, row in coh.iterrows():
        cohort_rows.append({'cohort': str(idx),
                            'v': [None if pd.isna(x) else round(float(x) * 100, 3) for x in row.values]})

# 卖家累计份额
sellers = sellers.sort_values('revenue', ascending=False).reset_index(drop=True)
cum = (sellers['revenue'].cumsum() / sellers['revenue'].sum() * 100).round(2).tolist()

DATA = {
    'kpiLabels': {
        'GMV': kpi_raw.get('GMV（含运费）', ''),
        'orders': kpi_raw.get('有效订单数', ''),
        'aov': kpi_raw.get('客单价 AOV', ''),
        'unit': kpi_raw.get('件单价', ''),
        'attach': kpi_raw.get('连带率', ''),
        'freight': kpi_raw.get('运费率（占商品额）', ''),
        'inst': kpi_raw.get('分期渗透率', ''),
        'repeat': kpi_raw.get('复购率', ''),
        'hhi': kpi_raw.get('卖家 HHI', ''),
        'score': kpi_raw.get('平均评分', ''),
        'cancel': kpi_raw.get('取消率', ''),
        'free': kpi_raw.get('免运费订单占比', ''),
        'top10': kpi_raw.get('Top10 卖家份额', ''),
        'cust': kpi_raw.get('客户数', ''),
        'sellers': kpi_raw.get('卖家数', ''),
        'gap': kpi_raw.get('回购间隔（中位）', ''),
        'low': kpi_raw.get('1-2 星占比', ''),
        'gmv_goods': kpi_raw.get('GMV（商品额）', ''),
    },
    'monthly': monthly,
    'pay': [{'k': r['支付方式'], 'o': round(r['订单数占比'] * 100, 2), 'v': round(r['金额占比'] * 100, 2)}
            for _, r in pay.iterrows()],
    'inst': inst_data,
    'cohort': {'cols': cohort_cols, 'rows': cohort_rows},
    'sellers': {'cum': cum, 'n': len(cum)},
}

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Olist 经营总览 · 2017-01 ~ 2018-08</title>
<style>
  :root{
    --bg:#f5f6f8; --card:#fff; --ink:#1a1d21; --sub:#6b7280; --line:#e5e7eb;
    --blue:#2f6feb; --orange:#e8590c; --green:#2f9e44; --gray:#94a3b8; --purple:#7048e8;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
       font:14px/1.55 -apple-system,"Segoe UI","Microsoft YaHei",system-ui,sans-serif}
  .wrap{max-width:1180px;margin:0 auto;padding:28px 20px 60px}
  header{margin-bottom:22px}
  h1{font-size:22px;margin:0 0 6px;letter-spacing:-.2px}
  .sub{color:var(--sub);font-size:13px}
  h2{font-size:15px;margin:34px 0 12px;padding-left:9px;border-left:3px solid var(--blue);font-weight:600}
  .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px}
  .grid{display:grid;gap:12px}
  .kpi{grid-template-columns:repeat(5,1fr)}
  .kpi .card{padding:14px 16px}
  .kpi .lab{color:var(--sub);font-size:12px;margin-bottom:6px}
  .kpi .val{font-size:21px;font-weight:650;letter-spacing:-.3px;font-variant-numeric:tabular-nums}
  .kpi .note{color:var(--sub);font-size:11px;margin-top:4px}
  .two{grid-template-columns:1fr 1fr}
  .chartcard{position:relative}
  .ctitle{font-size:13px;font-weight:600;margin-bottom:2px}
  .cdesc{color:var(--sub);font-size:11.5px;margin-bottom:8px}
  .legend{display:flex;gap:14px;flex-wrap:wrap;font-size:11.5px;color:var(--sub);margin-bottom:6px}
  .legend i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px;vertical-align:1px}
  svg{display:block;width:100%;overflow:visible}
  .tip{position:absolute;pointer-events:none;background:#111827;color:#fff;font-size:11.5px;
       padding:6px 9px;border-radius:6px;opacity:0;transition:opacity .1s;white-space:nowrap;z-index:9}
  .findings li{margin:8px 0}
  .findings b{font-weight:650}
  table.coh{border-collapse:separate;border-spacing:2px;font-size:11px;width:100%}
  table.coh th{color:var(--sub);font-weight:500;font-size:10.5px;padding:2px 0}
  table.coh td{text-align:center;padding:5px 0;border-radius:3px;color:#fff;font-variant-numeric:tabular-nums}
  table.coh td.l{color:var(--sub);text-align:left;padding-left:4px;background:none!important}
  footer{margin-top:34px;color:var(--sub);font-size:11.5px;line-height:1.7}
  details.dict{margin-top:34px;background:var(--card);border:1px solid var(--line);border-radius:10px}
  details.dict summary{cursor:pointer;padding:14px 18px;font-size:13px;font-weight:600;list-style:none;user-select:none}
  details.dict summary::-webkit-details-marker{display:none}
  details.dict summary::before{content:"▸";display:inline-block;width:15px;color:var(--sub);transition:transform .15s}
  details.dict[open] summary::before{transform:rotate(90deg)}
  details.dict .dbody{padding:0 18px 16px}
  table.dict{width:100%;border-collapse:collapse;font-size:12px}
  table.dict th{text-align:left;color:var(--sub);font-weight:600;font-size:10.5px;padding:6px 8px;
                border-bottom:1px solid var(--line);background:#fafbfc;white-space:nowrap}
  table.dict td{padding:8px;border-bottom:1px solid #f1f3f5;vertical-align:top;line-height:1.6}
  table.dict td:nth-child(1){font-weight:600;white-space:nowrap}
  table.dict td:nth-child(2){color:#374151;font-family:ui-monospace,Consolas,monospace;font-size:11px;white-space:nowrap}
  table.dict td:nth-child(3),table.dict td:nth-child(4){color:#4b5563}
  table.dict tr:last-child td{border-bottom:none}
  table.dict tbody tr:hover td{background:#f8fafc}
  @media (max-width:900px){.kpi{grid-template-columns:repeat(2,1fr)}.two{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>Olist 电商经营总览</h1>
  <div class="sub">经营指标 · 2017-01 ~ 2018-08（20 个完整月，97,910 有效订单）· 口径见 <code>metrics/指标口径.md</code></div>
</header>

<h2>核心指标</h2>
<div class="grid kpi" id="kpi"></div>

<h2>月度趋势</h2>
<div class="grid two">
  <div class="card chartcard">
    <div class="ctitle">GMV 与订单量</div>
    <div class="cdesc">柱：GMV（万 BRL，左轴）· 线：有效订单数（右轴）</div>
    <div class="legend"><span><i style="background:#2f6feb"></i>GMV（万 BRL）</span><span><i style="background:#e8590c"></i>订单数</span></div>
    <div id="c1"></div><div class="tip" id="t1"></div>
  </div>
  <div class="card chartcard">
    <div class="ctitle">运费率上行，客单价原地不动</div>
    <div class="cdesc">运费率从 15.85% 升至 17.10%（年均），客单价稳定在 160 BRL 附近</div>
    <div class="legend"><span><i style="background:#e8590c"></i>运费率 %（左轴）</span><span><i style="background:#2f9e44"></i>客单价 BRL（右轴）</span></div>
    <div id="c2"></div><div class="tip" id="t2"></div>
  </div>
</div>
<div class="grid two" style="margin-top:12px">
  <div class="card chartcard">
    <div class="ctitle">新客 vs 复购客户</div>
    <div class="cdesc">柱：新客（左轴）· 线：复购客户（右轴）。2018 年新客占 97.63%，复购客户每月仅 150—190 人</div>
    <div class="legend"><span><i style="background:#2f6feb"></i>新客（左轴）</span><span><i style="background:#7048e8"></i>复购客户（右轴）</span></div>
    <div id="c3"></div><div class="tip" id="t3"></div>
  </div>
  <div class="card chartcard">
    <div class="ctitle">分期渗透率与平均评分</div>
    <div class="cdesc">过半订单分期成交；评分由 4.09 缓升至 4.29</div>
    <div class="legend"><span><i style="background:#7048e8"></i>分期渗透率 %（左轴）</span><span><i style="background:#2f9e44"></i>平均评分（右轴）</span></div>
    <div id="c4"></div><div class="tip" id="t4"></div>
  </div>
</div>

<h2>客户留存</h2>
<div class="card">
  <div class="ctitle">Cohort 留存矩阵（%）</div>
  <div class="cdesc">行＝首购月份，列＝首购后第 k 个月仍下单的比例。首列恒为 100%，其余列基本落在 0.2%—0.6%——留存曲线贴底，是拉新驱动型盘子的典型形态。</div>
  <div id="coh" style="overflow-x:auto;margin-top:8px"></div>
</div>

<h2>支付与卖家结构</h2>
<div class="grid two">
  <div class="card chartcard">
    <div class="ctitle">支付方式结构</div>
    <div class="cdesc">信用卡占订单 75.5%、金额 78.5%；boleto 是巴西特有的线下付款票据</div>
    <div id="c5"></div><div class="tip" id="t5"></div>
  </div>
  <div class="card chartcard">
    <div class="ctitle">分期期数分布</div>
    <div class="cdesc">1 期占 48.5%，2—10 期合计约 48%，12 期以上不足 0.4%</div>
    <div id="c6"></div><div class="tip" id="t6"></div>
  </div>
</div>
<div class="grid two" style="margin-top:12px">
  <div class="card chartcard">
    <div class="ctitle">卖家集中度：Top50 累计份额</div>
    <div class="cdesc">3,029 家卖家，Top10 仅占 13.2%，HHI=36（极度分散，对照：美国司法部 &lt;1500 即视为竞争性市场）</div>
    <div id="c7"></div><div class="tip" id="t7"></div>
  </div>
  <div class="card">
    <div class="ctitle">四条结论</div>
    <ul class="findings" style="margin:10px 0 0;padding-left:18px;line-height:1.75">
      <li><b>运费在吃毛利</b>：运费率年均 15.85% → 17.10%，同期客单价 161.6 → 160.6 BRL，几乎不动。</li>
      <li><b>一半订单靠分期成交</b>：分期渗透率 51.49%，信用卡平均 2.93 期，12 期以上仅 0.32%。</li>
      <li><b>这不是购物车型平台</b>：连带率 1.14，90.1% 订单只有一件商品，凑单/满减天花板很低。</li>
      <li><b>增长全靠拉新</b>：复购率 3.04%，新客占比 97.63%，次月留存中位 0.51%。</li>
    </ul>
  </div>
</div>

<details class="dict">
  <summary>指标字典 · 18 个指标怎么算、怎么读（点开）</summary>
  <div class="dbody">
    <table class="dict">
      <thead><tr><th>指标</th><th>公式</th><th>大白话</th><th>本值说明什么</th></tr></thead>
      <tbody>
        <tr><td>GMV（含运费）</td><td>Σ(price + freight)</td><td>成交总额，按商品价加运费加总；剔除取消与不可用单。不等于平台收入</td><td>含运费 1,568 万 BRL，纯商品额 1,345 万，差额 219 万即运费</td></tr>
        <tr><td>有效订单数</td><td>全部订单 − canceled − unavailable</td><td>真正成交的单。「不可用」指订单已生成但支付或库存出问题、平台无法处理</td><td>97,910 单，占全量 99.65%</td></tr>
        <tr><td>客单价 AOV</td><td>GMV(含运费) ÷ 有效订单数</td><td>平均每单花多少钱。本身无好坏，须拆开看构成</td><td>160.18 = 商品 137.37 + 运费 22.82</td></tr>
        <tr><td>件单价</td><td>商品额 ÷ 件数</td><td>每件商品卖多少钱，不含运费</td><td>120.35 BRL/件。与客单价同时看，才能分清「涨价」还是「多买」</td></tr>
        <tr><td>连带率</td><td>件数 ÷ 有效订单数</td><td>一单平均买几件</td><td>1.14 件。90.1% 订单仅 1 件 → 凑单/满减/关联推荐的天花板极低</td></tr>
        <tr><td>取消率</td><td>canceled ÷ 全部订单</td><td>有多少单被取消</td><td>0.58%，量级太小，月度波动全为噪声，不宜作主指标</td></tr>
        <tr><td>运费率</td><td>Σ运费 ÷ Σ商品额</td><td>每卖 100 元商品，收多少运费。运费直接抵减毛利</td><td>16.61%；2017 年均 15.85% → 2018 年均 17.10%，同期客单价几乎不动</td></tr>
        <tr><td>免运费订单占比</td><td>运费合计=0 的订单 ÷ 有效订单</td><td>有多少单是包邮的</td><td>0.35%，几乎全平台收运费 → 包邮属结构性变革，非运营可选动作</td></tr>
        <tr><td>分期渗透率</td><td>订单级最大期数&gt;1 ÷ 有支付记录订单</td><td>有多少单是分期付的</td><td>51.49%。巴西信用卡分期是消费习惯而非促销；提客单价应看月供承受力</td></tr>
        <tr><td>分期期数均值</td><td>订单级最大期数均值</td><td>分期的人平均分几期</td><td>2.93 期；12 期以上仅 0.32%，不属长期负债消费</td></tr>
        <tr><td>信用卡金额占比</td><td>credit_card 金额 ÷ 总支付金额</td><td>钱有多少比例走信用卡</td><td>金额 78.46% vs 订单 75.47% → 信用卡用户单笔更大</td></tr>
        <tr><td>客户数</td><td>customer_unique_id 去重</td><td>真实的人数。注意 customer_id 是订单级唯一，不是人</td><td>94,707 人</td></tr>
        <tr><td>复购率</td><td>下单≥2 次客户 ÷ 全部客户</td><td>100 个客户里有几个买了第二次</td><td>3.04%。平台型电商常态（用户认商品不认平台），是结论不是错误</td></tr>
        <tr><td>回购间隔（中位）</td><td>复购客户相邻两单间隔，剔除同日拆单</td><td>多久回来买第二次</td><td>71 天（P25–P75 = 23–170 天），30 天内复购仅 29.7%。含同日拆单会假到 34 天／48.9%——同日拆单是同一笔消费拆两单，不是复购。周期这么散，设统一召回窗口没有依据</td></tr>
        <tr><td>新客占比</td><td>当月首购客户 ÷ 当月活跃客户</td><td>这个月下单的人里有多少是第一次买</td><td>2018 年 97.63%，与复购率 3.04% 是同一事实的两面</td></tr>
        <tr><td>Cohort 次月留存</td><td>首购次月仍下单 ÷ 该 cohort 人数</td><td>100 个新客，下个月回来几个。按月活算会严重高估，必须按同期群</td><td>中位 0.51%，留存曲线贴底</td></tr>
        <tr><td>卖家 HHI</td><td>Σ(份额²) × 10000</td><td>集中度指数：1 家垄断=10000，万分之一万家≈1。美司法部口径 &lt;1500 为竞争性市场</td><td>36，极度分散；Top10 仅 13.24%，与亚马逊头部主导相反</td></tr>
        <tr><td>平均评分 / 1-2 星率</td><td>mean(review_score)；评分≤2 ÷ 有评分订单</td><td>口碑基线，供各品类横向对照。评分仅 1–5 星，需自定义「1-2 星=差评」</td><td>4.118 / 13.80%</td></tr>
      </tbody>
    </table>
  </div>
</details>

<footer>
  数据来源：Kaggle Brazilian E-Commerce Public Dataset by Olist（9 表，99,441 订单）。<br>
  口径：GMV 含运费；有效订单剔除 canceled / unavailable；客户去重使用 customer_unique_id；分期按订单级最大期数；支付方式按订单金额最大行判定。<br>
  生成脚本：<code>metrics/build_dashboard.py</code>·指标口径：<code>metrics/指标口径.md</code>
</footer>
</div>

<script>
const D = __DATA__;

/* ---------- 通用工具 ---------- */
const fmt = (n, d=0) => n.toLocaleString('zh-CN', {minimumFractionDigits:d, maximumFractionDigits:d});
const NS = 'http://www.w3.org/2000/svg';
function el(tag, attrs={}, parent){
  const e = document.createElementNS(NS, tag);
  for(const k in attrs) e.setAttribute(k, attrs[k]);
  if(parent) parent.appendChild(e);
  return e;
}
function niceTicks(min, max, n=4){
  if(max===min){ max = min + 1; }
  const span = max - min, step0 = span / n;
  const mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const norm = step0 / mag;
  const step = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 2.5 ? 2.5 : norm <= 5 ? 5 : 10) * mag;
  const lo = Math.floor(min / step) * step, hi = Math.ceil(max / step) * step;
  const t = [];
  for(let v = lo; v <= hi + step*1e-9; v += step) t.push(+v.toFixed(6));
  return t;
}
function baseSvg(host, h){
  const W = host.clientWidth || 520, H = h || 260;
  const svg = el('svg', {viewBox:`0 0 ${W} ${H}`, height:H}, host);
  return {svg, W, H};
}
function axisSVG(svg, W, H, m, ticksL, ticksR, xLabels, maxTick){
  // gridlines + left axis + right axis + x labels
  const ih = H - m.t - m.b, iw = W - m.l - m.r;
  const lmin = ticksL[0], lmax = ticksL[ticksL.length-1];
  const decOf = (mx) => (Math.abs(mx) < 10 ? 2 : 0);
  const dL = decOf(lmax);
  ticksL.forEach(v => {
    const y = m.t + ih - (v - lmin) / (lmax - lmin) * ih;
    el('line', {x1:m.l, y1:y, x2:m.l+iw, y2:y, stroke:'#eef0f3', 'stroke-width':1}, svg);
    el('text', {x:m.l-8, y:y+4, 'text-anchor':'end', 'font-size':10.5, fill:'#94a3b8'}, svg).textContent = fmt(v, dL);
  });
  if(ticksR){
    const rmin = ticksR[0], rmax = ticksR[ticksR.length-1];
    const dR = decOf(rmax);
    ticksR.forEach(v => {
      const y = m.t + ih - (v - rmin) / (rmax - rmin) * ih;
      el('text', {x:m.l+iw+8, y:y+4, 'text-anchor':'start', 'font-size':10.5, fill:'#94a3b8'}, svg).textContent = fmt(v, dR);
    });
  }
  const step = Math.ceil(xLabels.length / maxTick);
  xLabels.forEach((lb, i) => {
    if(i % step) return;
    const x = m.l + (xLabels.length === 1 ? iw/2 : i * iw / (xLabels.length - 1));
    el('text', {x:x, y:H-m.b+16, 'text-anchor':'middle', 'font-size':10, fill:'#94a3b8'}, svg).textContent = lb;
  });
  return {ih, iw, lmin, lmax, rmin: ticksR?ticksR[0]:0, rmax: ticksR?ticksR[ticksR.length-1]:1};
}

/* ---------- 图 1：柱 + 右轴线 ---------- */
function barLine(hostId, tipId, labels, barData, lineData, cBar, cLine, unitBar, unitLine){
  const host = document.getElementById(hostId), tipp = document.getElementById(tipId);
  host.innerHTML = '';
  const {svg, W, H} = baseSvg(host, 250);
  const m = {t:14, r:46, b:26, l:46};
  const {ih, iw} = {ih:H-m.t-m.b, iw:W-m.l-m.r};
  const tL = niceTicks(0, Math.max(...barData), 4);
  const tR = niceTicks(0, Math.max(...lineData), 4);
  const ax = axisSVG(svg, W, H, m, tL, tR, labels, 7);
  const bw = iw / labels.length * 0.62;
  barData.forEach((v, i) => {
    const x = m.l + i * iw / labels.length + (iw/labels.length - bw)/2;
    const y = m.t + ih - (v - ax.lmin)/(ax.lmax-ax.lmin)*ih;
    el('rect', {x, y, width:bw, height:Math.max(1, m.t+ih-y), fill:cBar, opacity:.88, rx:2}, svg);
  });
  const pts = lineData.map((v, i) => {
    const x = m.l + i * iw / labels.length + iw/labels.length/2;
    const y = m.t + ih - (v - ax.rmin)/(ax.rmax-ax.rmin)*ih;
    return [x, y];
  });
  el('path', {d:pts.map((p,i)=> (i?'L':'M')+p[0]+','+p[1]).join(' '), fill:'none', stroke:cLine, 'stroke-width':2}, svg);
  pts.forEach(p => el('circle', {cx:p[0], cy:p[1], r:2.6, fill:'#fff', stroke:cLine, 'stroke-width':2}, svg));

  const hit = el('rect', {x:m.l, y:m.t, width:iw, height:ih, fill:'transparent'}, svg);
  hit.addEventListener('mousemove', ev => {
    const bb = svg.getBoundingClientRect();
    const px = (ev.clientX - bb.left) * (W / bb.width);
    let i = Math.round((px - m.l) / iw * labels.length - 0.5);
    i = Math.max(0, Math.min(labels.length-1, i));
    tipp.style.opacity = 1;
    tipp.style.left = Math.min(bb.width-150, Math.max(0, pts[i][0] * bb.width / W - 60)) + 'px';
    tipp.style.top = '18px';
    tipp.innerHTML = labels[i] + '<br>' + unitBar + ' ' + fmt(barData[i],1) + '　' + unitLine + ' ' + fmt(lineData[i],0);
  });
  hit.addEventListener('mouseleave', () => tipp.style.opacity = 0);
}

/* ---------- 图 2/4：双轴线（无柱） ---------- */
function dualLine(hostId, tipId, labels, s1, s2, c1, c2, u1, u2, d1, d2){
  const host = document.getElementById(hostId), tipp = document.getElementById(tipId);
  host.innerHTML = '';
  const {svg, W, H} = baseSvg(host, 250);
  const m = {t:14, r:46, b:26, l:46};
  const ih = H-m.t-m.b, iw = W-m.l-m.r;
  const pad = (a) => { const mn = Math.min(...a), mx = Math.max(...a), p = (mx-mn)*0.18 || 1; return [mn-p, mx+p]; };
  const [a1,b1] = pad(s1), [a2,b2] = pad(s2);
  const tL = niceTicks(a1, b1, 4), tR = niceTicks(a2, b2, 4);
  const ax = axisSVG(svg, W, H, m, tL, tR, labels, 7);
  function draw(vals, c, rmin, rmax, dash){
    const pts = vals.map((v,i) => {
      const x = m.l + i*iw/(labels.length-1);
      const y = m.t + ih - (v-rmin)/(rmax-rmin)*ih;
      return [x,y];
    });
    el('path', {d:pts.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+','+p[1].toFixed(1)).join(' '),
      fill:'none', stroke:c, 'stroke-width':2, 'stroke-dasharray': dash||'none'}, svg);
    pts.forEach(p => el('circle', {cx:p[0], cy:p[1], r:2.4, fill:'#fff', stroke:c, 'stroke-width':1.8}, svg));
    return pts;
  }
  const p1 = draw(s1, c1, ax.lmin, ax.lmax);
  const p2 = draw(s2, c2, ax.rmin, ax.rmax, '4 3');
  const hit = el('rect', {x:m.l, y:m.t, width:iw, height:ih, fill:'transparent'}, svg);
  hit.addEventListener('mousemove', ev => {
    const bb = svg.getBoundingClientRect();
    const px = (ev.clientX - bb.left) * (W / bb.width);
    let i = Math.round((px - m.l) / iw * (labels.length-1));
    i = Math.max(0, Math.min(labels.length-1, i));
    tipp.style.opacity = 1;
    tipp.style.left = Math.min(bb.width-160, Math.max(0, p1[i][0]*bb.width/W - 60)) + 'px';
    tipp.style.top = '18px';
    tipp.innerHTML = labels[i] + '<br>' + u1 + ' ' + fmt(s1[i], d1) + '　' + u2 + ' ' + fmt(s2[i], d2);
  });
  hit.addEventListener('mouseleave', () => tipp.style.opacity = 0);
}

/* ---------- 图 3：堆叠柱 ---------- */
function stacked(hostId, tipId, labels, a, b, ca, cb, na, nb){
  const host = document.getElementById(hostId), tipp = document.getElementById(tipId);
  host.innerHTML = '';
  const {svg, W, H} = baseSvg(host, 250);
  const m = {t:14, r:14, b:26, l:46};
  const ih = H-m.t-m.b, iw = W-m.l-m.r;
  const totals = a.map((v,i)=>v+b[i]);
  const tL = niceTicks(0, Math.max(...totals), 4);
  axisSVG(svg, W, H, m, tL, null, labels, 7);
  const bw = iw/labels.length*0.66;
  a.forEach((v,i)=>{
    const x = m.l + i*iw/labels.length + (iw/labels.length - bw)/2;
    const hA = v/tL[tL.length-1]*ih, hB = b[i]/tL[tL.length-1]*ih;
    const yB = m.t+ih-hA;
    el('rect', {x, y:yB, width:bw, height:Math.max(0,hB), fill:cb, rx:2}, svg);
    el('rect', {x, y:yB-hB, width:bw, height:Math.max(0.5,hA), fill:ca, rx:2}, svg);
  });
  const hit = el('rect', {x:m.l, y:m.t, width:iw, height:ih, fill:'transparent'}, svg);
  hit.addEventListener('mousemove', ev => {
    const bb = svg.getBoundingClientRect();
    const px = (ev.clientX-bb.left)*(W/bb.width);
    let i = Math.max(0, Math.min(labels.length-1, Math.round((px-m.l)/iw*labels.length-0.5)));
    tipp.style.opacity = 1;
    tipp.style.left = Math.min(bb.width-170, Math.max(0, (m.l + i*iw/labels.length)*bb.width/W)) + 'px';
    tipp.style.top = '18px';
    tipp.innerHTML = labels[i] + '<br>' + na + ' ' + fmt(a[i]) + '　' + nb + ' ' + fmt(b[i]);
  });
  hit.addEventListener('mouseleave', () => tipp.style.opacity = 0);
}

/* ---------- 图 5：横向分组条 ---------- */
function hbars(hostId, tipId, items){
  const host = document.getElementById(hostId), tipp = document.getElementById(tipId);
  host.innerHTML = '';
  const {svg, W, H} = baseSvg(host, 210);
  const m = {t:10, r:40, b:18, l:78};
  const ih = H-m.t-m.b, iw = W-m.l-m.r;
  const rowH = ih/items.length;
  const maxV = Math.max(...items.map(d=>Math.max(d.o,d.v)));
  items.forEach((d,i)=>{
    const y = m.t + i*rowH + rowH*0.16;
    const h = rowH*0.28;
    el('text', {x:m.l-8, y:y+h+1, 'text-anchor':'end', 'font-size':10.5, fill:'#4b5563'}, svg).textContent = d.k;
    el('rect', {x:m.l, y, width:Math.max(1, d.o/maxV*iw), height:h, fill:'#2f6feb', rx:2}, svg);
    el('rect', {x:m.l, y:y+h+3, width:Math.max(1, d.v/maxV*iw), height:h, fill:'#a5b4fc', rx:2}, svg);
    el('text', {x:m.l + Math.max(d.o,d.v)/maxV*iw + 6, y:y+h+1, 'font-size':10, fill:'#6b7280'}, svg)
      .textContent = d.o.toFixed(1)+'% / '+d.v.toFixed(1)+'%';
  });
  const hit = el('rect', {x:m.l, y:m.t, width:iw, height:ih, fill:'transparent'}, svg);
  hit.addEventListener('mousemove', ev=>{
    const bb = svg.getBoundingClientRect();
    const py = (ev.clientY-bb.top)*(H/bb.height);
    let i = Math.floor((py-m.t)/rowH); i = Math.max(0, Math.min(items.length-1,i));
    tipp.style.opacity = 1; tipp.style.left = '10px'; tipp.style.top = (py*bb.height/H - 8)+'px';
    tipp.innerHTML = items[i].k + '<br>订单占比 ' + items[i].o.toFixed(2) + '%　金额占比 ' + items[i].v.toFixed(2) + '%';
  });
  hit.addEventListener('mouseleave', ()=> tipp.style.opacity = 0);
}

/* ---------- 图 6：竖条 ---------- */
function vbars(hostId, tipId, items){
  const host = document.getElementById(hostId), tipp = document.getElementById(tipId);
  host.innerHTML = '';
  const {svg, W, H} = baseSvg(host, 210);
  const m = {t:12, r:12, b:34, l:42};
  const ih = H-m.t-m.b, iw = W-m.l-m.r;
  const mx = Math.max(...items.map(d=>d.v));
  const tL = niceTicks(0, mx, 3);
  axisSVG(svg, W, H, m, tL, null, [], 1);
  const bw = iw/items.length*0.6;
  items.forEach((d,i)=>{
    const x = m.l + i*iw/items.length + (iw/items.length-bw)/2;
    const h = d.v/tL[tL.length-1]*ih;
    el('rect', {x, y:m.t+ih-h, width:bw, height:Math.max(1,h), fill:'#7048e8', opacity:.85, rx:2}, svg);
    if(items.length<=12 || i%2===0)
      el('text', {x:x+bw/2, y:H-m.b+14, 'text-anchor':'middle', 'font-size':9.5, fill:'#94a3b8'}, svg).textContent = d.k.replace(' 期','');
  });
  const hit = el('rect', {x:m.l, y:m.t, width:iw, height:ih, fill:'transparent'}, svg);
  hit.addEventListener('mousemove', ev=>{
    const bb = svg.getBoundingClientRect();
    const px = (ev.clientX-bb.left)*(W/bb.width);
    let i = Math.max(0, Math.min(items.length-1, Math.floor((px-m.l)/iw*items.length)));
    tipp.style.opacity = 1; tipp.style.left = Math.min(bb.width-120,(px*bb.width/W)-20)+'px'; tipp.style.top='14px';
    tipp.innerHTML = items[i].k + '：' + items[i].v.toFixed(2) + '%';
  });
  hit.addEventListener('mouseleave', ()=> tipp.style.opacity = 0);
}

/* ---------- 图 7：累计曲线 ---------- */
function cumLine(hostId, tipId, vals){
  const host = document.getElementById(hostId), tipp = document.getElementById(tipId);
  host.innerHTML = '';
  const {svg, W, H} = baseSvg(host, 210);
  const m = {t:12, r:16, b:30, l:42};
  const ih = H-m.t-m.b, iw = W-m.l-m.r;
  const tL = niceTicks(0, 100, 4);
  axisSVG(svg, W, H, m, tL, null, ['1','10','20','30','40','50'], 6);
  const pts = vals.map((v,i)=>[m.l + i*iw/(vals.length-1), m.t + ih - v/100*ih]);
  el('path', {d:pts.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+','+p[1].toFixed(1)).join(' '),
              fill:'none', stroke:'#2f9e44', 'stroke-width':2}, svg);
  el('path', {d:`M${m.l},${m.t+ih} ` + pts.map(p=>'L'+p[0].toFixed(1)+','+p[1].toFixed(1)).join(' ')
              + ` L${m.l+iw},${m.t+ih} Z`, fill:'#2f9e44', opacity:.08}, svg);
  const hit = el('rect', {x:m.l, y:m.t, width:iw, height:ih, fill:'transparent'}, svg);
  hit.addEventListener('mousemove', ev=>{
    const bb = svg.getBoundingClientRect();
    const px = (ev.clientX-bb.left)*(W/bb.width);
    let i = Math.max(0, Math.min(vals.length-1, Math.round((px-m.l)/iw*(vals.length-1))));
    tipp.style.opacity=1; tipp.style.left=Math.min(bb.width-150,Math.max(0,pts[i][0]*bb.width/W-40))+'px'; tipp.style.top='14px';
    tipp.innerHTML = 'Top ' + (i+1) + ' 卖家累计占 ' + vals[i].toFixed(1) + '%';
  });
  hit.addEventListener('mouseleave', ()=> tipp.style.opacity = 0);
}

/* ---------- KPI 卡 ---------- */
const K = D.kpiLabels;
const cards = [
  ['GMV（含运费）', K.GMV, '商品额 ' + K.gmv_goods],
  ['有效订单数', K.orders, '20 个完整月'],
  ['客单价 AOV', K.aov, '件单价 ' + K.unit],
  ['连带率', K.attach, '90.1% 订单仅 1 件'],
  ['运费率', K.freight, '免运费仅 ' + K.free],
  ['分期渗透率', K.inst, '信用卡平均 2.93 期'],
  ['复购率', K.repeat, '回购间隔 ' + K.gap],
  ['客户数', K.cust, '2018 新客占 97.6%'],
  ['卖家 HHI', K.hhi, 'Top10 仅 ' + K.top10],
  ['平均评分', K.score, '1-2 星 ' + K.low],
];
document.getElementById('kpi').innerHTML = cards.map(c =>
  `<div class="card"><div class="lab">${c[0]}</div><div class="val">${c[1]}</div><div class="note">${c[2]}</div></div>`
).join('');

/* ---------- 渲染 ---------- */
const labels = D.monthly.map(d => d.month.slice(2));
barLine('c1','t1', labels, D.monthly.map(d=>d.gmv), D.monthly.map(d=>d.orders), '#2f6feb', '#e8590c', 'GMV(万)', '订单');
dualLine('c2','t2', labels, D.monthly.map(d=>d.freight), D.monthly.map(d=>d.aov), '#e8590c', '#2f9e44', '运费率', '客单价', 1, 0);
barLine('c3','t3', labels, D.monthly.map(d=>d.new_c), D.monthly.map(d=>d.rep_c), '#2f6feb', '#7048e8', '新客', '复购');
dualLine('c4','t4', labels, D.monthly.map(d=>d.inst), D.monthly.map(d=>d.score), '#7048e8', '#2f9e44', '分期%', '评分', 1, 2);
hbars('c5','t5', D.pay);
vbars('c6','t6', D.inst);
cumLine('c7','t7', D.sellers.cum);

/* ---------- cohort 热力图 ---------- */
(function(){
  const C = D.cohort, box = document.getElementById('coh');
  if(!C.rows.length){ box.textContent = '无数据'; return; }
  let mx = 0.6;
  C.rows.forEach(r => r.v.forEach((v,i) => { if(i>0 && v!=null && v>mx) mx = v; }));
  const color = v => {
    const t = Math.min(1, Math.max(0, v/mx));
    const a = 0.10 + t*0.86;
    return `rgba(47,111,235,${a.toFixed(3)})`;
  };
  let html = '<table class="coh"><thead><tr><th style="text-align:left;padding-left:4px">首购月</th>';
  C.cols.forEach(c => html += `<th>M+${c}</th>`);
  html += '</tr></thead><tbody>';
  C.rows.forEach(r => {
    html += `<tr><td class="l">${r.cohort}</td>`;
    r.v.forEach((v,i) => {
      if(v==null){ html += '<td style="background:#f8fafc"></td>'; return; }
      if(i===0){ html += '<td style="background:#fff;color:#1a1d21;font-weight:600">100</td>'; return; }
      const txt = v < 1 ? v.toFixed(2) : v.toFixed(1);
      html += `<td style="background:${color(v)}" title="${r.cohort} M+${i}: ${v}%">${txt}</td>`;
    });
    html += '</tr>';
  });
  html += '</tbody></table>';
  box.innerHTML = html;
})();

/* ---------- 自适应重绘 ---------- */
let rt;
window.addEventListener('resize', () => {
  clearTimeout(rt);
  rt = setTimeout(() => {
    barLine('c1','t1', labels, D.monthly.map(d=>d.gmv), D.monthly.map(d=>d.orders), '#2f6feb', '#e8590c', 'GMV(万)', '订单');
    dualLine('c2','t2', labels, D.monthly.map(d=>d.freight), D.monthly.map(d=>d.aov), '#e8590c', '#2f9e44', '运费率', '客单价', 1, 0);
    barLine('c3','t3', labels, D.monthly.map(d=>d.new_c), D.monthly.map(d=>d.rep_c), '#2f6feb', '#7048e8', '新客', '复购');
    dualLine('c4','t4', labels, D.monthly.map(d=>d.inst), D.monthly.map(d=>d.score), '#7048e8', '#2f9e44', '分期%', '评分', 1, 2);
    hbars('c5','t5', D.pay); vbars('c6','t6', D.inst); cumLine('c7','t7', D.sellers.cum);
  }, 160);
});
</script>
</body>
</html>
"""

html = HTML.replace('__DATA__', json.dumps(DATA, ensure_ascii=False))
path = os.path.join(DASH, '经营总览.html')
with open(path, 'w', encoding='utf-8') as f:
    f.write(html)
print('已生成:', path)
print('大小: %.1f KB' % (os.path.getsize(path) / 1024))
print('月份数:', len(monthly), '| cohort:', len(cohort_rows), '| 卖家点:', len(cum))
