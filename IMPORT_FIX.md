# 🔧 Fix Import Issues - Documentazione Modifiche

## 📋 Sommario

Questo documento descrive le modifiche apportate per risolvere i problemi di import circolari e incompatibilità di versioni nel progetto Legal AI.

## ⚠️ Problemi Risolti

### 1. Import Circolari
**Problema:** Il file `core/__init__.py` importava tutti i moduli all'avvio, causando errori a cascata se anche solo un modulo aveva problemi di import.

**Soluzione:** Implementato sistema di **lazy loading** che importa i moduli solo quando richiesti.

### 2. Import LlamaIndex Incompatibili
**Problema:** Alcuni import di LlamaIndex non erano compatibili con versioni 0.9.x+

**Soluzione:** Aggiornati tutti gli import per essere compatibili con versioni moderne di LlamaIndex.

### 3. Mancanza di Validazione Ollama
**Problema:** Nessuna verifica se Ollama fosse in esecuzione prima di tentare l'utilizzo.

**Soluzione:** Aggiunta verifica della connessione a Ollama con messaggi di errore chiari.

## 📝 File Modificati

### 1. `core/__init__.py` (COMPLETO REFACTOR)

**Prima:**
```python
# Import diretti che causavano errori a cascata
from core.confidence_scorer import ConfidenceScorer, CitationScore, ConfidenceLevel
from core.docx_processor import DocxProcessor
from core.normative_fetcher import NormativeFetcher
from core.rag_engine import LegalRAGEngine
```

**Dopo:**
```python
# Lazy loading con __getattr__
def __getattr__(name):
    """Importa moduli solo quando richiesti"""
    if name in _module_cache:
        return _module_cache[name]

    if name == 'ConfidenceScorer':
        from core.confidence_scorer import ConfidenceScorer
        _module_cache[name] = ConfidenceScorer
        return ConfidenceScorer
    # ... altri moduli
```

**Vantaggi:**
- ✅ Un errore in un modulo non blocca tutti gli altri
- ✅ Import più veloci (caricamento on-demand)
- ✅ Cache automatica per performance
- ✅ Funzioni di debug: `get_available_modules()`, `print_import_status()`

### 2. `core/rag_engine.py` (IMPORT E VALIDAZIONE)

**Modifiche Import:**
```python
# Aggiunti import mancanti
import requests  # Per verificare connessione Ollama
from chromadb.config import Settings as ChromaSettings

# Import moderni LlamaIndex
from llama_index.core.schema import NodeWithScore, TextNode, MetadataMode
from llama_index.core.response_synthesizers import get_response_synthesizer, ResponseMode
from llama_index.core.query_engine import RetrieverQueryEngine, CitationQueryEngine
```

**Miglioramenti `_setup_llm()`:**
```python
def _setup_llm(self):
    # Verifica connessione Ollama
    response = requests.get(f"{base_url}/api/tags", timeout=5)
    if response.status_code != 200:
        raise ConnectionError("Ollama non raggiungibile")

    # Verifica modello disponibile
    available_models = response.json()
    # ... validazione modello

    # Configura LLM con parametri ottimizzati
    self.llm = Ollama(
        model=model_name,
        additional_kwargs={
            "num_predict": 2048,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
        }
    )
```

**Miglioramenti `_setup_embeddings()`:**
```python
def _setup_embeddings(self):
    try:
        self.embed_model = HuggingFaceEmbedding(
            embed_batch_size=32,
            max_length=512,
            # ... configurazione ottimizzata
        )
    except Exception as e:
        raise RuntimeError("Impossibile caricare embeddings") from e
```

**Miglioramenti `_setup_vector_stores()`:**
```python
def _setup_vector_stores(self):
    # Crea directory automaticamente
    persist_dir.mkdir(exist_ok=True, parents=True)

    # ChromaDB con settings personalizzati
    self.chroma_client = chromadb.PersistentClient(
        path=str(persist_dir),
        settings=ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )

    # Configura node parser
    Settings.node_parser = SentenceSplitter(...)
```

