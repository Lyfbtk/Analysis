# -*- coding: utf-8 -*-
"""
Olist 经营指标补全（metrics 模块）
--------------------------------------------------------------------------
原有 logistics/ 与 market/ 两个方向做的是「履约诊断」与「商品市场归因」。
本模块补的是另四组从未计算过的经营指标：

  1. 规模与价格   GMV（含/不含运费）、订单数、客单价、件单价、连带率
  2. 支付结构     分期渗透率、分期期数分布、各支付方式金额占比
  3. 客户结构     复购率、回购间隔、cohort 留存矩阵、月度新客/回头客
  4. 卖家结构     卖家数、Top10 份额、HHI
  5. 口碑基线     评分分布、均分、1-2 星率

输出：out/*.csv + out/指标总表.csv
口径：见同目录 指标口径.md
"""
import os
import pandas as pd
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, '..', 'data', 'raw')
OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)

# 分析窗口：2016 年仅 329 单、2018-09 之后仅 20 单，均为数据不完整期，剔除
START, END = '2017-01-01', '2018-08-31'
INVALID = ('canceled', 'unavailable')   # 不计入 GMV 的状态


def load():
    o = pd.read_csv(f'{RAW}/olist_orders_dataset.csv')
    oi = pd.read_csv(f'{RAW}/olist_order_items_dataset.csv')
    p = pd.read_csv(f'{RAW}/olist_order_payments_dataset.csv')
    c = pd.read_csv(f'{RAW}/olist_customers_dataset.csv')
    r = pd.read_csv(f'{RAW}/olist_order_reviews_dataset.csv')
    s = pd.read_csv(f'{RAW}/olist_sellers_dataset.csv')
    return o, oi, p, c, r, s


