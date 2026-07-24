"""Generate seed CSV files for DuckDB demo data.

Run once: python backend/scripts/generate_seed_csv.py
"""

import csv
import os
import random
from datetime import datetime, timedelta

SEED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed")
os.makedirs(SEED_DIR, exist_ok=True)


def write_csv(name: str, headers: list[str], rows: list[list]) -> None:
    path = os.path.join(SEED_DIR, f"{name}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)
    print(f"  OK {name}.csv ({len(rows)} rows)")


def main():
    # product_category
    write_csv("product_category",
        ["product_category_name", "product_category_name_english"],
        [["eletronicos", "electronics"], ["moveis", "furniture"], ["roupas", "clothing"],
         ["alimentos", "food"], ["esportes", "sports"], ["livros", "books"]])

    # products
    cats = ["eletronicos", "eletronicos", "moveis", "roupas", "alimentos",
            "esportes", "livros", "eletronicos", "roupas", "moveis"]
    products = []
    for i in range(1, 11):
        products.append([f"PROD{i:03d}", cats[i-1], 15, 200, 3,
                         round(random.uniform(100, 5000), 2), round(random.uniform(10, 100), 2),
                         round(random.uniform(5, 50), 2), round(random.uniform(10, 50), 2)])
    write_csv("products",
        ["product_id", "product_category_name", "product_name_length",
         "product_description_length", "product_photos_qty", "product_weight_g",
         "product_length_cm", "product_height_cm", "product_width_cm"], products)

    # customers
    cities = ["sao paulo", "rio de janeiro", "belo horizonte", "salvador", "brasilia",
              "curitiba", "porto alegre", "recife", "fortaleza", "manaus",
              "santos", "niteroi", "uberlandia", "feira de santana", "goiania"]
    states = ["SP", "RJ", "MG", "BA", "DF", "PR", "RS", "PE", "CE", "AM", "SP", "RJ", "MG", "BA", "GO"]
    customers = []
    for i in range(1, 16):
        customers.append([f"C{i:03d}", f"UNIQ{i:03d}", "01001", cities[i-1], states[i-1]])
    write_csv("customers",
        ["customer_id", "customer_unique_id", "customer_zip_code_prefix",
         "customer_city", "customer_state"], customers)

    # sellers
    sellers = []
    for i in range(1, 6):
        sellers.append([f"SELL{i:03d}", "01002", "sao paulo", "SP"])
    write_csv("sellers",
        ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"], sellers)

    # orders + payments + order_items + reviews
    today = datetime.now()
    orders, payments, items, reviews = [], [], [], []
    oid = 1
    for do in range(89, -1, -1):
        d = today - timedelta(days=do)
        for _ in range(random.randint(1, 8)):
            ts = d.strftime("%Y-%m-%d %H:%M:%S")
            cid = f"C{random.randint(1, 15):03d}"
            orders.append([f"ORD{oid:04d}", cid, "delivered", ts, ts])
            payments.append([f"ORD{oid:04d}", 1,
                             random.choice(["credit_card", "boleto", "voucher", "debit_card"]),
                             random.randint(1, 12), round(random.uniform(50, 500), 2)])
            items.append([f"ORD{oid:04d}", 1, f"PROD{random.randint(1, 10):03d}",
                          f"SELL{random.randint(1, 5):03d}", ts,
                          round(random.uniform(50, 500), 2), round(random.uniform(10, 50), 2)])
            reviews.append([f"REV{oid:04d}", f"ORD{oid:04d}", random.randint(1, 5),
                            "auto", ts, ts])
            oid += 1

    write_csv("orders",
        ["order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_approved_at"],
        orders)
    write_csv("payments",
        ["order_id", "payment_sequential", "payment_type", "payment_installments", "payment_value"],
        payments)
    write_csv("order_items",
        ["order_id", "order_item_id", "product_id", "seller_id",
         "shipping_limit_date", "price", "freight_value"], items)
    write_csv("reviews",
        ["review_id", "order_id", "review_score", "review_comment_message",
         "review_creation_date", "review_answer_timestamp"], reviews)

    print(f"\nAll seed CSVs generated in {SEED_DIR}")


if __name__ == "__main__":
    main()