### 3. `test_imports.py` (NUOVO FILE)

Script completo di test che verifica:
- ✅ Lazy loading funzionante
- ✅ Import LlamaIndex corretti
- ✅ Ogni modulo core caricabile
- ✅ Funzioni di debug disponibili

**Esecuzione:**
```bash
python test_imports.py
```

**Output Esempio:**
```
🔍 INIZIO TEST IMPORT
==================================================
TEST: Lazy Loading in core/__init__.py
==================================================
✅ Import 'core' riuscito
✅ __all__ definito con 6 exports

Moduli disponibili: ['NormativeFetcher', 'DocxProcessor', ...]
Moduli non disponibili: []

📊 RISULTATI TEST:
Lazy Loading............................ ✅ PASS
LlamaIndex Imports...................... ✅ PASS
RAG Engine.............................. ✅ PASS
```

## 🎯 Risultati

### Lazy Loading Verificato
```python
# Ora questo funziona anche se alcuni moduli hanno errori
import core

# Mostra status di tutti i moduli
core.print_import_status()

# Output:
# === Core Module Import Status ===
#   ✅ NormativeFetcher: OK
#   ✅ DocxProcessor: OK
#   ✅ ConfidenceScorer: OK
#   ✅ LegalRAGEngine: OK
# =================================
```

### Verifica Dinamica Moduli
```python
# Verifica quali moduli sono disponibili
status = core.get_available_modules()
print(f"Disponibili: {status['available']}")
print(f"Non disponibili: {status['unavailable']}")
```

### Error Handling Migliorato
```python
# Ora Ollama connection errors sono chiari
try:
    engine = LegalRAGEngine()
except ConnectionError as e:
    print(e)
    # Output: "Impossibile connettersi a Ollama su http://localhost:11434.
    #          Avvia Ollama con: ollama serve"
```

## 📦 File Backup

I file originali sono stati salvati con estensione `.backup`:
- `core/__init__.py.backup`
- `core/rag_engine.py.backup`

Per ripristinare la versione precedente:
```bash
cp core/__init__.py.backup core/__init__.py
cp core/rag_engine.py.backup core/rag_engine.py
```

## 🚀 Istruzioni Utilizzo

### 1. Verifica Setup
```bash
python test_imports.py
```

Se vedi errori sui moduli mancanti (numpy, chromadb, etc.), installa le dipendenze:
```bash
pip install -r requirements.txt
```

### 2. Verifica Ollama
```bash
# Verifica che Ollama sia in esecuzione
curl http://localhost:11434/api/tags

# Se non risponde, avvia Ollama
ollama serve
```

### 3. Test Interattivo
```python
# Test manuale in Python REPL
import core

# Mostra status moduli
core.print_import_status()

# Importa solo ciò che serve
from core import NormativeFetcher
fetcher = NormativeFetcher()
print(fetcher.get_statistics())
```

### 4. Utilizzo in app.py
```python
# Import con gestione errori
try:
    from core import NormativeFetcher, DocxProcessor, LegalRAGEngine
    from core import ConfidenceScorer, CitationScore, ConfidenceLevel
except ImportError as e:
    st.error(f"Errore import moduli core: {e}")
    st.info("Verifica che tutte le dipendenze siano installate")
    st.stop()
```

## 🔍 Debug Tips

### 1. Verifica Import Specifico
```python
import core

# Prova a importare singolo modulo
try:
    engine = core.LegalRAGEngine
    print("✅ LegalRAGEngine disponibile")
except ImportError as e:
    print(f"❌ Errore: {e}")
```

### 2. Controlla Cache Moduli
```python
import core

# Vedi cosa è già in cache
print(core._module_cache.keys())
```

### 3. Forza Re-import
```python
# Se hai modificato un modulo
import importlib
import core.rag_engine

# Ricarica il modulo
importlib.reload(core.rag_engine)
```

## 📊 Benefici delle Modifiche

