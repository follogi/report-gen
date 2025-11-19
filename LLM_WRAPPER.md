# 🤖 Sistema Wrapper LLM Flessibile

Sistema unificato per gestire multipli provider LLM (Ollama, Claude, OpenAI, Groq, etc.) con supporto per fallback automatico, A/B testing e switching facile tra provider.

## 🎯 Obiettivi

- **Flessibilità totale**: Cambia provider con una sola riga di configurazione
- **Fallback automatico**: Se un provider fallisce, passa automaticamente al successivo
- **A/B Testing**: Confronta risposte da diversi provider
- **Costi ottimizzati**: Usa modelli economici per task semplici, premium per documenti critici
- **Sviluppo semplificato**: Sviluppa locale con Ollama gratis, deploy con Claude/GPT-4
- **Privacy-first**: Tutti i dati restano locali con Ollama

## 📁 Struttura Componenti

```
legal-ai-poc/
├── core/
│   ├── llm_wrapper.py           # Sistema wrapper principale
│   └── llama_index_compat.py    # Gestione import LlamaIndex
├── config/
│   └── llm_configs.yaml         # Configurazioni predefinite
├── .env.example                 # Template variabili ambiente
└── test_llm_wrapper.py          # Script di test
```

## 🚀 Quick Start

### 1. Configurazione Base (Ollama Locale - GRATIS)

```python
from core import LLMFactory, LLMConfig, LLMProvider

# Configurazione semplice
config = LLMConfig(
    provider=LLMProvider.OLLAMA,
    model_name="mistral"
)

llm = LLMFactory.create(config)

# Genera testo
response = llm.generate("Spiegami la responsabilità contrattuale")
print(response)
```

### 2. Configurazione da File YAML

```python
# Carica config predefinita da config/llm_configs.yaml
config = LLMConfig.from_yaml("config/llm_configs.yaml", "production")

llm = LLMFactory.create(config)
```

### 3. Configurazione da Environment Variables

```bash
# In .env
LLM_PROVIDER=claude
LLM_MODEL=claude-3-sonnet
ANTHROPIC_API_KEY=sk-ant-...
```

```python
# In codice
from core import LLMFactory

llm = LLMFactory.create_from_env()
```

### 4. Multi-LLM con Fallback Automatico

```python
from core import MultiLLMManager, LLMConfig, LLMProvider

manager = MultiLLMManager(
    primary_config=LLMConfig(
        provider=LLMProvider.CLAUDE,
        model_name="claude-3-sonnet"
    ),
    fallback_configs=[
        LLMConfig(provider=LLMProvider.OLLAMA, model_name="mistral"),
        LLMConfig(provider=LLMProvider.OPENAI, model_name="gpt-3.5-turbo")
    ]
)

# Se Claude fallisce, passa automaticamente a Ollama, poi OpenAI
response = manager.generate("La tua query")
```

## 📋 Provider Supportati

| Provider | Modelli | Costo | Velocità | Privacy | Note |
|----------|---------|-------|----------|---------|------|
| **Ollama** | Mistral, Llama2, Mixtral | 💰 GRATIS | 🟡 Media | 🔒 100% Locale | Perfetto per sviluppo |
| **Claude** | Opus, Sonnet, Haiku | 💰💰 $3-15/1M token | 🟢 Veloce | ☁️ Cloud | Massima qualità |
| **OpenAI** | GPT-4, GPT-3.5 | 💰💰 $10-30/1M token | 🟢 Veloce | ☁️ Cloud | Standard de facto |
| **Groq** | Mixtral, Llama | 💰 Parzialmente gratis | 🟢🟢 Molto veloce | ☁️ Cloud | Ultra-rapido |

## ⚙️ Configurazioni Predefinite

Le configurazioni sono definite in `config/llm_configs.yaml`:

### Sviluppo Locale (Ollama - GRATIS)

```yaml
development:
  provider: ollama
  model_name: mistral
  temperature: 0.1
  max_tokens: 4096
```

**Uso:**
```python
config = LLMConfig.from_yaml("config/llm_configs.yaml", "development")
```

### Produzione Bilanciata (Claude Sonnet)

