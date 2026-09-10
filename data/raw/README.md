# 原始数据放置说明

本目录存放 Olist 原始数据（体积较大，未随仓库分发，需自行下载）。

**下载地址**：https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

解压后把以下 9 个 CSV 直接放在**本目录**（`data/raw/`）下：

```
olist_orders_dataset.csv
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_customers_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
olist_geolocation_dataset.csv
product_category_name_translation.csv
```

放好后回到仓库根目录执行：

```bash
python logistics/analysis.py                  # 方向一：物流履约
python market/analysis.py && python market/charts.py   # 方向二：商品市场
```
