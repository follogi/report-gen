#!/usr/bin/env python3
"""
Test del sistema LLM wrapper per Legal AI.

Questo script testa:
1. Caricamento configurazioni da YAML
2. Creazione wrapper per diversi provider
3. Verifica disponibilità provider
4. Test fallback chain
5. Test generazione con citazioni
"""

import os
import sys
from pathlib import Path

# Setup path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.llm_wrapper import (
    LLMFactory,
    LLMConfig,
    LLMProvider,
    MultiLLMManager,
    test_llm_wrapper
)


def test_yaml_configs():
    """Test caricamento configurazioni da file YAML."""
    print("\n" + "="*60)
    print("TEST: Caricamento Configurazioni YAML")
    print("="*60)

    yaml_path = "config/llm_configs.yaml"

    if not Path(yaml_path).exists():
        print(f"  ❌ File {yaml_path} non trovato")
        return False

    try:
        import yaml
        with open(yaml_path) as f:
            configs = yaml.safe_load(f)

        print(f"\n  Configurazioni trovate: {len(configs)}")

        for name in ['development', 'production', 'production_economica', 'balanced']:
            if name in configs:
                print(f"\n  ✅ Config '{name}':")
                config_dict = configs[name]
                print(f"     Provider: {config_dict['provider']}")
                print(f"     Model: {config_dict['model_name']}")
                print(f"     Temperature: {config_dict.get('temperature', 'N/A')}")

                # Test creazione config
                try:
                    config = LLMConfig(**config_dict)
                    print(f"     ✅ Config object creato")
                except Exception as e:
                    print(f"     ❌ Errore creazione: {e}")
            else:
                print(f"  ⚠️ Config '{name}' non trovata")

        return True

    except Exception as e:
        print(f"  ❌ Errore: {e}")
        return False


def test_provider_availability():
    """Test disponibilità di ogni provider."""
    print("\n" + "="*60)
    print("TEST: Disponibilità Provider")
    print("="*60)

    providers_to_test = [
        (LLMProvider.OLLAMA, "mistral"),
        (LLMProvider.CLAUDE, "claude-3-haiku"),
        (LLMProvider.OPENAI, "gpt-3.5-turbo"),
    ]

    results = {}

    for provider, model in providers_to_test:
        print(f"\n  Testing {provider.value}...")

        try:
            config = LLMConfig(
                provider=provider,
                model_name=model,
                temperature=0.1
            )
            wrapper = LLMFactory.create(config)

            if wrapper.is_available():
                print(f"    ✅ {provider.value} disponibile")
                print(f"       Model: {model}")
                results[provider.value] = True
            else:
                print(f"    ❌ {provider.value} non disponibile")
                if provider == LLMProvider.OLLAMA:
                    print("       Avvia con: ollama serve")
                elif provider == LLMProvider.CLAUDE:
                    print("       Configura: ANTHROPIC_API_KEY in .env")
                elif provider == LLMProvider.OPENAI:
                    print("       Configura: OPENAI_API_KEY in .env")
                results[provider.value] = False

        except Exception as e:
            print(f"    ❌ Errore: {e}")
            results[provider.value] = False

    return results


def test_simple_generation():
    """Test generazione semplice con provider disponibile."""
    print("\n" + "="*60)
    print("TEST: Generazione Semplice")
    print("="*60)

    # Prova prima con Ollama
    print("\n  Tentativo con Ollama...")
    try:
        config = LLMConfig(
            provider=LLMProvider.OLLAMA,
            model_name="mistral"
        )
        wrapper = LLMFactory.create(config)

        if wrapper.is_available():
            prompt = "Rispondi con 'OK' in italiano."
            response = wrapper.generate(prompt)
            print(f"    ✅ Generazione riuscita")
            print(f"    Prompt: {prompt}")
            print(f"    Risposta: {response[:100]}...")
            return True
        else:
            print("    ⏭️ Ollama non disponibile, skip")

    except Exception as e:
        print(f"    ❌ Errore: {e}")

    # Se Ollama non disponibile, prova Claude
    if os.getenv('ANTHROPIC_API_KEY'):
        print("\n  Tentativo con Claude...")
        try:
            config = LLMConfig(
                provider=LLMProvider.CLAUDE,
                model_name="claude-3-haiku"
            )
            wrapper = LLMFactory.create(config)

            if wrapper.is_available():
                prompt = "Rispondi con 'OK' in italiano."
                response = wrapper.generate(prompt)
                print(f"    ✅ Generazione riuscita")
                print(f"    Risposta: {response[:100]}...")
                return True

        except Exception as e:
            print(f"    ❌ Errore: {e}")

    print("    ⚠️ Nessun provider disponibile per test generazione")
    return False


