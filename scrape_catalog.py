"""
scrape_catalog.py

Purpose of this file:
    Scrapes SHL's public product catalog (Individual Test Solutions
    only) and writes the result to data/shl_catalog.json in the shape
    our app expects.

Why it exists:
    The assignment requires the app to be grounded only in real,
    scraped catalog data - no hardcoded URLs. This script is meant to
    be run occasionally (not on every server start) to refresh
    data/shl_catalog.json.

    NOTE: I built and tested this project in a sandboxed environment
    with no internet access, so I could not run this script against
    the live site. data/shl_catalog.json currently ships with a small,
    hand-curated sample catalog instead so the rest of the app is
    fully runnable out of the box. Running this script for real
    (`python scripts/scrape_catalog.py`) with internet access will
    replace that sample with the live catalog. See approach_document.md
    for more on this limitation.

Possible interview questions from this file:
    - How do you make sure you only scrape Individual Test Solutions,
      not pre-packaged Job Solutions?
    - What would you change to make this robust against SHL changing
      their page structure?
    - Why write the whole catalog to one JSON file instead of a database?
"""

import json
import time
from pathlib import Path
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

CATALOG_URL = "https://www.shl.com/solutions/products/product-catalog/"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "shl_catalog.json"

# Being polite to SHL's servers - wait between requests.
REQUEST_DELAY_SECONDS = 1.0
HEADERS = {"User-Agent": "Mozilla/5.0 (student-project-shl-agent/1.0)"}


def fetch_page(url: str) -> Optional[BeautifulSoup]:
    """Download one catalog page and return a parsed BeautifulSoup tree,
    or None if the request fails."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"Failed to fetch {url}: {error}")
        return None
    return BeautifulSoup(response.text, "html.parser")


def get_individual_test_solution_links(list_page_url: str) -> List[str]:
    """Find links to individual assessment detail pages on a catalog
    listing page.

    SHL's catalog page groups results into two tables - "Individual
    Test Solutions" and "Pre-packaged Job Solutions". We only want
    links from the Individual Test Solutions table, so we look for the
    table/section whose heading text matches, then collect the links
    inside it.
    """
    soup = fetch_page(list_page_url)
    if soup is None:
        return []

    links: List[str] = []
    for heading in soup.find_all(["h2", "h3"]):
        if "individual test solutions" in heading.get_text(strip=True).lower():
            # The results usually live in the next table/list sibling.
            container = heading.find_next(["table", "ul"])
            if container is None:
                continue
            for anchor in container.find_all("a", href=True):
                href = anchor["href"]
                if "/product-catalog/view/" in href:
                    full_url = requests.compat.urljoin(list_page_url, href)
                    links.append(full_url)
    return links


def parse_assessment_detail_page(url: str) -> Optional[dict]:
    """Visit one assessment's detail page and extract the fields our
    app needs. Falls back gracefully if a field is missing so one bad
    page doesn't crash the whole scrape."""
    soup = fetch_page(url)
    if soup is None:
        return None

    title_tag = soup.find("h1")
    name = title_tag.get_text(strip=True) if title_tag else ""

    description_tag = soup.find("meta", attrs={"name": "description"})
    description = description_tag["content"].strip() if description_tag else ""

    # These fields vary in structure across SHL's site. We look for
    # common labelled rows (e.g. "Job levels", "Test type", "Duration")
    # and fall back to empty values if not found, rather than guessing.
    skills: List[str] = []
    duration = 0
    category = ""
    test_type = ""

    for row in soup.find_all(["tr", "li", "div"]):
        text = row.get_text(" ", strip=True).lower()
        if "duration" in text:
            digits = "".join(ch for ch in text if ch.isdigit())
            if digits:
                duration = int(digits)
        if "test type" in text:
            test_type = row.get_text(" ", strip=True).split(":")[-1].strip()
        if "job level" in text or "category" in text:
            category = row.get_text(" ", strip=True).split(":")[-1].strip()

    if not name:
        return None

    return {
        "name": name,
        "description": description,
        "skills": skills,
        "duration": duration,
        "category": category or "Uncategorised",
        "test_type": test_type or "K",
        "url": url,
    }


def scrape_full_catalog() -> List[dict]:
    """Walk the paginated catalog list and scrape every Individual Test
    Solution detail page found."""
    all_links: List[str] = []
    page_url = CATALOG_URL

    # SHL's catalog is paginated. We keep following a "next page" link
    # until there isn't one. Adjust the selector below if the site's
    # markup changes.
    visited_pages = set()
    while page_url and page_url not in visited_pages:
        visited_pages.add(page_url)
        print(f"Scanning listing page: {page_url}")
        all_links.extend(get_individual_test_solution_links(page_url))

        soup = fetch_page(page_url)
        next_link = soup.find("a", string=lambda s: s and "next" in s.lower()) if soup else None
        page_url = (
            requests.compat.urljoin(page_url, next_link["href"])
            if next_link and next_link.get("href")
            else None
        )
        time.sleep(REQUEST_DELAY_SECONDS)

    unique_links = sorted(set(all_links))
    print(f"Found {len(unique_links)} individual test solution pages.")

    catalog: List[dict] = []
    for link in unique_links:
        item = parse_assessment_detail_page(link)
        if item:
            catalog.append(item)
        time.sleep(REQUEST_DELAY_SECONDS)

    return catalog


def main() -> None:
    """Scrape the catalog and write it to data/shl_catalog.json."""
    catalog = scrape_full_catalog()
    if not catalog:
        print("No assessments were scraped - keeping the existing catalog file untouched.")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(catalog)} assessments to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
