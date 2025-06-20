## Project 1 - TutorSide

A FastAPI-based API to answer student questions.

### Feature

- Ask questions and get answers from the course materials and discussion channel.
- Supports image uploads.

### Setting up

#### Set up environment variables

Copy the `.env.example` file as `.env` and update the necessary environment variables.
| Name | Description | Required/Default |
|---|---|---|
| `OPENAI_BASE_URL` | Base URL for OpenAI LLM | Default: `https://api.openai.com/v1` |
| `OPENAI_API_KEY` | API key for OpenAI LLM | Required |
| `DUCKDB_PATH` | Path to DuckDB file | Default: `data/db.duckdb` |

The application would not start without the required variables.
For the app to picks up the default values correctly, comment the corresponding lines in `.env` file.

#### Install dependencies

The program uses [uv](https://docs.astral.sh/uv/) package manager.
To install the dependencies, run

```bash
uv sync
```

#### Scrape data

The program can scrape the data from the [course content](https://tds.s-anand.net/#/2025-01/) and [the discussion forum](https://discourse.onlinedegree.iitm.ac.in/c/courses/tds-kb/34).
To start data scraping, run the following command:

```
uv run python scraper/tds_scraper.py
uv run python scraper/discourse_scraper.py
```
This will scrape the JS-based webpages, pre-process the content, and save the data into `data/` directory as Parquet files

#### Running the application

Once the data is scraped and saved as Parquet files, the application is ready to start.
Run the following command to start the app in development mode:

```
uv run fastapi dev main.py --reload
```

To start in production mode, use:

```
uv run fastapi run main.py
```
During startup, this will:

1. Create the DuckDB database and required tables if they do not exist.
2. Generate the embeddings for the data in the Parquet files.
3. Insert the data and the embeddings into the DuckDB.

These steps are run only once, and reused on the subsequent startups.
To see the API documentation, visit [http://locahost:8000/docs](http://locahost:8000/docs).

### Submitted by

Student ID: `22f3002176`
Name: Nihara Mariyam PK
