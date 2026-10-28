"""Step 0 of the system: turn the raw Olist CSVs into one clean table, one row per order item.

Run once with `python -m src.data_prep`. The output, data/processed/order_items.csv, is what
build_index.py embeds into Chroma. This is the only module that uses pandas heavily.
Column names follow docs/DATA_CONTRACT.md.
"""
from __future__ import annotations

import unicodedata

import pandas as pd

from src import config


def normalize_city(name: str) -> str:
    """Lowercase and strip accents, matching how Olist spells cities ("São Paulo" -> "sao paulo")."""
    text = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    return " ".join(text.lower().split())


def load_raw() -> dict:
    read = lambda name, **kw: pd.read_csv(config.RAW_DIR / name, **kw)
    return {
        "orders": read("olist_orders_dataset.csv"),
        "items": read("olist_order_items_dataset.csv"),
        "products": read("olist_products_dataset.csv"),
        "sellers": read("olist_sellers_dataset.csv"),
        "customers": read("olist_customers_dataset.csv"),
        # The translation file starts with a BOM; without utf-8-sig the join silently fails.
        "translation": read("product_category_name_translation.csv", encoding="utf-8-sig"),
    }


def select_orders(orders: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    """The 10,000 most recent orders that have items and were not cancelled or unavailable."""
    keep = orders[~orders["order_status"].isin(config.EXCLUDED_STATUSES)]
    keep = keep[keep["order_id"].isin(items["order_id"])]
    return keep.sort_values("order_purchase_timestamp").tail(config.SUBSET_SIZE)


def join_tables(raw: dict) -> pd.DataFrame:
    orders = select_orders(raw["orders"], raw["items"])
    df = raw["items"].merge(orders, on="order_id", how="inner")
    df = df.merge(raw["products"], on="product_id", how="inner")
    df = df.merge(raw["sellers"], on="seller_id", how="inner")
    df = df.merge(raw["customers"], on="customer_id", how="inner")
    return df.merge(raw["translation"], on="product_category_name", how="left")


def add_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Fill gaps and add the derived fields every agent relies on."""
    out = pd.DataFrame()
    out["id"] = df["order_id"] + "-" + df["order_item_id"].astype(str)
    for col in ["order_id", "order_item_id", "product_id", "seller_id", "customer_id", "order_status"]:
        out[col] = df[col]
    out["purchase_date"] = df["order_purchase_timestamp"].str[:10]
    out["promised_date"] = df["order_estimated_delivery_date"].str[:10]
    # With no disruption, the order arrives when it really did, or on the promise if not yet delivered.
    out["baseline_eta"] = df["order_delivered_customer_date"].str[:10].fillna(out["promised_date"])
    for side in ["seller", "customer"]:
        out[f"{side}_city"] = df[f"{side}_city"].map(normalize_city)
        out[f"{side}_state"] = df[f"{side}_state"].str.upper()
    out["category_pt"] = df["product_category_name"].fillna("unknown")
    out["category"] = df["product_category_name_english"].fillna(out["category_pt"])
    # Missing weight or size counts as 0, so the item is never wrongly marked bulky.
    out["weight_kg"] = (df["product_weight_g"] / 1000).fillna(0.0)
    volume = df["product_length_cm"] * df["product_height_cm"] * df["product_width_cm"] / 1000
    out["volume_l"] = volume.fillna(0.0)
    out["is_bulky"] = (out["weight_kg"] >= config.BULKY_KG) | (out["volume_l"] >= config.BULKY_L)
    out["is_time_sensitive"] = out["category"].isin(config.TIME_SENSITIVE_CATEGORIES)
    out["price"] = df["price"].astype(float)
    out["freight_value"] = df["freight_value"].astype(float)
    out["document"] = out.apply(build_document, axis=1)
    return out


def size_phrase(row) -> str:
    if row["is_bulky"]:
        return "Heavy, bulky item"
    if row["weight_kg"] >= 2 or row["volume_l"] >= 15:
        return "Medium-sized item"
    return "Small, light item"


def build_document(row) -> str:
    """The text that gets embedded. Written for meaning, since semantic search compares it."""
    title = row["category"].replace("_", " ").capitalize()
    return (
        f"{title} ({row['category_pt']}). {size_phrase(row)}: "
        f"{row['weight_kg']:.1f} kg, {row['volume_l']:.0f} L. "
        f"Ships from a seller in {row['seller_city']}, {row['seller_state']} "
        f"to a customer in {row['customer_city']}, {row['customer_state']}. "
        f"Price R$ {row['price']:.2f}, freight R$ {row['freight_value']:.2f}. "
        f"Promised delivery {row['promised_date']}."
    )


def print_summary(df: pd.DataFrame) -> None:
    late = (pd.to_datetime(df["baseline_eta"]) > pd.to_datetime(df["promised_date"])).mean()
    print(f"Rows (items):          {len(df):,}")
    print(f"Unique orders:         {df['order_id'].nunique():,}")
    print(f"Purchase dates:        {df['purchase_date'].min()} to {df['purchase_date'].max()}")
    print(f"Items from SP sellers: {(df['seller_state'] == 'SP').sum():,}")
    print(f"Bulky items:           {df['is_bulky'].sum():,} ({df['is_bulky'].mean():.1%})")
    print(f"Time-sensitive items:  {df['is_time_sensitive'].sum():,}")
    print(f"Already late (real):   {late:.1%}")
    print(f"Null cells:            {int(df.isna().sum().sum())}")


def main() -> None:
    df = add_fields(join_tables(load_raw()))
    config.PROCESSED_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.PROCESSED_CSV, index=False)
    print(f"Saved {config.PROCESSED_CSV.relative_to(config.ROOT)}")
    print_summary(df)


if __name__ == "__main__":
    main()
