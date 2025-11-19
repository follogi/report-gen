"""
Modulo di compatibilità per import LlamaIndex.

Gestisce gli import di LlamaIndex in modo sicuro, permettendo al resto
del codice di funzionare anche se LlamaIndex non è installato.
"""

import logging

logger = logging.getLogger(__name__)

# Flag per indicare se LlamaIndex è disponibile
LLAMAINDEX_AVAILABLE = False

# Placeholder per classi non disponibili
Ollama = None
Settings = None
HuggingFaceEmbedding = None
VectorStoreIndex = None
Document = None
StorageContext = None
ChromaVectorStore = None

try:
    from llama_index.llms.ollama import Ollama
    from llama_index.core import Settings
    LLAMAINDEX_AVAILABLE = True
    logger.info("✅ LlamaIndex Ollama disponibile")
except ImportError as e:
    logger.debug(f"LlamaIndex Ollama non disponibile: {e}")

try:
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
except ImportError as e:
    logger.debug(f"LlamaIndex HuggingFace embeddings non disponibile: {e}")

try:
    from llama_index.core import VectorStoreIndex, Document, StorageContext
except ImportError as e:
    logger.debug(f"LlamaIndex core non disponibile: {e}")

try:
    from llama_index.vector_stores.chroma import ChromaVectorStore
except ImportError as e:
    logger.debug(f"LlamaIndex ChromaVectorStore non disponibile: {e}")


def check_llamaindex_available() -> bool:
    """
    Verifica se LlamaIndex è installato e configurato.

    Returns:
        True se LlamaIndex è disponibile
    """
    return LLAMAINDEX_AVAILABLE


def get_missing_dependencies() -> list:
    """
    Restituisce lista di dipendenze LlamaIndex mancanti.

    Returns:
        Lista di stringhe con nomi pacchetti mancanti
    """
    missing = []

    if Ollama is None:
        missing.append("llama-index-llms-ollama")

    if HuggingFaceEmbedding is None:
        missing.append("llama-index-embeddings-huggingface")

    if VectorStoreIndex is None or Document is None:
        missing.append("llama-index-core")

    if ChromaVectorStore is None:
        missing.append("llama-index-vector-stores-chroma")

    return missing


def print_installation_help():
    """Stampa istruzioni per installare dipendenze mancanti."""
    missing = get_missing_dependencies()

    if not missing:
        print("✅ Tutte le dipendenze LlamaIndex sono installate")
        return

    print("\n⚠️ Dipendenze LlamaIndex mancanti:")
    print("\nPer installare le dipendenze mancanti:")
    print(f"\n  pip install {' '.join(missing)}")
    print("\nOppure reinstalla tutte le dipendenze:")
    print("  pip install -r requirements.txt\n")


if __name__ == "__main__":
    print("=== LlamaIndex Compatibility Check ===")
    print(f"LlamaIndex disponibile: {LLAMAINDEX_AVAILABLE}")
    print_installation_help()
