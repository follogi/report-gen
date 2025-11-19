"""
Wrapper unificato per diversi provider LLM.
Permette di switchare tra Ollama, Claude, OpenAI, etc. con configurazione.
"""

import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Provider LLM supportati."""
    OLLAMA = "ollama"
    CLAUDE = "claude"
    OPENAI = "openai"
    GROQ = "groq"
    LOCAL = "local"


@dataclass
class LLMConfig:
    """Configurazione unificata per LLM."""
    provider: LLMProvider
    model_name: str
    temperature: float = 0.1
    max_tokens: int = 4096
    top_p: float = 0.9
    timeout: int = 120
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    additional_kwargs: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Converti provider in Enum se è stringa."""
        if isinstance(self.provider, str):
            self.provider = LLMProvider(self.provider.lower())

    @classmethod
    def from_yaml(cls, config_path: str, config_name: str = "development") -> 'LLMConfig':
        """
        Carica configurazione da file YAML.

        Args:
            config_path: Percorso al file YAML
            config_name: Nome della configurazione da caricare

        Returns:
            LLMConfig inizializzato
        """
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            configs = yaml.safe_load(f)

        if config_name not in configs:
            raise ValueError(f"Configurazione '{config_name}' non trovata in {config_path}")

        config_dict = configs[config_name]
        return cls(**config_dict)

    @classmethod
    def from_env(cls) -> 'LLMConfig':
        """
        Carica configurazione da variabili d'ambiente.

        Returns:
            LLMConfig da env vars
        """
        provider = os.getenv('LLM_PROVIDER', 'ollama').lower()
        return cls(
            provider=LLMProvider(provider),
            model_name=os.getenv('LLM_MODEL', 'mistral'),
            temperature=float(os.getenv('LLM_TEMPERATURE', '0.1')),
            max_tokens=int(os.getenv('LLM_MAX_TOKENS', '4096')),
            top_p=float(os.getenv('LLM_TOP_P', '0.9')),
            timeout=int(os.getenv('LLM_TIMEOUT', '120')),
            api_key=os.getenv('LLM_API_KEY'),
            base_url=os.getenv('LLM_BASE_URL')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Converte in dizionario."""
        return {
            'provider': self.provider.value,
            'model_name': self.model_name,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'top_p': self.top_p,
            'timeout': self.timeout,
            'has_api_key': self.api_key is not None,
            'base_url': self.base_url
        }


class BaseLLMWrapper(ABC):
    """Classe base astratta per wrapper LLM."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.llm = None
        self._initialize()

    @abstractmethod
    def _initialize(self):
        """Inizializza il provider LLM specifico."""
        pass

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Genera testo dal prompt."""
        pass

    @abstractmethod
    def generate_with_citations(
        self,
        prompt: str,
        context: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Genera testo con citazioni dal contesto."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se il provider è disponibile."""
        pass

    def get_info(self) -> Dict[str, Any]:
        """Ritorna informazioni sul provider."""
        return {
            'provider': self.config.provider.value,
            'model': self.config.model_name,
            'temperature': self.config.temperature,
            'max_tokens': self.config.max_tokens,
            'available': self.is_available()
        }


class OllamaWrapper(BaseLLMWrapper):
    """Wrapper per Ollama."""

    def _initialize(self):
        """Inizializza Ollama."""
        try:
            from core.llama_index_compat import Ollama, Settings

            if Ollama is None:
                raise ImportError("Ollama non disponibile in llama_index_compat")

            base_url = self.config.base_url or "http://localhost:11434"

            self.llm = Ollama(
                model=self.config.model_name,
                base_url=base_url,
                temperature=self.config.temperature,
                context_window=self.config.max_tokens,
                request_timeout=float(self.config.timeout),
                additional_kwargs={
                    "top_p": self.config.top_p,
                    "repeat_penalty": 1.1,
                    **self.config.additional_kwargs
                }
            )

            # Imposta come LLM globale per LlamaIndex
            if Settings is not None:
                Settings.llm = self.llm

            logger.info(f"✅ Ollama inizializzato: {self.config.model_name} su {base_url}")

        except Exception as e:
            logger.error(f"❌ Errore inizializzazione Ollama: {e}")
            self.llm = None

    def generate(self, prompt: str, **kwargs) -> str:
        """Genera testo con Ollama."""
        if not self.llm:
            raise RuntimeError("Ollama non inizializzato")

        try:
            response = self.llm.complete(prompt, **kwargs)
            return response.text if hasattr(response, 'text') else str(response)
        except Exception as e:
            logger.error(f"Errore generazione Ollama: {e}")
            raise

    def generate_with_citations(
        self,
        prompt: str,
        context: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Genera con citazioni usando il formato italiano per documenti legali."""

        # Prepara il prompt con contesto numerato
        context_str = "\n\n".join([f"[{i+1}] {ctx}" for i, ctx in enumerate(context)])

        full_prompt = f"""Sei un assistente legale italiano.

CONTESTO NORMATIVO:
{context_str}

REGOLE:
1. Usa SOLO le informazioni dal contesto fornito
2. Cita SEMPRE la fonte usando [N] dove N è il numero del documento
3. Se non trovi informazioni pertinenti, scrivi "INFORMAZIONE NON DISPONIBILE"
4. Non inventare MAI normative o articoli

RICHIESTA: {prompt}

RISPOSTA (con citazioni [N]):"""

        response_text = self.generate(full_prompt, **kwargs)

        # Estrai citazioni dal testo
        citations = re.findall(r'\[(\d+)\]', response_text)
        unique_citations = list(set(citations))

        return {
            'text': response_text,
            'citations': unique_citations,
            'context_used': [
                context[int(c)-1] for c in unique_citations
                if int(c) <= len(context)
            ],
            'provider_used': self.config.provider.value,
            'model_used': self.config.model_name
        }

    def is_available(self) -> bool:
        """Verifica se Ollama è disponibile."""
        try:
            import requests
            base_url = self.config.base_url or "http://localhost:11434"
            response = requests.get(f"{base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False


class ClaudeWrapper(BaseLLMWrapper):
    """Wrapper per Claude API di Anthropic."""

    def _initialize(self):
        """Inizializza Claude API."""
        try:
            from anthropic import Anthropic

            api_key = self.config.api_key or os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                logger.warning("⚠️ API key di Anthropic non configurata")
                self.client = None
                return

            self.client = Anthropic(api_key=api_key)

            # Mappa modelli Claude
            model_mapping = {
                'claude-3-opus': 'claude-3-opus-20240229',
                'claude-3-sonnet': 'claude-3-5-sonnet-20241022',
                'claude-3-haiku': 'claude-3-haiku-20240307',
                'claude': 'claude-3-5-sonnet-20241022'  # default
            }

            self.model_id = model_mapping.get(
                self.config.model_name,
                self.config.model_name
            )

            logger.info(f"✅ Claude API inizializzato: {self.model_id}")

        except ImportError:
            logger.warning(
                "⚠️ Anthropic SDK non installato. "
                "Installa con: pip install anthropic"
            )
            self.client = None
        except Exception as e:
            logger.error(f"❌ Errore inizializzazione Claude: {e}")
            self.client = None

    def generate(self, prompt: str, **kwargs) -> str:
        """Genera testo con Claude."""
        if not self.client:
            raise RuntimeError("Claude API non inizializzata")

        try:
            message = self.client.messages.create(
                model=self.model_id,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                **kwargs
            )

            return message.content[0].text

        except Exception as e:
            logger.error(f"Errore generazione Claude: {e}")
            raise

    def generate_with_citations(
        self,
        prompt: str,
        context: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Genera con citazioni usando Claude."""

        # Prepara il prompt strutturato per Claude
        context_str = "\n\n".join([f"[{i+1}] {ctx}" for i, ctx in enumerate(context)])

        system_prompt = """Sei un assistente legale specializzato nel diritto italiano.
Devi generare relazioni basate ESCLUSIVAMENTE sulle normative fornite.

REGOLE FERREE:
1. Ogni affermazione DEVE citare la fonte usando [N]
2. MAI inventare normative o articoli
3. Se non trovi info pertinenti: "NORMATIVA NON DISPONIBILE NEL CONTESTO"
4. Mantieni tono formale e professionale"""

        full_prompt = f"""<documenti>
{context_str}
</documenti>

<richiesta>
{prompt}
</richiesta>

Genera una risposta usando SOLO i documenti forniti, con citazioni [N]."""

        try:
            message = self.client.messages.create(
                model=self.model_id,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": full_prompt}
                ]
            )

            response_text = message.content[0].text

            # Estrai citazioni
            citations = re.findall(r'\[(\d+)\]', response_text)
            unique_citations = list(set(citations))

            return {
                'text': response_text,
                'citations': unique_citations,
                'context_used': [
                    context[int(c)-1] for c in unique_citations
                    if int(c) <= len(context)
                ],
                'provider_used': self.config.provider.value,
                'model_used': self.model_id,
                'usage': {
                    'input_tokens': message.usage.input_tokens if hasattr(message, 'usage') else None,
                    'output_tokens': message.usage.output_tokens if hasattr(message, 'usage') else None
                }
            }

        except Exception as e:
            logger.error(f"Errore generazione Claude con citazioni: {e}")
            raise

    def is_available(self) -> bool:
        """Verifica se Claude API è disponibile."""
        return self.client is not None


class OpenAIWrapper(BaseLLMWrapper):
    """Wrapper per OpenAI API."""

    def _initialize(self):
        """Inizializza OpenAI."""
        try:
            from openai import OpenAI

            api_key = self.config.api_key or os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning("⚠️ API key di OpenAI non configurata")
                self.client = None
                return

            base_url = self.config.base_url

            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url
            ) if base_url else OpenAI(api_key=api_key)

            # Default a GPT-4 se non specificato
            self.model_id = self.config.model_name or "gpt-4-turbo-preview"

            logger.info(f"✅ OpenAI API inizializzato: {self.model_id}")

        except ImportError:
            logger.warning(
                "⚠️ OpenAI SDK non installato. "
                "Installa con: pip install openai"
            )
            self.client = None
        except Exception as e:
            logger.error(f"❌ Errore inizializzazione OpenAI: {e}")
            self.client = None

    def generate(self, prompt: str, **kwargs) -> str:
        """Genera testo con OpenAI."""
        if not self.client:
            raise RuntimeError("OpenAI API non inizializzata")

        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": "Sei un assistente legale italiano esperto."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
                **kwargs
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Errore generazione OpenAI: {e}")
            raise

    def generate_with_citations(
        self,
        prompt: str,
        context: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Genera con citazioni usando OpenAI."""

        context_str = "\n\n".join([f"[{i+1}] {ctx}" for i, ctx in enumerate(context)])

        system_prompt = """Sei un assistente legale italiano.
Regole:
1. Usa SOLO il contesto fornito
2. Cita sempre con [N]
3. Mai inventare normative
4. Se non trovi info: "NON DISPONIBILE"
"""

        user_prompt = f"""Contesto normativo:
{context_str}

Richiesta: {prompt}

Rispondi usando SOLO il contesto, con citazioni [N]."""

        response_text = self.generate(user_prompt, **kwargs)

        # Estrai citazioni
        citations = re.findall(r'\[(\d+)\]', response_text)
        unique_citations = list(set(citations))

        return {
            'text': response_text,
            'citations': unique_citations,
            'context_used': [
                context[int(c)-1] for c in unique_citations
                if int(c) <= len(context)
            ],
            'provider_used': self.config.provider.value,
            'model_used': self.model_id
        }

    def is_available(self) -> bool:
        """Verifica se OpenAI API è disponibile."""
        return self.client is not None


class LLMFactory:
    """Factory per creare il wrapper LLM appropriato."""

    _wrappers = {
        LLMProvider.OLLAMA: OllamaWrapper,
        LLMProvider.CLAUDE: ClaudeWrapper,
        LLMProvider.OPENAI: OpenAIWrapper,
    }

    @classmethod
    def create(cls, config: Union[LLMConfig, str, Dict]) -> BaseLLMWrapper:
        """
        Crea un wrapper LLM dalla configurazione.

        Args:
            config: LLMConfig, path a YAML, o dict di configurazione

        Returns:
            Wrapper LLM inizializzato
        """
        # Converti in LLMConfig se necessario
        if isinstance(config, str):
            if config.endswith('.yaml') or config.endswith('.yml'):
                config = LLMConfig.from_yaml(config)
            else:
                # Assume sia il nome del provider
                config = LLMConfig(provider=LLMProvider(config), model_name='default')
        elif isinstance(config, dict):
            config = LLMConfig(**config)

        # Ottieni wrapper class
        wrapper_class = cls._wrappers.get(config.provider)
        if not wrapper_class:
            raise ValueError(f"Provider {config.provider} non supportato")

        # Crea e ritorna wrapper
        wrapper = wrapper_class(config)

        if not wrapper.is_available():
            logger.warning(f"⚠️ Provider {config.provider.value} non disponibile")

        return wrapper

    @classmethod
    def create_from_env(cls) -> BaseLLMWrapper:
        """Crea wrapper da variabili d'ambiente."""
        config = LLMConfig.from_env()
        return cls.create(config)

    @classmethod
    def register_wrapper(cls, provider: LLMProvider, wrapper_class: type):
        """Registra un nuovo wrapper provider."""
        cls._wrappers[provider] = wrapper_class

    @classmethod
    def list_providers(cls) -> List[str]:
        """Lista provider disponibili."""
        return [p.value for p in cls._wrappers.keys()]


class MultiLLMManager:
    """
    Manager per gestire multipli LLM e fare A/B testing o fallback.
    """

    def __init__(
        self,
        primary_config: LLMConfig,
        fallback_configs: Optional[List[LLMConfig]] = None
    ):
        """
        Inizializza con LLM primario e fallback opzionali.

        Args:
            primary_config: Configurazione LLM primario
            fallback_configs: Lista configurazioni di fallback
        """
        self.primary = LLMFactory.create(primary_config)
        self.fallbacks = []

        if fallback_configs:
            for config in fallback_configs:
                try:
                    wrapper = LLMFactory.create(config)
                    if wrapper.is_available():
                        self.fallbacks.append(wrapper)
                except Exception as e:
                    logger.warning(f"Impossibile creare fallback {config.provider}: {e}")

        self.current = self.primary if self.primary.is_available() else None

        if not self.current and self.fallbacks:
            self.current = self.fallbacks[0]
            logger.info(f"Usando fallback: {self.current.config.provider.value}")

    def generate(self, prompt: str, **kwargs) -> str:
        """Genera con fallback automatico."""
        if not self.current:
            raise RuntimeError("Nessun LLM disponibile")

        try:
            return self.current.generate(prompt, **kwargs)
        except Exception as e:
            logger.error(f"Errore con {self.current.config.provider.value}: {e}")

            # Prova fallback
            for fallback in self.fallbacks:
                if fallback != self.current and fallback.is_available():
                    logger.info(f"Switching a fallback: {fallback.config.provider.value}")
                    self.current = fallback
                    return self.current.generate(prompt, **kwargs)

            raise RuntimeError("Tutti gli LLM hanno fallito")

    def generate_with_citations(
        self,
        prompt: str,
        context: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Genera con citazioni e fallback."""
        if not self.current:
            raise RuntimeError("Nessun LLM disponibile")

        try:
            result = self.current.generate_with_citations(prompt, context, **kwargs)
            result['provider_used'] = self.current.config.provider.value
            return result
        except Exception as e:
            logger.error(f"Errore con {self.current.config.provider.value}: {e}")

            # Prova fallback
            for fallback in self.fallbacks:
                if fallback != self.current and fallback.is_available():
                    logger.info(f"Switching a fallback: {fallback.config.provider.value}")
                    self.current = fallback
                    result = self.current.generate_with_citations(prompt, context, **kwargs)
                    result['provider_used'] = self.current.config.provider.value
                    return result

            raise RuntimeError("Tutti gli LLM hanno fallito")

    def compare_providers(
        self,
        prompt: str,
        context: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compara risposte da diversi provider (per testing).

        Returns:
            Dict con risposte da ogni provider
        """
        results = {}

        all_providers = [self.primary] + self.fallbacks

        for wrapper in all_providers:
            if wrapper.is_available():
                try:
                    if context:
                        result = wrapper.generate_with_citations(prompt, context)
                    else:
                        result = {'text': wrapper.generate(prompt)}

                    result['provider'] = wrapper.config.provider.value
                    result['model'] = wrapper.config.model_name
                    results[wrapper.config.provider.value] = result

                except Exception as e:
                    results[wrapper.config.provider.value] = {
                        'error': str(e),
                        'provider': wrapper.config.provider.value
                    }

        return results


def test_llm_wrapper():
    """Test rapido del wrapper LLM."""
    print("\n" + "="*60)
    print("TEST LLM WRAPPER")
    print("="*60)

    # Test Ollama
    print("\n1. Test Ollama...")
    try:
        ollama_config = LLMConfig(
            provider=LLMProvider.OLLAMA,
            model_name="mistral",
            temperature=0.1
        )
        ollama = LLMFactory.create(ollama_config)
        if ollama.is_available():
            print("   ✅ Ollama disponibile")
        else:
            print("   ❌ Ollama non disponibile (avvia con: ollama serve)")
    except Exception as e:
        print(f"   ❌ Errore: {e}")

    # Test Claude (se API key configurata)
    print("\n2. Test Claude API...")
    if os.getenv('ANTHROPIC_API_KEY'):
        try:
            claude_config = LLMConfig(
                provider=LLMProvider.CLAUDE,
                model_name="claude-3-haiku",
                temperature=0.1
            )
            claude = LLMFactory.create(claude_config)
            if claude.is_available():
                print("   ✅ Claude disponibile")
            else:
                print("   ❌ Claude non disponibile")
        except Exception as e:
            print(f"   ❌ Errore: {e}")
    else:
        print("   ⏭️ Skipped (no API key in ANTHROPIC_API_KEY)")

    # Test OpenAI (se API key configurata)
    print("\n3. Test OpenAI API...")
    if os.getenv('OPENAI_API_KEY'):
        try:
            openai_config = LLMConfig(
                provider=LLMProvider.OPENAI,
                model_name="gpt-3.5-turbo",
                temperature=0.1
            )
            openai = LLMFactory.create(openai_config)
            if openai.is_available():
                print("   ✅ OpenAI disponibile")
            else:
                print("   ❌ OpenAI non disponibile")
        except Exception as e:
            print(f"   ❌ Errore: {e}")
    else:
        print("   ⏭️ Skipped (no API key in OPENAI_API_KEY)")

    # Lista provider disponibili
    print("\n4. Provider supportati:")
    for provider in LLMFactory.list_providers():
        print(f"   - {provider}")

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    test_llm_wrapper()
