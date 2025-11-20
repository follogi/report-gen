#!/bin/bash
# Script di avvio Legal RAG System

echo "🚀 Avvio Legal RAG System..."
echo ""

# Verifica Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 non trovato. Installa Python 3.10+ prima di continuare."
    exit 1
fi

# Verifica virtual environment
if [ ! -d "venv" ]; then
    echo "⚠️ Virtual environment non trovato."
    echo "Crealo con: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Attiva venv
echo "📦 Attivazione virtual environment..."
source venv/bin/activate

# Verifica Ollama
echo "🔍 Verifica Ollama..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️ Ollama non raggiungibile su http://localhost:11434"
    echo "Avvialo in un altro terminale con: ollama serve"
    echo ""
fi

# Verifica normative
echo "📚 Verifica normative..."
if [ -z "$(ls -A data/normative/*.json 2>/dev/null)" ]; then
    echo "⚠️ Nessuna normativa trovata in data/normative/"
    echo "Aggiungi almeno un file JSON normativa prima di procedere."
    echo ""
fi

# Avvia server
echo "🌐 Avvio server FastAPI..."
echo "Frontend disponibile su: http://localhost:8000"
echo "API docs su: http://localhost:8000/docs"
echo ""
echo "Premi CTRL+C per terminare"
echo ""

python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