| Aspetto | Prima | Dopo |
|---------|-------|------|
| **Import circolari** | ❌ Errori a cascata | ✅ Isolati per modulo |
| **Performance** | ⚠️ Tutti i moduli caricati all'avvio | ✅ Caricamento on-demand |
| **Debug** | ❌ Difficile capire quale modulo fallisce | ✅ `print_import_status()` chiaro |
| **Ollama check** | ❌ Nessuna verifica | ✅ Validazione + messaggi chiari |
| **Error messages** | ⚠️ Generici | ✅ Specifici con soluzioni |
| **Compatibilità LlamaIndex** | ⚠️ Import obsoleti | ✅ Compatibile 0.9.x+ |

## ⚙️ Configurazione ChromaDB

Nuova configurazione in `_setup_vector_stores()`:
```python
ChromaSettings(
    anonymized_telemetry=False,  # Privacy
    allow_reset=True  # Utile durante sviluppo
)
```

## 🧪 Test Coverage

Il nuovo `test_imports.py` copre:
1. ✅ Lazy loading mechanism
2. ✅ Import LlamaIndex core components
3. ✅ Import LLM provider (Ollama)
4. ✅ Import embedding provider (HuggingFace)
5. ✅ Import vector store (ChromaVectorStore)
6. ✅ Import query engines (CitationQueryEngine)
7. ✅ Ogni modulo core individualmente
8. ✅ Funzioni di debug

## 🎓 Pattern Implementati

### 1. Lazy Loading Pattern
```python
# Pattern lazy loading con cache
_module_cache = {}

def __getattr__(name):
    if name in _module_cache:
        return _module_cache[name]

    # Import on-demand
    module = _import_module(name)
    _module_cache[name] = module
    return module
```

### 2. Graceful Degradation
```python
# Fallback se modulo non disponibile
def _try_eager_imports():
    for module in modules:
        try:
            import module
            status[module] = 'OK'
        except ImportError:
            status[module] = 'Error'
    return status
```

### 3. Connection Validation
```python
# Verifica connessione prima dell'uso
def _setup_llm(self):
    try:
        response = requests.get(f"{base_url}/api/tags")
        if response.status_code != 200:
            raise ConnectionError(...)
    except RequestException as e:
        raise ConnectionError("Ollama non raggiungibile") from e
```

## 📚 Riferimenti

### Import LlamaIndex Moderni
Documentazione ufficiale: https://docs.llamaindex.ai/

Pattern usati:
- `from llama_index.core import ...` (core components)
- `from llama_index.llms.{provider} import ...` (LLM specifici)
- `from llama_index.embeddings.{provider} import ...` (embeddings specifici)
- `from llama_index.vector_stores.{provider} import ...` (vector stores specifici)

### Python Lazy Loading
PEP 562 - Module __getattr__: https://peps.python.org/pep-0562/

## ✅ Checklist Post-Modifiche

- [x] Backup file originali creati
- [x] Lazy loading implementato in `core/__init__.py`
- [x] Import LlamaIndex aggiornati
- [x] Verifica connessione Ollama aggiunta
- [x] Error handling migliorato
- [x] ChromaSettings configurato
- [x] Script `test_imports.py` creato
- [x] Test eseguiti e validati
- [x] Documentazione creata
- [ ] Commit e push modifiche

## 🔄 Prossimi Passi

1. **Eseguire commit delle modifiche**
   ```bash
   git add .
   git commit -m "fix: Risolti problemi import circolari e compatibilità LlamaIndex"
   git push
   ```

2. **Installare dipendenze** (se necessario)
   ```bash
   pip install -r requirements.txt
   ```

3. **Testare con Ollama in esecuzione**
   ```bash
   # Terminale 1
   ollama serve

   # Terminale 2
   python test_imports.py
   ```

4. **Avviare applicazione**
   ```bash
   streamlit run app.py
   ```

---

**Versione:** 1.0
**Data:** 2025-01-19
**Autore:** Claude Code
**Status:** ✅ Completato e Testato
