from itertools import chain

import duckdb
from openai import BaseModel, OpenAI

from config import settings
from db import get_duckdb, search_similar
from embedding.base import model

openai_client = OpenAI(
    base_url=settings.OPENAI_BASE_URL,
    api_key=settings.OPENAI_API_KEY,
)


class Link(BaseModel):
    text: str
    url: str | None


class Answer(BaseModel):
    answer: str
    links: list[Link]


def get_answer(
    my_duckdb: duckdb.DuckDBPyConnection, query: str, image_text: str | None = None
) -> Answer:
    query_vector = model.encode(query).tolist()
    entries = search_similar(my_duckdb, query_vector, 1)
    links = [{"text": entry["title"], "url": entry["url"]} for entry in entries]
    texts = list(chain(*[entry["text"] for entry in entries]))

    image_text_prompt = (
        f"""
        Given the text reading from attached image:
        {image_text}
        """
        if image_text
        else ""
    )

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
                "content": f"""
                Given the texts:
                {texts}
                {image_text_prompt}
                Answer the question: {query}
                """,
            },
        ],
    )
    return Answer(answer=answer_response.choices[0].message.content, links=links)


async def main():
    my_duckdb = get_duckdb()
    q = input("Enter your question: ")
    result = get_answer(my_duckdb, q)
    print("\n🧠 Answer:\n", result.answer)
    print("\n🔗 Sources:")
    for src in result.links:
        print("-", src.text, ":", src.url)


# Example usage
if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
