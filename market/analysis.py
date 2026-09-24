import os
import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(SCRIPT_DIR, "..", "data", "raw")
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

items = pd.read_csv(BASE + r"\olist_order_items_dataset.csv", encoding="utf-8-sig")
products = pd.read_csv(BASE + r"\olist_products_dataset.csv", encoding="utf-8-sig")
orders = pd.read_csv(BASE + r"\olist_orders_dataset.csv", encoding="utf-8-sig")
reviews = pd.read_csv(BASE + r"\olist_order_reviews_dataset.csv", encoding="utf-8-sig")
customers = pd.read_csv(BASE + r"\olist_customers_dataset.csv", encoding="utf-8-sig")

review_avg = reviews.groupby("order_id")["review_score"].mean().reset_index()
review_avg["差评"] = (review_avg["review_score"] <= 2).astype(int)
orders_ok = orders[orders["order_status"] == "delivered"][["order_id", "customer_id"]].merge(
    customers[["customer_id", "customer_state"]], on="customer_id", how="left"
)
df = items[["order_id", "product_id", "price"]].merge(
    products[["product_id", "product_category_name"]], on="product_id", how="left"
).merge(orders_ok, on="order_id", how="inner").merge(
    review_avg[["order_id", "review_score", "差评"]], on="order_id", how="left"
)
df["品类"] = df["product_category_name"].fillna("未分类")
df = df.rename(columns={"price": "单价", "review_score": "评分", "差评": "是否差评"})
order_val = df.groupby("order_id")["单价"].sum().reset_index().rename(columns={"单价": "订单金额"})
df = df.merge(order_val, on="order_id", how="left")
df = df[["order_id", "customer_id", "customer_state", "product_id", "品类", "单价", "订单金额", "评分", "是否差评"]]
df.to_csv(os.path.join(DATA_DIR, "商品主表.csv"), index=False, encoding="utf-8-sig")

print("=== 数据底座 ===")
print("主表行数:", len(df), "| 主表订单数:", df["order_id"].nunique(),
      "| 评分缺失(未评分):", df["评分"].isna().sum())
print()

d = df.dropna(subset=["评分"]).copy()
cat_agg = d.groupby("品类").agg(
    销量=("order_id", "count"),
    订单数=("order_id", "nunique"),
    件均价=("单价", "mean"),
    平均评分=("评分", "mean"),
    差评率=("是否差评", "mean"),
).reset_index()
cat_agg["每单件数"] = (cat_agg["销量"] / cat_agg["订单数"]).round(2)
cat = cat_agg
cat["件均价"] = cat["件均价"].round(2)
cat["平均评分"] = cat["平均评分"].round(2)
cat["差评率"] = (cat["差评率"] * 100).round(2)
cat = cat.sort_values("销量", ascending=False).reset_index(drop=True)
cat.to_csv(os.path.join(DATA_DIR, "品类结构.csv"), index=False, encoding="utf-8-sig")

print("=== 模块① 品类结构 Top 15 ===")
print(cat.head(15).to_string(index=False))
print()
print("参与品类数:", len(cat), "| 评分商品行:", len(d), "| 评分订单数:", d["order_id"].nunique())
print("全品类差评率(件数加权):", round(d["是否差评"].mean() * 100, 2), "%")
print("全品类平均评分:", round(d["评分"].mean(), 2))
print("全品类件均价:", round(d["单价"].mean(), 2))
print()

d_all = df.copy()
region = d_all.groupby("customer_state").agg(
    件数=("order_id", "count"),
    订单数=("order_id", "nunique"),
    件均价=("单价", "mean"),
).reset_index()
region["每单件数"] = (region["件数"] / region["订单数"]).round(2)
region["件均价"] = region["件均价"].round(2)
region = region.sort_values("件数", ascending=False).reset_index(drop=True)

dr = d_all[d_all["评分"].notna()].groupby("customer_state").agg(
    平均评分=("评分", "mean"),
    差评率=("是否差评", "mean"),
).reset_index()
dr["平均评分"] = dr["平均评分"].round(2)
dr["差评率"] = (dr["差评率"] * 100).round(2)
region = region.merge(dr, on="customer_state", how="left")
region.to_csv(os.path.join(DATA_DIR, "区域画像.csv"), index=False, encoding="utf-8-sig")

print("=== 模块③ 区域画像 Top 10 ===")
print(region.head(10).to_string(index=False))
print("州数:", len(region), "| 州×品类表（区域品类.csv）由模块⑩ 统一底座输出")
print()


def band_analysis(df, bins, labels, name):
    d = df.copy()
    d["价格档"] = pd.cut(d["单价"], bins=bins, labels=labels, right=False)
    g = d.groupby("价格档", observed=False).agg(
        件数=("order_id", "count"),
    ).reset_index()
    g["占比"] = (g["件数"] / len(d) * 100).round(1)
    ds = d[d["评分"].notna()].groupby("价格档", observed=False).agg(
        平均评分=("评分", "mean"),
        差评率=("是否差评", "mean"),
        件均价=("单价", "mean"),
    ).reset_index()
    ds["平均评分"] = ds["平均评分"].round(2)
    ds["差评率"] = (ds["差评率"] * 100).round(2)
    ds["件均价"] = ds["件均价"].round(2)
    res = g.merge(ds, on="价格档", how="left")
    res.sort_values("件数", ascending=False, inplace=True)
    main = res.loc[res["件数"].idxmax()]
    small = res[res["件数"] < 300]
    good = res.drop(small.index).loc[res.drop(small.index)["差评率"].idxmin()]
    bad = res.drop(small.index).loc[res.drop(small.index)["差评率"].idxmax()]
    print(f"--- 边界{name} ---")
    print(res.to_string(index=False))
    print(f"主力档: {main['价格档']} ({main['件数']:,}件, 占比{main['占比']}%) "
          f"| 口碑最好档: {good['价格档']} ({good['差评率']}%) "
          f"| 口碑最差档: {bad['价格档']} ({bad['差评率']}%)")
    print()
    return res, main, good, bad, name


bins_A = [0, 20, 50, 100, 200, 99999]
labels_A = ["0-20", "20-50", "50-100", "100-200", "200+"]
bins_B = [0, 30, 60, 120, 240, 99999]
labels_B = ["0-30", "30-60", "60-120", "120-240", "240+"]

