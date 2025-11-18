"""
Core module for Legal AI system.

Components:
- normative_fetcher: Download and manage Italian legal norms
- confidence_scorer: Evaluate reliability of generated content
- docx_processor: Handle DOCX templates and generation
- rag_engine: RAG system with LlamaIndex and citations
"""

from core.confidence_scorer import ConfidenceScorer, CitationScore, ConfidenceLevel
from core.docx_processor import DocxProcessor
from core.normative_fetcher import NormativeFetcher
from core.rag_engine import LegalRAGEngine

__version__ = "1.0.0"

__all__ = [
    "NormativeFetcher",
    "ConfidenceScorer",
    "DocxProcessor",
    "LegalRAGEngine",
    "CitationScore",
    "ConfidenceLevel",
]
