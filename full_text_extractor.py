import requests
from bs4 import BeautifulSoup

class FullTextExtractor:
    def __init__(self):
        self.pmc_base = "https://www.ncbi.nlm.nih.gov/pmc/articles"
    
    def extract_sections(self, pmc_id: str):
        url = f"{self.pmc_base}/PMC{pmc_id}/xml/"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'xml')
        
        return {
            'title': soup.find('article-title').text if soup.find('article-title') else '',
            'abstract': self._get_section(soup, 'abstract'),
            'methods': self._get_section(soup, 'methods'),
            'results': self._get_section(soup, 'results'),
            'figures': self._extract_figures(soup),
            'tables': self._extract_tables(soup)
        }
    
    def _get_section(self, soup, section_name):
        section = soup.find('sec', {'sec-type': section_name})
        return section.get_text() if section else ''
    
    def _extract_figures(self, soup):
        figures = []
        for fig in soup.find_all('fig'):
            caption = fig.find('caption')
            if caption:
                figures.append({
                    'id': fig.get('id'),
                    'caption': caption.text,
                    'label': fig.find('label').text if fig.find('label') else None
                })
        return figures
    
    def _extract_tables(self, soup):
        tables = []
        for table in soup.find_all('table-wrap'):
            caption = table.find('caption')
            rows = [[td.text.strip() for td in tr.find_all(['td', 'th'])] 
                   for tr in table.find_all('tr')]
            tables.append({
                'id': table.get('id'),
                'caption': caption.text if caption else '',
                'data': rows
            })
        return tables