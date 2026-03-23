"""
De Bestseller 60 — Scraper
Scrapes the weekly Top 60 thriller/spannend list from debestseller60.nl
and outputs a structured JSON file.

Usage:
    python bestseller60_scraper.py
    python bestseller60_scraper.py --genre fictie
    python bestseller60_scraper.py --genre spannend --week 12 --year 2026

Dependencies:
    pip install requests beautifulsoup4

Supported genres:
    fictie, non-fictie, spannend, jeugd, koken
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import argparse
import sys

GENRE_SLUGS = {
    "fictie": "fictie",
    "non-fictie": "non-fictie",
    "spannend": "spannend",
    "thriller": "spannend",
    "jeugd": "jeugd",
    "koken": "koken",
    "culinair": "koken",
}

BASE_URL = "https://www.debestseller60.nl"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9",
}


def build_url(genre: str, week: int = None, year: int = None) -> str:
    """Construct the URL for a given genre and optional week/year."""
    slug = GENRE_SLUGS.get(genre.lower(), genre.lower())
    if week and year:
        # Historical URL pattern: /YYYYWW/genre  (e.g. /202612/spannend)
        return f"{BASE_URL}/{year}{week:02d}/{slug}"
    return f"{BASE_URL}/{slug}"


def parse_books(soup: BeautifulSoup) -> list[dict]:
    """Extract book entries from the parsed HTML."""
    books = []

    # Each book is in a numbered list — find the ranked entries
    # The structure uses divs with rank numbers followed by book info
    entries = soup.select("div.list-item, li.list-item, article.book-item")

    if not entries:
        # Fallback: look for numbered blocks — rank + image + author + title pattern
        # The page renders as a sequence of divs; we use the rank number + img + p tags
        entries = soup.find_all("div", class_=re.compile(r"book|item|rank", re.I))

    if not entries:
        # Last resort: find all img tags with cover images and walk siblings
        entries = _parse_by_cover_images(soup)

    return entries


def _parse_by_cover_images(soup: BeautifulSoup) -> list[dict]:
    """
    Robust parser: finds cover images and extracts surrounding metadata.
    Works on the actual debestseller60.nl page structure.
    """
    books = []

    # The page has a pattern: rank number, cover img, author link, title text, description, publisher, price, ISBN, date
    # We look for the numbered rank markers (1, 2, 3 ... 60)
    # In the actual HTML they appear as standalone text nodes / span elements before each book block

    # Strategy: find all <img> tags with cover paths, then crawl the parent container
    cover_imgs = soup.find_all("img", src=re.compile(r"/cover/|/covers/", re.I))

    for img in cover_imgs:
        # Walk up to find the book container
        container = img.find_parent(["div", "li", "article", "section"])
        if not container:
            continue

        book = {}

        # Cover image
        src = img.get("src", "")
        book["cover_url"] = src if src.startswith("http") else BASE_URL + src
        book["title"] = img.get("alt", "").strip()

        # Author — often in an <a> tag pointing to /zoeken/
        author_tag = container.find("a", href=re.compile(r"/zoeken/"))
        if author_tag:
            book["author"] = author_tag.get_text(strip=True)

        # All text content in the container
        texts = [t.strip() for t in container.stripped_strings]

        # Extract structured fields from text list
        book["publisher"] = ""
        book["price"] = ""
        book["isbn"] = ""
        book["publish_date"] = ""
        book["description"] = ""

        desc_parts = []
        for text in texts:
            if re.match(r"^€\s*\d", text):
                book["price"] = text
            elif re.match(r"^ISBN\s*\d{13}", text):
                book["isbn"] = text.replace("ISBN ", "").strip()
            elif re.match(r"^\d{2}-\d{2}-\d{4}$", text):
                book["publish_date"] = text
            elif text == book.get("author") or text == book.get("title"):
                continue
            elif len(text) > 40 and not book["description"]:
                # First long text after title = short description / blurb
                desc_parts.append(text)

        book["description"] = " ".join(desc_parts)

        # Rank: look for a sibling or nearby element with a number
        rank_candidate = container.find(string=re.compile(r"^\d{1,2}$"))
        if rank_candidate:
            book["rank"] = int(rank_candidate.strip())

        if book.get("title") or book.get("author"):
            books.append(book)

    return books


def scrape_week(genre: str = "spannend", week: int = None, year: int = None) -> dict:
    """
    Scrape one week's bestseller list and return structured data.

    Returns:
        {
            "genre": str,
            "week": int,
            "year": int,
            "scraped_at": ISO timestamp,
            "source_url": str,
            "books": [ { rank, title, author, cover_url, ... }, ... ]
        }
    """
    url = build_url(genre, week, year)
    print(f"Fetching: {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching page: {e}", file=sys.stderr)
        sys.exit(1)

    soup = BeautifulSoup(response.text, "html.parser")

    # --- Extract week/year from page heading ---
    detected_week, detected_year = week, year
    heading = soup.find(string=re.compile(r"Week\s+\d+\s*[-–]\s*\d{4}", re.I))
    if heading:
        m = re.search(r"Week\s+(\d+)\s*[-–]\s*(\d{4})", heading, re.I)
        if m:
            detected_week = int(m.group(1))
            detected_year = int(m.group(2))

    # --- Parse books ---
    books_raw = _parse_by_cover_images(soup)

    # Assign sequential ranks if not already detected
    if books_raw and not books_raw[0].get("rank"):
        for i, b in enumerate(books_raw, start=1):
            b["rank"] = i

    # Sort by rank
    books_raw.sort(key=lambda b: b.get("rank", 999))

    return {
        "genre": GENRE_SLUGS.get(genre.lower(), genre.lower()),
        "week": detected_week,
        "year": detected_year,
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "source_url": url,
        "books": books_raw,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Scrape De Bestseller 60 into a JSON file."
    )
    parser.add_argument(
        "--genre",
        default="spannend",
        choices=list(GENRE_SLUGS.keys()),
        help="Which genre list to scrape (default: spannend)",
    )
    parser.add_argument("--week", type=int, default=None, help="Week number (1-53)")
    parser.add_argument("--year", type=int, default=None, help="Year (e.g. 2026)")
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON filename (default: auto-generated)",
    )
    args = parser.parse_args()

    data = scrape_week(genre=args.genre, week=args.week, year=args.year)

    week_str = f"week{data['week']:02d}" if data["week"] else "current"
    year_str = str(data["year"]) if data["year"] else "unknown"
    filename = args.output or f"bestseller60_{data['genre']}_{year_str}_{week_str}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved {len(data['books'])} books → {filename}")
    print(f"   Genre : {data['genre']}")
    print(f"   Week  : {data['week']} / {data['year']}")


if __name__ == "__main__":
    main()
