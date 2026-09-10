WITH 
 订单表 AS (
    SELECT order_id,
           order_delivered_customer_date::date - order_purchase_timestamp::date AS 配送天数,
           order_estimated_delivery_date::date - order_purchase_timestamp::date AS 承诺天数,
           (order_delivered_customer_date::date - order_purchase_timestamp::date) -
           (order_estimated_delivery_date::date - order_purchase_timestamp::date) AS 延迟天数
    FROM orders
    WHERE order_status='delivered'
),
平均表 AS  (
    SELECT avg(配送天数) AS 平均配送,
           avg(承诺天数) AS 平均承诺,
           COUNT(*) FILTER (WHERE 延迟天数 > 0) * 100.0 / COUNT(*) AS 延迟率
    FROM 订单表
),
均分表 AS (
        SELECT
		    order_id,
            avg(review_score) AS 平均评分
            FROM reviews
            GROUP BY order_id
),
总表 AS (
    SELECT 订单表.order_id,
           平均评分,
           配送天数,
           承诺天数,
           配送天数 - 承诺天数 AS 延迟天数,	
		   CASE WHEN 延迟天数 > 0 THEN '延迟' ELSE '未延迟' END AS 是否延迟
    FROM 订单表
        订单表 left join 均分表 ON 订单表.order_id = 均分表.order_id
)

select 
     是否延迟,
     count(order_id) FILTER( WHERE 平均评分<=2 )AS 差评数,
	 count(order_id) FILTER( WHERE 平均评分<=2 )*100/count(order_id)||'%'AS 差评率
FROM 总表
WHERE 平均评分 IS NOT NULL
GROUP BY 是否延迟