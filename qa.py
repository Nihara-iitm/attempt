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
    texts = list(chain([entry["text"] for entry in entries]))

    content = [
        {
            "type": "text",
            "text": f"""
                    Given the texts:
                    {texts}
                    Answer the question: {query}
                    """,
        },
    ]
    if image_data:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
            },
        )

    answer_response = openai_client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {
                "role": "system",
                "content": f"""
                You are a helpful assistant that can answer the question from the provided texts with simple text{" and image attached" if image_data else ""}.
                Do not add any formatting. The answer should be a simple sentence.
                Try to add reason for your answer.
                If the question is not answerable from the provided texts {" and image attached" if image_data else ""}, say "I don't know", and why.
                Your answer should be from the provided texts {" and image attached" if image_data else ""}. Answer only from the provided text {" and image attached" if image_data else ""}.
                """,
            },
            {"role": "user", "content": content},
        ],
    )
    return {
        "answer": answer_response.choices[0].message.content,
        "links": links,
    }


# Example usage
if __name__ == "__main__":
    my_duckdb = get_duckdb()
    q = input("Enter your question: ")
    result = get_answer(my_duckdb, q, None, 3)
    print("\nAnswer:\n", result["answer"])
    print("\nSources:")
    for src in result["links"]:
        print("-", src["text"], ":", src["url"])