```yaml
production:
  provider: claude
  model_name: claude-3-sonnet
  temperature: 0.1
  max_tokens: 4096
```

**Costo stimato**: ~$3-5 per 1M token input, $15 per 1M token output

### Produzione Economica (Claude Haiku)

```yaml
production_economica:
  provider: claude
  model_name: claude-3-haiku
  temperature: 0.1
  max_tokens: 2048
```

**Costo stimato**: ~10x meno di Sonnet, ideale per batch processing

### Massima Qualità (Claude Opus)

```yaml
production_premium:
  provider: claude
  model_name: claude-3-opus
  temperature: 0.05
  max_tokens: 8192
```

**Costo stimato**: ~15x Sonnet, ma qualità massima per documenti legali critici

## 🎨 Esempi di Utilizzo

### Esempio 1: Generazione Semplice

```python
from core import LLMFactory, LLMConfig, LLMProvider

config = LLMConfig(
    provider=LLMProvider.OLLAMA,
    model_name="mistral",
    temperature=0.1
)

llm = LLMFactory.create(config)
response = llm.generate("Cos'è la responsabilità extracontrattuale?")
print(response)
```

### Esempio 2: Generazione con Citazioni

```python
# Context normativo
context = [
    "Art. 2043 c.c. - Qualunque fatto doloso o colposo...",
    "Art. 2059 c.c. - Il danno non patrimoniale deve essere risarcito..."
]

# Genera con citazioni automatiche
result = llm.generate_with_citations(
    prompt="Spiega la responsabilità extracontrattuale",
    context=context
)

print(f"Testo: {result['text']}")
print(f"Citazioni usate: {result['citations']}")
print(f"Provider usato: {result['provider_used']}")
```

### Esempio 3: A/B Testing tra Provider

```python
from core import MultiLLMManager, LLMConfig, LLMProvider

manager = MultiLLMManager(
    primary_config=LLMConfig(provider=LLMProvider.CLAUDE, model_name="claude-3-haiku"),
    fallback_configs=[
        LLMConfig(provider=LLMProvider.OLLAMA, model_name="mistral"),
        LLMConfig(provider=LLMProvider.OPENAI, model_name="gpt-3.5-turbo")
    ]
)

# Confronta risposte da tutti i provider disponibili
context = ["Art. 2043 c.c. ..."]
comparisons = manager.compare_providers(
    prompt="Spiega responsabilità contrattuale",
    context=context
)

for provider, result in comparisons.items():
    print(f"\n--- {provider.upper()} ---")
    print(result.get('text', result.get('error')))
```

### Esempio 4: Switching Runtime

```python
# Inizia con Claude per qualità
llm = LLMFactory.create(LLMConfig(
    provider=LLMProvider.CLAUDE,
    model_name="claude-3-opus"
))

# Per batch processing, switcha a Haiku (economico)
llm = LLMFactory.create(LLMConfig(
    provider=LLMProvider.CLAUDE,
    model_name="claude-3-haiku"
))

# Per sviluppo/test, switcha a Ollama (gratis)
llm = LLMFactory.create(LLMConfig(
    provider=LLMProvider.OLLAMA,
    model_name="mistral"
))
```

## 🔧 Configurazione Avanzata

### Variabili Ambiente

Crea un file `.env` (copia da `.env.example`):

```bash
# Provider primario
LLM_PROVIDER=claude
LLM_MODEL=claude-3-sonnet
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096

# API Keys
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
GROQ_API_KEY=your-groq-key-here

# Ollama (per fallback locale)
OLLAMA_BASE_URL=http://localhost:11434

# Fallback automatico
ENABLE_LLM_FALLBACK=true
```

### Parametri di Configurazione

```python
config = LLMConfig(
    provider=LLMProvider.CLAUDE,
    model_name="claude-3-sonnet",
    temperature=0.1,        # 0=deterministico, 1=creativo
    max_tokens=4096,        # Lunghezza massima risposta
    top_p=0.9,              # Nucleus sampling
    timeout=120,            # Timeout richieste
    api_key="sk-...",       # API key (opzionale, da env)
    base_url="...",         # Base URL custom (opzionale)
    additional_kwargs={     # Parametri provider-specific
        "repeat_penalty": 1.1
    }
)
```

