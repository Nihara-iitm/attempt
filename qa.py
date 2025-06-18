from itertools import chain

import duckdb
from openai import OpenAI

from config import settings
from db import get_duckdb, search_similar
from embedding.base import model

openai_client = OpenAI(
    base_url=settings.OPENAI_BASE_URL,
    api_key=settings.OPENAI_API_KEY,
)


def get_answer(
    my_duckdb: duckdb.DuckDBPyConnection,
    query: str,
    image_data: str | None,
    max_sources: int,
) -> dict[str, str | list[dict[str, str]]]:
    query_vector = model.encode(query).tolist()
    entries = search_similar(my_duckdb, query_vector, max_sources)
    links = [{"text": entry["title"], "url": entry["url"]} for entry in entries]
    texts = list(chain(*[entry["text"] for entry in entries]))

    answer_response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """
                You are a helpful assistant that can answer the question from the provided texts with simple text.
                Do not add any formatting. The answer should be a simple sentence.
                """,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""
                        Given the texts:
                        {texts}
                        Answer the question: {query}
                        """,
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    },
                ],
            },
        ],
    )
    return {
        "answer": answer_response.choices[0].message.content,
        "links": links,
    }


async def main():
    my_duckdb = get_duckdb()
    q = input("Enter your question: ")
    result = get_answer(my_duckdb, q, None, 3)
    print("\nAnswer:\n", result.answer)
    print("\nSources:")
    for src in result.links:
        print("-", src.text, ":", src.url)


# Example usage
if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