print("=== 模块② 价格带 ===")
resA, mA, gA, bA, _ = band_analysis(df, bins_A, labels_A, "A: 0-20/50/100/200")
resA.to_csv(os.path.join(DATA_DIR, "价格带.csv"), index=False, encoding="utf-8-sig")
band_analysis(df, bins_B, labels_B, "B: 0-30/60/120/240")

# ---------------------------------------------------------------- 模块④ 品类 × 履约联合分析
# 回答：口碑差的品类，是"配送慢"连累的，还是品类自身的问题？
# 延迟标记复用方向一的口径（先相减再取整，延迟天数 > 0 记为延迟），不重新定义
orders["_购买"] = pd.to_datetime(orders["order_purchase_timestamp"])
orders["_签收"] = pd.to_datetime(orders["order_delivered_customer_date"])
orders["_预估"] = pd.to_datetime(orders["order_estimated_delivery_date"])
orders["延迟天数"] = ((orders["_签收"] - orders["_购买"]) - (orders["_预估"] - orders["_购买"])).dt.days
orders["是否延迟"] = (orders["延迟天数"] > 0).astype(int)
delay = orders[orders["order_status"] == "delivered"][["order_id", "是否延迟", "延迟天数"]]
delay = delay.dropna(subset=["延迟天数"])

j = d.merge(delay, on="order_id", how="inner")     # d = 有评分的商品行

print("=== 模块④ 品类 × 履约联合分析 ===")
print(f"有评分商品行 {len(d):,} → 有延迟数据 {len(j):,}，覆盖订单 {j['order_id'].nunique():,} 单")
print(f"平台整体延迟件占比 {j['是否延迟'].mean() * 100:.2f}%"
      f"（方向一订单加权 6.66%，差值来自加权单位，见 方法与口径.md 3.7）")
print()

jc = j.groupby("品类").agg(
    销量=("order_id", "count"),
    订单数=("order_id", "nunique"),
    差评率=("是否差评", "mean"),
    延迟率=("是否延迟", "mean"),
).reset_index()
p_d = j[j["是否延迟"] == 1].groupby("品类")["是否差评"].mean().rename("延迟组差评率")
p_o = j[j["是否延迟"] == 0].groupby("品类")["是否差评"].mean().rename("准时组差评率")
jc = jc.merge(p_d, on="品类", how="left").merge(p_o, on="品类", how="left")

# 延迟贡献（百分点）= 延迟率 ×（延迟组差评率 − 准时组差评率），即"因延迟多出来的差评"，
# 同时是"延迟全部消除"情景下的差评率降幅上限（见 方法与口径.md 3.7）
# 注意：占比、件数都要用未舍入的小数算，最后统一转百分点
jc["延迟贡献"] = jc["延迟率"] * (jc["延迟组差评率"] - jc["准时组差评率"])
jc["延迟贡献占比"] = (jc["延迟贡献"] / jc["差评率"] * 100).round(1)
jc["超额差评件数"] = (jc["销量"] * jc["延迟贡献"]).round(0)
jc["延迟率差(对平台)"] = jc["延迟率"] - j["是否延迟"].mean()
for c in ["差评率", "延迟率", "延迟组差评率", "准时组差评率", "延迟贡献", "延迟率差(对平台)"]:
    jc[c] = (jc[c] * 100).round(2)
jc = jc.sort_values("销量", ascending=False).reset_index(drop=True)
jc.to_csv(os.path.join(DATA_DIR, "品类履约联合.csv"), index=False, encoding="utf-8-sig")

lv = jc[(jc["销量"] >= 1000) & (jc["品类"] != "未分类")]
print(lv[["品类", "销量", "差评率", "延迟率", "延迟组差评率", "准时组差评率",
          "延迟贡献", "延迟贡献占比"]].to_string(index=False))
print()

tot, w = j["是否差评"].mean(), j["是否延迟"].mean()
p1 = j[j["是否延迟"] == 1]["是否差评"].mean()
p0 = j[j["是否延迟"] == 0]["是否差评"].mean()
print(f"平台层：差评率 {tot * 100:.2f}% = 延迟件 {w * 100:.2f}% × {p1 * 100:.2f}%"
      f" + 准时件 {(1 - w) * 100:.2f}% × {p0 * 100:.2f}%")
print(f"延迟贡献 {w * (p1 - p0) * 100:.2f} 个百分点，占全部差评 {w * (p1 - p0) / tot * 100:.1f}%")

jr = j[j["customer_state"] != "RJ"]
wr, t2 = jr["是否延迟"].mean(), jr["是否差评"].mean()
r1 = jr[jr["是否延迟"] == 1]["是否差评"].mean()
r0 = jr[jr["是否延迟"] == 0]["是否差评"].mean()
print(f"稳健性（剔除里约）：延迟贡献 {wr * (r1 - r0) * 100:.2f} 个百分点，占 {wr * (r1 - r0) / t2 * 100:.1f}%")
print("结果表已输出：品类履约联合.csv")

# ---------------------------------------------------------------- 模块⑤ 品类销量趋势与预测
# 口径：delivered 订单的商品行数（件数）按购买月份聚合；预测为历史趋势外推（指数平滑），
# 不是因果预测——数据没有曝光/价格弹性/竞品字段，外推结果只用于趋势展示
orders["购买日期"] = pd.to_datetime(orders["order_purchase_timestamp"])
ts = df.merge(orders[["order_id", "购买日期"]], on="order_id", how="left")
ts["月份"] = ts["购买日期"].dt.to_period("M")
P0, P1 = pd.Period("2016-10"), pd.Period("2018-08")
valid = ts[(ts["月份"] >= P0) & (ts["月份"] <= P1)]
monthly = valid.groupby(["品类", "月份"]).agg(件数=("order_id", "count")).reset_index()

def ses(series, alpha):
    level = float(series.iloc[0])
    out = [level]
    for x in series.iloc[1:]:
        level = alpha * float(x) + (1 - alpha) * level
        out.append(level)
    return pd.Series(out, index=series.index)

def mape(actual, pred):
    return float((abs(actual - pred) / actual).mean() * 100)

