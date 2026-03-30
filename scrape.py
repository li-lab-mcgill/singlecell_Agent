import sys
sys.path.append('src')
from literature_scraper import LiteratureScraper

QUERIES = [
    "single-cell RNA-seq clustering",
    "scVI OR scVI-tools single-cell",
    "Leiden clustering single-cell",
    "single-cell integration",
    "PBMC single-cell analysis",
]

scraper = LiteratureScraper(email="elizabeth.kourbatski@mail.mcgill.ca")
papers = scraper.scrape_pubmed(QUERIES, max_results=50, start_year=2020, end_year=2024)

if papers:
    sample = papers[0]
    print("\nSample paper:")
    print("Title:", sample["title"])
    print("Authors:", ", ".join(sample["authors"]))
    print("Year:", sample["year"])