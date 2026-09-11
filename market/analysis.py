import os
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

region_cat = d_all.groupby(["customer_state", "品类"]).agg(
    件数=("order_id", "count"),
    件均价=("单价", "mean"),
).reset_index()
region_cat["件均价"] = region_cat["件均价"].round(2)
region_cat = region_cat.sort_values(["customer_state", "件数"], ascending=False).reset_index(drop=True)
region_cat.to_csv(os.path.join(DATA_DIR, "区域品类.csv"), index=False, encoding="utf-8-sig")

print("=== 模块③ 区域画像 Top 10 ===")
print(region.head(10).to_string(index=False))
print("州数:", len(region), "| 州×品类组合数:", len(region_cat))
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
