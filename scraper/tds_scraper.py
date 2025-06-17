import os
from typing import TypedDict

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


class TDSLink(TypedDict):
    text: str
    href: str


class TDSDataSection(TypedDict):
    heading: str
    level: str
    content: list[str]


class TDSData(TypedDict):
    course_title: str
    sections: list[TDSDataSection]
    links: list[TDSLink]


class TDSScraper:
    def __init__(self):
        # Set up Playwright
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()

    def scrape_course_content(
        self,
        base_url: str = "https://tds.s-anand.net/#/2025-01/",
    ) -> TDSData:
        try:
            print(f"Loading {base_url}")
            self.page.goto(base_url, wait_until="networkidle")

            # Get the page source after JavaScript execution
            page_source = self.page.content()
            soup = BeautifulSoup(page_source, "html.parser")

            # Extract main content
            content_data: TDSData = {"course_title": "", "sections": [], "links": []}

            # Try to find the main content area
            # This will depend on the actual HTML structure
            main_content = (
                soup.find("main")
                or soup.find("div", class_="content")
                or soup.find("body")
            )

            if main_content:
                # Extract title
                title = main_content.find("h1") or main_content.find("title")
                if title:
                    content_data["course_title"] = title.get_text().strip()

                # Extract all headings and their content
                headings = main_content.find_all(["h1", "h2", "h3", "h4"])

                for heading in headings:
                    section: TDSDataSection = {
                        "heading": heading.get_text().strip(),
                        "level": heading.name,
                        "content": [],
                    }

                    # Get content after this heading until next heading
                    current = heading.next_sibling
                    while current and current.name not in ["h1", "h2", "h3", "h4"]:
                        if hasattr(current, "get_text"):
                            text = current.get_text().strip()
                            if text:
                                section["content"].append(text)
                        current = current.next_sibling

                    content_data["sections"].append(section)

                # Extract all links for potential navigation
                links = main_content.find_all("a", href=True)
                for link in links:
                    if (
                        link["href"].startswith("#")
                        or "tds.s-anand.net" in link["href"]
                    ):
                        content_data["links"].append(
                            {"text": link.get_text().strip(), "href": link["href"]}
                        )

            return content_data

        except Exception as e:
            print(f"Error scraping: {e}")
            return None

    def explore_navigation(self):
        """Try to find all course sections/pages"""
        try:
            # Look for navigation elements
            nav_elements = self.page.query_selector_all("nav, .nav, .menu")

            sections = []
            for nav in nav_elements:
                links = nav.query_selector_all("a")
                for link in links:
                    href = link.get_attribute("href")
                    text = link.inner_text().strip()
                    if href and text:
                        sections.append({"text": text, "href": href})

            return sections

        except Exception as e:
            print(f"Error exploring navigation: {e}")
            return []

    def get_all_links(self):
        """Get all internal links from the main page"""
        try:
            # Get all links
            links = self.page.query_selector_all("a")

            unique_links = set()
            for link in links:
                href = link.get_attribute("href")
                text = link.inner_text().strip()

                if href and (
                    href.startswith("https://tds.s-anand.net") or href.startswith("#")
                ):
                    # Convert relative links to full URLs
                    if href.startswith("#"):
                        href = f"https://tds.s-anand.net/{href}"

                    unique_links.add((href, text))

            return list(unique_links)

        except Exception as e:
            print(f"Error getting links: {e}")
            return []

    def scrape_all_sections(self):
        """Scrape the main page and all linked pages"""
        all_content = []
        visited_urls = set()

        # Start with main page
        base_url = "https://tds.s-anand.net/#/2025-01/"

        # Scrape main page
        print(f"Scraping main page: {base_url}")
        main_content = self.scrape_course_content(base_url)
        if main_content:
            main_content["url"] = base_url
            all_content.append(main_content)
            visited_urls.add(base_url)

        # Get all links from main page
        all_links = self.get_all_links()
        print(f"Found {len(all_links)} links to explore")

        # Visit each unique link
        for href, link_text in all_links:
            if href not in visited_urls:
                try:
                    print(f"Scraping: {link_text} ({href})")

                    # Navigate to the link
                    self.page.goto(href, wait_until="networkidle")

                    # Scrape content from this page
                    page_content = self.scrape_course_content(href)

                    if page_content and page_content.get("sections"):
                        page_content["url"] = href
                        page_content["link_text"] = link_text
                        all_content.append(page_content)

                    visited_urls.add(href)

                except Exception as e:
                    print(f"Error scraping {href}: {e}")
                    continue

        print(f"Successfully scraped {len(all_content)} pages")
        return all_content

    def save_to_parquet(
        self,
        data: list[TDSData],
        filename: str = "data/tds_course_content_links.parquet",
    ):
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        df = pd.DataFrame(data)
        df.to_parquet(filename, engine="pyarrow")
        print(f"Content saved to {filename}")

    def close(self):
        """Close the browser"""
        self.browser.close()
        self.playwright.stop()


# Usage example
if __name__ == "__main__":
    scraper = TDSScraper()

    try:
        # Scrape all content
        content = scraper.scrape_all_sections()
        # Save to file
        scraper.save_to_parquet(content)

        print(f"Scraped {len(content)} sections")
        for section in content:
            print(
                f"- {section.get('course_title', 'Unknown')} ({len(section.get('sections', []))} subsections)"
            )
    finally:
        scraper.close()