top8 = list(monthly.groupby("品类")["件数"].sum().sort_values(ascending=False).head(8).index)
rows = []
for 品类 in top8:
    s = monthly[monthly["品类"] == 品类].set_index("月份")["件数"].sort_index()
    s = s.reindex(pd.period_range(P0, P1, freq="M"), fill_value=0)
    train, test = s.iloc[:-4], s.iloc[-4:]
    pred = ses(train, alpha=0.3)
    pred_test = pd.Series([pred.iloc[-1]] * len(test), index=test.index)
    e = mape(test, pred_test)
    full = ses(s, alpha=0.3)
    next3 = [full.iloc[-1]] * 3
    rows.append({"品类": 品类, "最后4月MAPE%": round(e, 1), "预测下1月": round(next3[0]),
                 "预测下2月": round(next3[1]), "预测下3月": round(next3[2]), "近12月均值": round(s.iloc[-12:].mean())})

pred_df = pd.DataFrame(rows)

tot = monthly.groupby("月份")["件数"].sum().sort_index().reindex(
    pd.period_range(P0, P1, freq="M"), fill_value=0)
tot_pred = ses(tot, alpha=0.3)
tot_test = pd.Series([tot_pred.iloc[:-4].iloc[-1]] * 4, index=tot.index[-4:])
tot_mape = mape(tot.iloc[-4:], tot_test)

pred_df = pd.concat([pd.DataFrame([{
    "品类": "平台总体", "最后4月MAPE%": round(tot_mape, 1),
    "预测下1月": round(tot_pred.iloc[-1]), "预测下2月": round(tot_pred.iloc[-1]),
    "预测下3月": round(tot_pred.iloc[-1]), "近12月均值": round(tot.iloc[-12:].mean())}]), pred_df],
    ignore_index=True)
pred_df.to_csv(os.path.join(DATA_DIR, "品类销量预测.csv"), index=False, encoding="utf-8-sig")

long_rows = []
for 名称 in ["平台总体"] + top8:
    s = tot if 名称 == "平台总体" else monthly[monthly["品类"] == 名称].set_index("月份")["件数"].sort_index().reindex(
        pd.period_range(P0, P1, freq="M"), fill_value=0)
    for m, v in s.items():
        long_rows.append({"序列": 名称, "月份": str(m), "件数": int(v)})
pd.DataFrame(long_rows).to_csv(os.path.join(DATA_DIR, "月度销量.csv"), index=False, encoding="utf-8-sig")

def linreg_forecast(train, test):
    x = np.arange(len(train)); y = train.values.astype(float)
    b, a = np.polyfit(x, y, 1)
    xs = np.arange(len(train), len(train) + len(test))
    return pd.Series(a + b * xs, index=test.index)

def ma3_forecast(train, test):
    return pd.Series([train.iloc[-3:].mean()] * len(test), index=test.index)

def ses_forecast_test(train, test, alpha=0.3):
    lvl = float(ses(train, alpha).iloc[-1])
    return pd.Series([lvl] * len(test), index=test.index)

comp = []
for 名称 in ["平台总体"] + top8:
    s = tot if 名称 == "平台总体" else monthly[monthly["品类"] == 名称].set_index("月份")["件数"].sort_index().reindex(
        pd.period_range(P0, P1, freq="M"), fill_value=0)
    tr, te = s.iloc[:-4], s.iloc[-4:]
    comp.append({"序列": 名称,
                 "SES_MAPE%": round(mape(te, ses_forecast_test(tr, te)), 1),
                 "线性回归_MAPE%": round(mape(te, linreg_forecast(tr, te)), 1),
                 "3期移动平均_MAPE%": round(mape(te, ma3_forecast(tr, te)), 1)})
comp_df = pd.DataFrame(comp)
comp_df.to_csv(os.path.join(DATA_DIR, "预测模型对照.csv"), index=False, encoding="utf-8-sig")
print()
print("=== 模块⑤ 品类销量趋势与预测 ===")
print(f"月度序列：{P0} ~ {P1}（{len(tot)} 个月），平台月均销量 {round(tot.mean()):,} 件")
print(f"平台总体 SES 回测 MAPE：{mape(tot.iloc[-4:], tot_test):.1f}%")
print(f"平台未来 3 个月预测（SES 常数外推）：{round(tot_pred.iloc[-1]):,} 件/月")
print()
print(pred_df.to_string(index=False))
print()
print("模型对照（同口径回测，MAPE 越低越好）：")
print(comp_df.to_string(index=False))
print(f"平均 MAPE — SES {comp_df['SES_MAPE%'].mean():.1f}% / 线性回归 {comp_df['线性回归_MAPE%'].mean():.1f}% / 3期移动平均 {comp_df['3期移动平均_MAPE%'].mean():.1f}%")
print()
print("说明：SES 为历史趋势外推；品类间预测差异来自各品类销量走势，不构成经营承诺")
print("结果表已输出：品类销量预测.csv、月度销量.csv、预测模型对照.csv")

# ---------------------------------------------------------------- 模块⑥ 差评文本主题归类
# 口径：评论文本去重音后关键词匹配（规则分类，不是 NLP 模型）；一个评论可命中多个主题；
# 统计的是"提及率"（该组订单中有多少比例提到该主题），差评/好评按订单平均分 ≤2 划分
import unicodedata

