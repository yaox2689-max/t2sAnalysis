-- Olist E-Commerce Dataset Schema
-- https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
--
-- 8 tables: customers, sellers, orders, payments, order_items,
--          products, product_category, reviews
--
-- Naming: keeps original Olist column names (not simplified).
-- All foreign keys and indexes are defined inline.

SET FOREIGN_KEY_CHECKS = 0;

-- ── Drop (reverse dependency order) ────────────────────

DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS product_category;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS sellers;

SET FOREIGN_KEY_CHECKS = 1;

-- ── Create ─────────────────────────────────────────────

-- Table 1: customers
-- PK: customer_id
CREATE TABLE customers (
    customer_id              VARCHAR(64)   PRIMARY KEY,
    customer_unique_id       VARCHAR(64)   NOT NULL,
    customer_zip_code_prefix VARCHAR(16),
    customer_city            VARCHAR(64),
    customer_state           VARCHAR(4)
);

-- Table 2: sellers
-- PK: seller_id
CREATE TABLE sellers (
    seller_id              VARCHAR(64)   PRIMARY KEY,
    seller_zip_code_prefix VARCHAR(16),
    seller_city            VARCHAR(64),
    seller_state           VARCHAR(4)
);

-- Table 3: product_category (name translation)
-- PK: product_category_name
CREATE TABLE product_category (
    product_category_name          VARCHAR(128)   PRIMARY KEY,
    product_category_name_english  VARCHAR(128)
);

-- Table 4: products
-- PK: product_id
-- FK: product_category_name → product_category.product_category_name
CREATE TABLE products (
    product_id                  VARCHAR(64)   PRIMARY KEY,
    product_category_name       VARCHAR(128),
    product_name_length         INT,
    product_description_length  INT,
    product_photos_qty          INT,
    product_weight_g            DECIMAL(10, 2),
    product_length_cm           DECIMAL(10, 2),
    product_height_cm           DECIMAL(10, 2),
    product_width_cm            DECIMAL(10, 2),
    FOREIGN KEY (product_category_name)
        REFERENCES product_category(product_category_name)
);

-- Table 5: orders
-- PK: order_id
-- FK: customer_id → customers.customer_id
CREATE TABLE orders (
    order_id                        VARCHAR(64)   PRIMARY KEY,
    customer_id                     VARCHAR(64)   NOT NULL,
    order_status                    VARCHAR(32),
    order_purchase_timestamp        DATETIME,
    order_approved_at               DATETIME,
    order_delivered_carrier_date    DATETIME,
    order_delivered_customer_date   DATETIME,
    order_estimated_delivery_date   DATETIME,
    INDEX idx_orders_customer (customer_id),
    INDEX idx_orders_purchase (order_purchase_timestamp),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Table 6: payments
-- FK: order_id → orders.order_id
CREATE TABLE payments (
    id                   INT            AUTO_INCREMENT PRIMARY KEY,
    order_id             VARCHAR(64)    NOT NULL,
    payment_sequential   INT,
    payment_type         VARCHAR(32),
    payment_installments INT,
    payment_value        DECIMAL(12, 2),
    INDEX idx_payments_order (order_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- Table 7: order_items
-- PK: (order_id, order_item_id)  — composite, no auto_increment
-- FK: order_id   → orders.order_id
-- FK: product_id → products.product_id
-- FK: seller_id  → sellers.seller_id
CREATE TABLE order_items (
    order_id           VARCHAR(64)    NOT NULL,
    order_item_id      INT            NOT NULL,
    product_id         VARCHAR(64)    NOT NULL,
    seller_id          VARCHAR(64)    NOT NULL,
    shipping_limit_date DATETIME,
    price              DECIMAL(10, 2),
    freight_value      DECIMAL(10, 2),
    PRIMARY KEY (order_id, order_item_id),
    INDEX idx_items_product (product_id),
    INDEX idx_items_seller (seller_id),
    FOREIGN KEY (order_id)   REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (seller_id)  REFERENCES sellers(seller_id)
);

-- Table 8: reviews
-- PK: review_id (VARCHAR, as in original Olist)
-- FK: order_id → orders.order_id
CREATE TABLE reviews (
    review_id                VARCHAR(64)   PRIMARY KEY,
    order_id                 VARCHAR(64)   NOT NULL,
    review_score             INT,
    review_comment_title     TEXT,
    review_comment_message   TEXT,
    review_creation_date     DATETIME,
    review_answer_timestamp  DATETIME,
    INDEX idx_reviews_order (order_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);
