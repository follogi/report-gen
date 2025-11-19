#!/usr/bin/env python3
"""Script di verifica setup per Legal RAG Engine."""

import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test tutti gli import necessari."""
    logger.info("🧪 Test Import LlamaIndex...\n")

    tests = []

    # Test import critici
    import_tests = [
        ("llama_index.core", ["VectorStoreIndex", "Settings", "Document"]),
        ("llama_index.llms.ollama", ["Ollama"]),
        ("llama_index.embeddings.huggingface", ["HuggingFaceEmbedding"]),
        ("llama_index.vector_stores.chroma", ["ChromaVectorStore"]),
        ("chromadb", []),
        ("sentence_transformers", ["SentenceTransformer"]),
    ]

    for module_name, classes in import_tests:
        try:
            module = __import__(module_name, fromlist=classes if classes else [''])
            for cls in classes:
                getattr(module, cls)
            tests.append((True, module_name))
            logger.info(f"✅ {module_name}")
        except ImportError as e:
            tests.append((False, f"{module_name}: {e}"))
            logger.error(f"❌ {module_name}: {e}")

    return all(t[0] for t in tests)

def test_versions():
    """Verifica versioni pacchetti."""
    logger.info("\n📦 Versioni Pacchetti:\n")

    packages = [
        "llama_index",
        "chromadb",
        "sentence_transformers",
        "streamlit"
    ]

    for pkg_name in packages:
        try:
            pkg = __import__(pkg_name)
            version = getattr(pkg, '__version__', 'unknown')
            logger.info(f"  {pkg_name}: {version}")
        except ImportError:
            logger.error(f"  {pkg_name}: ❌ non installato")

def test_ollama():
    """Verifica connessione Ollama."""
    logger.info("\n🔌 Test Connessione Ollama...\n")

    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)

        if response.status_code == 200:
            models = response.json().get('models', [])
            logger.info(f"  ✅ Ollama raggiungibile ({len(models)} modelli)")
            if models:
                for model in models[:3]:  # Mostra solo primi 3
                    logger.info(f"     - {model['name']}")
        else:
            logger.warning(f"  ⚠️ Ollama status {response.status_code}")
    except Exception as e:
        logger.warning(f"  ⚠️ Ollama non raggiungibile: {e}")
        logger.info("  💡 Avvia con: ollama serve")

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("  VERIFICA SETUP LEGAL RAG ENGINE")
    logger.info("="*60 + "\n")

    test_versions()
    imports_ok = test_imports()
    test_ollama()

    logger.info("\n" + "="*60)
    if imports_ok:
        logger.info("🎉 Setup completato correttamente!")
        sys.exit(0)
    else:
        logger.error("⚠️ Alcuni problemi rilevati. Vedi errori sopra.")
        logger.info("\n💡 Per risolvere:")
        logger.info("   1. pip uninstall llama-index llama-index-core -y")
        logger.info("   2. pip install -r requirements.txt")
        sys.exit(1)