## 🧪 Testing

### Test Manuale

```bash
# Test built-in del wrapper
python -c "from core.llm_wrapper import test_llm_wrapper; test_llm_wrapper()"

# Test completo con tutte le funzionalità
python test_llm_wrapper.py
```

### Test da Codice

```python
# Test disponibilità provider
from core import LLMFactory, LLMConfig, LLMProvider

config = LLMConfig(provider=LLMProvider.OLLAMA, model_name="mistral")
llm = LLMFactory.create(config)

if llm.is_available():
    print("✅ Provider disponibile")
else:
    print("❌ Provider non disponibile")
```

## 💰 Stima Costi

### Claude (Anthropic)

| Modello | Input (1M token) | Output (1M token) | Uso Consigliato |
|---------|------------------|-------------------|------------------|
| **Haiku** | $0.25 | $1.25 | Batch processing, sviluppo |
| **Sonnet** | $3 | $15 | Produzione generale |
| **Opus** | $15 | $75 | Documenti critici |

### OpenAI

| Modello | Input (1M token) | Output (1M token) | Uso Consigliato |
|---------|------------------|-------------------|------------------|
| **GPT-3.5 Turbo** | $0.50 | $1.50 | Testing, batch |
| **GPT-4 Turbo** | $10 | $30 | Produzione |
| **GPT-4** | $30 | $60 | Massima qualità |

### Ollama

**GRATIS** - Eseguito localmente, nessun costo API

**Requisiti**: 8GB+ RAM, ~4GB storage per modello

## 🔐 Privacy e Sicurezza

### Provider Locali (Ollama)

✅ **100% Privacy**: Tutti i dati restano sulla tua macchina
✅ **Nessun costo**: Completamente gratuito
✅ **Nessuna API key**: Non servono credenziali
✅ **Offline**: Funziona senza connessione internet
⚠️ **Hardware**: Richiede risorse locali (CPU/RAM)

### Provider Cloud (Claude, OpenAI, Groq)

⚠️ **Dati cloud**: I prompt vengono inviati ai server del provider
✅ **Politiche privacy**: Provider affidabili con policy chiare
✅ **No training**: La maggior parte non usa i dati per training
💰 **Costi**: Pay-per-use basato su token
🔑 **API Keys**: Richiede gestione sicura delle chiavi

## 🛠️ Troubleshooting

### Problema: "Ollama non disponibile"

```bash
# Verifica che Ollama sia in esecuzione
ollama serve

# Verifica che il modello sia scaricato
ollama list

# Scarica modello se mancante
ollama pull mistral
```

### Problema: "Claude API non disponibile"

1. Verifica API key in `.env`:
   ```bash
   echo $ANTHROPIC_API_KEY
   ```

2. Testa API key:
   ```bash
   curl https://api.anthropic.com/v1/messages \
     -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "anthropic-version: 2023-06-01"
   ```

3. Installa SDK:
   ```bash
   pip install anthropic
   ```

### Problema: "ModuleNotFoundError: anthropic/openai"

```bash
# Installa provider SDK necessari
pip install anthropic  # Per Claude
pip install openai     # Per OpenAI
pip install groq       # Per Groq
```

### Problema: "Timeout durante generazione"

Aumenta il timeout nella configurazione:

```python
config = LLMConfig(
    provider=LLMProvider.OLLAMA,
    model_name="mistral",
    timeout=300  # 5 minuti
)
```

## 📊 Metriche e Monitoring

### Tracking Uso Provider

```python
from core import MultiLLMManager

manager = MultiLLMManager(...)

# Genera con tracking
result = manager.generate_with_citations(prompt, context)

print(f"Provider usato: {result['provider_used']}")
print(f"Model usato: {result['model_used']}")

# Con Claude/OpenAI, ottieni anche usage
if 'usage' in result:
    print(f"Token input: {result['usage']['input_tokens']}")
    print(f"Token output: {result['usage']['output_tokens']}")
```

### Logging

```python
import logging

# Abilita debug logging per vedere operazioni wrapper
logging.basicConfig(level=logging.DEBUG)
```

## 🚀 Best Practices

