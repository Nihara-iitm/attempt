import json

from tqdm import tqdm

from db import get_duckdb, prepare_db
from embedding.base import get_embedding


def embed_tds(file_path: str):
    my_duckdb = get_duckdb()

    # Read directly from the Parquet file
    tds_data = my_duckdb.execute(f"SELECT * FROM '{file_path}'").fetchall()
    columns = [desc[0] for desc in my_duckdb.description]

    # Process each course
    for row in tqdm(tds_data, desc="Embedding TDS Data"):
        record = dict(zip(columns, row))
        course_title = record["course_title"]
        links = record.get("links", [])
        sections = record.get("sections", [])

        for section in sections:
            heading = section["heading"]
            content_list = section["content"]
            content = "\n".join(content_list)
            text = f"{heading}\n{content}"
            if len(text.strip()) == 0:
                continue

            embedding = get_embedding(text)
            metadata = {
                "source": "tds",
                "course_title": course_title,
                "heading": heading,
                "links": links,
            }
            my_duckdb.execute(
                "INSERT INTO data (source, text, metadata, embedding) VALUES (?, ?, ?, ?)",
                ("tds", text, json.dumps(metadata), embedding),
            )

    print("Embeddings for TDS data stored.")


if __name__ == "__main__":
    prepare_db()
    embed_tds("data/tds_course_content_links.parquet")
