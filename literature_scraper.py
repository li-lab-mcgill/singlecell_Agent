from Bio import Entrez
import json
from pathlib import Path
from typing import List, Dict
import time

class LiteratureScraper:
    def __init__(self, email: str, base_dir: str = "data/papers"):
        Entrez.email = email
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def scrape_pubmed(self, search_terms: List[str], max_results: int = 50, 
                      start_year: int = 2020, end_year: int = 2024):
        all_papers = []
        seen = set()
        
        for query in search_terms:
            print(f"Searching: {query}")
            pmids = self._search_pubmed(query, max_results, start_year, end_year)
            papers = self._fetch_batch(pmids)
            
            for paper in papers:
                if paper['pmid'] not in seen:
                    all_papers.append(paper)
                    seen.add(paper['pmid'])
            
            print(f"Found {len(papers)} papers\n")
            time.sleep(0.34)
        
        print(f"Total unique papers: {len(all_papers)}")
        self._save_json(all_papers)
        return all_papers
    
    def _search_pubmed(self, query: str, max_results: int, start_year: int, end_year: int):
        handle = Entrez.esearch(
            db="pubmed",
            term=query,
            retmax=max_results,
            mindate=str(start_year),
            maxdate=str(end_year)
        )
        results = Entrez.read(handle)
        handle.close()
        return results["IdList"]
    
    def _fetch_batch(self, pmids: List[str]):
        if not pmids:
            return []
        
        handle = Entrez.efetch(db="pubmed", id=pmids, rettype="xml", retmode="text")
        records = Entrez.read(handle)
        handle.close()
        
        papers = []
        for record in records["PubmedArticle"]:
            article = record["MedlineCitation"]["Article"]
            
            abstract_parts = article.get("Abstract", {}).get("AbstractText", [])
            abstract = " ".join(str(part) for part in abstract_parts)
            
            authors = [a["LastName"] for a in article.get("AuthorList", [])[:3] 
                      if "LastName" in a]
            
            date_info = record["MedlineCitation"].get("DateCompleted", {})
            year = str(date_info.get("Year", "Unknown"))
            
            papers.append({
                "pmid": str(record["MedlineCitation"]["PMID"]),
                "title": str(article.get("ArticleTitle", "")),
                "abstract": abstract,
                "authors": authors,
                "year": year,
                "journal": str(article.get("Journal", {}).get("Title", ""))
            })
        
        return papers
    
    def _save_json(self, papers: List[Dict]):
        filepath = self.base_dir / "papers.json"
        with open(filepath, 'w') as f:
            json.dump(papers, f, indent=2)
        print(f"Saved {len(papers)} papers to {filepath}")