from typing import List, Dict, Optional, Any, Set
import os
from pathlib import Path
from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, UnstructuredPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain.chains.llm import LLMChain
from langchain_community.callbacks.manager import get_openai_callback
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_core.documents import Document
import json
import logging
import time
import re
from sentence_transformers import CrossEncoder
import pdfplumber

# Set up logging
logger = logging.getLogger(__name__)

# Add RerankerAgent class
class RerankerAgent:
    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)
    def rerank(self, question, docs, top_k=4):
        pairs = [[question, doc.page_content] for doc in docs]
        scores = self.model.predict(pairs)
        reranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
        return [doc for doc, score in reranked[:top_k]]

class VCReportAgent:
    def __init__(self, openai_api_key: str, report_path: str):
        """Initialize the VC Report Agent."""
        self.reports_dir = Path(report_path)
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        self.vector_store = None
        self.qa_chain = None
        self.llm = ChatOpenAI(temperature=0, model="gpt-4o", openai_api_key=openai_api_key)
        self.reranker = RerankerAgent()  # Add reranker
        self._initialize_agent()

    def _extract_keywords(self, question: str) -> Set[str]:
        """Extract relevant keywords from the question."""
        # Common VC and sector terms
        vc_terms = {'deal', 'exit', 'valuation', 'funding', 'investment', 'round', 'series', 
                   'pre-money', 'post-money', 'cagr', 'growth', 'quarter', 'annual', 'year'}
        
        # Sector-specific terms
        sector_terms = {'insurtech', 'biotech', 'gaming', 'quantum', 'ai', 'artificial intelligence',
                       'healthcare', 'fintech', 'enterprise', 'consumer', 'hardware', 'software'}
        
        # Extract words from question
        words = set(re.findall(r'\b\w+\b', question.lower()))
        
        # Combine with relevant terms
        keywords = words.union(vc_terms.intersection(words))
        keywords = keywords.union(sector_terms.intersection(words))
        
        # Add temporal terms if present
        if any(year in question for year in ['2020', '2021', '2022', '2023', '2024', '2025']):
            keywords.add('temporal')
        
        return keywords

    def _get_relevant_documents(self, question: str, k: int = 10) -> List[Any]:
        """Get relevant documents using both semantic and keyword search, then rerank."""
        keywords = self._extract_keywords(question)
        # Always retrieve more for reranking
        k_retrieve = max(10, k)
        semantic_docs = self.vector_store.similarity_search(question, k=k_retrieve)
        keyword_docs = []
        if keywords:
            for keyword in keywords:
                try:
                    docs = self.vector_store.similarity_search(keyword, k=2)
                    keyword_docs.extend(docs)
                except Exception as e:
                    logger.warning(f"Error searching for keyword {keyword}: {str(e)}")
        if 'cagr' in question.lower():
            try:
                year_docs = self.vector_store.similarity_search("2020 2021 2022 2023 2024 2025", k=3)
                keyword_docs.extend(year_docs)
            except Exception as e:
                logger.warning(f"Error searching for temporal data: {str(e)}")
        all_docs = semantic_docs + keyword_docs
        seen_content = set()
        unique_docs = []
        for doc in all_docs:
            content_hash = hash(doc.page_content[:100])
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_docs.append(doc)
        # Rerank and select top k
        top_docs = self.reranker.rerank(question, unique_docs, top_k=4)
        # Debug: print top reranked chunks
        print("\n\n--- Top Reranked Chunks for Debug ---\n")
        for i, doc in enumerate(top_docs):
            print(f"Chunk {i+1} (first 500 chars):\n{doc.page_content[:500]}\n")
        return top_docs

    def _initialize_agent(self):
        """Initialize the agent with document processing and retrieval, including table extraction."""
        documents = []
        for pdf_file in self.reports_dir.glob("*.pdf"):
            try:
                # 1. Extract text as before
                loader = UnstructuredPDFLoader(str(pdf_file))
                docs = loader.load()
                for doc in docs:
                    doc.metadata["source"] = str(pdf_file.name)
                documents.extend(docs)
                print(f"\n\n--- Extracted Chunks from {pdf_file.name} ---\n")
                for i, doc in enumerate(docs):
                    print(f"Chunk {i+1} (first 500 chars):\n{doc.page_content[:500]}\n")
                # 2. Extract tables and add as text chunks
                with pdfplumber.open(str(pdf_file)) as pdf:
                    for page_num, page in enumerate(pdf.pages, 1):
                        tables = page.extract_tables()
                        for t_idx, table in enumerate(tables, 1):
                            # Convert table to readable string (CSV-like)
                            table_str = "\n".join([", ".join([cell if cell is not None else "" for cell in row]) for row in table])
                            table_doc = Document(
                                page_content=f"Extracted table from {pdf_file.name}, page {page_num}, table {t_idx}:\n{table_str}",
                                metadata={"source": str(pdf_file.name), "page": page_num, "type": "table"}
                            )
                            documents.append(table_doc)
                            # Debug print
                            print(f"[Table] {pdf_file.name} page {page_num} table {t_idx} (first 500 chars):\n{table_str[:500]}\n")
            except Exception as e:
                logger.error(f"Error loading or extracting tables from {pdf_file}: {str(e)}")
                continue
        if not documents:
            raise ValueError("No documents found in the report directory")

        # Create vector store
        self.vector_store = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory="./chroma_db"
        )

        # Create the QA chain - using a simpler approach
        def create_qa_chain():
            def qa_with_context(input_dict):
                question = input_dict["query"]
                # Get relevant documents
                docs = self._get_relevant_documents(question, k=4)  # Reduced from 8 to 4
                # Combine context
                context = "\n\n".join([doc.page_content for doc in docs])
                
                # Create the full prompt
                full_prompt = f"""You are a VC report analysis expert. Use the following context to answer the question.

For CAGR (Compound Annual Growth Rate) calculations:
- Find the beginning and ending values from the context
- Calculate: CAGR = (Ending Value / Beginning Value)^(1/number of years) - 1
- Show your calculation step by step
- Convert the result to a percentage

Important: 
1. Use specific numbers and data points from the context
2. If you find conflicting information, explain the conflict
3. If you're unsure about any part, explicitly state what you're uncertain about
4. For calculations, show your work step by step in plain text
5. NEVER use LaTeX math formulas
6. Use simple text format for all math: "CAGR = (Ending Value / Beginning Value)^(1/n) - 1"
7. For fractions, use "X divided by Y" or "X/Y"
8. For exponents, use "X to the power of Y" or "X^Y"
9. For averages, use "Average = (A + B + C) / 3"
10. Make all mathematical expressions human-readable in plain text
11. Always perform the actual calculations when asked for CAGR, percentages, or other math
12. If you find data for different time periods, calculate CAGR for each period mentioned

Context: {context}

Question: {question}

Answer:"""
                
                # Get response from LLM
                response = self.llm.invoke(full_prompt)
                return {"result": response.content}
            
            return qa_with_context
        
        self.qa_chain = create_qa_chain()

    def _clean_math_formulas(self, text: str) -> str:
        """Convert LaTeX math formulas to human-readable text."""
        import re
        
        # Replace LaTeX fractions
        text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1 divided by \2', text)
        
        # Replace LaTeX text commands
        text = re.sub(r'\\text\{([^}]+)\}', r'\1', text)
        
        # Replace LaTeX brackets
        text = re.sub(r'\\\[', '', text)
        text = re.sub(r'\\\]', '', text)
        
        # Replace LaTeX parentheses
        text = re.sub(r'\\left\(', '(', text)
        text = re.sub(r'\\right\)', ')', text)
        
        # Replace LaTeX exponents
        text = re.sub(r'\^\{([^}]+)\}', r' to the power of \1', text)
        
        # Clean up any remaining LaTeX commands
        text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text)
        
        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def analyze_question(self, question: str) -> Dict[str, Any]:
        """Analyze a question about the VC report."""
        try:
            with get_openai_callback() as cb:
                # Get answer using the simpler QA chain
                result = self.qa_chain({"query": question})
                
                # Clean up any LaTeX math in the answer
                cleaned_answer = self._clean_math_formulas(result["result"])
                
                # Get relevant documents for sources
                docs = self._get_relevant_documents(question, k=8)
                
                # Validate temporal context
                temporal_valid = self._validate_temporal_context(question, docs)
                
                # Extract sources and add validation metadata, removing duplicates
                seen_sources = set()
                sources = []
                for doc in docs:
                    source = doc.metadata.get("source", "Unknown")
                    if source not in seen_sources:
                        seen_sources.add(source)
                        source_info = {
                            "source": source,
                            "has_visual": doc.metadata.get("has_visual", False),
                            "temporal_valid": temporal_valid,
                            "keywords_found": list(self._extract_keywords(question).intersection(
                                set(re.findall(r'\b\w+\b', doc.page_content.lower()))
                            ))
                        }
                        if "page" in doc.metadata:
                            source_info["page"] = doc.metadata["page"]
                        sources.append(source_info)
                
                return {
                    "answer": cleaned_answer,
                    "sources": sources,
                    "validation": {
                        "temporal_valid": temporal_valid,
                        "tokens_used": cb.total_tokens,
                        "cost": cb.total_cost,
                        "keywords_searched": list(self._extract_keywords(question))
                    }
                }
                
        except Exception as e:
            logger.error(f"Error analyzing question: {str(e)}")
            return {
                "answer": f"Error analyzing question: {str(e)}",
                "sources": [],
                "validation": {
                    "temporal_valid": False,
                    "tokens_used": 0,
                    "cost": 0.0,
                    "keywords_searched": []
                }
            }

    def _validate_temporal_context(self, question: str, context: List[Any]) -> bool:
        """Validate that the temporal context of the question matches the data."""
        # Extract year from question if present
        year_match = re.search(r'20\d{2}', question)
        if not year_match:
            return True
        
        target_year = year_match.group(0)
        
        # Check if any context documents contain data from different years
        for doc in context:
            if str(target_year) not in doc.page_content:
                return False
        return True

    def get_insurtech_deal_activity(self) -> Dict:
        """Get current deal activity size for Insurtech in the most recent quarter."""
        return self.analyze_question("What's the current deal activity size for Insurtech in the most recent financial quarter?")

    def get_biotech_exits(self) -> Dict:
        """Get total value of exits in the biotechnology/bio tools space in Q1 2025."""
        return self.analyze_question("What's the total value of exits in the biotechnology/bio tools space in Q1 2025?")

    def get_top_spinout_institutions(self) -> Dict:
        """Get top 3 academic institutions by spin out activity in the UK."""
        return self.analyze_question("What are the top 3 academic institutions by spin out activity in the UK? How many companies do they spin out on average individually?")

    def get_top_spinout_sector(self) -> Dict:
        """Get top sector of UK academic spinouts."""
        return self.analyze_question("What is the top sector of UK academic spinouts?")

    def get_top_quantum_subsector(self) -> Dict:
        """Get top sub-sector of Quantum Computing by number of companies."""
        return self.analyze_question("What's the top sub-sector of Quantum Computing by number of companies generated?")

    def get_gaming_cagr(self) -> Dict:
        """Get CAGR of median gaming early-stage VC deal value and pre-money valuation."""
        return self.analyze_question("What's the CAGR of median gaming early-stage VC deal value and pre-money valuation ($M) in the segment of development?")

    def _clean_metadata(self, metadata: dict) -> dict:
        """Clean and filter document metadata to ensure compatibility with Chroma."""
        # Keep only essential metadata
        essential_metadata = {
            "source": str(metadata.get("source", "Unknown")),
            "page": str(metadata.get("page_number", 1)),
            "has_visual": bool("figure" in str(metadata.get("category", "")).lower())
        }
        
        # Filter out any remaining complex metadata
        return filter_complex_metadata(essential_metadata)

    def _process_pdf_content(self, content: str, metadata: dict) -> Document:
        """Process PDF content and create a Document object."""
        # Clean and normalize the text
        cleaned_content = ' '.join(content.split())
        
        # Only create document if content is meaningful
        if len(cleaned_content.strip()) > 50:
            return Document(
                page_content=cleaned_content,
                metadata=self._clean_metadata(metadata)
            )
        return None

    def _initialize_vector_store(self, report_path: str):
        """Initialize the vector store with the report."""
        # Load documents with both text and visual elements
        documents = []
        for pdf_file in Path(report_path).glob("*.pdf"):
            try:
                # Use UnstructuredPDFLoader for better handling of visual elements
                loader = UnstructuredPDFLoader(str(pdf_file), mode="elements")
                elements = loader.load()
                
                # Process each element
                for element in elements:
                    if isinstance(element, Document):
                        # Clean and normalize the text
                        element.page_content = ' '.join(element.page_content.split())
                        
                        # Update metadata
                        element.metadata.update({
                            "source": pdf_file.name,
                            "page_number": element.metadata.get("page_number", 1),
                            "category": element.metadata.get("type", "text")
                        })
                        
                        # Clean metadata and only add if content is meaningful
                        if len(element.page_content.strip()) > 50:
                            element.metadata = self._clean_metadata(element.metadata)
                            documents.append(element)
                    else:
                        logger.warning(f"Unexpected element type: {type(element)}")
                        continue
                
                logger.info(f"Processed {pdf_file.name}: {len(documents)} documents")
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {str(e)}")
                continue
        
        if not documents:
            raise ValueError("No valid documents found in the report directory")
        
        # Create and persist the vector store
        self.vector_store = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            collection_name="vc_reports",
            persist_directory="./chroma_db"
        )
        
        logger.info(f"Vector store initialized with {len(documents)} documents")

    def _create_qa_chain(self):
        """Create the question-answering chain."""
        # Create a prompt template for the QA chain
        prompt = ChatPromptTemplate.from_template(
            """You are a helpful AI assistant analyzing venture capital reports. 
            Use the following pieces of context to answer the question at the end.
            If you don't know the answer, explain why you can't find the specific information in the context.
            If the question is about temporal data (dates, quarters, years), make sure to validate the time period mentioned in the context.
            If the question is about specific companies or sectors, make sure to validate the data against the context.
            If the question is about percentages or calculations, make sure to validate the numbers against the context.

            Context: {context}

            Question: {question}

            Guidelines:
            1. If you can't find the exact information, explain what information is available
            2. If the data is from a different time period, mention this
            3. If the context is unclear or incomplete, explain what's missing
            4. Always cite your sources when possible

            Answer:"""
        )

        # Create a simple QA chain with better context handling
        def format_docs(docs):
            """Format documents with clear separation and source attribution."""
            formatted = []
            for doc in docs:
                source = doc.metadata.get("source", "Unknown")
                page = doc.metadata.get("page", "Unknown")
                formatted.append(f"[Source: {source}, Page {page}]\n{doc.page_content}\n")
            return "\n---\n".join(formatted)

        self.qa_chain = (
            {"context": self.retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )

    def _validate_temporal_data(self, question: str, docs: List[Any]) -> Dict[str, Any]:
        """Validate temporal data in the question against the context."""
        try:
            # Extract year from question if present
            year_match = re.search(r'20\d{2}', question)
            if not year_match:
                return {"valid": True, "reason": "No specific year mentioned"}
            
            target_year = year_match.group(0)
            
            # Check if any context documents contain data from different years
            for doc in docs:
                if str(target_year) not in doc.page_content:
                    return {
                        "valid": False,
                        "reason": f"Data from {target_year} not found in context"
                    }
            return {"valid": True, "reason": f"Data from {target_year} validated"}
        except Exception as e:
            return {"valid": False, "reason": f"Error in temporal validation: {str(e)}"}

    def _validate_company_data(self, question: str, docs: List[Any]) -> Dict[str, Any]:
        """Validate company/sector data in the question against the context."""
        try:
            # Simple validation - check if any company/sector terms are found
            company_terms = ["company", "sector", "industry", "startup", "venture"]
            found_terms = [term for term in company_terms if term.lower() in question.lower()]
            
            if not found_terms:
                return {"valid": True, "reason": "No company/sector specific question"}
            
            # Check if terms appear in context
            for doc in docs:
                if any(term.lower() in doc.page_content.lower() for term in found_terms):
                    return {"valid": True, "reason": "Company/sector data found in context"}
            
            return {"valid": False, "reason": "Company/sector data not found in context"}
        except Exception as e:
            return {"valid": False, "reason": f"Error in company validation: {str(e)}"}

    def _validate_numerical_data(self, question: str, docs: List[Any]) -> Dict[str, Any]:
        """Validate numerical data in the question against the context."""
        try:
            # Check for numerical terms
            numerical_terms = ["percentage", "number", "amount", "value", "total", "average"]
            found_terms = [term for term in numerical_terms if term.lower() in question.lower()]
            
            if not found_terms:
                return {"valid": True, "reason": "No numerical data requested"}
            
            # Check if numerical data appears in context
            for doc in docs:
                if any(term.lower() in doc.page_content.lower() for term in found_terms):
                    return {"valid": True, "reason": "Numerical data found in context"}
            
            return {"valid": False, "reason": "Numerical data not found in context"}
        except Exception as e:
            return {"valid": False, "reason": f"Error in numerical validation: {str(e)}"}

    def get_uk_spinout_analysis(self) -> Dict:
        """Get analysis of UK academic spinout activity."""
        return self.analyze_question(
            "What are the top 3 academic institutions by spin out activity in the UK, "
            "how many companies do they spin out on average individually, "
            "and what is the top sector of UK academic spinouts?"
        )

    def get_quantum_computing_analysis(self) -> Dict:
        """Get analysis of Quantum Computing sub-sectors."""
        return self.analyze_question(
            "What's the top sub-sector of Quantum Computing by number of companies generated? "
            "Please provide specific numbers and trends."
        )

    def get_gaming_deal_analysis(self) -> Dict:
        """Get analysis of gaming early-stage VC deal values."""
        return self.analyze_question(
            "What's the CAGR of median gaming early-stage VC deal value and pre-money valuation ($M) "
            "in the segment of development? Please provide specific numbers and trends."
        ) 