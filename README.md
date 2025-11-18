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

## 🚀 Installazione

### 1. Clone Repository

```bash
cd /path/to/legal-ai-poc
```

### 2. Crea Virtual Environment

```bash
python -m venv venv

# Attiva virtual environment
# Linux/Mac:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 3. Installa Dipendenze

```bash
pip install -r requirements.txt
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

## 🎬 Avvio Applicazione

### 1. Avvia Ollama (Terminale 1)

```bash
ollama serve
```

Lasciare questo terminale aperto.

### 2. Avvia Streamlit (Terminale 2)

```bash
streamlit run app.py
```

L'applicazione si aprirà automaticamente nel browser a: `http://localhost:8501`

## 📚 Guida Utilizzo

### Primo Avvio

Al primo avvio, l'applicazione ti chiederà se scaricare il database normative base.

1. Vai al tab **"📚 Normative"**
2. Clicca **"📥 Scarica Normative Base"**
3. Seleziona le normative da scaricare (consigliato: tutte)
4. Clicca **"⬇️ Scarica Selezionate"**
5. Attendi il completamento (può richiedere alcuni minuti)

### Workflow Tipico

#### 1. Gestione Normative (Tab 1)

- **Visualizza normative disponibili**: Tree view con tutte le normative caricate
- **Aggiungi normative custom**: Upload PDF/DOCX/TXT di normative aggiuntive
- **Ricostruisci database**: Cancella e riscarica tutto

#### 2. Documenti Sessione (Tab 2)

**Template DOCX:**
- Upload del template con placeholders `{{VARIABILE}}`
- Esempio: `{{CLIENTE}}`, `{{DATA}}`, `{{OGGETTO}}`
- Marker per contenuto generato: `{{CONTENUTO_GENERATO}}`

**Esempi:**
- Upload multiplo di documenti di riferimento (PDF, DOCX, TXT)
- Usati per guidare lo stile e la struttura
- Max 10 file, 10MB ciascuno

#### 3. Genera Relazione (Tab 3)

**Form Principale:**
1. Scrivi la richiesta (cosa deve contenere la relazione)
2. Configura opzioni avanzate:
   - **Soglia Confidence**: 0.3-0.9 (default: 0.7)
   - **Solo normative citate**: Raccomandato ✅
   - **Stile**: Formale / Semi-formale / Sintetico
3. Compila variabili template (se presenti)
4. Clicca **"🚀 Genera Relazione"**

**Processo Generazione:**
- Fase 1: Caricamento normative
- Fase 2: Analisi template
- Fase 3: Indicizzazione esempi
- Fase 4: Generazione con AI
- Fase 5: Creazione documento

#### 4. Risultato (Tab 4)

**Preview:**
- Visualizzazione documento generato
- Legenda colori:
  - 🟢 Verde: Alta confidenza (>80%)
  - 🟡 Giallo: Media confidenza (50-80%)
  - 🔴 Rosso: Bassa confidenza (<50%)

**Citazioni:**
- Lista completa con fonte, articolo, confidence
- Clic per espandere dettagli

**Download:**
- **📥 DOCX**: Documento completo con highlighting
- **📑 Bibliografia**: File TXT con riferimenti normativi
- **📊 Report Confidence**: JSON con analisi dettagliata

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
