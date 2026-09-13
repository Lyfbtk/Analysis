import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150

NAVY = "#1F4E79"; ORANGE = "#E67E22"; SKY = "#5DADE2"; GRAY = "#7F8C8D"; LGRAY = "#BDC3C7"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
FIG_DIR = os.path.join(SCRIPT_DIR, "图表")
os.makedirs(FIG_DIR, exist_ok=True)

STATE = {"SP": "圣保罗", "RJ": "里约", "MG": "米纳斯", "RS": "南大河", "PR": "巴拉那",
         "SC": "圣卡塔", "BA": "巴伊亚", "DF": "联邦区", "GO": "戈亚斯", "ES": "圣灵",
         "PE": "伯南", "CE": "塞阿拉", "PA": "帕拉", "MT": "马托", "MS": "南马托",
         "MA": "马拉尼昂", "PB": "帕拉伊巴", "PI": "皮奥伊", "RN": "北里奥", "AL": "阿拉戈",
         "SE": "塞尔希培", "TO": "托坎", "RO": "朗多", "AM": "亚马孙", "AC": "阿克里", "AP": "阿马帕", "RR": "罗赖马"}

CN = {"cama_mesa_banho": "床品家纺", "beleza_saude": "美妆健康", "esporte_lazer": "运动休闲",
      "moveis_decoracao": "家具装饰", "informatica_acessorios": "电脑配件", "utilidades_domesticas": "日用",
      "relogios_presentes": "钟表礼品", "telefonia": "手机通讯", "ferramentas_jardim": "工具园艺",
      "automotivo": "汽车用品", "brinquedos": "玩具", "cool_stuff": "酷玩", "perfumaria": "香氛",
      "bebes": "婴童", "eletronicos": "电子", "未分类": "未分类", "papelaria": "文具",
      "moveis_escritorio": "办公家具", "fashion_bolsas_e_acessorios": "箱包配件",
      "pet_shop": "宠物用品", "consoles_games": "游戏机", "malas_acessorios": "行李箱"}

