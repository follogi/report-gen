# 📦 Manifest del Progetto Legal AI

Questo documento elenca tutti i file e componenti creati per il sistema di generazione relazioni legali.

## 🎯 Struttura Completa

### Directory Principali

```
legal-ai-poc/
├── core/                   # Moduli Python core
├── config/                 # File di configurazione
├── data/                   # Dati e documenti
│   ├── normative_base/     # Normative italiane (scaricate runtime)
│   ├── normative_custom/   # Normative custom utente
│   ├── esempi/             # Esempi temporanei sessione
│   └── templates/          # Template DOCX
├── vectordb/               # Database vettoriale ChromaDB
│   ├── normative_core/     # Indice normative (persistente)
│   └── session/            # Indice esempi (temporaneo)
├── logs/                   # Log applicazione
└── cache/                  # Cache embeddings
    └── embeddings/
```

## 📄 File Core

### Applicazione Principale

| File | Dimensione | Descrizione |
|------|------------|-------------|
| `app.py` | ~22KB | Entry point Streamlit - Interfaccia multi-tab |
| `create_template.py` | ~0.5KB | Script creazione template DOCX esempio |
| `test_setup.py` | ~6KB | Script verifica setup corretto |

### Moduli Core (`core/`)

| File | Dimensione | Descrizione |
|------|------------|-------------|
| `__init__.py` | ~0.7KB | Package initialization |
| `normative_fetcher.py` | ~18KB | Download e gestione normative da Normattiva.it |
| `confidence_scorer.py` | ~19KB | Sistema valutazione affidabilità citazioni |
| `docx_processor.py` | ~22KB | Parsing template e generazione DOCX |
| `rag_engine.py` | ~21KB | RAG con LlamaIndex e CitationQueryEngine |

**Totale moduli core:** ~80KB di codice Python

### Configurazione (`config/`)

| File | Dimensione | Descrizione |
|------|------------|-------------|
| `settings.yaml` | ~1.4KB | Configurazione generale sistema |
| `prompts.yaml` | ~4.1KB | Template prompts in italiano |

### Documentazione

| File | Dimensione | Descrizione |
|------|------------|-------------|
| `README.md` | ~12KB | Documentazione completa |
| `QUICK_START.md` | ~2KB | Guida rapida avvio |
| `MANIFEST.md` | Questo file | Elenco componenti |
| `LICENSE` | ~1.5KB | Licenza MIT + disclaimer |

### Configurazione Sviluppo

| File | Descrizione |
|------|-------------|
| `.gitignore` | Esclusioni git (logs, cache, venv, etc.) |
| `.env.example` | Template configurazione environment |
| `requirements.txt` | Dipendenze Python |

## 🔧 Componenti Funzionali

### 1. NormativeFetcher (`normative_fetcher.py`)

**Responsabilità:**
- Download normative da Normattiva.it via API REST
- Parsing HTML/XML delle normative
- Salvataggio strutturato in JSON (metadata + articoli)
- Cache con hash MD5 per evitare re-download
- Fallback automatico se Normattiva.it non disponibile

**Normative Prioritarie Supportate:**
- Costituzione della Repubblica Italiana (1947)
- Codice Civile (1942)
- Codice Penale (1930)
- Codice di Procedura Civile (1940)
- Codice del Consumo (2005)
- Codice Privacy (2003)

**API Pubbliche:**
- `download_normativa(codice)`: Scarica singola normativa
- `download_all_prioritarie()`: Scarica tutte le normative base
- `get_normativa(codice)`: Recupera normativa cached
- `get_articolo(codice, numero)`: Recupera singolo articolo
- `is_normativa_cached(codice)`: Verifica cache
- `clear_cache()`: Pulisce cache

### 2. ConfidenceScorer (`confidence_scorer.py`)

**Responsabilità:**
- Calcolo confidence score (0-1) per ogni citazione
- Classificazione in livelli: HIGH (>0.8), MEDIUM (0.5-0.8), LOW (<0.5)
- Algoritmo di scoring con boost/penalità:
  - Boost: citazione esatta articolo (+0.15)
  - Boost: metadata completi (+0.1)
  - Penalità: keyword mancanti (-0.2)
  - Penalità: testo troppo breve (-0.1)
