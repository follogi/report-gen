"""
Caricatore di normative da file JSON locali.

Questo modulo sostituisce NormativeFetcher eliminando la dipendenza
dall'API Normattiva.it. Carica normative pre-scaricate in formato JSON.
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from llama_index.core import Document

logger = logging.getLogger(__name__)


class NormativeLoader:
    """
    Carica normative da file JSON nella directory data/normative/.

    Formato JSON atteso:
    {
        "codice": "CC",
        "urlFonte": "https://...",
        "dataDownload": "2024-01-15T10:30:00Z",
        "testiArticoli": ["Art. 1 - ...", "Art. 2 - ..."]
    }
    """

    def __init__(self, normative_dir: str = "data/normative"):
        """
        Inizializza il loader.

        Args:
            normative_dir: Path alla directory contenente file JSON normative
        """
        self.normative_dir = Path(normative_dir)

        # Crea directory se non esiste
        self.normative_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"NormativeLoader inizializzato: {self.normative_dir}")

    def list_available_normative(self) -> List[Dict[str, str]]:
        """
        Lista tutte le normative disponibili nella directory.

        Returns:
            Lista di dict con metadata: [{"codice": "CC", "filename": "codice_civile.json", "path": "..."}]
        """
        normative_files = []

        for json_file in self.normative_dir.glob("*.json"):
            try:
                # Leggi solo metadata (non caricare tutti gli articoli)
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                normative_files.append({
                    "codice": data.get("codice", "UNKNOWN"),
                    "filename": json_file.name,
                    "path": str(json_file),
                    "url_fonte": data.get("urlFonte", ""),
                    "data_download": data.get("dataDownload", "")
                })
            except Exception as e:
                logger.warning(f"Errore lettura {json_file}: {e}")

        logger.info(f"Trovate {len(normative_files)} normative")
        return normative_files

    def load_normativa(self, codice: str) -> Optional[Dict]:
        """
        Carica una normativa specifica per codice.

        Args:
            codice: Codice normativa (es: "CC", "CP")

        Returns:
            Dict con struttura completa o None se non trovata
        """
        # Cerca file con questo codice
        for json_file in self.normative_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if data.get("codice") == codice:
                    logger.info(f"Normativa {codice} caricata da {json_file.name}")
                    return data
            except Exception as e:
                logger.error(f"Errore caricamento {json_file}: {e}")

        logger.warning(f"Normativa {codice} non trovata")
        return None

    def load_all_normative(self) -> List[Dict]:
        """
        Carica tutte le normative disponibili.

        Returns:
            Lista di dict con struttura completa
        """
        all_normative = []

        for json_file in self.normative_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                all_normative.append(data)
                logger.info(f"Caricata: {data.get('codice', 'UNKNOWN')} da {json_file.name}")
            except Exception as e:
                logger.error(f"Errore caricamento {json_file}: {e}")

        return all_normative

    def convert_to_documents(self, normativa_data: Dict) -> List[Document]:
        """
        Converte una normativa in documenti LlamaIndex.

        Args:
            normativa_data: Dict con struttura normativa

        Returns:
            Lista di Document LlamaIndex (uno per articolo)
        """
        documents = []

        codice = normativa_data.get("codice", "UNKNOWN")
        url_fonte = normativa_data.get("urlFonte", "")
        testi_articoli = normativa_data.get("testiArticoli", [])

        for idx, testo_articolo in enumerate(testi_articoli, start=1):
            # Estrai numero articolo dal testo (assume formato "Art. X - ...")
            numero_articolo = self._extract_article_number(testo_articolo)

            # Metadata ricchi
            metadata = {
                "codice": codice,
                "articolo": numero_articolo or f"art_{idx}",
                "fonte": url_fonte,
                "tipo": "normativa",
                "indice_articolo": idx
            }

            doc = Document(
                text=testo_articolo,
                extra_info=metadata,
                doc_id=f"{codice}_art_{numero_articolo or idx}"
            )

            documents.append(doc)

        logger.info(f"Convertiti {len(documents)} articoli per {codice}")
        return documents

    def _extract_article_number(self, text: str) -> Optional[str]:
        """
        Estrae numero articolo dal testo (es: "Art. 2043 - ..." -> "2043").

        Args:
            text: Testo articolo

        Returns:
            Numero articolo o None
        """
        # Pattern: "Art. 123" o "Articolo 123"
        match = re.search(r'Art(?:icolo)?\.?\s+(\d+)', text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def get_statistics(self) -> Dict:
        """
        Statistiche sulle normative caricate.

        Returns:
            Dict con conteggi
        """
        normative = self.list_available_normative()

        total_articles = 0
        for norm in normative:
            try:
                with open(norm['path'], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                total_articles += len(data.get('testiArticoli', []))
            except:
                pass

        return {
            "num_normative": len(normative),
            "total_articles": total_articles,
            "normative_directory": str(self.normative_dir)
        }


def create_example_normativa(output_path: str):
    """
    Crea un file JSON esempio per testing.

    Args:
        output_path: Path dove salvare il file
    """
    example = {
        "codice": "EXAMPLE",
        "urlFonte": "https://example.com/normativa",
        "dataDownload": datetime.now().isoformat(),
        "testiArticoli": [
            "Art. 1 - Esempio primo articolo. Questo è il testo completo del primo articolo della normativa esempio.",
            "Art. 2 - Esempio secondo articolo. Questo è il testo completo del secondo articolo."
        ]
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(example, f, indent=2, ensure_ascii=False)

    logger.info(f"File esempio creato: {output_path}")


if __name__ == "__main__":
    # Test del loader
    logging.basicConfig(level=logging.INFO)

    loader = NormativeLoader()

    # Crea esempio se directory vuota
    if not list(loader.normative_dir.glob("*.json")):
        create_example_normativa(str(loader.normative_dir / "esempio.json"))

    # Test caricamento
    normative = loader.list_available_normative()
    print(f"\n=� Normative disponibili: {len(normative)}")

    for norm in normative:
        print(f"  - {norm['codice']}: {norm['filename']}")

    # Test statistiche
    stats = loader.get_statistics()
    print(f"\n=� Statistiche:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