def norm(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()

KEYWORDS = {
    "物流配送": ["entrega", "atraso", "atrasou", "demorou", "demora", "prazo", "chegou", "correios", "transportadora", "frete", "rastreio", "nao chegou", "nao recebi", "entrega atrasada"],
    "商品质量": ["qualidade", "ruim", "pessimo", "quebrado", "quebrada", "defeito", "estragou", "fragil", "danificado", "parou de funcionar", "nao funciona", "material"],
    "描述/尺寸不符": ["tamanho", "pequeno", "pequena", "grande demais", "diferente", "foto", "anuncio", "descricao", "nao e como", "cor errada", "nao corresponde"],
    "包装破损": ["embalagem", "amassado", "arranhado", "riscado", "molhado", "rachado"],
    "售后/客服": ["atendimento", "vendedor", "troca", "devolucao", "reembolso", "estorno", "contato", "suporte", "cancel"],
}

rv = reviews.groupby("order_id")["review_comment_message"].apply(
    lambda s: " ".join(s.dropna().astype(str))).reset_index()
rv = rv.merge(review_avg, on="order_id", how="inner")
rv["文本norm"] = rv["review_comment_message"].apply(norm)
rv["差评"] = (rv["review_score"] <= 2).astype(int)

rows = []
for theme, kws in KEYWORDS.items():
    kws_n = [norm(k) for k in kws]
    hit = rv["文本norm"].apply(lambda t: any(k in t for k in kws_n))
    bad_hit = (hit & (rv["差评"] == 1)).sum()
    good_hit = (hit & (rv["差评"] == 0)).sum()
    bad_n = (rv["差评"] == 1).sum()
    good_n = (rv["差评"] == 0).sum()
    rows.append({"主题": theme, "差评提及数": int(bad_hit), "差评提及率%": round(bad_hit / bad_n * 100, 1),
                 "好评提及率%": round(good_hit / good_n * 100, 1),
                 "差评/好评倍率": round((bad_hit / bad_n) / (good_hit / good_n), 2)})

theme_df = pd.DataFrame(rows).sort_values("差评提及率%", ascending=False).reset_index(drop=True)
theme_df.to_csv(os.path.join(DATA_DIR, "差评主题.csv"), index=False, encoding="utf-8-sig")

print()
print("=== 模块⑥ 差评文本主题归类 ===")
print(f"有文本评论的评分订单：{len(rv):,} / 有评分订单 {len(review_avg):,}")
print(f"差评订单 {rv['差评'].sum():,}、好评订单 {(rv['差评'] == 0).sum():,}")
print()
print(theme_df.to_string(index=False))
print()

focus = d.merge(review_avg[["order_id", "review_score"]], on="order_id", how="left")
focus = focus[focus["review_score"].notna()]
bad_orders = set(rv[rv["差评"] == 1]["order_id"])
focus["订单差评"] = focus["order_id"].isin(bad_orders)
for 品类 in ["cama_mesa_banho", "moveis_decoracao", "moveis_escritorio", "beleza_saude"]:
    sub = focus[focus["品类"] == 品类]
    sub_bad = rv[rv["order_id"].isin(set(sub[sub["订单差评"]]["order_id"]))]
    sub_good = rv[rv["order_id"].isin(set(sub[~sub["订单差评"]]["order_id"]))]
    line = []
    for theme, kws in KEYWORDS.items():
        kws_n = [norm(k) for k in kws]
        br = sub_bad["文本norm"].apply(lambda t: any(k in t for k in kws_n)).mean() * 100
        gr = sub_good["文本norm"].apply(lambda t: any(k in t for k in kws_n)).mean() * 100
        line.append(f"{theme} 差评{br:.0f}%/好评{gr:.0f}%")
    print(f"[{品类}] 差评订单 {len(sub_bad):,}、好评订单 {len(sub_good):,}")
    print("   " + " | ".join(line))
print()
print("结果表已输出：差评主题.csv")

# ---------------------------------------------------------------- 模块⑦ 3C 品类竞争位
# 口径：电脑配件/手机/电子三个 3C 类目的价格分布、差评率与区域分布，与全平台对照
c3_names = ["informatica_acessorios", "telefonia", "eletronicos"]
c3 = d[d["品类"].isin(c3_names)].copy()
c3["大类"] = c3["品类"].map({
    "informatica_acessorios": "电脑配件", "telefonia": "手机", "eletronicos": "电子"})
c3_rows = []
for 大类 in ["电脑配件", "手机", "电子"]:
    s = c3[c3["大类"] == 大类]
    q = s["单价"].quantile([0.25, 0.5, 0.75]).round(1)
    top_state = s.groupby("customer_state")["order_id"].count().sort_values(ascending=False)
    s1 = top_state.iloc[0] / len(s) * 100 if len(s) else 0
    c3_rows.append({
        "3C类目": 大类, "件数": len(s),
        "P25元": q[0.25], "P50元": q[0.5], "P75元": q[0.75],
        "差评率%": round(s["是否差评"].mean() * 100, 2),
        "平均评分": round(s["评分"].mean(), 2),
        "最大区域": top_state.index[0], "最大区域占比%": round(s1, 1),
    })
c3_df = pd.DataFrame(c3_rows)
c3_df.to_csv(os.path.join(DATA_DIR, "3C品类竞争位.csv"), index=False, encoding="utf-8-sig")

print()
print("=== 模块⑦ 3C 品类竞争位（对照：全平台差评率 14.73%、P50 74.9 元）===")
print(c3_df.to_string(index=False))
print()
print("结果表已输出：3C品类竞争位.csv")

# ---------------------------------------------------------------- 模块⑧ 订单全链路漏斗
# 口径：用 4 个时间戳（下单/支付批准/交承运商/签收）做真实链路转化，不是看状态占比；
# 环节耗时只统计全链路完成的订单（4 个时间戳齐全）
all_orders = pd.read_csv(os.path.join(BASE, "olist_orders_dataset.csv"), encoding="utf-8-sig")
n_all = len(all_orders)
steps = [("下单", "order_purchase_timestamp"), ("支付批准", "order_approved_at"),
         ("交付承运商", "order_delivered_carrier_date"), ("买家签收", "order_delivered_customer_date")]
f_rows, prev = [], None
for label, col in steps:
    cnt = int(all_orders[col].notna().sum())
    f_rows.append({"环节": label, "订单数": cnt, "占下单%": round(cnt / n_all * 100, 2),
                   "本环节流失": (prev - cnt) if prev is not None else 0})
    prev = cnt
funnel = pd.DataFrame(f_rows)

ts4 = ["order_purchase_timestamp", "order_approved_at",
       "order_delivered_carrier_date", "order_delivered_customer_date"]
ok = all_orders.dropna(subset=ts4).copy()
for c in ts4:
    ok[c] = pd.to_datetime(ok[c])
stage_days = pd.DataFrame({
    "环节": ["下单→支付批准", "批准→交承运商", "交承运商→签收"],
    "平均天数": [round((ok["order_approved_at"] - ok["order_purchase_timestamp"]).dt.days.mean(), 1),
                 round((ok["order_delivered_carrier_date"] - ok["order_approved_at"]).dt.days.mean(), 1),
                 round((ok["order_delivered_customer_date"] - ok["order_delivered_carrier_date"]).dt.days.mean(), 1)],
})
funnel_out = pd.concat([funnel, pd.DataFrame([{"环节": "—— 环节平均耗时 ——", "订单数": None, "占下单%": None, "本环节流失": None}]), stage_days], ignore_index=True)
funnel_out.to_csv(os.path.join(DATA_DIR, "订单漏斗.csv"), index=False, encoding="utf-8-sig")

lost = all_orders[all_orders["order_delivered_customer_date"].isna()]["order_status"].value_counts()
print()
print("=== 模块⑧ 订单全链路漏斗 ===")
print(f"全部订单 {n_all:,} 单（含未签收）")
print(funnel.to_string(index=False))
print()
print("各环节平均耗时（全链路完成订单）:")
print(stage_days.to_string(index=False))
print()
print("未签收订单的状态分布:")
print(lost.to_string())
print()
print("结果表已输出：订单漏斗.csv")

# ---------------------------------------------------------------- 模块⑨ 用户复购与分层
# 口径：客户唯一标识用 customer_unique_id（一个客户可能多次下单、每次生成新 customer_id）；
# 复购 = 同一客户下单 ≥2 次；分层按订单数分为 一次性 / 2 次 / 3 次及以上
cu = pd.read_csv(os.path.join(BASE, "olist_customers_dataset.csv"), encoding="utf-8-sig")[["customer_id", "customer_unique_id"]]
oa = all_orders.merge(cu, on="customer_id", how="left")
oa["购买日期"] = pd.to_datetime(oa["order_purchase_timestamp"])
val = items.groupby("order_id")["price"].sum().rename("订单金额")
oa = oa.merge(val, on="order_id", how="left")
oa = oa.merge(review_avg.rename(columns={"review_score": "评分"}), on="order_id", how="left")

cust = oa.groupby("customer_unique_id").agg(
    订单数=("order_id", "nunique"),
    消费总额=("订单金额", "sum"),
    首次购买=("购买日期", "min"),
    末次购买=("购买日期", "max"),
).reset_index()
cust["层"] = pd.cut(cust["订单数"], bins=[0, 1, 2, 10 ** 9], labels=["一次性", "2 次", "3 次及以上"])
rep_rate = float((cust["订单数"] >= 2).mean() * 100)

layer = cust.groupby("层", observed=False).agg(
    客户数=("customer_unique_id", "count"),
    总消费=("消费总额", "sum"),
).reset_index()
layer["客户占比%"] = (layer["客户数"] / len(cust) * 100).round(1)
layer["消费占比%"] = (layer["总消费"] / cust["消费总额"].sum() * 100).round(1)
layer["人均消费"] = (layer["总消费"] / layer["客户数"]).round(2)

bad_by_cust = oa.groupby("customer_unique_id")["差评"].mean().rename("差评单占比")
cust = cust.merge(bad_by_cust, on="customer_unique_id", how="left")

layer = cust.groupby("层", observed=False).agg(
    客户数=("customer_unique_id", "count"),
    总消费=("消费总额", "sum"),
    平均差评单占比=("差评单占比", "mean"),
).reset_index()
layer["客户占比%"] = (layer["客户数"] / len(cust) * 100).round(1)
layer["消费占比%"] = (layer["总消费"] / cust["消费总额"].sum() * 100).round(1)
layer["人均消费"] = (layer["总消费"] / layer["客户数"]).round(2)
layer["平均差评单占比%"] = (layer["平均差评单占比"] * 100).round(2)
layer = layer[["层", "客户数", "客户占比%", "消费占比%", "人均消费", "平均差评单占比%"]]
layer.to_csv(os.path.join(DATA_DIR, "用户复购分层.csv"), index=False, encoding="utf-8-sig")

print()
print("=== 模块⑨ 用户复购与分层 ===")
print(f"独立客户数（customer_unique_id）{len(cust):,} | 复购率（下单 ≥2 次）{rep_rate:.2f}%")
print()
print(layer.to_string(index=False))
print()
span = (cust["末次购买"].max() - cust["首次购买"].min()).days
print(f"数据时间跨度 {span} 天（{cust['首次购买'].min().date()} ~ {cust['末次购买'].max().date()}）")
print("说明：复购窗口受数据口径限制（仅 22 个月），复购率是下界估计")
print()
print("结果表已输出：用户复购分层.csv")

# ---------------------------------------------------------------- 模块⑩ 品类 × 州：双占比与渗透指数
# 口径：底座与模块④一致（有评分 + 已签收的商品行，见 方法与口径.md 3.13）；不使用全商品行口径，
# 避免同一品类出现两套件数。两张占比互为校验：州占该品类%（行内合计 100%）与渗透指数（区位商）。
jc_state = j.groupby(["customer_state", "品类"]).agg(
    件数=("order_id", "count"),
    件均价=("单价", "mean"),
    差评率=("是否差评", "mean"),
).reset_index()
cat_sum = jc_state.groupby("品类")["件数"].sum().rename("品类全国件数")
state_sum = jc_state.groupby("customer_state")["件数"].sum().rename("州全国件数")
N_js = int(jc_state["件数"].sum())
jc_state = jc_state.merge(cat_sum, on="品类", how="left").merge(state_sum, on="customer_state", how="left")
jc_state["州占该品类%"] = (jc_state["件数"] / jc_state["品类全国件数"] * 100).round(2)
jc_state["州内品类结构%"] = (jc_state["件数"] / jc_state["州全国件数"] * 100).round(2)
jc_state["全国品类结构%"] = (jc_state["品类全国件数"] / N_js * 100).round(2)
jc_state["渗透指数"] = ((jc_state["件数"] / jc_state["州全国件数"]) / (jc_state["品类全国件数"] / N_js)).round(3)
jc_state["件均价"] = jc_state["件均价"].round(2)
jc_state["差评率%"] = (jc_state["差评率"] * 100).round(2)
main_cats = [c for c in cat_sum[cat_sum >= 1000].sort_values(ascending=False).index if c != "未分类"]
top_states = list(state_sum.sort_values(ascending=False).head(8).index)
jc_state["入主表"] = np.where(
    jc_state["customer_state"].isin(top_states) & jc_state["品类"].isin(main_cats), "是", "")
jc_state = jc_state[["customer_state", "品类", "件数", "件均价", "州占该品类%", "州内品类结构%",
                     "全国品类结构%", "渗透指数", "差评率%", "入主表"]]
jc_state = jc_state.sort_values(["customer_state", "件数"], ascending=[True, False]).reset_index(drop=True)
jc_state.to_csv(os.path.join(DATA_DIR, "区域品类.csv"), index=False, encoding="utf-8-sig")

main_tab = jc_state[jc_state["入主表"] == "是"]
print()
print("=== 模块⑩ 品类 × 州：双占比与渗透指数 ===")
print(f"统一底座件数 {N_js:,}（模块④口径：有评分 + 已签收）｜主表 = 前 8 州 × {len(main_cats)} 个主力品类 "
      f"= {len(main_tab)} 格，覆盖件数 {main_tab['件数'].sum() / N_js * 100:.1f}%")
print(f"全表 {len(jc_state)} 格｜格子件数中位数：主表 {int(main_tab['件数'].median())}、全表 {int(jc_state['件数'].median())}")
chk = jc_state.groupby("品类")["州占该品类%"].sum()
print(f"自检：州占该品类% 行内合计 = 100%（最大偏差 {abs(chk - 100).max():.2f} 个百分点）")
print()
print("渗透指数最高 6 格：")
print(main_tab.sort_values("渗透指数", ascending=False).head(6)[
    ["品类", "customer_state", "件数", "州占该品类%", "渗透指数", "差评率%"]].to_string(index=False))
print("渗透指数最低 6 格：")
print(main_tab.sort_values("渗透指数").head(6)[
    ["品类", "customer_state", "件数", "州占该品类%", "渗透指数", "差评率%"]].to_string(index=False))
print()
print("结果表已输出：区域品类.csv（统一底座 + 双占比 + 渗透指数）")

# ---------------------------------------------------------------- 模块⑪ 品类级产品痛点（主题二分 + 词 lift）
# 口径：主题沿用模块⑥ 的 5 类关键词规则匹配（不拆细），按性质二分——履约类（物流/售后/包装）、
# 产品类（质量/描述尺寸）；统计单位 = 有文本的差评订单；分母 <100 的格子留空，不填 0
oc = j[["order_id", "品类"]].drop_duplicates()
multi_cat = oc.groupby("order_id")["品类"].nunique()
hit = pd.DataFrame({"order_id": rv["order_id"], "是否差评": rv["差评"]})
for _t, _kws in KEYWORDS.items():
    _kn = [norm(k) for k in _kws]
    hit[_t] = rv["文本norm"].apply(lambda t: any(k in t for k in _kn))
hit["履约类"] = hit[["物流配送", "售后/客服", "包装破损"]].any(axis=1)
hit["产品类"] = hit[["商品质量", "描述/尺寸不符"]].any(axis=1)

# 扩展词典（敏感性检验用，不改模块⑥ 的既有平台级口径）：
# 抽检发现原词典是"高精准、低召回"，漏配集中在缺件、错发、仿品、材质四类，故补词重算
EXT = {
    "订单不完整": ["faltou", "faltando", "faltam", "incompleto", "recebi metade", "somente um",
                   "apenas um", "so veio", "veio somente", "vieram apenas", "recebi apenas",
                   "nao veio", "falta um", "dos dois", "dos tres"],
    "错发/规格不符": ["outro modelo", "veio outro", "mandaram outro", "enviaram outro", "produto errado",
                     "modelo errado", "cor errada", "tamanho errado", "veio errado", "era outro",
                     "veio diferente", "nao era o que", "gramsatura", "gramatura", "medidas"],
    "仿品/非原装": ["replica", "falso", "falsa", "paralelo", "falsificado", "nao e original",
                    "nao original", "nao aparentava"],
    "材质/做工": ["plastico", "acabamento", "aspero", "aspera", "costura", "muito leve", "material ruim",
                  "material fraco", "fino demais"],
}
for _t, _kws in EXT.items():
    _kn = [norm(k) for k in _kws]
    hit[_t] = rv["文本norm"].apply(lambda t: any(k in t for k in _kn))
hit["履约类_扩展"] = hit[["物流配送", "售后/客服", "包装破损", "订单不完整"]].any(axis=1)
hit["产品类_扩展"] = hit[["商品质量", "描述/尺寸不符", "错发/规格不符", "仿品/非原装", "材质/做工"]].any(axis=1)

THEMES = list(KEYWORDS.keys()) + ["履约类", "产品类"]
THEMES_EXT = list(KEYWORDS.keys()) + list(EXT.keys()) + [
    "履约类", "产品类", "履约类_扩展", "产品类_扩展"]
bad_hit = hit[hit["是否差评"] == 1].merge(oc, on="order_id", how="inner")

rows = []
for _c in main_cats:
    s = bad_hit[bad_hit["品类"] == _c]
    if len(s) == 0:
        continue
    r = {"品类": _c, "差评文本订单数": len(s)}
    for _t in THEMES_EXT:
        r[_t + "提及率%"] = round(s[_t].mean() * 100, 1) if len(s) >= 100 else None
    r["产品类/履约类"] = round(s["产品类"].mean() / s["履约类"].mean(), 2) if len(s) >= 100 else None
    r["产品类/履约类_扩展"] = round(
        s["产品类_扩展"].mean() / s["履约类_扩展"].mean(), 2) if len(s) >= 100 else None
    rows.append(r)
pain = pd.DataFrame(rows).sort_values("差评文本订单数", ascending=False).reset_index(drop=True)
pain.to_csv(os.path.join(DATA_DIR, "品类产品痛点.csv"), index=False, encoding="utf-8-sig")

_w = rv[rv["差评"] == 1][["order_id", "文本norm"]].copy()
_w["词"] = _w["文本norm"].str.split(r"[^a-z]+")
_w = _w.explode("词")
_w = _w[_w["词"].str.len() >= 4]
STOP_PT = {"para", "mais", "esta", "este", "isso", "pelo", "pela", "sobre", "depois", "antes",
           "entre", "cada", "outro", "outra", "porque", "pois", "entao", "apenas", "desde", "mesmo",
           "agora", "qual", "quais", "suas", "seus", "dele", "dela", "voce", "ele", "ela", "nos",
           "eles", "meu", "minha", "ainda", "quando", "todos", "tudo", "tambem", "muito", "produto",
           "compra", "loja", "pedido", "empresa", "site", "aplicativo", "coisa", "fazer", "fez",
           "vou", "vai", "veio", "ver", "gostei", "gostaria", "recomendo", "apenas", "excelente",
           "otimo", "otima", "bom", "boa", "perfeito", "satisfeito", "obrigado", "obrigada"}
_w = _w[~_w["词"].isin(STOP_PT)]
nat_n = _w["order_id"].nunique()
nat_word = _w.groupby("词")["order_id"].nunique().rename("全国提及订单数")
_wc = _w.merge(oc, on="order_id", how="inner")
_wc = _wc[_wc["品类"].isin(main_cats)]
cat_n = bad_hit.groupby("品类")["order_id"].nunique()
gw = _wc.groupby(["品类", "词"])["order_id"].nunique().rename("提及订单数").reset_index()
gw["该品类差评文本订单数"] = gw["品类"].map(cat_n)
gw = gw.merge(nat_word, on="词", how="left")
gw["lift"] = ((gw["提及订单数"] / gw["该品类差评文本订单数"]) / (gw["全国提及订单数"] / nat_n)).round(2)
gw["该品类提及率%"] = (gw["提及订单数"] / gw["该品类差评文本订单数"] * 100).round(1)
gw["全国提及率%"] = (gw["全国提及订单数"] / nat_n * 100).round(1)
gw = gw[gw["提及订单数"] >= 30].sort_values(["品类", "lift"], ascending=[True, False])
gw = gw[["品类", "词", "提及订单数", "该品类差评文本订单数", "该品类提及率%", "全国提及率%", "lift"]]
gw.to_csv(os.path.join(DATA_DIR, "品类差评特有词.csv"), index=False, encoding="utf-8-sig")

n_samp = min(120, bad_hit["order_id"].nunique())
samp = bad_hit.drop_duplicates("order_id")[["order_id", "品类"]].sample(n_samp, random_state=42)
samp = samp.merge(rv[["order_id", "review_comment_message"]], on="order_id", how="left")
samp = samp.merge(hit[["order_id"] + THEMES_EXT], on="order_id", how="left")
samp["规则命中主题"] = samp[THEMES].apply(lambda r: "|".join([t for t in THEMES if r[t]]), axis=1)
EXT_ONLY = list(KEYWORDS.keys()) + list(EXT.keys()) + ["履约类_扩展", "产品类_扩展"]
samp["规则命中主题_扩展"] = samp[EXT_ONLY].apply(
    lambda r: "|".join([t for t in EXT_ONLY if r[t]]), axis=1)
samp["人工/AI复核主题"] = ""
samp = samp[["order_id", "品类", "review_comment_message", "规则命中主题", "规则命中主题_扩展",
             "人工/AI复核主题"]]
samp_path = os.path.join(DATA_DIR, "文本标注抽检.csv")
if os.path.exists(samp_path):
    print("抽检样本表已存在：保留原表（含人工/AI 复核列），不覆盖")
else:
    samp.to_csv(samp_path, index=False, encoding="utf-8-sig")

print()
print("=== 模块⑪ 品类级产品痛点 ===")
print(f"跨品类订单 {(multi_cat > 1).sum():,} 单（占 {(multi_cat > 1).mean() * 100:.2f}%），其评价同时计入涉及的每个品类")
print(f"有文本的差评订单 {int((hit['是否差评'] == 1).sum()):,} 单 → 含品类归属 {len(bad_hit):,} 行")
print()
print(pain.to_string(index=False))
print()
bidx = hit["是否差评"] == 1
b_old = float(hit.loc[bidx, "产品类"].mean() * 100); b_ext = float(hit.loc[bidx, "产品类_扩展"].mean() * 100)
f_old = float(hit.loc[bidx, "履约类"].mean() * 100); f_ext = float(hit.loc[bidx, "履约类_扩展"].mean() * 100)
print(f"平台层（有文本的差评订单 {int(bidx.sum()):,} 单）：产品类提及率 原词典 {b_old:.1f}% → 扩展词典 "
      f"{b_ext:.1f}%（+{b_ext - b_old:.1f}pp）；履约类 {f_old:.1f}% → {f_ext:.1f}%（+{f_ext - f_old:.1f}pp）")
print(f"产品类/履约类 比值：{b_old / f_old:.2f} → {b_ext / f_ext:.2f}")
print()
cmp = pain.dropna(subset=["产品类_扩展提及率%"]).sort_values("产品类_扩展提及率%", ascending=False)
print("原词典 vs 扩展词典（产品类 / 履约类提及率 %）：")
print(cmp[["品类", "差评文本订单数", "产品类提及率%", "产品类_扩展提及率%",
           "履约类提及率%", "履约类_扩展提及率%", "产品类/履约类", "产品类/履约类_扩展"]].to_string(index=False))
print()
print("差评特有词（提及订单数 ≥30、lift 降序，每品类前 4）：")
for _c in main_cats:
    sub = gw[gw["品类"] == _c].head(4)
    if len(sub):
        print(f"  {_c}: " + " | ".join(
            f"{r['词']}({r['提及订单数']}单 lift{r['lift']})" for _, r in sub.iterrows()))
print()
print("抽检样本表：文本标注抽检.csv（120 条，人工/AI 复核列见该表）")
print("结果表已输出：品类产品痛点.csv、品类差评特有词.csv")

# ---------------------------------------------------------------- 模块⑫ 主力价格带与结构分解
# 口径：单价与到手价（单价 + 运费）都用商品行；州际均价差在"两州共同在售商品篮子"上分解为
# 价格效应（同一批商品的价差）与结构效应（同一批商品的销量权重差），两项之和恒等于篮子内均价差
pb = items[["order_id", "product_id", "price", "freight_value", "seller_id"]].merge(
    products[["product_id", "product_category_name"]], on="product_id", how="left").merge(
    orders_ok, on="order_id", how="inner")
pb["品类"] = pb["product_category_name"].fillna("未分类")
pb["到手价"] = pb["price"] + pb["freight_value"]
pm = pb[pb["品类"].isin(main_cats) & pb["customer_state"].isin(top_states)].copy()

band_rows = []
for _c in main_cats:
    s = pm[pm["品类"] == _c]
    for _st in top_states:
        x = s[s["customer_state"] == _st]
        if len(x) < 100:
            continue
        q = x["price"].quantile([0.25, 0.5, 0.75])
        qd = x["到手价"].quantile([0.25, 0.5, 0.75])
        band_rows.append({"品类": _c, "州": _st, "件数": len(x),
                          "单价P25": round(q[0.25], 1), "单价P50": round(q[0.5], 1), "单价P75": round(q[0.75], 1),
                          "到手价P25": round(qd[0.25], 1), "到手价P50": round(qd[0.5], 1),
                          "到手价P75": round(qd[0.75], 1), "件均运费": round(x["freight_value"].mean(), 2)})
band = pd.DataFrame(band_rows)
band.to_csv(os.path.join(DATA_DIR, "品类州价格带.csv"), index=False, encoding="utf-8-sig")

dec_rows = []
for _c in main_cats:
    s = pm[pm["品类"] == _c]
    sp = s[s["customer_state"] == "SP"]
    a = sp.groupby("product_id").agg(n=("price", "size"), p=("price", "mean"))
    for _st in [x for x in top_states if x != "SP"]:
        sj = s[s["customer_state"] == _st]
        b = sj.groupby("product_id").agg(n=("price", "size"), p=("price", "mean"))
        jj = a.join(b, lsuffix="_基准", rsuffix="_州", how="inner")
        if len(jj) == 0 or jj["n_基准"].sum() < 100 or jj["n_州"].sum() < 100:
            continue
        wb = jj["n_基准"] / jj["n_基准"].sum()
        wj = jj["n_州"] / jj["n_州"].sum()
        wm = (wb + wj) / 2
        pmm = (jj["p_基准"] + jj["p_州"]) / 2
        pe = float((wm * (jj["p_州"] - jj["p_基准"])).sum())
        se = float((pmm * (wj - wb)).sum())
        basket = float((wj * jj["p_州"]).sum() - (wb * jj["p_基准"]).sum())
        dec_rows.append({
            "品类": _c, "州": _st, "基准州": "SP",
            "全样本单价差(州−SP)": float(sj["price"].mean() - sp["price"].mean()),
            "篮子内单价差": basket, "价格效应": pe, "结构效应": se,
            "篮子覆盖%_基准": jj["n_基准"].sum() / len(sp) * 100,
            "篮子覆盖%_州": jj["n_州"].sum() / len(sj) * 100,
            "件均运费差(州−SP)": float(sj["freight_value"].mean() - sp["freight_value"].mean()),
            "到手价差(州−SP)": float(sj["到手价"].mean() - sp["到手价"].mean()),
        })

dec = pd.DataFrame(dec_rows)
dec["结构效应占比%"] = (dec["结构效应"] / dec["篮子内单价差"] * 100)
dec["分解校验差"] = dec["价格效应"] + dec["结构效应"] - dec["篮子内单价差"]
dec["到手价校验差"] = dec["到手价差(州−SP)"] - (dec["全样本单价差(州−SP)"] + dec["件均运费差(州−SP)"])
for _c2 in ["全样本单价差(州−SP)", "篮子内单价差", "价格效应", "结构效应",
            "件均运费差(州−SP)", "到手价差(州−SP)", "结构效应占比%"]:
    dec[_c2] = dec[_c2].round(2)
dec["篮子覆盖%_基准"] = dec["篮子覆盖%_基准"].round(1)
dec["篮子覆盖%_州"] = dec["篮子覆盖%_州"].round(1)
dec["分解校验差"] = dec["分解校验差"].round(6)
dec["到手价校验差"] = dec["到手价校验差"].round(6)
dec = dec.sort_values(["品类", "州"]).reset_index(drop=True)
dec.to_csv(os.path.join(DATA_DIR, "价格分解.csv"), index=False, encoding="utf-8-sig")

sku = pb.groupby("product_id").agg(州数=("customer_state", "nunique"), 卖家数=("seller_id", "nunique"),
                                   价种数=("price", "nunique"), 件数=("price", "size"))
sku5 = sku[sku["州数"] >= 5]
sku_sum = pd.DataFrame([
    {"指标": "覆盖 ≥5 个州的 SKU 数", "值": len(sku5)},
    {"指标": "价格只有单一取值的 SKU 占比%", "值": round((sku5["价种数"] == 1).mean() * 100, 1)},
    {"指标": "价格取值种数 P50", "值": int(sku5["价种数"].median())},
    {"指标": "价格取值种数 P90", "值": int(sku5["价种数"].quantile(0.9))},
    {"指标": "多卖家 SKU 占比%", "值": round((sku5["卖家数"] >= 2).mean() * 100, 1)},
    {"指标": "多卖家 SKU 价格种数 P50", "值": int(sku5[sku5["卖家数"] >= 2]["价种数"].median())},
    {"指标": "单卖家 SKU 价格种数 P50", "值": int(sku5[sku5["卖家数"] == 1]["价种数"].median())},
])
sku_sum.to_csv(os.path.join(DATA_DIR, "同SKU跨州定价.csv"), index=False, encoding="utf-8-sig")

print()
print("=== 模块⑫ 主力价格带与结构分解 ===")
print(f"价格样本：主力品类 × 前 8 州共 {len(pm):,} 件商品行（含运费）")
print(sku_sum.to_string(index=False))
print()
print("|结构效应| 最大 8 组（结构效应为正 = 该州买的是更贵的款式，不是同款更贵）：")
print(dec.reindex(dec["结构效应"].abs().sort_values(ascending=False).index).head(8)[
    ["品类", "州", "全样本单价差(州−SP)", "价格效应", "结构效应", "结构效应占比%",
     "件均运费差(州−SP)", "到手价差(州−SP)", "篮子覆盖%_州"]].to_string(index=False))
print()
print(f"分解校验：价格效应 + 结构效应 − 篮子内单价差 最大偏差 {dec['分解校验差'].abs().max():.2e} 元")
print(f"到手价校验：到手价差 −（单价差 + 运费差）最大偏差 {dec['到手价校验差'].abs().max():.2e} 元")
print(f"篮子覆盖率（州侧）中位数 {dec['篮子覆盖%_州'].median():.1f}%、最低 {dec['篮子覆盖%_州'].min():.1f}%")
print()
print("结果表已输出：品类州价格带.csv、价格分解.csv、同SKU跨州定价.csv")
