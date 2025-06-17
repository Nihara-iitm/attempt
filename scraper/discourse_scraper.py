import json
import os
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError, sync_playwright


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")


class DiscourseScraper:
    def __init__(
        self,
        base_url: str = "https://discourse.onlinedegree.iitm.ac.in",
        category_json_path: str = "/c/courses/tds-kb",
        category_id: int = 34,
        auth_state_file: str = "auth.json",
        date_from: datetime = datetime(2025, 1, 1),
        date_to: datetime = datetime(2025, 4, 14),
    ):
        self.base_url = base_url
        self.category_json_path = f"{category_json_path}/{category_id}.json"
        self.auth_state_file = auth_state_file
        self.date_from = date_from
        self.date_to = date_to

        # Set up Playwright
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

        if not self.is_authenticated():
            print("Authenticating...")
            self.login_and_save_auth()
        else:
            print("Using the existing authenticated session.")

    def login_and_save_auth(self):
        print("No authentication found. Opening browser for manual login...")
        self.browser = self.playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.page.goto(f"{self.base_url}/login")
        print(
            "Please log in manually using Google. Then press Resume in Playwright bar."
        )
        self.page.pause()
        self.context.storage_state(path=self.auth_state_file)
        print("Login state has been saved.")
        self.browser.close()

    def is_authenticated(self):
        if not os.path.exists(self.auth_state_file):
            return False

        try:
            self.page.goto(
                f"{self.base_url}{self.category_json_path}", wait_until="networkidle"
            )
            self.page.wait_for_selector("pre")
            json.loads(self.page.inner_text("pre"))
            return True
        except (TimeoutError, json.JSONDecodeError):
            print("Previous session is invalid.")
            return False

    def scrape_posts(self):
        print("Starting scrape using saved session...")
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context(storage_state=self.auth_state_file)
        self.page = self.context.new_page()

        all_topics = []
        page_num = 0
        while True:
            paginated_url = f"{self.base_url}{self.category_json_path}?page={page_num}"
            print(f"Fetching page {page_num}...")
            self.page.goto(paginated_url)

            try:
                data = json.loads(self.page.inner_text("pre"))
            except Exception:
                data = json.loads(self.page.content())

            topics = data.get("topic_list", {}).get("topics", [])
            if not topics:
                break

            all_topics.extend(topics)
            page_num += 1

        print(f"Found {len(all_topics)} topics in total across all pages")

        filtered_posts = []
        for topic in all_topics:
            created_at = parse_date(topic["created_at"])
            if self.date_from <= created_at <= self.date_to:
                topic_url = f"{self.base_url}/t/{topic['slug']}/{topic['id']}.json"
                self.page.goto(topic_url)
                try:
                    topic_data = json.loads(self.page.inner_text("pre"))
                except Exception:
                    topic_data = json.loads(self.page.content())

                posts = topic_data.get("post_stream", {}).get("posts", [])
                accepted_answer_id = topic_data.get(
                    "accepted_answer", topic_data.get("accepted_answer_post_id")
                )

                # Build reply count map
                reply_counter = {}
                for post in posts:
                    reply_to = post.get("reply_to_post_number")
                    if reply_to is not None:
                        reply_counter[reply_to] = reply_counter.get(reply_to, 0) + 1

                for post in posts:
                    filtered_posts.append(
                        {
                            "topic_id": topic["id"],
                            "topic_title": topic.get("title"),
                            "category_id": topic.get("category_id"),
                            "tags": topic.get("tags", []),
                            "post_id": post["id"],
                            "post_number": post["post_number"],
                            "author": post["username"],
                            "created_at": post["created_at"],
                            "updated_at": post.get("updated_at"),
                            "reply_to_post_number": post.get("reply_to_post_number"),
                            "is_reply": post.get("reply_to_post_number") is not None,
                            "reply_count": reply_counter.get(post["post_number"], 0),
                            "like_count": post.get("like_count", 0),
                            "is_accepted_answer": post["id"] == accepted_answer_id,
                            "mentioned_users": [
                                u["username"] for u in post.get("mentioned_users", [])
                            ],
                            "url": f"{self.base_url}/t/{topic['slug']}/{topic['id']}/{post['post_number']}",
                            "content": BeautifulSoup(
                                post["cooked"], "html.parser"
                            ).get_text(),
                        }
                    )
        print(
            f"Scraped {len(filtered_posts)} posts from {self.date_from.date()} to {self.date_to.date()}"
        )
        return filtered_posts

    def save_to_parquet(
        self, data: list[dict], filename: str = "data/discourse_posts.parquet"
    ):
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        df = pd.DataFrame(data)
        df.to_parquet(filename, engine="pyarrow")
        print(f"Posts saved to {filename}")

    def close(self):
        self.browser.close()
        self.playwright.stop()


def main():
    scraper = DiscourseScraper()

    try:
        posts = scraper.scrape_posts()
        scraper.save_to_parquet(posts)
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