def test_generation_with_citations():
    """Test generazione con citazioni."""
    print("\n" + "="*60)
    print("TEST: Generazione con Citazioni")
    print("="*60)

    # Context di esempio
    context = [
        "Art. 2043 c.c. - Qualunque fatto doloso o colposo, che cagiona ad altri un danno ingiusto, obbliga colui che ha commesso il fatto a risarcire il danno.",
        "Art. 2059 c.c. - Il danno non patrimoniale deve essere risarcito solo nei casi determinati dalla legge."
    ]

    prompt = "Spiega brevemente la responsabilità extracontrattuale."

    # Prova con primo provider disponibile
    for provider_name in ['ollama', 'claude', 'openai']:
        print(f"\n  Tentativo con {provider_name}...")

        try:
            if provider_name == 'ollama':
                config = LLMConfig(provider=LLMProvider.OLLAMA, model_name="mistral")
            elif provider_name == 'claude' and os.getenv('ANTHROPIC_API_KEY'):
                config = LLMConfig(provider=LLMProvider.CLAUDE, model_name="claude-3-haiku")
            elif provider_name == 'openai' and os.getenv('OPENAI_API_KEY'):
                config = LLMConfig(provider=LLMProvider.OPENAI, model_name="gpt-3.5-turbo")
            else:
                print(f"    ⏭️ Skip {provider_name}")
                continue

            wrapper = LLMFactory.create(config)

            if not wrapper.is_available():
                print(f"    ⏭️ {provider_name} non disponibile")
                continue

            result = wrapper.generate_with_citations(prompt, context)

            print(f"    ✅ Generazione con citazioni riuscita!")
            print(f"    Citazioni trovate: {result.get('citations', [])}")
            print(f"    Testo (primi 200 char): {result['text'][:200]}...")
            print(f"    Provider usato: {result.get('provider_used')}")

            return True

        except Exception as e:
            print(f"    ❌ Errore: {e}")

    print("    ⚠️ Nessun provider disponibile per test citazioni")
    return False


def test_fallback_chain():
    """Test della fallback chain tra provider."""
    print("\n" + "="*60)
    print("TEST: Fallback Chain")
    print("="*60)

    try:
        # Setup manager con fallback
        manager = MultiLLMManager(
            primary_config=LLMConfig(
                provider=LLMProvider.CLAUDE,
                model_name="claude-3-haiku"
            ),
            fallback_configs=[
                LLMConfig(provider=LLMProvider.OLLAMA, model_name="mistral"),
                LLMConfig(provider=LLMProvider.OPENAI, model_name="gpt-3.5-turbo")
            ]
        )

        if manager.current:
            print(f"  ✅ Manager inizializzato")
            print(f"     Provider corrente: {manager.current.config.provider.value}")
            print(f"     Fallback disponibili: {len(manager.fallbacks)}")

            # Test generazione
            response = manager.generate("Test fallback: rispondi OK")
            print(f"  ✅ Generazione riuscita con: {manager.current.config.provider.value}")
            print(f"     Risposta: {response[:100]}...")

            return True
        else:
            print("  ❌ Nessun provider disponibile nel manager")
            return False

    except Exception as e:
        print(f"  ❌ Errore: {e}")
        return False


def test_config_from_env():
    """Test caricamento configurazione da env vars."""
    print("\n" + "="*60)
    print("TEST: Configurazione da Environment")
    print("="*60)

    try:
        # Salva env originale
        original_provider = os.getenv('LLM_PROVIDER')
        original_model = os.getenv('LLM_MODEL')

        # Set test env
        os.environ['LLM_PROVIDER'] = 'ollama'
        os.environ['LLM_MODEL'] = 'mistral'

        config = LLMConfig.from_env()

        print(f"  ✅ Config da env caricata")
        print(f"     Provider: {config.provider.value}")
        print(f"     Model: {config.model_name}")
        print(f"     Temperature: {config.temperature}")

        # Restore env
        if original_provider:
            os.environ['LLM_PROVIDER'] = original_provider
        if original_model:
            os.environ['LLM_MODEL'] = original_model

        return True

    except Exception as e:
        print(f"  ❌ Errore: {e}")
        return False


def main():
    """Esegue tutti i test."""
    print("\n" + "="*60)
    print("🧪 TEST SUITE LLM WRAPPER")
    print("="*60)

    # Esegui test built-in
    test_llm_wrapper()

    # Test aggiuntivi
    results = {
        "Configurazioni YAML": test_yaml_configs(),
        "Disponibilità Provider": test_provider_availability(),
        "Generazione Semplice": test_simple_generation(),
        "Generazione con Citazioni": test_generation_with_citations(),
        "Fallback Chain": test_fallback_chain(),
        "Config da Environment": test_config_from_env()
    }

    # Riepilogo
    print("\n" + "="*60)
    print("📊 RIEPILOGO TEST")
    print("="*60)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name:.<45} {status}")

    all_passed = all(results.values())

    print("\n" + "="*60)

    if all_passed:
        print("🎉 TUTTI I TEST PASSATI!")
        print("\nIl sistema wrapper LLM è configurato correttamente.")
    else:
        print("⚠️ ALCUNI TEST FALLITI")
        print("\nSuggerimenti:")
        print("  1. Avvia Ollama: ollama serve")
        print("  2. Configura API keys in .env")
        print("  3. Installa SDK provider: pip install anthropic openai")

    print("="*60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
