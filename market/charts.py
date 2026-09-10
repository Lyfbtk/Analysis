import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

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
      "bebes": "婴童", "eletronicos": "电子", "未分类": "未分类"}

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

print("4 张图已保存到 market/图表/")
