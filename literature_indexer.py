from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
import json

class LiteratureIndexer:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/allenai-specter"
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " "]
        )
    
    def index_papers(self, papers):
        documents = []
        metadatas = []
        
        for paper in papers:
            chunks = self._chunk_paper(paper)
            for chunk in chunks:
                documents.append(chunk['text'])
                metadatas.append({
                    'pmid': paper.get('pmid'),
                    'title': paper['title'],
                    'year': paper['year'],
                    'authors': ', '.join(paper['authors'][:3]),
                    'section': chunk['section']
                })
        
        vectorstore = FAISS.from_texts(documents, self.embeddings, metadatas=metadatas)
        vectorstore.save_local("data/literature_index")
        return vectorstore
    
    def _chunk_paper(self, paper):
        chunks = []
        
        # Abstract
        abstract_text = paper.get('abstract', '')
        chunks.append({
            'text': f"{paper['title']}\n\nAbstract:\n{abstract_text}",
            'section': 'abstract'
        })
        
        # Full text sections if available
        if 'sections' in paper:
            for section_name, section_text in paper['sections'].items():
                section_chunks = self.text_splitter.split_text(section_text)
                for chunk_text in section_chunks:
                    chunks.append({
                        'text': f"{paper['title']}\n\n{section_name}:\n{chunk_text}",
                        'section': section_name
                    })
        
        return chunks