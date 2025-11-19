#!/usr/bin/env python3
"""
Script di test per verificare che tutti gli import funzionino correttamente
dopo le modifiche al lazy loading e fix degli import LlamaIndex.
"""

import sys
import traceback
from pathlib import Path

# Aggiungi il percorso del progetto al PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_lazy_loading():
    """Testa il lazy loading di core/__init__.py"""
    print("\n" + "="*50)
    print("TEST: Lazy Loading in core/__init__.py")
    print("="*50)

    # Test 1: Import del modulo core
    try:
        import core
        print("✅ Import 'core' riuscito")
    except ImportError as e:
        print(f"❌ Errore import 'core': {e}")
        return False

    # Test 2: Verifica che __all__ sia definito
    try:
        all_exports = core.__all__
        print(f"✅ __all__ definito con {len(all_exports)} exports")
    except AttributeError:
        print("❌ __all__ non definito in core/__init__.py")
        return False

    # Test 3: Test lazy loading di ogni modulo
    print("\nTest lazy loading moduli:")
    for module_name in ['NormativeFetcher', 'DocxProcessor',
                       'ConfidenceScorer', 'LegalRAGEngine']:
        try:
            # Usa getattr per triggerare lazy loading
            module_class = getattr(core, module_name)
            print(f"  ✅ {module_name} caricato con successo")
        except (ImportError, AttributeError) as e:
            print(f"  ⚠️ {module_name} non disponibile: {e}")

    # Test 4: Verifica status function
    if hasattr(core, 'get_available_modules'):
        status = core.get_available_modules()
        print(f"\nModuli disponibili: {status['available']}")
        if status['unavailable']:
            print(f"Moduli non disponibili: {status['unavailable']}")

    return True

def test_llama_index_imports():
    """Testa che gli import di LlamaIndex siano corretti"""
    print("\n" + "="*50)
    print("TEST: Import LlamaIndex")
    print("="*50)

    imports_to_test = [
        ("llama_index.core", ["VectorStoreIndex", "Settings", "Document"]),
        ("llama_index.llms.ollama", ["Ollama"]),
        ("llama_index.embeddings.huggingface", ["HuggingFaceEmbedding"]),
        ("llama_index.vector_stores.chroma", ["ChromaVectorStore"]),
        ("llama_index.core.query_engine", ["CitationQueryEngine"]),
    ]

    all_success = True
    for module_path, classes in imports_to_test:
        try:
            module = __import__(module_path, fromlist=classes)
            for class_name in classes:
                if hasattr(module, class_name):
                    print(f"  ✅ {module_path}.{class_name}")
                else:
                    print(f"  ❌ {module_path}.{class_name} non trovato")
                    all_success = False
        except ImportError as e:
            print(f"  ❌ Impossibile importare {module_path}: {e}")
            all_success = False

    return all_success

def test_rag_engine_import():
    """Testa specificamente l'import di LegalRAGEngine"""
    print("\n" + "="*50)
    print("TEST: Import LegalRAGEngine")
    print("="*50)

    try:
        # Prova import diretto
        from core.rag_engine import LegalRAGEngine
        print("✅ Import diretto di LegalRAGEngine riuscito")

        # Prova tramite lazy loading
        from core import LegalRAGEngine as LegalRAGEngineLazy
        print("✅ Import tramite lazy loading riuscito")

        # Verifica che siano la stessa classe
        if LegalRAGEngine is LegalRAGEngineLazy:
            print("✅ Le due modalità di import restituiscono la stessa classe")

        return True

    except ImportError as e:
        print(f"❌ Errore import LegalRAGEngine: {e}")
        print("\nTraceback completo:")
        traceback.print_exc()
        return False

def test_confidence_scorer_import():
    """Testa import di ConfidenceScorer e componenti correlati"""
    print("\n" + "="*50)
    print("TEST: Import ConfidenceScorer")
    print("="*50)

    try:
        from core import ConfidenceScorer, CitationScore, ConfidenceLevel
        print("✅ Import ConfidenceScorer, CitationScore, ConfidenceLevel riuscito")

        # Verifica che siano classi/enum
        print(f"  ConfidenceScorer: {type(ConfidenceScorer)}")
        print(f"  CitationScore: {type(CitationScore)}")
        print(f"  ConfidenceLevel: {type(ConfidenceLevel)}")

        return True

    except ImportError as e:
        print(f"❌ Errore import ConfidenceScorer: {e}")
        traceback.print_exc()
        return False

def test_docx_processor_import():
    """Testa import di DocxProcessor"""
    print("\n" + "="*50)
    print("TEST: Import DocxProcessor")
    print("="*50)

    try:
        from core import DocxProcessor
        print("✅ Import DocxProcessor riuscito")

        # Verifica che sia una classe
        print(f"  DocxProcessor: {type(DocxProcessor)}")

        return True

    except ImportError as e:
        print(f"❌ Errore import DocxProcessor: {e}")
        traceback.print_exc()
        return False

def test_normative_fetcher_import():
    """Testa import di NormativeFetcher"""
    print("\n" + "="*50)
    print("TEST: Import NormativeFetcher")
    print("="*50)

    try:
        from core import NormativeFetcher
        print("✅ Import NormativeFetcher riuscito")

        # Verifica che sia una classe
        print(f"  NormativeFetcher: {type(NormativeFetcher)}")

        return True

    except ImportError as e:
        print(f"❌ Errore import NormativeFetcher: {e}")
        traceback.print_exc()
        return False

def test_import_status():
    """Testa la funzione print_import_status() di core"""
    print("\n" + "="*50)
    print("TEST: Import Status Function")
    print("="*50)

    try:
        import core

        if hasattr(core, 'print_import_status'):
            core.print_import_status()
            print("✅ print_import_status() eseguita con successo")
            return True
        else:
            print("⚠️ print_import_status() non trovata")
            return False

    except Exception as e:
        print(f"❌ Errore esecuzione print_import_status(): {e}")
        return False

def main():
    """Esegue tutti i test"""
    print("\n🔍 INIZIO TEST IMPORT")
    print("="*60)

    results = {
        "Lazy Loading": test_lazy_loading(),
        "LlamaIndex Imports": test_llama_index_imports(),
        "RAG Engine": test_rag_engine_import(),
        "ConfidenceScorer": test_confidence_scorer_import(),
        "DocxProcessor": test_docx_processor_import(),
        "NormativeFetcher": test_normative_fetcher_import(),
        "Import Status Function": test_import_status()
    }

    print("\n" + "="*60)
    print("📊 RISULTATI TEST:")
    print("="*60)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<40} {status}")

    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 TUTTI I TEST PASSATI!")
        print("\n✅ Il sistema è pronto per l'utilizzo.")
        print("   Puoi avviare l'applicazione con: streamlit run app.py")
    else:
        print("\n⚠️ ALCUNI TEST FALLITI - Verifica gli errori sopra")
        print("\nPossibili soluzioni:")
        print("1. Installa dipendenze: pip install -r requirements.txt")
        print("2. Verifica versioni: pip list | grep llama-index")
        print("3. Per Ollama: verifica sia in esecuzione con 'ollama serve'")

    print("="*60)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
