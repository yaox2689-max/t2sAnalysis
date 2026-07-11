# Olist Dataset Initialization

## Entity-Relationship

```
customers
     │
     ▼
orders ──────────────────────┐
     │                        │
     ▼                        ▼
order_items               payments
     │
     ├──────────► products ────► product_category
     │
     └──────────► sellers
orders ──────────────────────► reviews
```

## Schema

### customers

| Column | Type | Constraints |
|--------|------|-------------|
| customer_id | VARCHAR(64) | **PK** |
| customer_unique_id | VARCHAR(64) | NOT NULL |
| customer_zip_code_prefix | VARCHAR(16) | |
| customer_city | VARCHAR(64) | |
| customer_state | VARCHAR(4) | |

### sellers

| Column | Type | Constraints |
|--------|------|-------------|
| seller_id | VARCHAR(64) | **PK** |
| seller_zip_code_prefix | VARCHAR(16) | |
| seller_city | VARCHAR(64) | |
| seller_state | VARCHAR(4) | |

### product_category

| Column | Type | Constraints |
|--------|------|-------------|
| product_category_name | VARCHAR(128) | **PK** |
| product_category_name_english | VARCHAR(128) | |

### products

| Column | Type | Constraints |
|--------|------|-------------|
| product_id | VARCHAR(64) | **PK** |
| product_category_name | VARCHAR(128) | FK → product_category |
| product_name_length | INT | |
| product_description_length | INT | |
| product_photos_qty | INT | |
| product_weight_g | DECIMAL(10,2) | |
| product_length_cm | DECIMAL(10,2) | |
| product_height_cm | DECIMAL(10,2) | |
| product_width_cm | DECIMAL(10,2) | |

### orders

| Column | Type | Constraints |
|--------|------|-------------|
| order_id | VARCHAR(64) | **PK** |
| customer_id | VARCHAR(64) | NOT NULL, FK → customers |
| order_status | VARCHAR(32) | |
| order_purchase_timestamp | DATETIME | |
| order_approved_at | DATETIME | |
| order_delivered_carrier_date | DATETIME | |
| order_delivered_customer_date | DATETIME | |
| order_estimated_delivery_date | DATETIME | |

### payments

| Column | Type | Constraints |
|--------|------|-------------|
| id | INT | **PK** (auto_increment) |
| order_id | VARCHAR(64) | NOT NULL, FK → orders |
| payment_sequential | INT | |
| payment_type | VARCHAR(32) | |
| payment_installments | INT | |
| payment_value | DECIMAL(12,2) | |

### order_items

| Column | Type | Constraints |
|--------|------|-------------|
| order_id | VARCHAR(64) | NOT NULL, **PK** (composite), FK → orders |
| order_item_id | INT | NOT NULL, **PK** (composite) |
| product_id | VARCHAR(64) | NOT NULL, FK → products |
| seller_id | VARCHAR(64) | NOT NULL, FK → sellers |
| shipping_limit_date | DATETIME | |
| price | DECIMAL(10,2) | |
| freight_value | DECIMAL(10,2) | |

### reviews

| Column | Type | Constraints |
|--------|------|-------------|
| review_id | VARCHAR(64) | **PK** |
| order_id | VARCHAR(64) | NOT NULL, FK → orders |
| review_score | INT | |
| review_comment_title | TEXT | |
| review_comment_message | TEXT | |
| review_creation_date | DATETIME | |
| review_answer_timestamp | DATETIME | |

## Prerequisites

Download the Olist Brazilian E-Commerce dataset from Kaggle:

https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

## Setup

1. Download the dataset (CSV files) from Kaggle
2. Extract the archive
3. Copy all CSV files into `backend/scripts/olist_data/`

Expected files:

```
backend/scripts/olist_data/
├── olist_customers_dataset.csv
├── olist_sellers_dataset.csv
├── olist_orders_dataset.csv
├── olist_order_payments_dataset.csv
├── olist_order_items_dataset.csv
├── olist_order_reviews_dataset.csv
├── olist_products_dataset.csv
└── product_category_name_translation.csv
```

## Run

```bash
cd backend/scripts

# Set your database credentials
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=your_password
export DB_NAME=t2s_analysis

python init_db.py
```

The script is idempotent: running it multiple times produces the same result.

## Verify

```sql
USE t2s_analysis;
SELECT COUNT(*) FROM orders;
SELECT COUNT(*) FROM customers;
```