# 交互看板模板（单文件 HTML：无外部依赖、离线可用；占位符 __DATA__ 等在生成时替换）
DASHBOARD_TPL = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>品类 × 履约联合：差评里有多少来自配送</title>
<style>
  :root{--navy:#1F4E79;--orange:#E67E22;--sky:#5DADE2;--gray:#7F8C8D;--lgray:#BDC3C7;}
  *{box-sizing:border-box}
  body{margin:0;padding:28px 20px 40px;background:#FBFCFC;color:#222;
       font-family:"Microsoft YaHei","PingFang SC","Helvetica Neue",Arial,sans-serif}
  .wrap{max-width:1180px;margin:0 auto}
  h1{font-size:24px;color:var(--navy);margin:0 0 6px}
  .sub{color:var(--gray);font-size:13px;margin:0 0 18px}
  .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:16px}
  .kpi{background:#fff;border:1px solid #E5EAEA;border-radius:10px;padding:12px 14px}
  .kpi b{display:block;font-size:13px;color:var(--gray);font-weight:400;margin-bottom:6px}
  .kpi span{font-size:24px;font-weight:700;color:var(--navy)}
  .kpi i{display:block;font-style:normal;font-size:12px;color:var(--lgray);margin-top:4px}
  .controls{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin:0 0 16px;font-size:13px;color:var(--gray)}
  select,input{font:inherit;padding:5px 8px;border:1px solid #D5DBDB;border-radius:6px;background:#fff;color:#222}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  @media(max-width:900px){.grid{grid-template-columns:1fr}}
  .card{background:#fff;border:1px solid #E5EAEA;border-radius:10px;padding:14px 16px 10px;margin-bottom:16px}
  .card h2{font-size:15px;color:var(--navy);margin:0 0 10px}
  svg{width:100%;height:auto;display:block}
  .tip{position:fixed;pointer-events:none;background:rgba(31,78,121,.95);color:#fff;font-size:12.5px;
       line-height:1.55;padding:8px 10px;border-radius:8px;display:none;z-index:9;white-space:nowrap}
  .dim{opacity:.18}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th,td{padding:6px 8px;text-align:right;border-bottom:1px solid #EEF2F2;white-space:nowrap}
  th:first-child,td:first-child{text-align:left}
  th{color:var(--gray);font-weight:600;cursor:pointer;user-select:none}
  th.sorted{color:var(--navy)}
  tr.hi{background:#FDF3E7}
  tbody tr:hover{background:#F6F9F9}
  .foot{color:var(--lgray);font-size:12px;margin-top:10px}
</style></head><body><div class="wrap">
<h1>品类 × 履约联合：差评里有多少来自配送</h1>
<p class="sub">Olist 巴西电商 · 方向二延伸 · 延迟标记复用方向一口径（订单级延迟率 6.66%，件数加权 <b id="pdl"></b>%）
 · 全表 __N_CAT__ 个品类 / __N_ITEM__ 件 · 数据源 market/data/品类履约联合.csv，生成脚本 market/charts.py</p>

<div class="kpis">
  <div class="kpi"><b>平台差评率</b><span id="k1"></span><i>延迟件 6.48% × 62.88% + 准时件 93.52% × 11.40%</i></div>
  <div class="kpi"><b>延迟贡献</b><span>3.33pp</span><i>占全部差评的 22.6%（剔除里约后 20.2%）</i></div>
  <div class="kpi"><b>品类层物流杠杆</b><span>12.6%~32.4%</span><i>办公家具（自身问题）→ 文具（履约可拿回）</i></div>
  <div class="kpi"><b>最大绝对贡献</b><span>377 件</span><i>床品家纺因延迟多出的差评件数</i></div>
</div>

<div class="controls">
  <label>销量门槛
    <select id="minvol">
      <option value="0">全部品类</option>
      <option value="1000" selected>≥ 1,000 件</option>
      <option value="3000">≥ 3,000 件</option>
      <option value="5000">≥ 5,000 件</option>
    </select>
  </label>
  <label>搜索品类 <input id="q" placeholder="如：床品 / cam"></label>
  <span>悬停看数值 · 点击品类高亮 · 点表头排序 · 已排除"未分类"</span>
</div>

<div class="grid">
  <div class="card"><h2>延迟率 × 差评率（气泡 = 销量）</h2><svg id="scatter" viewBox="0 0 660 440"></svg></div>
  <div class="card"><h2>销量 Top12 品类：差评率拆解（按差评率排序）</h2><svg id="bar" viewBox="0 0 660 440"></svg></div>
</div>

<div class="card"><h2>全量结果表（点击表头排序）</h2>
<p class="foot" style="margin:0 0 8px">列怎么读（件口径）：差评率 = 差评件 ÷ 件数；延迟率 = 件落在延迟订单里的占比；
延迟组/准时组差评率 = 这两批件各自的差评占比；延迟贡献 = 延迟率 ×（延迟组差评率 − 准时组差评率），
即"因延迟多出来的差评"折算到全部件上的百分点；延迟贡献占比 = 延迟贡献 ÷ 差评率。</p>
<div id="tablebox"></div>
<p class="foot">图表由 market/charts.py 生成；口径见 方法与口径.md 3.7。数据为件数加权，差异说明见文档。</p></div>

<div class="tip" id="tip"></div>
</div>
<script>
const DATA = __DATA__;
const PD = +"__PLAT_DELAY__", PR = +"__PLAT_RATE__";
const NAVY="#1F4E79", ORANGE="#E67E22", SKY="#5DADE2", GRAY="#7F8C8D", LGRAY="#BDC3C7";
const SVGNS = "http://www.w3.org/2000/svg";
let minVol = 1000, q = "", sel = null, sortKey = "vol", sortAsc = false;
const tip = document.getElementById("tip");
document.getElementById("k1").textContent = PR.toFixed(2) + "%";
document.getElementById("pdl").textContent = PD.toFixed(2);

const base = DATA.filter(d => d.cat !== "未分类");
const shown = () => base.filter(d => d.vol >= minVol && (q === "" || d.cn.includes(q) || d.cat.toLowerCase().includes(q.toLowerCase())));
const el = (t, a, txt) => { const n = document.createElementNS(SVGNS, t); for (const k in a) n.setAttribute(k, a[k]); if (txt != null) n.textContent = txt; return n; };
const fmt = (v, n) => (v == null ? "—" : Number(v).toFixed(n));
function showTip(e, html){ tip.innerHTML = html; tip.style.display = "block";
  const x = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 10);
  tip.style.left = x + "px"; tip.style.top = (e.clientY + 14) + "px"; }
function hideTip(){ tip.style.display = "none"; }
function pickCat(c){ sel = (sel === c) ? null : c; draw(); }

function axes(svg, M, xd, yd, xlab, ylab, xticks, yticks){
  const {l, r, t, b} = M, W = 660, H = 440;
  const sx = v => l + (v - xd[0]) / (xd[1] - xd[0]) * (W - l - r);
  const sy = v => H - b - (v - yd[0]) / (yd[1] - yd[0]) * (H - t - b);
  yticks.forEach(v => { svg.appendChild(el("line", {x1:l, x2:W-r, y1:sy(v), y2:sy(v), stroke:"#EFF3F3"}));
    svg.appendChild(el("text", {x:l-8, y:sy(v)+4, fill:GRAY, "font-size":11, "text-anchor":"end"}, v)); });
  xticks.forEach(v => { svg.appendChild(el("line", {x1:sx(v), x2:sx(v), y1:t, y2:H-b, stroke:"#EFF3F3"}));
    svg.appendChild(el("text", {x:sx(v), y:H-b+18, fill:GRAY, "font-size":11, "text-anchor":"middle"}, v)); });
  svg.appendChild(el("line", {x1:l, x2:W-r, y1:H-b, y2:H-b, stroke:LGRAY}));
  svg.appendChild(el("line", {x1:l, x2:l, y1:t, y2:H-b, stroke:LGRAY}));
  svg.appendChild(el("text", {x:(l+W-r)/2, y:H-8, fill:GRAY, "font-size":12, "text-anchor":"middle"}, xlab));
  svg.appendChild(el("text", {x:14, y:(t+H-b)/2, fill:GRAY, "font-size":12, "text-anchor":"middle",
    transform:`rotate(-90 14 ${(t+H-b)/2})`}, ylab));
  return {sx, sy};
}

function draw(){
  const pts = shown();
  const svg = document.getElementById("scatter"); svg.innerHTML = "";
  const M = {l:54, r:18, t:18, b:44};
  const x0 = 3.8, x1 = 8.3, y0 = 5, y1 = 27;
  const g = axes(svg, M, [x0,x1], [y0,y1], "延迟率（%）", "差评率（%）",
                 [4,5,6,7,8], [5,10,15,20,25]);
  svg.appendChild(el("line", {x1:g.sx(PD), x2:g.sx(PD), y1:M.t, y2:440-M.b, stroke:LGRAY, "stroke-dasharray":"5 4"}));
  svg.appendChild(el("line", {x1:M.l, x2:660-M.r, y1:g.sy(PR), y2:g.sy(PR), stroke:LGRAY, "stroke-dasharray":"5 4"}));
  svg.appendChild(el("text", {x:g.sx(PD)+4, y:M.t+10, fill:GRAY, "font-size":11}, `平台延迟率 ${PD.toFixed(2)}%`));
  svg.appendChild(el("text", {x:M.l+4, y:g.sy(PR)-6, fill:GRAY, "font-size":11}, `平台差评率 ${PR.toFixed(2)}%`));
  pts.slice().sort((a,b) => b.vol - a.vol).forEach(d => {
    const c = el("circle", {cx:g.sx(d.delay), cy:g.sy(d.rate), r:(4 + Math.sqrt(d.vol)/6.2).toFixed(1),
      fill:SKY, "fill-opacity":.62, stroke:NAVY, "stroke-width":1});
    if (sel && sel !== d.cat) c.setAttribute("class", "dim");
    c.style.cursor = "pointer";
    c.onmousemove = e => showTip(e, `<b>${d.cn}</b><br>销量 ${d.vol.toLocaleString()} 件 · 差评率 ${fmt(d.rate,2)}%<br>
      延迟率 ${fmt(d.delay,2)}% · 延迟组 ${fmt(d.pd,2)}% / 准时组 ${fmt(d.po,2)}%<br>
      延迟贡献 ${fmt(d.contrib,2)}pp（占差评 ${fmt(d.share,1)}%）`);
    c.onmouseleave = hideTip;
    c.onclick = () => pickCat(d.cat);
    svg.appendChild(c);
    if (d.cat === sel) svg.appendChild(el("text", {x:g.sx(d.delay)+10, y:g.sy(d.rate)+3, fill:NAVY,
      "font-size":12, "font-weight":"bold"}, d.cn));
  });

  const svg2 = document.getElementById("bar"); svg2.innerHTML = "";
  const top = base.slice().sort((a,b) => b.vol - a.vol).slice(0,12).sort((a,b) => a.rate - b.rate);
  const M2 = {l:78, r:34, t:14, b:40}, W = 660, H = 440, bw = (H - M2.t - M2.b) / top.length;
  const xmax = 28, bx = v => M2.l + v / xmax * (W - M2.l - M2.r);
  [0,5,10,15,20,25].forEach(v => { svg2.appendChild(el("line", {x1:bx(v), x2:bx(v), y1:M2.t, y2:H-M2.b, stroke:"#EFF3F3"}));
    svg2.appendChild(el("text", {x:bx(v), y:H-M2.b+16, fill:GRAY, "font-size":11, "text-anchor":"middle"}, v)); });
  svg2.appendChild(el("line", {x1:bx(PR), x2:bx(PR), y1:M2.t, y2:H-M2.b, stroke:NAVY, "stroke-dasharray":"6 4"}));
  svg2.appendChild(el("text", {x:bx(PR)+4, y:M2.t+10, fill:NAVY, "font-size":11}, `平台整体差评率 ${PR.toFixed(2)}%`));
  svg2.appendChild(el("text", {x:(M2.l+W-M2.r)/2, y:H-6, fill:GRAY, "font-size":12, "text-anchor":"middle"}, "差评率（%）"));
  top.forEach((d, i) => {
    const y = M2.t + i * bw, h = bw * 0.62, self = d.rate - d.contrib;
    const dimmed = sel && sel !== d.cat;
    const g1 = el("g", {}); if (dimmed) g1.setAttribute("class", "dim");
    g1.appendChild(el("rect", {x:M2.l, y, width:bx(self)-M2.l, height:h, fill:LGRAY}));
    g1.appendChild(el("rect", {x:bx(self), y, width:bx(d.rate)-bx(self), height:h, fill:ORANGE}));
    g1.appendChild(el("text", {x:M2.l-8, y:y+h/2+4, fill:GRAY, "font-size":11.5, "text-anchor":"end"}, d.cn));
    g1.appendChild(el("text", {x:bx(d.rate)+5, y:y+h/2+4, fill:GRAY, "font-size":11}, fmt(d.rate,1)+"%"));
    if (d.contrib >= 1.2) g1.appendChild(el("text", {x:(bx(self)+bx(d.rate))/2, y:y+h/2+4, fill:"#fff",
      "font-size":10.5, "font-weight":"bold", "text-anchor":"middle"}, fmt(d.contrib,1)));
    g1.style.cursor = "pointer";
    g1.onmousemove = e => showTip(e, `<b>${d.cn}</b> · 销量 ${d.vol.toLocaleString()} 件<br>
      差评率 ${fmt(d.rate,2)}% = 品类自身 ${fmt(self,2)} + 延迟贡献 ${fmt(d.contrib,2)}pp<br>
      延迟率 ${fmt(d.delay,2)}% · 超额差评 ${fmt(d.excess, 0)} 件`);
    g1.onmouseleave = hideTip;
    g1.onclick = () => pickCat(d.cat);
    svg2.appendChild(g1);
  });

  const keys = [["cn","品类"],["vol","销量（件）"],["rate","差评率 %"],["delay","延迟率 %"],["pd","延迟组差评率 %"],
                ["po","准时组差评率 %"],["contrib","延迟贡献 pp"],["share","延迟贡献占比 %"],["excess","超额差评（件）"]];
  const rs = shown().slice().sort((a,b) => {
    const va = a[sortKey], vb = b[sortKey];
    const na = (va == null) ? -Infinity : va, nb = (vb == null) ? -Infinity : vb;
    return (sortAsc ? 1 : -1) * (na > nb ? 1 : na < nb ? -1 : 0);
  });
  let th = "<tr>" + keys.map(([k,label]) => `<th data-k="${k}" class="${k===sortKey?'sorted':''}">${label}${k===sortKey?(sortAsc?' ▲':' ▼'):''}</th>`).join("") + "</tr>";
  let tb = rs.map(d => `<tr class="${d.cat===sel?'hi':''}"><td>${d.cn}</td><td>${d.vol.toLocaleString()}</td>
      <td>${fmt(d.rate,2)}</td><td>${fmt(d.delay,2)}</td><td>${fmt(d.pd,2)}</td><td>${fmt(d.po,2)}</td>
      <td>${fmt(d.contrib,2)}</td><td>${fmt(d.share,1)}</td><td>${fmt(d.excess, 0)}</td></tr>`).join("");
  document.getElementById("tablebox").innerHTML = `<table><thead>${th}</thead><tbody>${tb}</tbody></table>`;
  document.querySelectorAll("th").forEach(t => t.onclick = () => {
    const k = t.dataset.k; if (k === sortKey) sortAsc = !sortAsc; else { sortKey = k; sortAsc = (k === "cn"); } draw(); });
}
document.getElementById("minvol").onchange = e => { minVol = +e.target.value; draw(); };
document.getElementById("q").oninput = e => { q = e.target.value.trim(); draw(); };
draw();
</script></body></html>
"""

cat = pd.read_csv(os.path.join(DATA_DIR, "品类结构.csv"), encoding="utf-8-sig")
med_price = cat["件均价"].median()
med_rate = cat["差评率"].median()
top12 = cat.head(12)["品类"].tolist()
fig, ax = plt.subplots(figsize=(10, 6.4))
for _, r in cat.iterrows():
    if r["品类"] in top12:
        color = ORANGE if r["差评率"] > med_rate else NAVY
        ax.scatter(r["件均价"], r["差评率"], s=r["销量"] / 18, color=color, alpha=0.85, zorder=3)
        ax.annotate(r["品类"], (r["件均价"], r["差评率"]), textcoords="offset points",
                    xytext=(0, 7), ha="center", fontsize=8.5, color=GRAY)
    else:
        ax.scatter(r["件均价"], r["差评率"], s=r["销量"] / 18, color=LGRAY, alpha=0.5, zorder=2)
ax.axvline(med_price, color=LGRAY, linestyle="--", lw=1)
ax.axhline(med_rate, color=LGRAY, linestyle="--", lw=1)
ax.set_xlabel("件均价（巴西雷亚尔）", fontsize=11)
ax.set_ylabel("差评率（%）", fontsize=11)
ax.set_title("品类定位：销量 × 件均价 × 口碑（气泡=商品件数）", fontsize=13, fontweight="bold", color=NAVY, pad=12)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="both", linestyle="--", alpha=0.25)
ax.tick_params(colors=GRAY)
ax.legend(handles=[
    Line2D([], [], marker="o", color="none", markerfacecolor=NAVY, markersize=10, label="口碑好于中位"),
    Line2D([], [], marker="o", color="none", markerfacecolor=ORANGE, markersize=10, label="口碑差于中位")],
    loc="upper left", fontsize=9, frameon=False)
fig.savefig(os.path.join(FIG_DIR, "品类定位图.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)

band = pd.read_csv(os.path.join(DATA_DIR, "价格带.csv"), encoding="utf-8-sig")
order = ["0-20", "20-50", "50-100", "100-200", "200+"]
band["价格档"] = pd.Categorical(band["价格档"], categories=order, ordered=True)
band = band.sort_values("价格档")
fig, ax1 = plt.subplots(figsize=(9, 5.2))
bars = ax1.bar(band["价格档"], band["件数"], color=[SKY, SKY, NAVY, ORANGE, ORANGE], width=0.55, zorder=3)
for b, v, r in zip(bars, band["件数"], band["占比"]):
    ax1.text(b.get_x() + b.get_width() / 2, v + 800, f"{v:,}\n({r}%)", ha="center", fontsize=9, color=GRAY)
ax1.set_ylabel("商品件数", fontsize=11)
ax1.set_ylim(0, band["件数"].max() * 1.25)
ax1.set_xlabel("价格档（巴西雷亚尔）", fontsize=11)
ax1.tick_params(colors=GRAY)
ax1.spines[["top", "right"]].set_visible(False)
ax2 = ax1.twinx()
ax2.plot(range(len(band)), band["差评率"], "-o", color=ORANGE, linewidth=2, markersize=6, zorder=4)
for i, v in enumerate(band["差评率"]):
    ax2.annotate(f"{v}%", (i, v), textcoords="offset points", xytext=(0, -14), ha="center", fontsize=8.5, color=ORANGE)
ax2.set_ylabel("差评率（%）", fontsize=11, color=ORANGE)
ax2.set_ylim(13, 18)
ax2.tick_params(colors=ORANGE, axis="y")
ax2.spines[["top"]].set_visible(False)
ax1.set_title("价格带结构：中低价是主力，中高价位口碑最好", fontsize=13, fontweight="bold", color=NAVY, pad=12)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "价格带结构图.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)

region = pd.read_csv(os.path.join(DATA_DIR, "区域画像.csv"), encoding="utf-8-sig")
region["州"] = region["customer_state"].map(STATE).fillna(region["customer_state"])
mean_rate = region["差评率"].mean()
fig, ax = plt.subplots(figsize=(10, 6))
for _, r in region.iterrows():
    color = ORANGE if r["差评率"] > mean_rate + 2 else (SKY if r["差评率"] > mean_rate else NAVY)
    ax.scatter(r["件数"], r["差评率"], s=max(r["件数"] / 90, 20), color=color, alpha=0.75, zorder=3)
    off = (0, 5) if r["差评率"] > mean_rate else (0, -12)
    ax.annotate(r["州"], (r["件数"], r["差评率"]), textcoords="offset points", xytext=off, ha="center", fontsize=9, color=GRAY)
ax.axhline(mean_rate, color=LGRAY, linestyle="--", lw=1)
ax.set_xscale("log")
ax.set_xlabel("市场规模（商品件数，对数刻度）", fontsize=11)
ax.set_ylabel("差评率（%）", fontsize=11)
ax.set_title("区域市场：规模 × 口碑（气泡=市场规模，橙=差评明显偏高）", fontsize=13, fontweight="bold", color=NAVY, pad=12)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="both", linestyle="--", alpha=0.2)
ax.tick_params(colors=GRAY)
ax.legend(handles=[
    Line2D([], [], marker="o", color="none", markerfacecolor=ORANGE, markersize=10, label="差评偏高（均值+2pp）"),
    Line2D([], [], marker="o", color="none", markerfacecolor=SKY, markersize=10, label="略高于均值"),
    Line2D([], [], marker="o", color="none", markerfacecolor=NAVY, markersize=10, label="低于均值")],
    loc="upper right", fontsize=9, frameon=False)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "区域市场图.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)

region_cat = pd.read_csv(os.path.join(DATA_DIR, "区域品类.csv"), encoding="utf-8-sig")
top_states = ["SP", "RJ", "MG", "BA"]
fig, axes = plt.subplots(1, 4, figsize=(14, 4.6), sharey=True)
for ax, st in zip(axes, top_states):
    sub = region_cat[region_cat["customer_state"] == st].head(5).sort_values("件数")
    labels = [CN.get(c, c) for c in sub["品类"]]
    ax.barh(labels, sub["件数"], color=NAVY, height=0.6, zorder=3)
    for i, v in enumerate(sub["件数"]):
        ax.text(v, i, f" {v:,}", va="center", fontsize=8, color=GRAY)
    ax.set_title(STATE.get(st, st), fontsize=11, fontweight="bold", color=NAVY)
    ax.set_xlim(0, sub["件数"].max() * 1.35)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", linestyle="--", alpha=0.2)
    ax.tick_params(colors=GRAY)
fig.suptitle("大州品类偏好（各州销量 Top5 品类）", fontsize=13, fontweight="bold", color=NAVY)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(os.path.join(FIG_DIR, "区域品类偏好图.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)

# ---------------- 品类 × 履约联合 ----------------
jc = pd.read_csv(os.path.join(DATA_DIR, "品类履约联合.csv"), encoding="utf-8-sig")
# 参考线用全表（含"未分类"）的件数加权均值，与报告里的平台层数字（6.48% / 14.73%）一致
platform_delay = (jc["延迟率"] * jc["销量"]).sum() / jc["销量"].sum()
platform_rate = (jc["差评率"] * jc["销量"]).sum() / jc["销量"].sum()
jc = jc[jc["品类"] != "未分类"]
lv = jc[jc["销量"] >= 1000].copy()

fig, ax = plt.subplots(figsize=(10, 6.4))
ax.scatter(lv["延迟率"], lv["差评率"], s=lv["销量"] / 18, color=SKY, alpha=0.75, zorder=3)
ax.axvline(platform_delay, color=LGRAY, linestyle="--", lw=1)
ax.axhline(platform_rate, color=LGRAY, linestyle="--", lw=1)
labels = lv.sort_values("延迟贡献占比", ascending=False).head(5)["品类"].tolist() + \
         lv.sort_values("差评率", ascending=False).head(4)["品类"].tolist()
for _, r in lv.iterrows():
    if r["品类"] in dict.fromkeys(labels):
        ax.annotate(CN.get(r["品类"], r["品类"]), (r["延迟率"], r["差评率"]),
                    textcoords="offset points", xytext=(7, 4), fontsize=9, color=GRAY)
ax.set_xlabel("延迟率（该品类所在订单的延迟占比，%）", fontsize=11)
ax.set_ylabel("差评率（%）", fontsize=11)
ax.set_title("品类 × 履约：右上 = 配送慢且口碑差；左上 = 延迟不高但口碑差（品类自身）",
             fontsize=13, fontweight="bold", color=NAVY, pad=12)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(linestyle="--", alpha=0.25)
ax.tick_params(colors=GRAY)
ax.legend(handles=[
    Line2D([], [], marker="o", color="none", markerfacecolor=SKY, markersize=10, label="气泡 = 销量（件）"),
    Line2D([], [], color=LGRAY, linestyle="--",
           label=f"平台延迟率 {platform_delay:.2f}% / 差评率 {platform_rate:.2f}%")],
    loc="lower right", fontsize=9, frameon=False)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "品类履约联合_散点图.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)

top = jc.sort_values("销量", ascending=False).head(12).sort_values("差评率")
self_part = top["差评率"] - top["延迟贡献"]
y = np.arange(len(top))
fig, ax = plt.subplots(figsize=(10, 6))
ax.barh(y, self_part, color=LGRAY, height=0.6, label="品类自身（与延迟无关）", zorder=3)
ax.barh(y, top["延迟贡献"], left=self_part, color=ORANGE, height=0.6,
        label="延迟贡献（能靠履约改善拿回）", zorder=3)
ax.set_yticks(y)
ax.set_yticklabels([CN.get(c, c) for c in top["品类"]], fontsize=9.5)
ax.axvline(platform_rate, color=NAVY, linestyle="--", lw=1.2, label=f"平台整体差评率 {platform_rate:.2f}%")
for i, (_, r) in enumerate(top.iterrows()):
    ax.text(r["差评率"] + 0.25, i, f"{r['差评率']:.1f}%", va="center", fontsize=8.5, color=GRAY)
    if r["延迟贡献"] >= 1.2:      # 太窄的段不标，避免压字
        ax.text(self_part.iloc[i] + r["延迟贡献"] / 2, i, f"{r['延迟贡献']:.1f}",
                va="center", ha="center", fontsize=8, color="white", fontweight="bold")
ax.set_xlabel("差评率（%）", fontsize=11)
ax.set_title("销量 Top12 品类差评率拆解：橙色是能靠履约改善拿回的部分",
             fontsize=13, fontweight="bold", color=NAVY, pad=12)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="x", linestyle="--", alpha=0.25)
ax.tick_params(colors=GRAY)
ax.legend(loc="lower right", fontsize=9, frameon=False)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "品类履约联合_分解图.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)

# ---------------- 品类 × 履约联合：整页汇总（Python 制图，非 Power BI 截图） ----------------
jc2 = pd.read_csv(os.path.join(DATA_DIR, "品类履约联合.csv"), encoding="utf-8-sig")
plat_delay = (jc2["延迟率"] * jc2["销量"]).sum() / jc2["销量"].sum()
plat_rate = (jc2["差评率"] * jc2["销量"]).sum() / jc2["销量"].sum()
j2 = jc2[jc2["品类"] != "未分类"]
lv2 = j2[j2["销量"] >= 1000].copy()
top2 = j2.sort_values("销量", ascending=False).head(12).sort_values("差评率")
kpi = [("平台差评率", f"{plat_rate:.2f}%", "74 个品类 / 109,362 件"),
       ("延迟贡献", "3.33pp", "占全部差评的 22.6%"),
       ("品类层物流杠杆", "12.6%~32.4%", "办公家具 → 文具"),
       ("最大绝对贡献", "377 件", "床品家纺（因延迟多出的差评）")]

fig = plt.figure(figsize=(14, 9.2), facecolor="white")
gs = fig.add_gridspec(3, 2, height_ratios=[0.42, 0.52, 1.55], hspace=0.55, wspace=0.22,
                      left=0.055, right=0.965, top=0.945, bottom=0.065)

ax_h = fig.add_subplot(gs[0, :]); ax_h.axis("off")
ax_h.text(0, 0.82, "品类 × 履约联合：差评里有多少来自配送", fontsize=19, fontweight="bold", color=NAVY)
ax_h.text(0, 0.28, f"Olist 巴西电商 · 方向二延伸 · 延迟标记复用方向一口径（订单级延迟率 6.66%）"
                   f" · 全表 {len(jc2)} 个品类 / {int(jc2['销量'].sum()):,} 件（含未分类）",
          fontsize=10.5, color=GRAY)

ax_k = fig.add_subplot(gs[1, :]); ax_k.axis("off")
for i, (k, v, s) in enumerate(kpi):
    x0 = i * 0.25
    ax_k.add_patch(FancyBboxPatch((x0 + 0.006, 0.06), 0.235, 0.86, boxstyle="round,pad=0.012",
                                  linewidth=1, edgecolor="#D5DBDB", facecolor="#F8F9F9",
                                  transform=ax_k.transAxes, zorder=1))
    ax_k.text(x0 + 0.024, 0.66, k, fontsize=10.5, color=GRAY, transform=ax_k.transAxes)
    ax_k.text(x0 + 0.024, 0.24, v, fontsize=17, fontweight="bold", color=NAVY, transform=ax_k.transAxes)
    ax_k.text(x0 + 0.024, 0.02, s, fontsize=8.8, color=LGRAY, transform=ax_k.transAxes)

ax1 = fig.add_subplot(gs[2, 0])
ax1.scatter(lv2["延迟率"], lv2["差评率"], s=lv2["销量"] / 22, color=SKY, alpha=0.75, zorder=3)
ax1.axvline(plat_delay, color=LGRAY, linestyle="--", lw=1)
ax1.axhline(plat_rate, color=LGRAY, linestyle="--", lw=1)
ax1.text(plat_delay, 0.985, f" 平台延迟率 {plat_delay:.2f}%（件数加权）", fontsize=8, color=GRAY,
         va="top", ha="left", transform=ax1.get_xaxis_transform())
ax1.text(0.02, plat_rate, f" 平台差评率 {plat_rate:.2f}%", fontsize=8, color=GRAY, va="bottom",
         ha="left", transform=ax1.get_yaxis_transform())
lab = lv2.sort_values("延迟贡献占比", ascending=False).head(5)["品类"].tolist() + \
      lv2.sort_values("差评率", ascending=False).head(4)["品类"].tolist()
for _, r in lv2.iterrows():
    if r["品类"] in dict.fromkeys(lab):
        ax1.annotate(CN.get(r["品类"], r["品类"]), (r["延迟率"], r["差评率"]),
                     textcoords="offset points", xytext=(6, 3), fontsize=8.5, color=GRAY)
ax1.legend(handles=[Line2D([], [], marker="o", color="none", markerfacecolor=SKY,
                           markersize=9, alpha=0.8, label="气泡 = 销量（件）")],
           loc="lower right", fontsize=8.5, frameon=False)
ax1.set_xlabel("延迟率（%）", fontsize=10)
ax1.set_ylabel("差评率（%）", fontsize=10)
ax1.set_title("延迟率 × 差评率：右上 = 配送慢且口碑差；左上 = 品类自身问题",
              fontsize=12, fontweight="bold", color=NAVY, pad=10)
ax1.spines[["top", "right"]].set_visible(False)
ax1.grid(linestyle="--", alpha=0.25)
ax1.tick_params(colors=GRAY, labelsize=9)

ax2 = fig.add_subplot(gs[2, 1])
self2 = top2["差评率"] - top2["延迟贡献"]
y2 = np.arange(len(top2))
ax2.barh(y2, self2, color=LGRAY, height=0.62, label="品类自身（与延迟无关）", zorder=3)
ax2.barh(y2, top2["延迟贡献"], left=self2, color=ORANGE, height=0.62,
         label="延迟贡献（能靠履约改善拿回）", zorder=3)
ax2.set_yticks(y2)
ax2.set_yticklabels([CN.get(c, c) for c in top2["品类"]], fontsize=9)
ax2.axvline(plat_rate, color=NAVY, linestyle="--", lw=1.2, label=f"平台整体差评率 {plat_rate:.2f}%")
for i, (_, r) in enumerate(top2.iterrows()):
    ax2.text(r["差评率"] + 0.25, i, f"{r['差评率']:.1f}%", va="center", fontsize=8, color=GRAY)
    if r["延迟贡献"] >= 1.2:
        ax2.text(self2.iloc[i] + r["延迟贡献"] / 2, i, f"{r['延迟贡献']:.1f}", va="center",
                 ha="center", fontsize=7.5, color="white", fontweight="bold")
ax2.set_xlabel("差评率（%）", fontsize=10)
ax2.set_xlim(0, 28)
ax2.set_title("销量 Top12 品类：差评率拆解（按差评率排序）", fontsize=12, fontweight="bold", color=NAVY, pad=10)
ax2.spines[["top", "right"]].set_visible(False)
ax2.grid(axis="x", linestyle="--", alpha=0.25)
ax2.tick_params(colors=GRAY, labelsize=9)
ax2.legend(loc="lower right", fontsize=8.5, frameon=False)

fig.savefig(os.path.join(FIG_DIR, "品类履约联合_汇总页.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)
print("7 张图已保存到 market/图表/（含整页汇总页）")

# ---------------- 品类 × 履约联合：交互看板（单文件 HTML，零依赖，双击即开） ----------------
def _nz(v):
    """NaN → None（JSON null）：延迟率为 0 的小品类没有延迟订单，延迟贡献无法估计"""
    return None if pd.isna(v) else float(v)

rows = [{"cat": r["品类"], "cn": CN.get(r["品类"], r["品类"]), "vol": int(r["销量"]),
         "rate": _nz(r["差评率"]), "delay": _nz(r["延迟率"]), "pd": _nz(r["延迟组差评率"]),
         "po": _nz(r["准时组差评率"]), "contrib": _nz(r["延迟贡献"]),
         "share": _nz(r["延迟贡献占比"]), "excess": _nz(r["超额差评件数"])}
        for _, r in jc2.iterrows()]
html = (DASHBOARD_TPL
        .replace("__DATA__", json.dumps(rows, ensure_ascii=False))
        .replace("__PLAT_DELAY__", f"{plat_delay:.2f}")
        .replace("__PLAT_RATE__", f"{plat_rate:.2f}")
        .replace("__N_CAT__", str(len(jc2)))
        .replace("__N_ITEM__", f"{int(jc2['销量'].sum()):,}"))
with open(os.path.join(SCRIPT_DIR, "品类履约联合_交互看板.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("交互看板已输出：品类履约联合_交互看板.html（双击即开，无需联网）")

# ---------------- Power BI 导入用表（加中文品类名，直接拖进 PBI 建页） ----------------
pbi = jc2.copy()
pbi.insert(0, "品类中文", [CN.get(c, c) for c in pbi["品类"]])
pbi = pbi[["品类中文", "品类", "销量", "差评率", "延迟率", "延迟组差评率", "准时组差评率",
           "延迟贡献", "延迟贡献占比", "超额差评件数"]]
pbi.to_csv(os.path.join(DATA_DIR, "品类履约联合_PowerBI.csv"), index=False, encoding="utf-8-sig")
print("Power BI 导入用表已输出：data/品类履约联合_PowerBI.csv（含中文品类名）")

# ---------------- 模块⑤ 销量趋势与预测图 ----------------
ms = pd.read_csv(os.path.join(DATA_DIR, "月度销量.csv"), encoding="utf-8-sig")
pred = pd.read_csv(os.path.join(DATA_DIR, "品类销量预测.csv"), encoding="utf-8-sig")
plat_pred = pred[pred["品类"] == "平台总体"].iloc[0]
plat = ms[ms["序列"] == "平台总体"].reset_index(drop=True)

fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.6))
ax = axes[0]
ax.bar(range(len(plat)), plat["件数"], color=SKY, label="月度实际销量")
fx = [len(plat) - 1, len(plat), len(plat) + 1, len(plat) + 2]
fy = [plat["件数"].iloc[-1], plat_pred["预测下1月"], plat_pred["预测下2月"], plat_pred["预测下3月"]]
ax.plot(fx, fy, color=ORANGE, ls="--", lw=2.2, marker="o",
        label=f"未来 3 个月预测（SES，回测 MAPE {plat_pred['最后4月MAPE%']}%）")
ax.set_xticks([0, 4, 8, 12, 16, len(plat) - 1])
ax.set_xticklabels([plat["月份"].iloc[i] for i in [0, 4, 8, 12, 16, len(plat) - 1]], fontsize=9)
ax.set_ylabel("销量（件/月）")
ax.set_title("平台月销量与未来 3 个月预测（趋势外推）", fontsize=12, color=NAVY, fontweight="bold")
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.3)

ax = axes[1]
top3 = [s for s in ms["序列"].unique() if s != "平台总体"][:3]
for name, color in zip(top3, [NAVY, ORANGE, "#27AE60"]):
    sub = ms[ms["序列"] == name].reset_index(drop=True)
    ax.plot(range(len(sub)), sub["件数"], marker="o", ms=3.5, lw=1.8, color=color, label=CN.get(name, name))
sub0 = ms[ms["序列"] == top3[0]].reset_index(drop=True)
xt = [0, 6, 12, 18, len(sub0) - 1]
ax.set_xticks(xt)
ax.set_xticklabels([sub0["月份"].iloc[i] for i in xt], fontsize=9)
ax.set_ylabel("销量（件/月）")
ax.set_title("销量 Top3 品类月度走势", fontsize=12, color=NAVY, fontweight="bold")
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "销量趋势与预测.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)

# ---------------- 模块⑥ 差评主题对比图 ----------------
th = pd.read_csv(os.path.join(DATA_DIR, "差评主题.csv"), encoding="utf-8-sig").sort_values("差评提及率%")
fig, ax = plt.subplots(figsize=(9, 4.4))
y = np.arange(len(th))
ax.barh(y + 0.2, th["差评提及率%"], height=0.38, color=ORANGE, label="差评订单")
ax.barh(y - 0.2, th["好评提及率%"], height=0.38, color=SKY, label="好评订单")
for i, (b, g, r) in enumerate(zip(th["差评提及率%"], th["好评提及率%"], th["差评/好评倍率"])):
    ax.text(b + 0.5, i + 0.2, f"{b}%", va="center", fontsize=9, color=ORANGE)
    ax.text(g + 0.5, i - 0.2, f"{g}%", va="center", fontsize=9, color=GRAY)
    ax.text(max(b, g) + 6.2, i, f"{r}×", va="center", fontsize=9.5, color=NAVY, fontweight="bold")
ax.set_yticks(y)
ax.set_yticklabels(th["主题"])
ax.set_xlim(0, max(th["差评提及率%"]) + 10)
ax.set_xlabel("提及率（该主题被提到的订单占比）")
ax.set_title("差评第一痛点是物流，售后/客服倍率最高（差评 vs 好评）", fontsize=12, color=NAVY, fontweight="bold")
ax.legend(fontsize=9, loc="lower right")
ax.grid(axis="x", alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "差评主题对比.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)

# ---------------- 模块⑦ 3C 品类竞争位图 ----------------
c3 = pd.read_csv(os.path.join(DATA_DIR, "3C品类竞争位.csv"), encoding="utf-8-sig")
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.4))
x = np.arange(len(c3))
ax = axes[0]
ax.bar(x, c3["P50元"], color=NAVY, width=0.5, label="P50 中位价")
ax.errorbar(x, c3["P50元"], yerr=[c3["P50元"] - c3["P25元"], c3["P75元"] - c3["P50元"]],
            fmt="none", ecolor=GRAY, capsize=6, lw=1.5)
ax.axhline(74.9, color=ORANGE, ls="--", lw=1.8, label="全平台 P50 = 74.9 元")
for i, v in enumerate(c3["P50元"]):
    ax.text(i, v + 4, f"{v:.0f} 元", ha="center", fontsize=9.5, color=NAVY)
ax.set_xticks(x); ax.set_xticklabels(c3["3C类目"])
ax.set_ylabel("单件价格（元）")
ax.set_title("平台 3C 是低价配件市场（中线上方为高于全平台）", fontsize=11.5, color=NAVY, fontweight="bold")
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.3)

ax = axes[1]
ax.bar(x, c3["差评率%"], color=ORANGE, width=0.5, label="差评率")
ax.axhline(14.73, color=NAVY, ls="--", lw=1.8, label="全平台差评率 14.73%")
for i, v in enumerate(c3["差评率%"]):
    ax.text(i, v + 0.25, f"{v}%", ha="center", fontsize=9.5, color=ORANGE)
ax.set_xticks(x); ax.set_xticklabels(c3["3C类目"])
ax.set_ylabel("差评率（%）")
ax.set_ylim(0, max(c3["差评率%"]) * 1.25)
ax.set_title("3C 三个类目差评率均高于或接近全平台", fontsize=11.5, color=NAVY, fontweight="bold")
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "3C品类竞争位.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)

print("新增 3 张图：销量趋势与预测.png、差评主题对比.png、3C品类竞争位.png")

# ---------------- 模块⑧ 订单全链路漏斗图 ----------------
fn = pd.read_csv(os.path.join(DATA_DIR, "订单漏斗.csv"), encoding="utf-8-sig")
stage = fn[fn["订单数"].notna()].reset_index(drop=True)
days = fn[fn["订单数"].isna()].iloc[1:].reset_index(drop=True)

fig, axes = plt.subplots(1, 2, figsize=(13, 4.4), gridspec_kw={"width_ratios": [1.35, 1]})
ax = axes[0]
y = np.arange(len(stage))[::-1]
ax.barh(y, stage["订单数"], color=[NAVY, SKY, SKY, "#27AE60"], height=0.55)
for i, yy in enumerate(y):
    r = stage.iloc[i]
    ax.text(r["订单数"] * 0.5, yy, f"{int(r['订单数']):,}", va="center", ha="center",
            color="white", fontsize=10, fontweight="bold")
    tail = f"占下单 {r['占下单%']:.2f}%" + (f"（本级流失 {int(r['本环节流失']):,}）" if r["本环节流失"] else "")
    ax.text(r["订单数"] + stage["订单数"].max() * 0.02, yy, tail, va="center", fontsize=9, color=GRAY)
ax.set_yticks(y)
ax.set_yticklabels(stage["环节"])
ax.set_xlim(0, stage["订单数"].max() * 1.42)
ax.set_xlabel("订单数")
ax.set_title("订单全链路漏斗：签收率 %.2f%%" % (stage["订单数"].iloc[-1] / stage["订单数"].iloc[0] * 100),
             fontsize=12, color=NAVY, fontweight="bold")
ax.grid(axis="x", alpha=0.3)

ax = axes[1]
ax.axis("off")
ax.set_title("各环节平均耗时（天）", fontsize=12, color=NAVY, fontweight="bold", pad=12)
for i, r in enumerate(days.itertuples()):
    ax.text(0.05, 0.78 - i * 0.22, r.环节, fontsize=11, transform=ax.transAxes)
    ax.text(0.95, 0.78 - i * 0.22, f"{r.平均天数:.1f} 天", fontsize=12, fontweight="bold",
            color=ORANGE, ha="right", transform=ax.transAxes)
    ax.plot([0.05, 0.95], [0.72 - i * 0.22, 0.72 - i * 0.22], color="#d5dbe1", lw=1,
            transform=ax.transAxes, clip_on=False)
tot = days["平均天数"].sum()
ax.text(0.05, 0.78 - 3 * 0.22, "全链路合计", fontsize=11, fontweight="bold", transform=ax.transAxes)
ax.text(0.95, 0.78 - 3 * 0.22, f"{tot:.1f} 天", fontsize=12, fontweight="bold", color=NAVY,
        ha="right", transform=ax.transAxes)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "订单漏斗图.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)

# ---------------- 模块⑨ 用户复购与分层图 ----------------
ly = pd.read_csv(os.path.join(DATA_DIR, "用户复购分层.csv"), encoding="utf-8-sig")
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.4))
x = np.arange(len(ly)); w = 0.36
ax = axes[0]
ax.bar(x - w / 2, ly["客户占比%"], width=w, color=SKY, label="客户占比")
ax.bar(x + w / 2, ly["消费占比%"], width=w, color=NAVY, label="消费金额占比")
for i, (a, b) in enumerate(zip(ly["客户占比%"], ly["消费占比%"])):
    ax.text(i - w / 2, a + 0.6, f"{a}%", ha="center", fontsize=9, color=GRAY)
    ax.text(i + w / 2, b + 0.6, f"{b}%", ha="center", fontsize=9, color=NAVY, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(ly["层"])
ax.set_ylabel("占比（%）")
ax.set_title("复购客户仅占 3.2%，消费贡献 5.7%（客户 vs 消费占比）", fontsize=11.5, color=NAVY, fontweight="bold")
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.3)

ax = axes[1]
ax.bar(x - w / 2, ly["人均消费"], width=w, color="#27AE60", label="人均消费（元）")
ax2 = ax.twinx()
ax2.plot(x + w / 2, ly["平均差评单占比%"], marker="o", lw=2, color=ORANGE, label="平均差评单占比（%）")
for i, (v, d) in enumerate(zip(ly["人均消费"], ly["平均差评单占比%"])):
    ax.text(i - w / 2, v + 20, f"{v:,.0f}", ha="center", fontsize=9, color="#27AE60")
    ax2.text(i + w / 2, d + 0.4, f"{d}%", ha="center", fontsize=9, color=ORANGE)
ax.set_xticks(x); ax.set_xticklabels(ly["层"])
ax.set_ylabel("人均消费（元）", color="#27AE60")
ax2.set_ylabel("平均差评单占比（%）", color=ORANGE)
ax.set_title("高频客户人均消费更高、口碑更稳", fontsize=11.5, color=NAVY, fontweight="bold")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, fontsize=9, loc="upper left")
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "用户复购分层图.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)

print("新增 2 张图：订单漏斗图.png、用户复购分层图.png")
