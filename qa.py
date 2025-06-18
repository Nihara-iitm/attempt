import json
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
                    {"Analyze the image attached." if image_data else ""}

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
                "content": """
                You are a helpful assistant to teachers that can answer the question from the provided texts with simple text and image attached.
                These texts are from the course materials and discussion forums.
                Thoroughly analyse the image attached.
                Try to add reason for your answer.
                Give preference to images, source materials and discussion forums in the order, over other sources.
                If and only if the question is not answerable from the provided texts and image attached, say "I don't know", and why.
                Your answer should be from the provided texts and image attached.
                If a task is mentioned in the image, bias your answer towards the task.
                The answer should stick to this format:

                {{
                    "answer": "The answer to the question",
                    "text_indexes": [Indexes of the texts that were helpful to answer the question]
                }}
                """,
            },
            {"role": "user", "content": content},
        ],
    )
    response_data = json.loads(answer_response.choices[0].message.content)
    answer = response_data["answer"]
    text_indexes = response_data["text_indexes"]
    links = [links[i] for i in text_indexes]
    return {
        "answer": answer,
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