### 1. Sviluppo vs Produzione

```python
# SVILUPPO: Usa Ollama (gratis, locale)
if os.getenv('ENVIRONMENT') == 'development':
    config = LLMConfig(provider=LLMProvider.OLLAMA, model_name="mistral")

# PRODUZIONE: Usa Claude Sonnet (bilanciato)
else:
    config = LLMConfig(provider=LLMProvider.CLAUDE, model_name="claude-3-sonnet")
```

### 2. Fallback Chain

Configura sempre un fallback per produzione:

```python
manager = MultiLLMManager(
    primary_config=LLMConfig(provider=LLMProvider.CLAUDE, model_name="claude-3-sonnet"),
    fallback_configs=[
        LLMConfig(provider=LLMProvider.CLAUDE, model_name="claude-3-haiku"),  # Più economico
        LLMConfig(provider=LLMProvider.OLLAMA, model_name="mistral")  # Gratis
    ]
)
```

### 3. Ottimizzazione Costi

```python
# Task semplici: usa Haiku (10x più economico)
simple_config = LLMConfig(provider=LLMProvider.CLAUDE, model_name="claude-3-haiku")

# Documenti critici: usa Opus (massima qualità)
critical_config = LLMConfig(provider=LLMProvider.CLAUDE, model_name="claude-3-opus")
```

### 4. Gestione API Keys

```python
# ❌ MAI hardcodare API keys
config = LLMConfig(
    provider=LLMProvider.CLAUDE,
    api_key="sk-ant-hardcoded-key"  # MALE!
)

# ✅ Sempre da environment variables
config = LLMConfig(
    provider=LLMProvider.CLAUDE
    # api_key viene letto automaticamente da ANTHROPIC_API_KEY
)
```

## 📚 Riferimenti API

### LLMConfig

```python
@dataclass
class LLMConfig:
    provider: LLMProvider          # Provider da usare
    model_name: str                # Nome modello
    temperature: float = 0.1       # Controllo creatività
    max_tokens: int = 4096         # Lunghezza massima
    top_p: float = 0.9             # Nucleus sampling
    timeout: int = 120             # Timeout secondi
    api_key: Optional[str] = None  # API key (opzionale)
    base_url: Optional[str] = None # URL custom (opzionale)
```

### LLMFactory

```python
# Crea da config object
llm = LLMFactory.create(config)

# Crea da YAML
llm = LLMFactory.create("config/llm_configs.yaml")

# Crea da environment
llm = LLMFactory.create_from_env()

# Lista provider supportati
providers = LLMFactory.list_providers()  # ['ollama', 'claude', 'openai', ...]
```

### BaseLLMWrapper

```python
# Genera testo semplice
response: str = llm.generate(prompt, **kwargs)

# Genera con citazioni
result: Dict = llm.generate_with_citations(prompt, context, **kwargs)
# result = {
#     'text': str,
#     'citations': List[str],
#     'context_used': List[str],
#     'provider_used': str,
#     'model_used': str,
#     'usage': Dict (solo Claude/OpenAI)
# }

# Verifica disponibilità
available: bool = llm.is_available()

# Info provider
info: Dict = llm.get_info()
```

### MultiLLMManager

```python
# Genera con fallback automatico
response: str = manager.generate(prompt)

# Genera citazioni con fallback
result: Dict = manager.generate_with_citations(prompt, context)

# Confronta provider (A/B testing)
comparisons: Dict = manager.compare_providers(prompt, context)
# comparisons = {
#     'ollama': {'text': ..., 'citations': ...},
#     'claude': {'text': ..., 'citations': ...},
#     'openai': {'text': ..., 'citations': ...}
# }
```

## 🎓 Tutorial Completo

Vedi `test_llm_wrapper.py` per esempi completi di:
- ✅ Caricamento configurazioni da YAML
- ✅ Test disponibilità provider
- ✅ Generazione semplice
- ✅ Generazione con citazioni
- ✅ Fallback automatico
- ✅ A/B testing tra provider

Esegui: `python test_llm_wrapper.py`

---

**Versione**: 1.0.0
**Data**: Gennaio 2025
**Autore**: Claude Code
**Status**: ✅ Pronto per Produzione