def main():
    o, oi, p, c, r, s = load()

    # ---------- 0. 订单主表（窗口内） ----------
    o['ts'] = pd.to_datetime(o['order_purchase_timestamp'])
    o = o[(o['ts'] >= START) & (o['ts'] <= END)].copy()
    o['month'] = o['ts'].dt.to_period('M').astype(str)
    o['valid'] = ~o['order_status'].isin(INVALID)
    o = o.merge(c[['customer_id', 'customer_unique_id']], on='customer_id', how='left')

    # ---------- 1. 商品行聚合到订单级 ----------
    it = oi.groupby('order_id').agg(
        price=('price', 'sum'),
        freight=('freight_value', 'sum'),
        n_items=('order_item_id', 'size'),
    )
    od = o.merge(it, on='order_id', how='left').fillna({'price': 0, 'freight': 0, 'n_items': 0})
    ok = od[od['valid']].copy()
    ok['gmv_goods'] = ok['price']
    ok['gmv_all'] = ok['price'] + ok['freight']

    # ---------- 2. 支付：订单级 ----------
    pay = p.groupby('order_id').agg(
        pay_value=('payment_value', 'sum'),
        inst_max=('payment_installments', 'max'),
        n_pay_rows=('payment_value', 'size'),
    )
    # 主支付方式 = 该订单金额最大的一行（一单可能拆成 voucher + credit_card 两行）
    main_type = (p.sort_values('payment_value', ascending=False)
                   .drop_duplicates('order_id')[['order_id', 'payment_type']])
    pay = pay.merge(main_type, on='order_id', how='left')

    # ---------- 3. 评价：订单级 ----------
    rv = r.groupby('order_id')['review_score'].mean().rename('score').reset_index()

    od = od.merge(pay, on='order_id', how='left').merge(rv, on='order_id', how='left')
    ok = od[od['valid']].copy()
    ok['gmv_goods'] = ok['price']
    ok['gmv_all'] = ok['price'] + ok['freight']

    # ================= 指标 =================
    n_all = len(od)
    n_ok = len(ok)
    gmv_all, gmv_goods = ok['gmv_all'].sum(), ok['gmv_goods'].sum()
    n_items = ok['n_items'].sum()
    aov = gmv_all / n_ok
    unit_price = gmv_goods / n_items
    attach = n_items / n_ok
    cancel_rate = (od['order_status'] == 'canceled').mean()
    unavail_rate = (od['order_status'] == 'unavailable').mean()
    freight_rate_goods = ok['freight'].sum() / ok['price'].sum()
    freight_rate_gmv = ok['freight'].sum() / gmv_all
    free_ship_orders = (ok['freight'] == 0).mean()

    pk = ok[ok['inst_max'].notna()]
    installment_rate = (pk['inst_max'] > 1).mean()
    inst_dist = pk['inst_max'].value_counts(normalize=True).sort_index()

    # 支付结构：按订单数（主支付方式）与按金额（分摊）
    type_share_order = ok['payment_type'].value_counts(normalize=True)
    type_share_value = (p[p['order_id'].isin(ok['order_id'])]
                        .groupby('payment_type')['payment_value'].sum())
    type_share_value = type_share_value / type_share_value.sum()

    # 客户
    cust = ok[['customer_unique_id', 'order_id', 'ts', 'month']]
    per_cust = cust.groupby('customer_unique_id').agg(n=('order_id', 'size'),
                                                      first=('ts', 'min'), last=('ts', 'max'))
    repeat_rate = (per_cust['n'] > 1).mean()
    gap = (per_cust['last'] - per_cust['first']).dt.days
    # 同日拆单不是复购：末单-首单=0 天的"复购客户"占 29.4%，多是同一次消费被拆成两张单。
    # 含进去会把中位间隔从 71 天压到 34 天、"30 天内回来"从 30% 抬到 49%，必须剔除。
    n_repeat_true = int(((per_cust['n'] > 1) & (gap > 0)).sum())
    # 回购间隔用"相邻两单间隔"（池化），不用末单-首单：3 单以上客户用首末差会系统性高估单次间隔
    seq = cust.sort_values(['customer_unique_id', 'ts'])
    seq_gap = (seq['ts'] - seq.groupby('customer_unique_id')['ts'].shift(1)).dt.days
    gap_valid = seq_gap[(seq_gap > 0) & seq_gap.notna()]
    repeat_gap_median = gap_valid.median()
    repeat_gap_p25, repeat_gap_p75 = gap_valid.quantile([.25, .75])
    share_within_30 = (gap_valid <= 30).mean()

    # 卖家
    sv = oi.merge(s[['seller_id', 'seller_state']], on='seller_id', how='left')
    sv = sv[sv['order_id'].isin(ok['order_id'])]
    srev = sv.groupby('seller_id')['price'].sum().sort_values(ascending=False)
    share = srev / srev.sum()

    # 口碑
    score = ok['score'].dropna()
    low_share = (score <= 2).mean()

    # ================= 月度经营表 =================
    ok['month'] = ok['month']
    monthly = ok.groupby('month').agg(
        gmv_all=('gmv_all', 'sum'),
        gmv_goods=('gmv_goods', 'sum'),
        orders=('order_id', 'nunique'),
        items=('n_items', 'sum'),
        freight=('freight', 'sum'),
    ).reset_index()
    monthly['aov'] = monthly['gmv_all'] / monthly['orders']
    monthly['unit_price'] = monthly['gmv_goods'] / monthly['items']
    monthly['attach'] = monthly['items'] / monthly['orders']
    monthly['freight_rate'] = monthly['freight'] / monthly['gmv_goods']

    m_all = od.groupby('month').agg(orders_all=('order_id', 'nunique'),
                                    canceled=('order_status', lambda x: (x == 'canceled').sum())).reset_index()
    monthly = monthly.merge(m_all, on='month', how='left')
    monthly['cancel_rate'] = monthly['canceled'] / monthly['orders_all']

    inst_m = (od[od['valid']].dropna(subset=['inst_max'])
                .assign(inst_yes=lambda d: d['inst_max'] > 1)
                .groupby('month')['inst_yes'].mean().rename('installment_rate').reset_index())
    monthly = monthly.merge(inst_m, on='month', how='left')

    # 月度新客 / 回头客
    per_cust = per_cust.reset_index()
    per_cust['first_m'] = pd.to_datetime(per_cust['first']).dt.to_period('M').astype(str)
    cust_m = cust.merge(per_cust[['customer_unique_id', 'first_m']], on='customer_unique_id')
    cust_m['is_new'] = cust_m['month'] == cust_m['first_m']
    cm = (cust_m.groupby('month')
          .agg(customers=('customer_unique_id', 'nunique'),
               new_customers=('customer_unique_id', lambda s: s[cust_m.loc[s.index, 'is_new']].nunique()))
          .reset_index())
    monthly = monthly.merge(cm, on='month', how='left')
    monthly['repeat_customers'] = monthly['customers'] - monthly['new_customers']

    sc = ok.dropna(subset=['score']).groupby('month')['score'].mean().rename('avg_score').reset_index()
    monthly = monthly.merge(sc, on='month', how='left')
    monthly['avg_score'] = monthly['avg_score'].round(3)

    for col in ['gmv_all', 'gmv_goods', 'aov', 'unit_price', 'freight_rate', 'cancel_rate', 'installment_rate']:
        monthly[col] = monthly[col].round(4)

    # ================= cohort 留存 =================
    first = pd.to_datetime(per_cust['first']).dt.to_period('M')
    per_cust['cohort'] = first
    rows = []
    obs_end = pd.Period(END, freq='M')
    for ch, grp in cust.groupby(cust['customer_unique_id'].map(per_cust.set_index('customer_unique_id')['cohort'])):
        size = grp['customer_unique_id'].nunique()
        if size < 100:
            continue
        periods = (pd.to_datetime(grp['ts']).dt.to_period('M') - ch).apply(lambda x: x.n)
        max_k = (obs_end - ch).n
        for k in range(0, min(max_k, 12) + 1):
            active = grp.loc[periods == k, 'customer_unique_id'].nunique()
            rows.append({'cohort': str(ch), 'month_index': k, 'cohort_size': size,
                         'active': active, 'retention': round(active / size, 4)})
    cohort = pd.DataFrame(rows)

    # ---------- 输出 ----------
    monthly.to_csv(f'{OUT}/月度经营表.csv', index=False, encoding='utf-8-sig')
    cohort.pivot(index='cohort', columns='month_index', values='retention') \
          .to_csv(f'{OUT}/cohort_留存矩阵.csv', encoding='utf-8-sig')
    inst_dist.rename('share').to_frame().to_csv(f'{OUT}/分期期数分布.csv', encoding='utf-8-sig')
    pd.DataFrame({'支付方式': type_share_order.index,
                  '订单数占比': type_share_order.round(4).values,
                  '金额占比': [round(type_share_value.get(i, 0), 4) for i in type_share_order.index]}) \
        .to_csv(f'{OUT}/支付结构.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame({'seller_id': srev.head(50).index, 'revenue': srev.head(50).round(2).values,
                  'share': share.head(50).round(5).values}) \
        .to_csv(f'{OUT}/卖家Top50.csv', index=False, encoding='utf-8-sig')

    rows = [
        dict(指标='GMV（含运费）', 数值=round(gmv_all, 2), 单位='BRL', 口径='Σ(price+freight)，排除 canceled/unavailable', 分母='—'),
        dict(指标='GMV（商品额）', 数值=round(gmv_goods, 2), 单位='BRL', 口径='Σ(price)，同上', 分母='—'),
        dict(指标='有效订单数', 数值=int(n_ok), 单位='单', 口径='状态非 canceled/unavailable', 分母='—'),
        dict(指标='客单价 AOV', 数值=round(aov, 2), 单位='BRL/单', 口径='GMV含运费 ÷ 有效订单数', 分母='有效订单数'),
        dict(指标='件单价', 数值=round(unit_price, 2), 单位='BRL/件', 口径='商品额 ÷ 件数', 分母='件数'),
        dict(指标='连带率', 数值=round(attach, 3), 单位='件/单', 口径='件数 ÷ 有效订单数（单价订单占比 90.1%）', 分母='有效订单数'),
        dict(指标='取消率', 数值=round(cancel_rate, 4), 单位='比例', 口径='canceled ÷ 全部订单', 分母='全部订单'),
        dict(指标='不可用率', 数值=round(unavail_rate, 4), 单位='比例', 口径='unavailable ÷ 全部订单', 分母='全部订单'),
        dict(指标='运费率（占商品额）', 数值=round(freight_rate_goods, 4), 单位='比例', 口径='Σfreight ÷ Σprice（商品行级）', 分母='商品额'),
        dict(指标='免运费订单占比', 数值=round(free_ship_orders, 4), 单位='比例', 口径='订单运费合计=0 ÷ 有效订单', 分母='有效订单'),
        dict(指标='分期渗透率', 数值=round(installment_rate, 4), 单位='比例', 口径='订单级取最大期数>1 ÷ 有支付记录的订单', 分母='有支付记录订单'),
        dict(指标='复购率', 数值=round(repeat_rate, 4), 单位='比例', 口径='下单≥2次客户 ÷ 全部客户（customer_unique_id）', 分母='客户数'),
        dict(指标='客户数', 数值=int(per_cust.shape[0]), 单位='人', 口径='customer_unique_id 去重', 分母='—'),
        dict(指标='复购客户（剔除同日拆单）', 数值=n_repeat_true, 单位='人', 口径='末单-首单>0 天的复购客户；同日拆单多为同一次消费拆成两单', 分母='—'),
        dict(指标='回购间隔（中位）', 数值=round(repeat_gap_median, 1), 单位='天', 口径=f'相邻两单间隔（已剔除同日拆单），P25–P75 = {int(repeat_gap_p25)}–{int(repeat_gap_p75)} 天', 分母='复购客户的相邻订单对'),
        dict(指标='30 天内复购占比', 数值=round(share_within_30, 4), 单位='比例', 口径='相邻间隔≤30 天 ÷ 全部相邻间隔（已剔除同日拆单）', 分母='相邻订单对'),
        dict(指标='卖家数', 数值=int(len(srev)), 单位='家', 口径='有效订单中出现过的 seller', 分母='—'),
        dict(指标='Top10 卖家份额', 数值=round(share.head(10).sum(), 4), 单位='比例', 口径='前10卖家商品额 ÷ 全部商品额', 分母='商品额'),
        dict(指标='卖家 HHI', 数值=round((share ** 2).sum() * 10000, 1), 单位='点', 口径='Σ份额² ×10000', 分母='—'),
        dict(指标='平均评分', 数值=round(score.mean(), 3), 单位='分', 口径='订单级 mean(review_score)', 分母='有评分订单'),
        dict(指标='1-2 星占比', 数值=round(low_share, 4), 单位='比例', 口径='评分≤2 ÷ 有评分订单', 分母='有评分订单'),
    ]
    mt = pd.DataFrame(rows)
    mt.insert(0, '时间窗口', f'{START} ~ {END}（20 个完整月）')

    def _fmt(r):
        v, u = r['数值'], r['单位']
        if u == '比例':
            return f'{v * 100:.2f}%'
        if u in ('BRL', 'BRL/单', 'BRL/件'):
            return f'{v:,.2f}'
        if u == '分':
            return f'{v:.3f}'
        if u in ('单', '人', '家'):
            return f'{int(round(v)):,}'
        return f'{v:,.2f}'

    mt['显示值'] = mt.apply(_fmt, axis=1)
    mt = mt[['时间窗口', '指标', '显示值', '单位', '口径', '分母']]
    mt.to_csv(f'{OUT}/指标总表.csv', index=False, encoding='utf-8-sig')

    print(mt[['指标', '显示值', '单位']].to_string(index=False))
    print('\n输出目录:', OUT)
    print('月度表行数:', len(monthly), '| cohort 行数:', len(cohort))


if __name__ == '__main__':
    main()
