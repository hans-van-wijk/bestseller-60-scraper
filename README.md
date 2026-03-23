# 📚 Bestseller 60 Scraper

Scrapes the weekly bestseller lists from [debestseller60.nl](https://www.debestseller60.nl)
and exports them as clean JSON files — ready to power your custom front-end app.

---

## Setup

### 1. Install dependencies

```bash
pip install requests beautifulsoup4
```

### 2. Run the scraper

```bash
# Current week, thriller/spannend list (default)
python bestseller60_scraper.py

# Specific genre
python bestseller60_scraper.py --genre fictie
python bestseller60_scraper.py --genre non-fictie
python bestseller60_scraper.py --genre jeugd
python bestseller60_scraper.py --genre koken

# Historical week
python bestseller60_scraper.py --genre spannend --week 10 --year 2026

# Custom output filename
python bestseller60_scraper.py --output my_list.json
```

---

## Output format

Each run produces a `.json` file like this:

```json
{
  "genre": "spannend",
  "week": 12,
  "year": 2026,
  "scraped_at": "2026-03-20T10:00:00Z",
  "source_url": "https://www.debestseller60.nl/spannend",
  "books": [
    {
      "rank": 1,
      "title": "Het ultieme geheim",
      "author": "Dan Brown",
      "cover_url": "https://www.debestseller60.nl/cover/thumb/...",
      "publisher": "Luitingh-Sijthoff",
      "price": "€ 29,99",
      "isbn": "9789021056531",
      "publish_date": "09-09-2025",
      "description": "In een zinderende race door Praag..."
    }
  ]
}
```

---

## Weekly automation

### macOS / Linux — cron job

Run every Monday at 9:00 AM:

```bash
# Open crontab
crontab -e

# Add this line (adjust paths)
0 9 * * 1 /usr/bin/python3 /path/to/bestseller60_scraper.py --genre spannend >> /path/to/scraper.log 2>&1
```

### Windows — Task Scheduler

1. Open **Task Scheduler** → Create Basic Task
2. Trigger: Weekly → Monday
3. Action: Start a Program
   - Program: `python`
   - Arguments: `C:\path\to\bestseller60_scraper.py --genre spannend`

### GitHub Actions (automated + version-controlled)

Create `.github/workflows/scrape.yml`:

```yaml
name: Weekly Bestseller Scrape

on:
  schedule:
    - cron: "0 8 * * 1" # Every Monday at 08:00 UTC
  workflow_dispatch: # Also allow manual runs

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install requests beautifulsoup4

      - name: Run scraper
        run: python bestseller60_scraper.py

      - name: Commit & push JSON
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add *.json
          git commit -m "Weekly update: Bestseller 60 $(date +'%Y-W%V')" || echo "No changes"
          git push
```

This will automatically commit the new JSON to your repo every Monday —
your front-end can then fetch it directly from GitHub Pages or any static host.

---

## Scraping all genres at once

```bash
for genre in fictie non-fictie spannend jeugd koken; do
  python bestseller60_scraper.py --genre $genre
  sleep 2   # be polite to the server
done
```

---

## Notes

- The site renders server-side HTML, so no headless browser needed.
- The list updates weekly (typically Monday morning).
- Out of politeness, avoid hammering the server — once per week per genre is fine.
- The full list is 60 books; the page may paginate. If you get fewer than 60, check
  whether the site uses JavaScript-loaded pagination for entries 21–60.