- Generazione report di affidabilità
- Mapping a colori per highlighting DOCX

**API Pubbliche:**
- `score_retrieval(query, chunks)`: Score chunks RAG
- `score_generated_text(text, citations)`: Score testo generato
- `generate_report(sections)`: Report completo
- `get_highlight_color(score)`: Colore per DOCX

### 3. DocxProcessor (`docx_processor.py`)

**Responsabilità:**
- Parsing template DOCX con identificazione:
  - Placeholders: `{{VARIABILE}}` o `<<<VARIABILE>>>`
  - Sezioni ripetibili: `<<<LOOP_START:NAME>>>` ... `<<<LOOP_END:NAME>>>`
- Generazione documento finale:
  - Sostituzione variabili preservando formattazione
  - Inserimento contenuto generato
  - Highlighting basato su confidence:
    - Verde: score > 0.8
    - Giallo: score 0.5-0.8
    - Rosa: score < 0.5
  - Citazioni in apice numerato
- Aggiunta bibliografia automatica
- Export bibliografia in TXT

**API Pubbliche:**
- `parse_template(path)`: Analizza template
- `generate_document(template, output, variables, content, citations)`: Genera DOCX
- `export_bibliography_txt(citations, output)`: Esporta bibliografia
- `create_sample_template(output)`: Crea template esempio

### 4. LegalRAGEngine (`rag_engine.py`)

**Responsabilità:**
- Orchestrazione RAG completa con LlamaIndex
- Doppio indice ChromaDB:
  - Normative (persistente): `normative_v1`
  - Esempi (temporaneo): `session_TIMESTAMP`
- Configurazione LLM:
  - Ollama locale (Mistral-7B)
  - Temperature: 0.1 (deterministico)
  - Context window: 8192 token
- Embeddings:
  - HuggingFace: `all-MiniLM-L6-v2`
  - Cache locale per performance
- CitationQueryEngine per tracciabilità
- Chunking specializzato per articoli di legge:
  - Chunk size: 512
  - Overlap: 50
  - Separator: `\n\n`

**API Pubbliche:**
- `build_normative_index(force_rebuild)`: Costruisce/carica indice normative
- `build_esempi_index(files, session_id)`: Costruisce indice esempi temporaneo
- `query_with_citations(query, confidence_threshold, top_k)`: Query con citazioni
- `generate_legal_document(request, template, esempi, style)`: Genera documento completo
- `clear_session_index(session_id)`: Pulisce indice temporaneo
- `get_statistics()`: Statistiche sistema

## 📊 Statistiche Codice

### Linee di Codice (approssimative)

| Componente | Linee |
|------------|-------|
| `normative_fetcher.py` | ~600 |
| `confidence_scorer.py` | ~650 |
| `docx_processor.py` | ~750 |
| `rag_engine.py` | ~700 |
| `app.py` | ~800 |
| **Totale Core** | **~3500** |

### Dipendenze Python

**Totale pacchetti:** ~25

**Categorie:**
- Framework Web: streamlit
- RAG: llama-index (+ 4 plugin)
- Vector DB: chromadb
- Document Processing: python-docx, PyPDF2
- NLP: sentence-transformers, transformers
- ML: torch
- Utility: pyyaml, requests, tqdm, colorama

**Dimensione download stimata:** ~2-3 GB (include modelli embedding)

## 🎨 Interfaccia Utente (Streamlit)

### Tab 1: 📚 Gestione Normative

**Componenti:**
- Tree view normative caricate (con expanders)
- Upload normative custom (drag & drop)
- Bottone "Ricostruisci Database"
- Modal download normative prioritarie
- Statistiche: numero normative, articoli, spazio disco

### Tab 2: 📄 Documenti Sessione

**Componenti:**
- File uploader template DOCX
- Preview struttura template (variabili, sezioni)
- Multi-file uploader esempi
- Lista file caricati con rimozione
- Bottone "Analizza Esempi"
- Bottone "Pulisci Sessione"

### Tab 3: ⚙️ Genera Relazione

**Componenti:**
- Text area prompt (pre-compilato)
- Expander "Opzioni Avanzate":
  - Slider confidence threshold
  - Checkbox "Solo normative citate"
  - Select stile (formale/semi-formale/sintetico)
  - Slider top_k (fonti da recuperare)
