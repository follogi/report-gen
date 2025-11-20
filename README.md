# ⚖️ Legal AI - Sistema Generazione Relazioni Legali

Sistema completo di generazione relazioni legali basato su AI che elimina il rischio di allucinazioni attraverso citazioni rigorose delle fonti normative italiane.

## 🎯 Caratteristiche Principali

- **RAG con LlamaIndex**: Retrieval Augmented Generation per risposte basate su fonti verificate
- **CitationQueryEngine**: Ogni affermazione è tracciabile a una fonte specifica
- **Confidence Scoring**: Sistema di valutazione dell'affidabilità di ogni citazione
- **Highlighting Automatico**: Evidenziazione colorata basata sul livello di confidenza
- **Normative Italiane**: Database di normative italiane (Costituzione, Codici, etc.)
- **Interfaccia Streamlit**: UI multi-tab intuitiva per gestione completa
- **Locale e Privato**: Tutto in esecuzione locale con Ollama, nessun dato a servizi cloud

## 🏗️ Architettura

### Stack Tecnologico

- **Frontend**: Streamlit (interfaccia web)
- **Backend**: Python 3.10+
- **RAG Framework**: LlamaIndex con CitationQueryEngine
- **Vector Database**: ChromaDB (persistente)
- **LLM**: Ollama con Mistral-7B (locale)
- **Document Processing**: python-docx, PyPDF2
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2

### Componenti Core

```
core/
├── normative_fetcher.py    # Download normative da Normattiva.it
├── rag_engine.py           # RAG con LlamaIndex e CitationQueryEngine
├── confidence_scorer.py    # Valutazione affidabilità citazioni
└── docx_processor.py       # Gestione template DOCX e generazione
```

## 📋 Prerequisiti

### 1. Python 3.10+

```bash
python --version  # Deve essere >= 3.10
```

### 2. Ollama

Installare Ollama dal sito ufficiale: https://ollama.ai

```bash
# Linux/Mac
curl -fsSL https://ollama.ai/install.sh | sh

# Verifica installazione
ollama --version
```

### 3. Modello Mistral

```bash
# Scarica modello Mistral (circa 4GB)
ollama pull mistral

# Avvia server Ollama (in un terminale separato)
ollama serve
```

## 📋 Setup Normative

Il sistema carica normative da file JSON locali invece di scaricarle automaticamente.

### Formato JSON Normative

Crea file JSON nella directory `data/normative/` con questo formato:

```json
{
  "codice": "CC",
  "urlFonte": "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262",
  "dataDownload": "2024-11-20T10:30:00Z",
  "testiArticoli": [
    "Art. 1 - Fonti del diritto. Sono fonti del diritto: 1) le leggi; 2) i regolamenti...",
    "Art. 2 - Abrogazione delle leggi. Le leggi non sono abrogate che da leggi posteriori...",
    "Art. 2043 - Risarcimento per fatto illecito. Qualunque fatto doloso o colposo..."
  ]
}
```

**Campi:**
- `codice`: Identificativo breve (es: "CC", "CP", "CPC")
- `urlFonte`: URL fonte originale (opzionale, per tracciabilità)
- `dataDownload`: Timestamp ISO 8601
- `testiArticoli`: Array di stringhe, ogni elemento è un articolo completo con numero e testo

### Preparare le Normative

1. Scarica le normative che ti servono da fonti ufficiali
2. Crea un file JSON per ogni normativa
3. Posiziona i file in `data/normative/`
4. Il sistema caricherà automaticamente tutti i file `.json` trovati

**Esempio:**
```bash
data/normative/
├── codice_civile.json
├── codice_penale.json
├── codice_procedura_civile.json
└── esempio.json  # File di test già incluso
```

## 🚀 Installazione

### Prerequisiti
- Python 3.10 o 3.11
- Ollama installato e in esecuzione

### Installazione

1. **Crea virtual environment:**
```bash
python3.10 -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate
```

