import base64
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI
from pydantic import BaseModel, Field, HttpUrl, field_validator

from db import get_duckdb, has_data, prepare_db
from embedding.discourse import embed_discourse
from embedding.tds import embed_tds
from qa import get_answer


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    my_duckdb = get_duckdb()
    if not has_data(my_duckdb):
        prepare_db()
        embed_tds("data/tds_course_content_links.parquet")
        embed_discourse("data/discourse_posts.parquet")
    my_duckdb.close()
    print("Startup complete")

    yield

    # Shutdown


app = FastAPI(lifespan=lifespan)


class QuestionRequest(BaseModel):
    question: str
    image: Annotated[str | None, Field(description="Optional base64 image")] = None

    @field_validator("image")
    def validate_image(cls, v: str | None) -> str | None:
        # Decode the base64 image if provided
        if v:
            try:
                base64.b64decode(v)
            except Exception:
                raise ValueError("Invalid base64 image data")
        return v


class Link(BaseModel):
    url: HttpUrl
    text: str


class QuestionResponse(BaseModel):
    answer: str
    links: list[Link]


async def process_question(
    data: QuestionRequest,
) -> dict[str, str | list[dict[str, str]]]:
    my_duckdb = get_duckdb()
    return get_answer(my_duckdb, data.question, data.image, max_sources=10)


# Without forwarding slash is the standard
# but forward slash is mentioned in the project description
app.post("/api", response_model=QuestionResponse)(process_question)
app.post("/api/", response_model=QuestionResponse)(process_question)
