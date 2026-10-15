-- Step 1: one pre-joined (denormalized) table at sale grain - same 10M rows, no joins at query time
CREATE OR REPLACE TABLE ${catalog}.${schema}.wide_sales AS
SELECT
  d.sale_id, d.week_id, w.week_idx, w.week_start, w.fiscal_week, w.fiscal_year, w.fiscal_quarter, w.fiscal_month,
  c.country_code, c.country_name, c.country_group,
  b.brand_name,
  d.product_id, r.product_name, r.product_type, r.new_or_repeat, r.category,
  ps.pack_size,
  d.customer_id, cu.loyalty_group,
  d.is_flagged, d.rating_scale_used, d.rating_value, d.units_sold
FROM ${catalog}.${schema}.fact_sales d
JOIN ${catalog}.${schema}.dim_week w      ON d.week_id = w.week_id
JOIN ${catalog}.${schema}.dim_country c   ON d.country_id = c.country_id
JOIN ${catalog}.${schema}.dim_brand b     ON d.brand_id = b.brand_id
JOIN ${catalog}.${schema}.dim_product r    ON d.product_id = r.product_id
JOIN ${catalog}.${schema}.dim_pack_size ps ON d.pack_size_id = ps.pack_size_id
JOIN ${catalog}.${schema}.dim_customer cu ON d.customer_id = cu.customer_id;

-- Step 3: materialized grain = product x country x brand x week x flag (~0.77M rows, ~13x smaller).
-- Pack size / loyalty group are customer-level attributes and are NOT in this grain -> queries that
-- filter or split by them fall back to the detail table.
CREATE OR REPLACE MATERIALIZED VIEW ${catalog}.${schema}.agg_product_country_week AS
SELECT
  week_id, week_idx, fiscal_week, fiscal_year, fiscal_quarter, fiscal_month,
  country_code, country_group, brand_name,
  product_id, product_type, new_or_repeat,
  is_flagged,
  COUNT(*)                         AS sold,
  COUNT(rating_value)              AS n_ratings,
  COUNT_IF(rating_value = 1)       AS n1,
  COUNT_IF(rating_value = 2)       AS n2,
  SUM(CASE WHEN rating_scale_used = '4-star' THEN 1 + (rating_value - 1) * 4.0 / 3 ELSE rating_value END) AS sum_score_5,
  SUM(CASE WHEN rating_scale_used = '5-star' THEN 1 + (rating_value - 1) * 0.75 ELSE rating_value END)    AS sum_score_4
FROM ${catalog}.${schema}.wide_sales
GROUP BY ALL;
