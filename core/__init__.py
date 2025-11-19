"""
Core module con lazy loading per evitare import circolari e errori a cascata.
I moduli vengono importati solo quando effettivamente richiesti.
"""

__version__ = "0.1.0"

# Lista dei moduli disponibili per l'export
__all__ = [
    # Confidence Scorer
    'ConfidenceScorer',
    'CitationScore',
    'ConfidenceLevel',
    # Document Processor
    'DocxProcessor',
    # Normative Fetcher
    'NormativeFetcher',
    # RAG Engine
    'LegalRAGEngine',
]

# Cache per moduli già importati
_module_cache = {}

def __getattr__(name):
    """
    Lazy loading dei moduli - importa solo quando richiesto.
    Questo previene errori a cascata se un modulo ha problemi di import.
    """
    # Check cache first
    if name in _module_cache:
        return _module_cache[name]

    # Confidence Scorer components
    if name in ['ConfidenceScorer', 'CitationScore', 'ConfidenceLevel']:
        try:
            from core.confidence_scorer import (
                ConfidenceScorer,
                CitationScore,
                ConfidenceLevel
            )
            if name == 'ConfidenceScorer':
                _module_cache[name] = ConfidenceScorer
                return ConfidenceScorer
            elif name == 'CitationScore':
                _module_cache[name] = CitationScore
                return CitationScore
            elif name == 'ConfidenceLevel':
                _module_cache[name] = ConfidenceLevel
                return ConfidenceLevel
        except ImportError as e:
            raise ImportError(f"Impossibile importare {name} da confidence_scorer: {e}")

    # Document Processor
    elif name == 'DocxProcessor':
        try:
            from core.docx_processor import DocxProcessor
            _module_cache[name] = DocxProcessor
            return DocxProcessor
        except ImportError as e:
            raise ImportError(f"Impossibile importare DocxProcessor: {e}")

    # Normative Fetcher
    elif name == 'NormativeFetcher':
        try:
            from core.normative_fetcher import NormativeFetcher
            _module_cache[name] = NormativeFetcher
            return NormativeFetcher
        except ImportError as e:
            raise ImportError(f"Impossibile importare NormativeFetcher: {e}")

    # RAG Engine
    elif name == 'LegalRAGEngine':
        try:
            from core.rag_engine import LegalRAGEngine
            _module_cache[name] = LegalRAGEngine
            return LegalRAGEngine
        except ImportError as e:
            raise ImportError(f"Impossibile importare LegalRAGEngine: {e}")

    # Attribute not found
    raise AttributeError(f"Il modulo '{__name__}' non ha l'attributo '{name}'")

def get_available_modules():
    """
    Utility function per verificare quali moduli sono disponibili.
    Utile per debug.
    """
    available = []
    unavailable = []

    for module_name in __all__:
        try:
            # Prova ad importare
            _ = __getattr__(module_name)
            available.append(module_name)
        except ImportError:
            unavailable.append(module_name)

    return {
        'available': available,
        'unavailable': unavailable
    }

# Per backward compatibility, prova ad importare i moduli principali
# ma non fallire se ci sono problemi
def _try_eager_imports():
    """
    Prova ad importare eagerly i moduli principali per verificare
    che siano disponibili, ma non fallire se ci sono problemi.
    """
    modules_status = {}

    try:
        from core.normative_fetcher import NormativeFetcher
        modules_status['NormativeFetcher'] = 'OK'
    except ImportError as e:
        modules_status['NormativeFetcher'] = f'Error: {str(e)}'

    try:
        from core.docx_processor import DocxProcessor
        modules_status['DocxProcessor'] = 'OK'
    except ImportError as e:
        modules_status['DocxProcessor'] = f'Error: {str(e)}'

    try:
        from core.confidence_scorer import ConfidenceScorer
        modules_status['ConfidenceScorer'] = 'OK'
    except ImportError as e:
        modules_status['ConfidenceScorer'] = f'Error: {str(e)}'

    try:
        from core.rag_engine import LegalRAGEngine
        modules_status['LegalRAGEngine'] = 'OK'
    except ImportError as e:
        modules_status['LegalRAGEngine'] = f'Error: {str(e)}'

    return modules_status

# Store status for debugging
_import_status = _try_eager_imports()

def print_import_status():
    """Stampa lo stato degli import per debugging."""
    print("\n=== Core Module Import Status ===")
    for module, status in _import_status.items():
        emoji = "✅" if status == "OK" else "❌"
        print(f"  {emoji} {module}: {status}")
    print("=================================\n")
