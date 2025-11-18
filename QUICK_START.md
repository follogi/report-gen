# 🚀 Quick Start Guide

Guida rapida per iniziare subito con Legal AI.

## Prerequisiti (5 minuti)

### 1. Installa Ollama

```bash
# Linux/Mac
curl -fsSL https://ollama.ai/install.sh | sh

# Windows: scarica da https://ollama.ai
```

### 2. Scarica Modello Mistral

```bash
ollama pull mistral
```

## Setup Progetto (2 minuti)

### 1. Virtual Environment

```bash
cd legal-ai-poc
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure: venv\Scripts\activate  # Windows
```

### 2. Installa Dipendenze

```bash
pip install -r requirements.txt
```

## Avvio (30 secondi)

### Terminale 1 - Ollama

```bash
ollama serve
```

### Terminale 2 - Streamlit

```bash
streamlit run app.py
```

**L'app si apre automaticamente nel browser!**

## Primo Utilizzo (3 minuti)

### 1. Scarica Normative

- Tab **"📚 Normative"**
- Click **"📥 Scarica Normative Base"**
- Seleziona tutte
- Click **"⬇️ Scarica Selezionate"**
- Attendi 2-3 minuti

### 2. Genera Template

- Tab **"📄 Documenti"**
- Click **"📝 Crea Template Esempio"**

### 3. Genera Prima Relazione

- Tab **"⚙️ Genera"**
- Usa prompt predefinito o scrivi il tuo
- Click **"🚀 Genera Relazione"**
- Attendi 30-60 secondi

### 4. Scarica Risultato

- Tab **"📥 Risultato"**
- Click **"📥 Scarica DOCX"**

## Risoluzione Problemi Comuni

### Errore: "Ollama non raggiungibile"

```bash
# Controlla se Ollama è attivo
ps aux | grep ollama

# Se no, avvialo
ollama serve
```

### Errore: "ModuleNotFoundError"

```bash
pip install -r requirements.txt --upgrade
```

### Documento Vuoto

1. Verifica normative caricate (Tab 1)
2. Riavvia Ollama
3. Prova con prompt più semplice

## Prossimi Passi

- Carica il tuo template DOCX personalizzato
- Aggiungi esempi di documenti
- Personalizza prompts in `config/prompts.yaml`
- Esplora opzioni avanzate

## Supporto

Per aiuto dettagliato, consulta `README.md`

---

**Tempo totale setup**: ~10 minuti
**Prima generazione**: ~5 minuti
