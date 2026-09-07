import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import os

# 数据目录：相对路径（仓库 clone 后，数据放入 data/raw/ 即可运行）
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
base = os.path.join(data_dir, "raw")
orders  = pd.read_csv(f"{base}/olist_orders_dataset.csv")
reviews = pd.read_csv(f"{base}/olist_order_reviews_dataset.csv")
customers= pd.read_csv(f"{base}/olist_customers_dataset.csv")
items= pd.read_csv(f"{base}/olist_order_items_dataset.csv")
sellers=pd.read_csv(f"{base}/olist_sellers_dataset.csv")
geolocation=pd.read_csv(f"{base}/olist_geolocation_dataset.csv")

orders = orders[orders["order_status"] == "delivered"]

orders["购买日期"] = pd.to_datetime(orders["order_purchase_timestamp"])
orders["签收日期"] = pd.to_datetime(orders["order_delivered_customer_date"])
orders["预估日期"] = pd.to_datetime(orders["order_estimated_delivery_date"])
a=orders["签收日期"] - orders["购买日期"]
b=orders["预估日期"] - orders["购买日期"]
c=a-b
orders["配送天数"] = a.dt.days
orders["承诺天数"] = b.dt.days
orders["延迟天数"] = c.dt.days

review_avg = reviews.groupby("order_id")["review_score"].mean().reset_index()
df = orders.merge(review_avg, on="order_id", how="left")

df = df[["order_id", "配送天数", "承诺天数", "延迟天数", "review_score"]]
df = df.dropna(subset=["review_score", "配送天数", "延迟天数"])
df["差评"] = (df["review_score"] <= 2).astype(int)

X = df[[ "承诺天数", "延迟天数"]]
Y = df["差评"]

model = RandomForestClassifier(random_state=42)
model.fit(X, Y)
for 特征, 重要性 in zip(X.columns, model.feature_importances_):
    print(f"{特征}: {重要性:.3f}")

geolocation = geolocation.groupby("geolocation_zip_code_prefix")[["geolocation_lat","geolocation_lng"]].mean().reset_index()
items1 = items.groupby("order_id")["seller_id"].nunique().reset_index()
items1 = items1.rename(columns={"seller_id":"卖家数"})
items1 = items1[items1["卖家数"]==1]
items1 = items1.merge(items[['order_id','seller_id']], on="order_id", how="left")
items1 = items1.drop_duplicates(subset="order_id")
items1 = items1.merge(orders[['order_id','customer_id']], on="order_id", how="left")
items1 = items1.merge(customers[['customer_id','customer_state',"customer_zip_code_prefix"]], on="customer_id", how="left")
items1 = items1.dropna(subset=["customer_id"])
items1 = items1.merge(sellers[['seller_id','seller_state',"seller_zip_code_prefix"]], on="seller_id", how="left")
items1["地点组"] = items1["seller_state"] + items1["customer_state"]
items1 = items1.merge(orders[['order_id','配送天数','承诺天数','延迟天数']], on="order_id", how="left")
items1 = items1.dropna(subset=["配送天数"])
items1['是否延迟'] = (items1["延迟天数"] > 0).astype(int)
items1 = items1.merge(geolocation[["geolocation_zip_code_prefix","geolocation_lat","geolocation_lng"]], left_on="seller_zip_code_prefix",right_on="geolocation_zip_code_prefix",how="left")
items1 = items1.rename(columns={"geolocation_lng":"卖家经度","geolocation_lat":"卖家纬度"})
items1 = items1.merge(geolocation[["geolocation_zip_code_prefix","geolocation_lat","geolocation_lng"]], left_on="customer_zip_code_prefix",right_on="geolocation_zip_code_prefix",how="left")
items1 = items1.rename(columns={"geolocation_lng":"买家经度","geolocation_lat":"买家纬度"})
items1 = items1.dropna(subset=["买家纬度","卖家纬度","买家经度","卖家经度"])
items1 = items1.drop(columns=["geolocation_zip_code_prefix_x","geolocation_zip_code_prefix_y"])

R = 6371
def haversine(lat1, lng1, lat2, lng2):
    lat1, lng1, lat2, lng2 = map(np.radians, [lat1, lng1, lat2, lng2])
    a = np.sin((lat2-lat1)/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin((lng2-lng1)/2)**2
    return R * 2 * np.arcsin(np.sqrt(a))

items1["距离km"] = haversine(items1["卖家纬度"], items1["卖家经度"],items1["买家纬度"], items1["买家经度"])
items1["距离档"] = pd.cut(items1["距离km"], bins=[0,200,500,1000,2000,99999],labels=["0-200","200-500","500-1000","1000-2000","2000+"])
items1["是否跨州"] = (items1["seller_state"] != items1["customer_state"])
items1 = items1.dropna(subset=["距离档"])

route = items1.groupby("地点组").agg(
    订单数=("order_id","count"),
    中位距离=("距离km","median"),
    配送P50=("配送天数","median"),
    配送P90=("配送天数", lambda x: x.quantile(0.9)),
    配送P95=("配送天数", lambda x: x.quantile(0.95)),
    最短安全承诺=("配送天数", lambda x: int(x.quantile(0.9334)) + 1),
    现状延迟率=("是否延迟",lambda x: x.mean()*100 ),
    承诺后延迟率=("配送天数", lambda x: (x > (int(x.quantile(0.9334)) + 1)).mean()*100),
).reset_index()

route["距离档"] = pd.cut(
    route["中位距离"],          # ① 要切的列
    bins=[0,200,500,1000,2000,99999],   # ② 切分点(区间边界)
    labels=["0-200","200-500","500-1000","1000-2000","2000+"]   # ③ 每段的名字
)

route_1 = items1.groupby("距离档").agg(
    订单数=("order_id","count"),
    基准延迟率=("是否延迟", lambda x: x.mean()*100)).reset_index()

route_2 = items1.groupby("是否跨州").agg(
    订单数=("order_id","count"),
    延迟率=("是否延迟", lambda x: x.mean()*100)).round(2).reset_index()
route_2["是否跨州"] = route_2["是否跨州"].map({False:"州内", True:"跨州"})

route = route.merge(route_1[["距离档","基准延迟率"]],on="距离档",how="left")
route["该订单延迟率-该档位平均延迟率"] = route["现状延迟率"]-route["基准延迟率"]
route["延迟率是否不正常"] = (route["该订单延迟率-该档位平均延迟率"] >1).map({True:"不正常", False:"正常"})
route["超额延迟贡献"] = (route["订单数"] * route["该订单延迟率-该档位平均延迟率"]).round(0)
route_final = route[route["订单数"] >= 300]
route_final = route_final.sort_values("超额延迟贡献", ascending=False)
route_final.to_csv(os.path.join(data_dir, "分线路统计.csv"), index=False, encoding="utf-8-sig", )

route_1.to_csv(os.path.join(data_dir, "距离档.csv"), index=False, encoding="utf-8-sig")
route_2.to_csv(os.path.join(data_dir, "州内跨州.csv"), index=False, encoding="utf-8-sig")
