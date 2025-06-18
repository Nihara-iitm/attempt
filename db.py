# Connect to DuckDB and SQLite

import json
from typing import TypedDict

import duckdb

from config import settings
from embedding.base import vector_dim


class DataEntry(TypedDict):
    text: str
    title: str
    url: str


def get_duckdb():
    db = duckdb.connect(settings.DUCKDB_PATH)

    db.install_extension("parquet")
    db.load_extension("parquet")

    db.install_extension("vss")
    db.load_extension("vss")
    return db


def has_data(my_duckdb: duckdb.DuckDBPyConnection):
    try:
        return my_duckdb.execute("SELECT COUNT(*) FROM data").fetchone()[0] > 0
    except Exception:
        return False


def prepare_db():
    my_duckdb = get_duckdb()
    my_duckdb.execute("DROP TABLE IF EXISTS data")
    my_duckdb.execute(
        f"CREATE TABLE data (source TEXT, text TEXT, metadata TEXT, embedding FLOAT[{vector_dim}])"
    )
    # Enable experimental persistence for HNSW indexes
    my_duckdb.execute("SET hnsw_enable_experimental_persistence=true")

    # Create the HNSW index
    my_duckdb.execute("CREATE INDEX vector_idx ON data USING HNSW (embedding)")


def search_similar(
    conn: duckdb.DuckDBPyConnection,
    query_vector: list[float],
    n_results: int = 1,
) -> list[DataEntry]:
    """Search for documents similar to query using vector similarity."""

    # Search using HNSW index with explicit FLOAT[] cast
    results = conn.execute(
        f"""
        SELECT source, text, metadata, array_distance(embedding, CAST(? AS FLOAT[{vector_dim}])) as distance
        FROM data
        ORDER BY
            distance,
            CASE 
                WHEN source = 'tds' THEN 0
                WHEN source = 'discourse' THEN 1
                ELSE 2
            END
        LIMIT ?
    """,
        [query_vector, n_results],
    ).fetchall()

    res = []
    for source, text, mtdata, distance in results:
        metadata = json.loads(mtdata)
        title = (
            metadata.get("course_title", "")
            if source == "tds"
            else metadata.get("topic_title", "")
        )
        url = metadata.get("url", "")
        res.append(DataEntry(text=text, title=title, url=url))
    return res
