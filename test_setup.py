"""
Script di test per verificare che il setup sia corretto.

Esegui questo script dopo l'installazione per verificare che
tutti i componenti siano configurati correttamente.
"""

import sys
from pathlib import Path


def test_imports():
    """Test che tutti i moduli core si importino correttamente."""
    print("🧪 Test Import Moduli...")

    try:
        from core.normative_fetcher import NormativeFetcher
        print("  ✅ normative_fetcher")
    except ImportError as e:
        print(f"  ❌ normative_fetcher: {e}")
        return False

    try:
        from core.confidence_scorer import ConfidenceScorer
        print("  ✅ confidence_scorer")
    except ImportError as e:
        print(f"  ❌ confidence_scorer: {e}")
        return False

    try:
        from core.docx_processor import DocxProcessor
        print("  ✅ docx_processor")
    except ImportError as e:
        print(f"  ❌ docx_processor: {e}")
        return False

    try:
        from core.rag_engine import LegalRAGEngine
        print("  ✅ rag_engine")
    except ImportError as e:
        print(f"  ❌ rag_engine: {e}")
        return False

    return True


def test_directories():
    """Test che le directory necessarie esistano."""
    print("\n📁 Test Directory...")

    required_dirs = [
        "data/normative_base",
        "data/normative_custom",
        "data/esempi",
        "data/templates",
        "vectordb/normative_core",
        "vectordb/session",
        "config",
        "logs",
        "cache/embeddings"
    ]

    all_exist = True

    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"  ✅ {dir_path}")
        else:
            print(f"  ❌ {dir_path} - MANCANTE!")
            all_exist = False

    return all_exist


def test_config_files():
    """Test che i file di configurazione esistano."""
    print("\n⚙️ Test File Configurazione...")

    required_files = [
        "config/settings.yaml",
        "config/prompts.yaml",
        "requirements.txt"
    ]

    all_exist = True

    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - MANCANTE!")
            all_exist = False

    return all_exist


def test_ollama():
    """Test connessione a Ollama."""
    print("\n🤖 Test Ollama...")

    try:
        import requests

        response = requests.get("http://localhost:11434/api/tags", timeout=5)

        if response.status_code == 200:
            print("  ✅ Ollama in esecuzione")

            # Controlla se Mistral è disponibile
            data = response.json()
            models = [m['name'] for m in data.get('models', [])]

            if any('mistral' in m for m in models):
                print("  ✅ Modello Mistral disponibile")
                return True
            else:
                print("  ⚠️  Modello Mistral non trovato")
                print("     Esegui: ollama pull mistral")
                return False
        else:
            print(f"  ❌ Ollama risponde con status {response.status_code}")
            return False

    except requests.RequestException:
        print("  ❌ Ollama non raggiungibile")
        print("     Avvia Ollama con: ollama serve")
        return False


def test_python_version():
    """Test versione Python."""
    print("\n🐍 Test Versione Python...")

    version = sys.version_info

    if version.major == 3 and version.minor >= 10:
        print(f"  ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"  ❌ Python {version.major}.{version.minor}.{version.micro}")
        print("     Richiesto: Python 3.10+")
        return False


def main():
    """Esegue tutti i test."""
    print("=" * 60)
    print("🔍 VERIFICA SETUP LEGAL AI SYSTEM")
    print("=" * 60)

    results = {
        "Python Version": test_python_version(),
        "Import Moduli": test_imports(),
        "Directory": test_directories(),
        "Config Files": test_config_files(),
        "Ollama": test_ollama()
    }

    print("\n" + "=" * 60)
    print("📊 RIEPILOGO")
    print("=" * 60)

    for test_name, result in results.items():
        status = "✅ OK" if result else "❌ ERRORE"
        print(f"{test_name:.<40} {status}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)

    if all_passed:
        print("🎉 SETUP COMPLETATO CORRETTAMENTE!")
        print("\nPuoi avviare l'applicazione con:")
        print("  streamlit run app.py")
    else:
        print("⚠️  ALCUNI TEST HANNO FALLITO")
        print("\nControlla gli errori sopra e:")
        print("  1. Installa dipendenze: pip install -r requirements.txt")
        print("  2. Avvia Ollama: ollama serve")
        print("  3. Scarica Mistral: ollama pull mistral")

    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