2. **Installa dipendenze:**
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

3. **Verifica installazione:**
```bash
python test_setup.py
```

4. **Configura Ollama:**
```bash
# In un terminale separato
ollama serve

# In un altro terminale
ollama pull mistral:latest
ollama pull nomic-embed-text
```

**Nota**: L'installazione può richiedere alcuni minuti per scaricare tutti i modelli di embedding.

### 4. Verifica Struttura Directory

La struttura dovrebbe essere:

```
legal-ai-poc/
├── app.py                  # Entry point Streamlit
├── core/                   # Moduli core
├── data/                   # Dati e documenti
│   ├── normative_base/     # Normative scaricate
│   ├── normative_custom/   # Normative custom
│   ├── esempi/             # Esempi temporanei
│   └── templates/          # Template DOCX
├── vectordb/               # Database vettoriale ChromaDB
├── config/                 # Configurazioni
├── logs/                   # Log applicazione
└── cache/                  # Cache embeddings
```

## 🎬 Avvio Sistema

### Metodo 1: Comando Singolo (Raccomandato)

```bash
# Assicurati che Ollama sia in esecuzione in background
ollama serve &

# Avvia backend FastAPI (serve anche il frontend)
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Apri il browser su: **http://localhost:8000**

### Metodo 2: Due Terminali Separati

**Terminale 1 - Ollama:**
```bash
ollama serve
```

**Terminale 2 - Backend + Frontend:**
```bash
python -m uvicorn api.main:app --reload --port 8000
```

**Apri browser:** http://localhost:8000

### Note Avvio
- Il flag `--reload` riavvia automaticamente il server quando modifichi il codice (utile in sviluppo)
- Il frontend HTML/JS è servito direttamente da FastAPI
- L'API REST è disponibile su http://localhost:8000/api/
- La documentazione API interattiva è su http://localhost:8000/docs

## 📚 Guida Utilizzo

### Interfaccia Web

Il sistema ora usa un'interfaccia HTML/JavaScript moderna accessibile da browser. All'avvio vedrai:

- **Header**: Status del sistema (verde = pronto)
- **Sidebar destra**: Lista normative caricate dal sistema
- **Area principale**: Sezioni per upload e generazione

### Workflow Tipico

#### 1. Preparazione Normative

Prima del primo utilizzo, assicurati di avere file JSON normative in `data/normative/`:

```bash
# Verifica normative disponibili
ls data/normative/

# Dovresti vedere almeno esempio.json
# Aggiungi le tue normative in formato JSON
```

#### 2. Carica File Esempio (Opzionale)

**Trascina o clicca nella sezione "📄 File Esempio"**
- Formati supportati: PDF, DOCX, TXT
- Upload multiplo consentito
- Gli esempi guidano lo stile del documento generato

#### 3. Carica Template (Opzionale)

**Trascina o clicca nella sezione "📋 Template"**
- Formati supportati: DOCX, TXT
- Il template definisce la struttura del documento finale
- Placeholder supportati: `{{VARIABILE}}`

#### 4. Scrivi la Richiesta

Nella sezione **"✍️ Richiesta"**:
1. Descrivi la relazione che vuoi generare
2. Scegli lo stile (Formale, Semi-formale, Sintetico)
3. Clicca **"🚀 Genera Relazione"**

**Esempio prompt:**
```
Genera una relazione sulla responsabilità extracontrattuale
secondo l'art. 2043 CC, con focus su danni da circolazione
stradale. Includi giurisprudenza rilevante se disponibile.
```

#### 5. Visualizza Risultato

Il sistema mostrerà:
- **Confidence Score**: Barra di progresso con percentuale di affidabilità
- **Alert**: Se il documento richiede revisione manuale
- **Documento**: Testo completo generato
- **Citazioni**: Lista delle fonti normative utilizzate con score
- **Download**: Pulsante per scaricare il documento in formato TXT

**Legenda Confidence:**
- 🟢 >80%: Alta affidabilità
- 🟡 50-80%: Media affidabilità (verifica consigliata)
- 🔴 <50%: Bassa affidabilità (revisione necessaria)

## ⚙️ Configurazione Avanzata

### File `config/settings.yaml`

```yaml
ollama:
  model: "mistral:latest"        # Modello LLM
  temperature: 0.1               # Determinismo (basso = più preciso)
  max_tokens: 4096               # Lunghezza massima risposta

