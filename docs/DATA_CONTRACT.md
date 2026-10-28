# Data contract

This is the single source of truth for column names and types. `data_prep.py` writes these columns,
`build_index.py` stores them, the agents read them, and the tests check them.
If you need to change a name, change it here first and then everywhere else.

## Subset rule

1. Load the orders table and drop orders with status `canceled` or `unavailable`.
2. Keep only orders that have at least one row in the order items table.
3. Sort by `order_purchase_timestamp` and keep the last 10,000.
4. Inner join the items with orders, products, sellers and customers. Left join the category translation.

Result: 11,301 rows, one per order item, and 10,000 unique orders. The file is committed, so reviewers
do not need the raw Kaggle CSVs.

## Processed CSV: `data/processed/order_items.csv`

| Column | Type | How it is built |
|---|---|---|
| `id` | str | `f"{order_id}-{order_item_id}"`, unique, used as the Chroma id |
| `order_id` | str | from orders |
| `order_item_id` | int | from order items |
| `product_id` | str | from order items |
| `seller_id` | str | from order items |
| `customer_id` | str | from orders |
| `order_status` | str | from orders |
| `purchase_date` | str (YYYY-MM-DD) | date part of `order_purchase_timestamp` |
| `promised_date` | str (YYYY-MM-DD) | date part of `order_estimated_delivery_date` |
| `baseline_eta` | str (YYYY-MM-DD) | date part of `order_delivered_customer_date`, or `promised_date` if missing |
| `seller_city` | str | lowercase, accents removed |
| `seller_state` | str | 2-letter code, uppercase |
| `customer_city` | str | lowercase, accents removed |
| `customer_state` | str | 2-letter code, uppercase |
| `category` | str | English name. Falls back to the Portuguese name, then to `unknown` |
| `category_pt` | str | Portuguese name, or `unknown` |
| `weight_kg` | float | `product_weight_g / 1000`, 0.0 if missing |
| `volume_l` | float | `length_cm * height_cm * width_cm / 1000`, 0.0 if missing |
| `is_bulky` | bool | `weight_kg >= BULKY_KG or volume_l >= BULKY_L`, from config |
| `is_time_sensitive` | bool | `category in TIME_SENSITIVE_CATEGORIES`, from config |
| `price` | float | from order items, in BRL |
| `freight_value` | float | from order items, in BRL |
| `document` | str | the text that gets embedded, see below |

None of these columns may be null. Chroma rejects `None` metadata, and the agents assume every field is set.

## Document template

Write the text for meaning, because it is what semantic search compares. Include the English and
Portuguese category, plain size words, the route and the promise. Keep it to two or three sentences.

```text
{Category title} ({category_pt}). {size_phrase}: {weight_kg:.1f} kg, {volume_l:.0f} L.
Ships from a seller in {seller_city}, {seller_state} to a customer in {customer_city}, {customer_state}.
Price R$ {price:.2f}, freight R$ {freight_value:.2f}. Promised delivery {promised_date}.
```

`size_phrase` comes from code, not the LLM:

- `"Heavy, bulky item"` if `is_bulky`
- `"Medium-sized item"` if `weight_kg >= 2` or `volume_l >= 15`
- `"Small, light item"` otherwise

## Chroma collection

- Path: `data/chroma`. Collection name: `order_items`.
- Created with Chroma's default embedding function (all-MiniLM-L6-v2, local, no key) and metadata
  `{"embed_model": <EMBED_MODEL>, "hnsw:space": "cosine"}`. Chroma embeds `documents` on `add` and
  `query_texts` on `query`, with the same model.
- `ids` come from the `id` column, and `documents` from the `document` column.
- `metadatas` hold every other column. Booleans stay booleans, numbers stay numbers, dates stay ISO strings.
- Rebuilding always deletes the collection and creates it again, so the build is idempotent.

## AffectedItem

`AffectedItem` in `models.py` has one field per metadata key, plus `id` and `focus_match: bool = False`.
The retrieval agent builds it with `AffectedItem(id=chroma_id, **metadata)`, so the field names must
match this contract exactly.
