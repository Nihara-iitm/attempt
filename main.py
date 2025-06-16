import base64
from typing import Annotated

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl

app = FastAPI()


class QuestionRequest(BaseModel):
    question: str
    image: Annotated[str | None, Field(description="Optional base64 image")]=None

class Link(BaseModel):
    url: HttpUrl
    text: str


class QuestionResponse(BaseModel):
    answer: str
    links: list[Link]


@app.post("/api", response_model=QuestionResponse)
async def process_question(
    request: QuestionRequest,
) -> dict[str, str | list[dict[str, str]]]:
    # Decode the base64 image if provided
    if request.image:
        try:
            image_data = base64.b64decode(request.image)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")

    # Simulate processing the question and image
    # Here you would implement your logic to generate the answer and links
    answer = "You must use `gpt-3.5-turbo-0125`, even if the AI Proxy only supports `gpt-4o-mini`. Use the OpenAI API directly for this question."
    links = [
        {
            "url": "https://discourse.onlinedegree.iitm.ac.in/t/ga5-question-8-clarification/155939/4",
            "text": "Use the model that's mentioned in the question.",
        },
        {
            "url": "https://discourse.onlinedegree.iitm.ac.in/t/ga5-question-8-clarification/155939/3",
            "text": "My understanding is that you just have to use a tokenizer, similar to what Prof. Anand used, to get the number of tokens and multiply that by the given rate.",
        },
    ]

    return {
        "answer": answer,
        "links": links,
    }
