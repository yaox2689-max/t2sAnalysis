"""Seed synthetic Olist data for development.

Reads database credentials from environment variables (same as config.py).
Uses parameterized queries to avoid SQL injection.
"""

import os
import random
from datetime import datetime, timedelta

import pymysql
from dotenv import load_dotenv

load_dotenv()

conn = pymysql.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "3307")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "t2s_analysis"),
)
cur = conn.cursor()

for t in ["reviews", "order_items", "payments", "orders", "products", "customers", "sellers", "product_category"]:
    cur.execute(f"DELETE FROM `{t}`")

cur.execute(
    "INSERT INTO product_category (product_category_name, product_category_name_english) VALUES "
    "(%s, %s), (%s, %s), (%s, %s), (%s, %s), (%s, %s), (%s, %s)",
    ("eletronicos", "electronics", "moveis", "furniture", "roupas", "clothing",
     "alimentos", "food", "esportes", "sports", "livros", "books"),
)

cats = ["eletronicos", "eletronicos", "moveis", "roupas", "alimentos", "esportes", "livros", "eletronicos", "roupas", "moveis"]
for i in range(1, 11):
    cur.execute(
        "INSERT INTO products (product_id, product_category_name, product_name_length, "
        "product_description_length, product_photos_qty, product_weight_g, product_length_cm, "
        "product_height_cm, product_width_cm) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (f"PROD{i:03d}", cats[i - 1], 15, 200, 3,
         round(random.uniform(100, 5000), 2), round(random.uniform(10, 100), 2),
         round(random.uniform(5, 50), 2), round(random.uniform(10, 50), 2)),
    )

cities = ["sao paulo", "rio de janeiro", "belo horizonte", "salvador", "brasilia",
           "curitiba", "porto alegre", "recife", "fortaleza", "manaus",
           "santos", "niteroi", "uberlandia", "feira de santana", "goiania"]
states = ["SP", "RJ", "MG", "BA", "DF", "PR", "RS", "PE", "CE", "AM", "SP", "RJ", "MG", "BA", "GO"]
for i in range(1, 16):
    cur.execute(
        "INSERT INTO customers (customer_id, customer_unique_id, customer_zip_code_prefix, "
        "customer_city, customer_state) VALUES (%s, %s, %s, %s, %s)",
        (f"C{i:03d}", f"UNIQ{i:03d}", "01001", cities[i - 1], states[i - 1]),
    )

for i in range(1, 6):
    cur.execute(
        "INSERT INTO sellers (seller_id, seller_zip_code_prefix, seller_city, seller_state) "
        "VALUES (%s, %s, %s, %s)",
        (f"SELL{i:03d}", "01002", "sao paulo", "SP"),
    )

today = datetime.now()
oid = 1
for do in range(89, -1, -1):
    d = today - timedelta(days=do)
    for _ in range(random.randint(1, 8)):
        ts = d.strftime("%Y-%m-%d %H:%M:%S")
        cust_id = f"C{random.randint(1, 15):03d}"
        pay_type = random.choice(["credit_card", "boleto", "voucher", "debit_card"])
        cur.execute(
            "INSERT INTO orders (order_id, customer_id, order_status, "
            "order_purchase_timestamp, order_approved_at) VALUES (%s, %s, %s, %s, %s)",
            (f"ORD{oid:04d}", cust_id, "delivered", ts, ts),
        )
        cur.execute(
            "INSERT INTO payments (order_id, payment_sequential, payment_type, "
            "payment_installments, payment_value) VALUES (%s, %s, %s, %s, %s)",
            (f"ORD{oid:04d}", 1, pay_type, random.randint(1, 12), round(random.uniform(50, 500), 2)),
        )
        cur.execute(
            "INSERT INTO order_items (order_id, order_item_id, product_id, seller_id, "
            "shipping_limit_date, price, freight_value) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (f"ORD{oid:04d}", 1, f"PROD{random.randint(1, 10):03d}",
             f"SELL{random.randint(1, 5):03d}", ts,
             round(random.uniform(50, 500), 2), round(random.uniform(10, 50), 2)),
        )
        cur.execute(
            "INSERT INTO reviews (review_id, order_id, review_score, review_comment_message, "
            "review_creation_date, review_answer_timestamp) VALUES (%s, %s, %s, %s, %s, %s)",
            (f"REV{oid:04d}", f"ORD{oid:04d}", random.randint(1, 5), "auto", ts, ts),
        )
        oid += 1

conn.commit()
cur.close()
conn.close()
print(f"Inserted {oid - 1} orders")
