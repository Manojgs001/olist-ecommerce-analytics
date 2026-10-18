-- ============================================================
-- STEP 5: CREATE BI VIEWS (Star Schema Data Warehouse Layer)
-- Project: Olist Brazilian E-Commerce Analytics
-- Run this AFTER loading CSVs and creating indexes
-- ============================================================


-- ─────────────────────────────────────────────
-- VIEW 1: bi_dim_product
-- Dimension table: Products with English category names
-- ─────────────────────────────────────────────
CREATE OR REPLACE VIEW bi_dim_product AS
SELECT
    p.product_id,
    COALESCE(t.product_category_name_english, p.product_category_name) AS category,
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm,
    (p.product_length_cm * p.product_height_cm * p.product_width_cm) AS volume_cm3
FROM olist_products_dataset p
LEFT JOIN product_category_name_translation t
    ON t.product_category_name = p.product_category_name;


-- ─────────────────────────────────────────────
-- VIEW 2: bi_fact_review_latest
-- De-duplicated: one review per order (most recent)
-- ─────────────────────────────────────────────
CREATE OR REPLACE VIEW bi_fact_review_latest AS
SELECT DISTINCT ON (r.order_id)
    r.order_id,
    r.review_score,
    r.review_creation_date,
    r.review_answer_timestamp
FROM olist_order_reviews_dataset r
ORDER BY r.order_id, r.review_creation_date DESC NULLS LAST;


-- ─────────────────────────────────────────────
-- VIEW 3: bi_fact_order
-- Order-level facts: status, dates, delivery timing, customer info
-- ─────────────────────────────────────────────
CREATE OR REPLACE VIEW bi_fact_order AS
SELECT
    o.order_id,
    o.customer_id,
    o.order_status,
    o.order_purchase_timestamp::date   AS purchase_date,
    date_trunc('month', o.order_purchase_timestamp)::date AS purchase_month,
    o.order_delivered_customer_date::date   AS delivered_date,
    o.order_estimated_delivery_date::date   AS estimated_date,

    -- Delivery duration in days
    CASE
        WHEN o.order_status = 'delivered'
         AND o.order_delivered_customer_date IS NOT NULL
        THEN (o.order_delivered_customer_date::date - o.order_purchase_timestamp::date)
        ELSE NULL
    END AS delivery_days,

    -- Was delivery late? (1 = Late, 0 = On Time)
    CASE
        WHEN o.order_status = 'delivered'
         AND o.order_delivered_customer_date IS NOT NULL
         AND o.order_estimated_delivery_date IS NOT NULL
         AND o.order_delivered_customer_date::date > o.order_estimated_delivery_date::date
        THEN 1
        ELSE 0
    END AS is_late,

    c.customer_unique_id,
    c.customer_city,
    c.customer_state
FROM olist_orders_dataset o
JOIN olist_customers_dataset c ON c.customer_id = o.customer_id;


-- ─────────────────────────────────────────────
-- VIEW 4: bi_payments_order
-- Aggregated payment info per order (handles split payments)
-- ─────────────────────────────────────────────
CREATE OR REPLACE VIEW bi_payments_order AS
SELECT
    op.order_id,
    SUM(op.payment_value)                                                          AS order_payment_value,
    MAX(op.payment_installments)                                                   AS order_payment_installments,
    (ARRAY_AGG(op.payment_type ORDER BY op.payment_value DESC NULLS LAST))[1]     AS order_payment_type
FROM olist_order_payments_dataset op
GROUP BY op.order_id;


-- ─────────────────────────────────────────────
-- VIEW 5: bi_fact_sales  ⭐ THE MAIN FACT TABLE
-- Central view joining everything for Power BI
-- ─────────────────────────────────────────────
CREATE OR REPLACE VIEW bi_fact_sales AS
SELECT
    -- Order Item Details
    oi.order_id,
    oi.order_item_id,
    oi.product_id,
    oi.seller_id,
    oi.shipping_limit_date::date AS shipping_limit_date,
    oi.price,
    oi.freight_value,

    -- Order & Customer Info (from bi_fact_order)
    fo.customer_id,
    fo.customer_unique_id,
    fo.order_status,
    fo.purchase_date,
    fo.purchase_month,
    fo.delivered_date,
    fo.estimated_date,
    fo.delivery_days,
    fo.is_late,
    fo.customer_city,
    fo.customer_state,

    -- Product Category (from bi_dim_product)
    dp.category,

    -- Review Score (from bi_fact_review_latest)
    r.review_score,

    -- Payment Info (from olist_order_payments_dataset)
    p.payment_type,
    p.payment_installments,
    p.payment_value,

    -- Seller Location
    s.seller_city,
    s.seller_state

FROM olist_order_items_dataset oi
JOIN  bi_fact_order           fo ON fo.order_id  = oi.order_id
LEFT JOIN bi_dim_product      dp ON dp.product_id = oi.product_id
LEFT JOIN bi_fact_review_latest r ON r.order_id   = oi.order_id
LEFT JOIN olist_order_payments_dataset p ON p.order_id = oi.order_id
LEFT JOIN olist_sellers_dataset        s ON s.seller_id = oi.seller_id;


-- ✅ Verify all views are working
SELECT COUNT(*) AS total_rows, 'bi_fact_sales' AS view_name FROM bi_fact_sales;
