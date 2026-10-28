"""Step 0b: embed every order item into a local Chroma collection, the knowledge base for retrieval.

Run once with `python -m src.build_index` after data_prep. Chroma's built-in all-MiniLM-L6-v2 model
embeds the documents locally, so no API key is needed. Rebuilding deletes and recreates the
collection, so it is always safe to run again.
"""
from __future__ import annotations

import time

import chromadb
import pandas as pd

from src import config

BATCH_SIZE = 500


def build() -> int:
    df = pd.read_csv(config.PROCESSED_CSV)
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    try:
        client.delete_collection(config.COLLECTION)
    except Exception:   # NotFoundError on the first build
        pass
    # No embedding_function argument: Chroma uses its default, all-MiniLM-L6-v2, on the CPU.
    collection = client.create_collection(
        config.COLLECTION,
        metadata={"embed_model": config.EMBED_MODEL, "hnsw:space": "cosine"},
    )
    for start in range(0, len(df), BATCH_SIZE):
        batch = df.iloc[start:start + BATCH_SIZE]
        collection.add(
            ids=batch["id"].tolist(),
            documents=batch["document"].tolist(),
            # Everything except id and document becomes filterable metadata (no nulls, see data_prep).
            metadatas=batch.drop(columns=["id", "document"]).to_dict("records"),
        )
        print(f"  embedded {min(start + BATCH_SIZE, len(df)):,} / {len(df):,}", end="\r")
    print()
    return collection.count()


def open_collection():
    """Open the index for querying. Stops with the fix, not a stack trace, when it is missing or stale."""
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    try:
        collection = client.get_collection(config.COLLECTION)
    except Exception:   # chromadb raises NotFoundError
        raise SystemExit("Index not found. Run: python -m src.build_index")
    built_with = (collection.metadata or {}).get("embed_model")
    if built_with != config.EMBED_MODEL:
        raise SystemExit(f"Index was built with {built_with}, but config uses {config.EMBED_MODEL}. "
                         "Run: python -m src.build_index")
    return collection


def main() -> None:
    if not config.PROCESSED_CSV.exists():
        raise SystemExit("Processed data not found. Run: python -m src.data_prep")
    started = time.time()
    count = build()
    print(f"Indexed {count:,} items into '{config.COLLECTION}' in {time.time() - started:.0f} s "
          f"({config.CHROMA_DIR.relative_to(config.ROOT)})")


if __name__ == "__main__":
    main()
