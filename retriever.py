from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
import json
import re

class RetrievalAgent:
    def __init__(self, vectorstore_path="data/literature_index"):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/allenai-specter"
        )
        self.vectorstore = FAISS.load_local(
            vectorstore_path,
            self.embeddings,
            allow_dangerous_deserialization=True
        )
    
    def retrieve(self, query: str, k: int = 5):
        docs = self.vectorstore.similarity_search(query, k=k)
        return self._format_citations(docs)
    
    def _format_citations(self, docs):
        citations = []
        for doc in docs:
            citations.append({
                'title': doc.metadata['title'],
                'authors': doc.metadata['authors'],
                'year': doc.metadata['year'],
                'section': doc.metadata['section'],
                'excerpt': doc.page_content[:500]
            })
        return citations
    
    def retrieve_method_comparison(self, methods: list, k: int = 10):
        query = f"benchmark compare {' '.join(methods)}"
        docs = self.vectorstore.similarity_search(
            query, k=k,
            filter={'section': ['table', 'results']}
        )
        
        comparisons = []
        for doc in docs:
            metrics = self._extract_performance_numbers(doc.page_content)
            if metrics:
                comparisons.append({
                    'paper': doc.metadata['title'],
                    'year': doc.metadata['year'],
                    'performance': metrics
                })
        return comparisons
    
    def _extract_performance_numbers(self, text: str):
        metrics = {}
        
        ari = re.search(r'ARI[:\s]+([0-9.]+)', text, re.IGNORECASE)
        if ari:
            metrics['ARI'] = float(ari.group(1))
        
        sil = re.search(r'silhouette[:\s]+([0-9.]+)', text, re.IGNORECASE)
        if sil:
            metrics['silhouette'] = float(sil.group(1))
        
        nmi = re.search(r'NMI[:\s]+([0-9.]+)', text, re.IGNORECASE)
        if nmi:
            metrics['NMI'] = float(nmi.group(1))
        
        return metrics