confidence:
  high_threshold: 0.8            # Soglia confidenza alta
  medium_threshold: 0.5          # Soglia confidenza media
  min_acceptable: 0.3            # Minimo accettabile

retrieval:
  top_k: 5                       # Numero chunks da recuperare
  similarity_cutoff: 0.3         # Cutoff similarità minima
```

### File `config/prompts.yaml`

Contiene i template di prompt in italiano. Modificabile per personalizzare il comportamento dell'AI.

## 🔧 Troubleshooting

### Problema: "cannot import name 'VectorStoreIndex'"

**Causa:** Versione LlamaIndex incompatibile (0.9.x invece di 0.10.x)

**Soluzione:**
```bash
pip uninstall llama-index llama-index-core -y
pip cache purge
pip install -r requirements.txt
```

**Verifica versioni corrette:**
```bash
pip show llama-index-core  # Deve essere 0.10.67
pip show llama-index       # Deve essere 0.10.67
```

### Problema: "Ollama non raggiungibile"

**Soluzione:**
```bash
# Verifica che Ollama sia in esecuzione
ps aux | grep ollama

# Se non è in esecuzione, avvialo
ollama serve
```

### Problema: "ModuleNotFoundError"

**Soluzione:**
```bash
# Reinstalla dipendenze
pip install -r requirements.txt --force-reinstall
```

### Problema: "Normative non scaricate"

**Soluzione:**
- Verifica connessione internet
- Normattiva.it potrebbe essere temporaneamente non disponibile
- Il sistema usa automaticamente fallback se il download fallisce

### Problema: "Documento generato vuoto o con errori"

**Soluzione:**
1. Verifica che il database normative sia caricato (Tab 1)
2. Controlla che Ollama funzioni: `ollama run mistral "test"`
3. Riduci `top_k` nelle opzioni avanzate
4. Aumenta il timeout in `config/settings.yaml`

### Problema: "Memory Error durante embedding"

**Soluzione:**
```yaml
# In config/settings.yaml, riduci chunk_size
chunking:
  chunk_size: 256  # invece di 512
  chunk_overlap: 25
```

## 📊 Metriche e Monitoring

### Log

I log sono salvati in `logs/legal_ai.log`:

```bash
# Visualizza log in tempo reale
tail -f logs/legal_ai.log

# Cerca errori
grep ERROR logs/legal_ai.log
```

### Statistiche Database

Nel tab **Normative**, visualizza:
- Numero normative caricate
- Totale articoli indicizzati
- Spazio disco utilizzato

### Report Confidence

Ogni generazione produce un report JSON con:
- Score complessivo documento
- Breakdown citazioni (alta/media/bassa)
- Sezioni che necessitano revisione
- Raccomandazioni specifiche

## 🧪 Testing

### Test Componenti Singoli

```bash
# Test NormativeFetcher
python -m core.normative_fetcher

# Test ConfidenceScorer
python -m core.confidence_scorer

# Test DocxProcessor
python -m core.docx_processor

