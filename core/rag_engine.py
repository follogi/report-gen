"""
Modulo RAG Engine per generazione relazioni legali con citazioni.

Questo modulo implementa il sistema RAG (Retrieval Augmented Generation) usando:
- LlamaIndex per orchestrazione
- ChromaDB per vector storage
- Ollama per LLM locale
- CitationQueryEngine per tracciabilità

Compatibile con llama-index 0.9.x+
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import chromadb
import requests
import yaml
from chromadb.config import Settings as ChromaSettings

# Import corretti per LlamaIndex moderna
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings,
    Document,
    load_index_from_storage
)
from llama_index.core.schema import (
    NodeWithScore,
    TextNode,
    MetadataMode
)
from llama_index.core.node_parser import (
    SentenceSplitter,
)
from llama_index.core.indices.query.base import BaseQueryEngine
from llama_index.core.response_synthesizers import (
    get_response_synthesizer,
    ResponseMode
)
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import (
    RetrieverQueryEngine,
    CitationQueryEngine
)

# LLM e Embeddings - Import specifici per provider
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Vector Store
from llama_index.vector_stores.chroma import ChromaVectorStore

# Import locali con import relativi per evitare circular imports
from core.confidence_scorer import CitationScore, ConfidenceScorer
from core.normative_loader import NormativeLoader

# Setup logging
logger = logging.getLogger(__name__)

# Verifica versione LlamaIndex installata
try:
    import llama_index
    LLAMA_VERSION = getattr(llama_index, '__version__', 'unknown')
    logger.info(f"📦 LlamaIndex version: {LLAMA_VERSION}")

    # Warning se versione incompatibile
    if LLAMA_VERSION.startswith("0.9"):
        logger.error(
            "❌ LlamaIndex 0.9.x non compatibile. "
            "Reinstalla: pip uninstall llama-index -y && pip install -r requirements.txt"
        )
except Exception as e:
    logger.warning(f"⚠️ Impossibile verificare versione LlamaIndex: {e}")


class RAGEngineError(Exception):
    """Eccezione per errori del RAG engine."""
    pass


class LegalRAGEngine:
    """
    Engine RAG specializzato per documenti legali.

    Features:
    - Doppio index: normative (persistente) + esempi (temporaneo)
    - CitationQueryEngine per tracciabilità completa
    - Confidence scoring per ogni retrieval
    - Sistema prompt specializzato per diritto italiano
    """

    def __init__(self, config_path: str = "config/settings.yaml"):
        """
        Inizializza il RAG engine.

        Args:
            config_path: Percorso al file di configurazione
        """
        logger.info("Inizializzazione LegalRAGEngine...")

        # Verifica compatibilità import
        self._verify_imports()

        # Carica configurazione
        self.config = self._load_config(config_path)
        self.prompts = self._load_prompts()

        # Inizializza componenti
        self._setup_llm()
        self._setup_embeddings()
        self._setup_vector_stores()

        # Componenti ausiliari
        self.normative_loader = NormativeLoader(
            normative_dir=self.config.get("data", {}).get("normative_dir", "data/normative")
        )
        self.confidence_scorer = ConfidenceScorer(self.config)

        # Indici
        self.normative_index = None
        self.esempi_index = None

        logger.info("LegalRAGEngine inizializzato con successo")

    def _load_config(self, config_path: str) -> Dict:
        """Carica configurazione da YAML."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config non trovato: {config_path}, uso default")
            return {}

    def _load_prompts(self) -> Dict:
        """Carica template prompts."""
        try:
            with open("config/prompts.yaml", 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning("Prompts file non trovato, uso default")
            return {
                "system_prompt": "Sei un assistente legale specializzato nel diritto italiano.",
                "query_prompt_template": "{context}\n\nDomanda: {query}"
            }

    def _verify_imports(self):
        """Verifica che tutti gli import critici siano disponibili."""
        required_imports = [
            ("llama_index.core", "VectorStoreIndex"),
            ("llama_index.llms.ollama", "Ollama"),
            ("llama_index.embeddings.huggingface", "HuggingFaceEmbedding"),
            ("llama_index.vector_stores.chroma", "ChromaVectorStore"),
        ]

        missing = []
        for module_name, class_name in required_imports:
            try:
                module = __import__(module_name, fromlist=[class_name])
                getattr(module, class_name)
            except (ImportError, AttributeError) as e:
                missing.append(f"{module_name}.{class_name}")
                logger.error(f"❌ Import fallito: {module_name}.{class_name}")

        if missing:
            raise ImportError(
                f"Dipendenze mancanti: {', '.join(missing)}. "
                f"Reinstalla: pip install -r requirements.txt"
            )

        logger.info("✅ Tutti gli import verificati")

    def _setup_llm(self):
        """Configura il Large Language Model (Ollama) con verifica connessione."""
        ollama_config = self.config.get("ollama", {})
        base_url = ollama_config.get("base_url", "http://localhost:11434")
        model_name = ollama_config.get("model", "mistral:latest")

        # Verifica che Ollama sia raggiungibile
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                raise ConnectionError(f"Ollama non raggiungibile su {base_url}")

            # Verifica che il modello sia disponibile
            available_models = response.json()
            models_list = [m['name'] for m in available_models.get('models', [])]

            # Normalizza nome modello per confronto (mistral vs mistral:latest)
            model_base = model_name.split(':')[0]
            if not any(model_base in m for m in models_list):
                logger.warning(
                    f"⚠️ Modello {model_name} non trovato. "
                    f"Modelli disponibili: {', '.join(models_list)}"
                )
                logger.info(f"💡 Scarica il modello con: ollama pull {model_name}")

            logger.info(f"✅ Ollama raggiungibile su {base_url}")

        except requests.RequestException as e:
            logger.error(f"❌ Errore connessione Ollama: {e}")
            logger.warning("⚠️ Assicurati che Ollama sia in esecuzione: ollama serve")
            raise ConnectionError(
                f"Impossibile connettersi a Ollama su {base_url}. "
                f"Avvia Ollama con: ollama serve"
            ) from e

        # Configura LLM
        self.llm = Ollama(
            model=model_name,
            base_url=base_url,
            temperature=ollama_config.get("temperature", 0.1),
            request_timeout=ollama_config.get("timeout", 120),
            context_window=ollama_config.get("context_window", 8192),
            additional_kwargs={
                "num_predict": 2048,  # Max token in output
                "top_p": 0.9,  # Focus su token più probabili
                "repeat_penalty": 1.1,  # Evita ripetizioni
            }
        )

        # Imposta come LLM globale per LlamaIndex
        Settings.llm = self.llm

        logger.info(f"✅ LLM configurato: Ollama {model_name}")

    def _setup_embeddings(self):
        """Configura il modello di embeddings locale."""
        embed_config = self.config.get("embedding", {})
        model_name = embed_config.get("model", "sentence-transformers/all-MiniLM-L6-v2")

        try:
            self.embed_model = HuggingFaceEmbedding(
                model_name=model_name,
                cache_folder=embed_config.get("cache_dir", "./cache/embeddings"),
                embed_batch_size=32,  # Batch size per embedding
                max_length=512,  # Lunghezza massima sequenze
                device=embed_config.get("device", "cpu")  # Usa "cuda" se hai GPU
            )

            # Imposta come embedding globale per LlamaIndex
            Settings.embed_model = self.embed_model

            logger.info(f"✅ Embeddings configurati: {model_name}")

        except Exception as e:
            logger.error(f"❌ Errore caricamento embeddings: {e}")
            raise RuntimeError(
                f"Impossibile caricare embedding model {model_name}. "
                f"Verifica che sentence-transformers sia installato correttamente."
            ) from e

    def _setup_vector_stores(self):
        """Configura ChromaDB per vector storage."""
        chroma_config = self.config.get("chromadb", {})
        persist_dir = Path(chroma_config.get("persist_directory", "./vectordb"))

        # Crea directory se non esiste
        persist_dir.mkdir(exist_ok=True, parents=True)

        try:
            # Client ChromaDB persistente con configurazione
            self.chroma_client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=ChromaSettings(
                    anonymized_telemetry=False,  # Disabilita telemetria
                    allow_reset=True  # Permette reset durante sviluppo
                )
            )

            logger.info(f"✅ ChromaDB configurato in: {persist_dir}")

        except Exception as e:
            logger.error(f"❌ Errore inizializzazione ChromaDB: {e}")
            raise RuntimeError(
                f"Impossibile inizializzare ChromaDB in {persist_dir}. "
                f"Verifica i permessi della directory."
            ) from e

        # Configura node parser per documenti legali
        Settings.node_parser = SentenceSplitter(
            chunk_size=512,
            chunk_overlap=50,
            separator=" ",
            paragraph_separator="\n\n"
        )

        logger.info("✅ Node parser configurato per documenti legali")

    def build_normative_index(self, force_rebuild: bool = False) -> VectorStoreIndex:
        """
        Costruisce o carica l'indice delle normative.

        Args:
            force_rebuild: Se True, ricostruisce l'indice da zero

        Returns:
            VectorStoreIndex delle normative
        """
        logger.info("Costruzione indice normative...")

        collection_name = self.config.get("chromadb", {}).get("collection_normative", "normative_v1")

        # Se force_rebuild, elimina collection esistente
        if force_rebuild:
            try:
                self.chroma_client.delete_collection(collection_name)
                logger.info("Collection normative eliminata per rebuild")
            except:
                pass

        # Crea o ottieni collection
        chroma_collection = self.chroma_client.get_or_create_collection(collection_name)

        # Crea vector store
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

        # Se collection è vuota, costruisci indice
        if chroma_collection.count() == 0 or force_rebuild:
            logger.info("Costruzione nuovo indice normative...")

            # Carica normative
            documents = self._load_normative_documents()

            if not documents:
                logger.warning("Nessuna normativa trovata!")
                return None

            # Crea indice
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            # Configura chunking specializzato per articoli
            chunk_config = self.config.get("chunking", {})
            text_splitter = SentenceSplitter(
                chunk_size=chunk_config.get("chunk_size", 512),
                chunk_overlap=chunk_config.get("chunk_overlap", 50),
                separator=chunk_config.get("separator", "\n\n")
            )

            Settings.text_splitter = text_splitter

            self.normative_index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
                show_progress=True
            )

            logger.info(f"Indice normative creato con {len(documents)} documenti")

        else:
            logger.info("Caricamento indice normative esistente...")

            # Carica indice esistente
            self.normative_index = VectorStoreIndex.from_vector_store(vector_store)

            logger.info(f"Indice normative caricato ({chroma_collection.count()} chunks)")

        return self.normative_index

    def _load_normative_documents(self) -> List[Document]:
        """
        Carica le normative come documenti LlamaIndex da file JSON locali.

        Returns:
            Lista di Document
        """
        documents = []

        # Carica tutte le normative dalla directory
        all_normative = self.normative_loader.load_all_normative()

        if not all_normative:
            logger.warning("Nessuna normativa trovata in data/normative/")
            return documents

        # Converti ogni normativa in documenti
        for normativa_data in all_normative:
            norm_documents = self.normative_loader.convert_to_documents(normativa_data)
            documents.extend(norm_documents)

        logger.info(f"Caricati {len(documents)} articoli da {len(all_normative)} normative")

        return documents

    def build_esempi_index(self, esempio_files: List[str], session_id: str = "default") -> VectorStoreIndex:
        """
        Costruisce indice temporaneo per esempi della sessione.

        Args:
            esempio_files: Lista di percorsi a file esempio
            session_id: ID della sessione

        Returns:
            VectorStoreIndex degli esempi
        """
        logger.info(f"Costruzione indice esempi (sessione: {session_id})...")

        collection_name = f"{self.config.get('chromadb', {}).get('collection_esempi_prefix', 'session_')}{session_id}"

        # Elimina collection precedente se esiste
        try:
            self.chroma_client.delete_collection(collection_name)
        except:
            pass

        # Crea nuova collection
        chroma_collection = self.chroma_client.create_collection(collection_name)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

        # Carica documenti esempio
        documents = self._load_esempio_documents(esempio_files)

        if not documents:
            logger.warning("Nessun esempio caricato")
            return None

        # Crea indice
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        self.esempi_index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            show_progress=True
        )

        logger.info(f"Indice esempi creato con {len(documents)} documenti")

        return self.esempi_index

    def _load_esempio_documents(self, esempio_files: List[str]) -> List[Document]:
        """
        Carica file esempio come documenti.

        Args:
            esempio_files: Lista percorsi file

        Returns:
            Lista Document
        """
        documents = []

        for idx, file_path in enumerate(esempio_files):
            try:
                # Determina tipo file
                file_path_obj = Path(file_path)
                extension = file_path_obj.suffix.lower()

                # Leggi contenuto
                if extension == '.txt':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                elif extension == '.docx':
                    from docx import Document as DocxDocument
                    docx_doc = DocxDocument(file_path)
                    text = "\n".join([p.text for p in docx_doc.paragraphs])
                elif extension == '.pdf':
                    from PyPDF2 import PdfReader
                    reader = PdfReader(file_path)
                    text = "\n".join([page.extract_text() for page in reader.pages])
                else:
                    logger.warning(f"Tipo file non supportato: {extension}")
                    continue

                # Crea documento
                doc = Document(
                    text=text,
                    metadata={
                        "filename": file_path_obj.name,
                        "source": file_path,
                        "tipo": "esempio",
                        "index": idx
                    },
                    id_=f"esempio_{idx}"
                )

                documents.append(doc)

                logger.info(f"Esempio caricato: {file_path_obj.name}")

            except Exception as e:
                logger.error(f"Errore caricamento {file_path}: {e}")

        return documents

    def query_with_citations(
        self,
        query: str,
        use_esempi: bool = True,
        confidence_threshold: float = 0.7,
        top_k: int = 5
    ) -> Dict:
        """
        Esegue query con citazioni verificate.

        Args:
            query: Domanda/richiesta dell'utente
            use_esempi: Se True, usa anche indice esempi
            confidence_threshold: Soglia minima di confidenza
            top_k: Numero di chunks da recuperare

        Returns:
            Dizionario con risposta, citazioni e confidence scores
        """
        logger.info(f"Query con citazioni: {query[:100]}...")

        if self.normative_index is None:
            raise RAGEngineError("Indice normative non costruito. Eseguire build_normative_index() prima.")

        # Crea CitationQueryEngine
        citation_query_engine = CitationQueryEngine.from_args(
            index=self.normative_index,
            similarity_top_k=top_k,
            citation_chunk_size=512,
        )

        # Esegui query
        try:
            # Costruisci prompt con system message
            full_prompt = self._build_query_prompt(query)

            response = citation_query_engine.query(full_prompt)

            # Estrai citazioni
            citations_raw = getattr(response, 'source_nodes', [])

            # Converti in CitationScore con confidence
            citations = []
            for node in citations_raw:
                score = node.score if hasattr(node, 'score') else 0.5

                citation = CitationScore(
                    text=node.text if hasattr(node, 'text') else str(node),
                    source=node.metadata.get('nome_normativa', 'Unknown') if hasattr(node, 'metadata') else 'Unknown',
                    score=score,
                    level=self.confidence_scorer._get_confidence_level(score),
                    metadata=node.metadata if hasattr(node, 'metadata') else {}
                )

                citations.append(citation)

            # Filtra per confidence threshold
            citations_filtered = [c for c in citations if c.score >= confidence_threshold]

            # Score generale della risposta
            overall_confidence = sum(c.score for c in citations_filtered) / max(len(citations_filtered), 1)

            result = {
                "response": str(response),
                "citations": citations_filtered,
                "all_citations": citations,
                "confidence": overall_confidence,
                "meets_threshold": overall_confidence >= confidence_threshold,
                "metadata": {
                    "query": query,
                    "num_citations": len(citations_filtered),
                    "top_k": top_k
                }
            }

            logger.info(f"Query completata - Confidence: {overall_confidence:.2f}, Citazioni: {len(citations_filtered)}")

            return result

        except Exception as e:
            logger.error(f"Errore durante query: {e}")
            raise RAGEngineError(f"Errore query: {e}")

    def _build_query_prompt(self, query: str, esempi_context: str = "", template_structure: str = "") -> str:
        """
        Costruisce il prompt completo per la query.

        Args:
            query: Query utente
            esempi_context: Contesto dagli esempi (opzionale)
            template_structure: Struttura template (opzionale)

        Returns:
            Prompt formattato
        """
        # Usa template da config
        template = self.prompts.get("query_prompt_template", "{user_request}")

        # Sostituisci placeholder
        prompt = template.format(
            normative_context="[Recuperato automaticamente dal RAG]",
            esempi_context=esempi_context or "[Nessun esempio fornito]",
            template_structure=template_structure or "[Nessun template fornito]",
            user_request=query
        )

        return prompt

    def generate_legal_document(
        self,
        user_request: str,
        template_structure: Optional[str] = None,
        esempi_context: Optional[str] = None,
        style: str = "formale"
    ) -> Dict:
        """
        Genera un documento legale completo.

        Args:
            user_request: Richiesta dell'utente
            template_structure: Struttura template (opzionale)
            esempi_context: Contesto esempi (opzionale)
            style: Stile di scrittura (formale/semi_formale/sintetico)

        Returns:
            Dizionario con documento generato e metadata
        """
        logger.info("Generazione documento legale...")

        # Aggiungi istruzioni di stile al prompt
        style_instruction = self.prompts.get("style_prompts", {}).get(style, "")

        # Costruisci query completa
        full_query = f"{style_instruction}\n\n{user_request}"

        # Esegui query con citazioni
        result = self.query_with_citations(
            query=full_query,
            use_esempi=esempi_context is not None
        )

        # Valuta confidence complessiva
        section_score = self.confidence_scorer.score_generated_text(
            generated_text=result['response'],
            citations=[c.to_dict() for c in result['citations']]
        )

        # Genera report
        report = self.confidence_scorer.generate_report([section_score])

        return {
            "document": result['response'],
            "citations": result['citations'],
            "confidence": result['confidence'],
            "section_score": section_score.to_dict(),
            "report": report,
            "needs_review": section_score.needs_review
        }

    def clear_session_index(self, session_id: str = "default"):
        """
        Elimina indice temporaneo della sessione.

        Args:
            session_id: ID della sessione
        """
        collection_name = f"{self.config.get('chromadb', {}).get('collection_esempi_prefix', 'session_')}{session_id}"

        try:
            self.chroma_client.delete_collection(collection_name)
            self.esempi_index = None
            logger.info(f"Indice sessione {session_id} eliminato")
        except Exception as e:
            logger.warning(f"Errore eliminazione sessione: {e}")

    def get_statistics(self) -> Dict:
        """
        Restituisce statistiche sul RAG engine.

        Returns:
            Dizionario con statistiche
        """
        stats = {
            "normative_index_loaded": self.normative_index is not None,
            "esempi_index_loaded": self.esempi_index is not None,
            "llm_model": self.config.get("ollama", {}).get("model", "unknown"),
            "embedding_model": self.config.get("embedding", {}).get("model", "unknown")
        }

        # Aggiungi stats normative se disponibili
        if self.normative_index:
            try:
                collection_name = self.config.get("chromadb", {}).get("collection_normative", "normative_v1")
                collection = self.chroma_client.get_collection(collection_name)
                stats["normative_chunks"] = collection.count()
            except:
                stats["normative_chunks"] = 0

        # Statistiche normative loader
        loader_stats = self.normative_loader.get_statistics()
        stats.update({
            "num_normative_files": loader_stats["num_normative"],
            "total_normative_articles": loader_stats["total_articles"]
        })

        return stats


def main():
    """Funzione di test per il modulo."""
    logging.basicConfig(level=logging.INFO)

    print("=== Test LegalRAGEngine ===\n")

    # Inizializza engine
    engine = LegalRAGEngine()

    # Test build normative index
    print("Costruzione indice normative...")
    index = engine.build_normative_index(force_rebuild=False)

    if index:
        print("✅ Indice normative pronto\n")

        # Test query
        print("Test query con citazioni...")
        result = engine.query_with_citations(
            query="Cos'è la responsabilità extracontrattuale?",
            confidence_threshold=0.5
        )

        print(f"Risposta: {result['response'][:200]}...")
        print(f"Citazioni: {len(result['citations'])}")
        print(f"Confidence: {result['confidence']:.2f}")
        print()

        # Statistiche
        stats = engine.get_statistics()
        print("Statistiche:")
        for key, value in stats.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
