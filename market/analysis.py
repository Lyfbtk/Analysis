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