# Test RAGEngine
python -m core.rag_engine
```

### Test End-to-End

1. Avvia applicazione
2. Scarica normative base
3. Carica template esempio
4. Genera relazione di test con prompt:
   ```
   Redigi una breve analisi sulla responsabilità extracontrattuale
   secondo il codice civile italiano.
   ```
5. Verifica:
   - Citazioni presenti
   - Confidence score > 0.7
   - DOCX scaricabile

## 🔐 Privacy e Sicurezza

- ✅ **Tutto locale**: Nessun dato inviato a servizi cloud
- ✅ **Ollama locale**: LLM eseguito sulla macchina locale
- ✅ **Database locale**: ChromaDB persistente in locale
- ✅ **No API keys**: Nessuna API key o credential necessaria

## 📈 Performance

### Requisiti Hardware Raccomandati

- **CPU**: 4+ cores
- **RAM**: 8GB+ (16GB raccomandato)
- **Storage**: 10GB+ liberi
- **GPU**: Opzionale (accelera embeddings)

### Tempi Medi

- **Download normative base**: 2-5 minuti
- **Build indice normative**: 1-3 minuti (prima volta)
- **Generazione relazione**: 30-60 secondi
- **Caricamento indice esistente**: 5-10 secondi

## 🛠️ Sviluppo

### Aggiungere Nuove Normative

```python
# In core/normative_fetcher.py, aggiungi a NORMATIVE_PRIORITARIE:

NORMATIVE_PRIORITARIE = {
    # ... esistenti ...
    "mia_normativa": {
        "urn": "urn:nir:stato:legge:YYYY-MM-DD;NNN",
        "nome": "Nome Completo Normativa",
        "anno": "YYYY"
    }
}
```

### Personalizzare Prompts

Modifica `config/prompts.yaml` per:
- Cambiare system prompt
- Aggiungere nuovi stili
- Modificare template query

### Estendere Confidence Scoring

In `core/confidence_scorer.py`, metodo `_adjust_score()`:

```python
# Aggiungi nuovi boost/penalità
if condition:
    score = min(score + 0.1, 1.0)  # Boost
```

## 📝 Limitazioni Note (POC)

Questa è una **Proof of Concept**. Limitazioni:

1. **Parsing Normattiva.it**: Parsing HTML semplificato, potrebbe non estrarre perfettamente tutte le strutture complesse
2. **Fallback normative**: Se Normattiva.it non risponde, usa dati minimi di fallback
3. **Template DOCX**: Supporto base per placeholders, formattazione complessa potrebbe non essere preservata
4. **Multilingua**: Ottimizzato per italiano, altre lingue non supportate
5. **Scalabilità**: Ottimizzato per uso singolo utente, non concorrenza multi-utente

## 🗺️ Roadmap Future Funzionalità

- [ ] Integrazione con database giurisprudenziali
- [ ] Export in formato PDF
- [ ] Versioning documenti generati
- [ ] Collaborative editing
- [ ] API REST per integrazione esterna
- [ ] Supporto GPU per accelerazione
- [ ] Dashboard analytics avanzata
- [ ] Plugin per Word/Google Docs

## 🤝 Contributi

Questo è un progetto POC. Per contributi o segnalazioni:

1. Controlla issue esistenti
2. Crea nuovo issue descrivendo il problema/feature
3. Fork e pull request benvenuti

## 📄 Licenza

Questo progetto è una Proof of Concept per scopi dimostrativi ed educativi.

## ⚠️ Disclaimer Legale

**IMPORTANTE**: Questo sistema è uno strumento di supporto per professionisti legali.

- ✅ **USA**: Come bozza iniziale da revisionare
- ✅ **USA**: Per ricerca e analisi normativa
- ❌ **NON USARE**: Come fonte definitiva senza verifica
- ❌ **NON USARE**: In sostituzione di consulenza legale professionale

**Il professionista legale deve SEMPRE revisionare e validare i documenti generati prima dell'utilizzo.**

## 📞 Supporto

Per domande o problemi:

1. Consulta questa documentazione
2. Controlla i log: `logs/legal_ai.log`
3. Verifica Troubleshooting section
4. Crea issue su GitHub (se disponibile)

---

**Versione**: 1.0.0 POC
**Data**: Novembre 2025
**Sviluppato con**: ⚖️ + 🤖 = 💼