- Form variabili template (dinamico)
- Progress bar multi-step (5 fasi)
- Bottone "Genera Relazione" (primary)

### Tab 4: 📥 Risultato

**Componenti:**
- Preview documento con highlighting
- Sidebar citazioni (expandable)
- Bottoni download:
  - DOCX completo
  - Bibliografia TXT
  - Report Confidence JSON
- Report affidabilità:
  - Score complessivo
  - Breakdown citazioni (alta/media/bassa)
  - Raccomandazioni

## 🔐 Sicurezza e Privacy

### Dati Sensibili

**NON memorizzati in git:**
- Database normative (troppo grande)
- Cache embeddings (ricostruibile)
- File esempi utente (temporanei)
- Log con informazioni sessione
- Output generati

**Inclusi in .gitignore:**
```
vectordb/
cache/
logs/*.log
data/normative_base/*
data/normative_custom/*
data/esempi/*
output_*.docx
```

### Esecuzione Locale

- ✅ LLM locale (Ollama)
- ✅ Embeddings locali (HuggingFace cache)
- ✅ Database locale (ChromaDB)
- ✅ Nessuna API key esterna richiesta
- ✅ Nessun dato inviato a servizi cloud

## 🧪 Testing

### Script di Test

- `test_setup.py`: Verifica completa setup
  - Python version
  - Import moduli
  - Directory esistenti
  - File configurazione
  - Connessione Ollama

### Test Moduli Singoli

Ogni modulo core ha una funzione `main()` per test standalone:

```bash
python -m core.normative_fetcher  # Test download normative
python -m core.confidence_scorer  # Test scoring
python -m core.docx_processor     # Test DOCX
python -m core.rag_engine         # Test RAG
```

## 📈 Performance

### Tempi Stimati

| Operazione | Prima volta | Successive |
|------------|-------------|------------|
| Setup iniziale | 10 min | - |
| Download normative base | 2-5 min | - |
| Build indice normative | 1-3 min | 5-10 sec |
| Caricamento esempi | 10-30 sec | - |
| Generazione relazione | 30-60 sec | 30-60 sec |

### Spazio Disco

| Componente | Dimensione |
|------------|------------|
| Dipendenze Python | ~2-3 GB |
| Ollama Mistral-7B | ~4 GB |
| Normative base | ~10-50 MB |
| Indice ChromaDB | ~50-100 MB |
| Cache embeddings | ~100-200 MB |
| **Totale stimato** | **~6-8 GB** |

## 🔄 Workflow Tipico

1. **Setup** (una volta)
   - Installa dipendenze
   - Scarica Mistral
   - Download normative base

2. **Nuova Sessione**
   - Upload template
   - Upload esempi
   - Genera relazione
   - Download DOCX

3. **Iterazione**
   - Modifica prompt
   - Ajusta confidence threshold
   - Ri-genera
   - Confronta risultati

## 📦 Deliverables

Questo progetto fornisce:

1. ✅ **Codice sorgente completo** (~3500 LOC)
2. ✅ **Documentazione dettagliata** (README + Quick Start)
3. ✅ **Configurazione pronta all'uso** (YAML)
4. ✅ **Script di utilità** (setup test, template creator)
5. ✅ **Sistema end-to-end funzionante** (POC completa)

## 🎓 Tecnologie e Pattern

### Design Patterns

- **Singleton**: Session state Streamlit
- **Factory**: Creazione documenti DOCX
- **Strategy**: Stili di generazione (formale/semi-formale/sintetico)
- **Observer**: Progress callbacks durante download

### Architettura

- **Layered**: UI (Streamlit) → Business Logic (Core) → Data (ChromaDB/Files)
- **RAG**: Retrieval Augmented Generation
- **Pipeline**: Fetch → Index → Query → Generate → Export

### Best Practices

- ✅ Type hints ovunque
- ✅ Docstrings complete in italiano
- ✅ Error handling robusto
- ✅ Logging strutturato
- ✅ Configurazione esternalizzata
- ✅ Separation of concerns

---

**Versione Manifest:** 1.0.0
**Data:** Novembre 2025
**Totale File Creati:** ~20 file
**Totale Directory:** 15
**Dimensione Progetto:** ~100 KB (codice) + 6-8 GB (runtime con dipendenze)
