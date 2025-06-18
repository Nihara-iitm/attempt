import json

from tqdm import tqdm

from db import get_duckdb, prepare_db
from embedding.base import get_embedding


def embed_discourse(file_path: str):
    # Setup OpenAI and database connections
    my_duckdb = get_duckdb()

    # Query discourse posts
    discourse_posts = my_duckdb.execute(f"SELECT * FROM '{file_path}'").fetchall()
    columns = [desc[0] for desc in my_duckdb.description]

    for row in tqdm(discourse_posts, desc="Embedding Discourse Posts"):
        post = dict(zip(columns, row))
        text = post["content"]
        if not text.strip():
            continue

        embedding = get_embedding(text)
        metadata = {
            "source": "discourse",
            "topic_id": post["topic_id"],
            "post_id": post["post_id"],
            "topic_title": post["topic_title"],
            "author": post["author"],
            "like_count": post.get("like_count", 0),
            "is_accepted_answer": post.get("is_accepted_answer", False),
            "url": post.get("url"),
        }
        my_duckdb.execute(
            "INSERT INTO data (source, text, metadata, embedding) VALUES (?, ?, ?, ?)",
            ("discourse", text, json.dumps(metadata), embedding),
        )

    print("Embeddings for Discourse posts stored.")


if __name__ == "__main__":
    prepare_db()
    embed_discourse("data/discourse_posts.parquet")
