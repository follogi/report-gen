"""
Modulo per il download e la gestione delle normative italiane.

Questo modulo si occupa di:
- Scaricare normative da Normattiva.it
- Parsare il contenuto XML
- Salvare in formato strutturato JSON
- Gestire cache e aggiornamenti
- Fornire fallback in caso di errore
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

import requests
import yaml
from bs4 import BeautifulSoup
from tqdm import tqdm

# Configurazione logging
logger = logging.getLogger(__name__)


class NormativeNotFoundError(Exception):
    """Eccezione sollevata quando una normativa non viene trovata."""
    pass


class NormativeFetcherError(Exception):
    """Eccezione generica per errori del fetcher."""
    pass


class NormativeFetcher:
    """
    Classe per scaricare e gestire normative italiane da Normattiva.it.

    Attributes:
        base_url: URL base di Normattiva
        data_dir: Directory per salvare le normative
        config: Configurazione caricata da settings.yaml
    """

    # Normative prioritarie da scaricare al primo avvio
    NORMATIVE_PRIORITARIE = {
        "costituzione": {
            "urn": "urn:nir:stato:costituzione:1947-12-27;1",
            "nome": "Costituzione della Repubblica Italiana",
            "anno": "1947"
        },
        "codice_civile": {
            "urn": "urn:nir:stato:regio.decreto:1942-03-16;262",
            "nome": "Codice Civile",
            "anno": "1942"
        },
        "codice_penale": {
            "urn": "urn:nir:stato:regio.decreto:1930-10-19;1398",
            "nome": "Codice Penale",
            "anno": "1930"
        },
        "codice_procedura_civile": {
            "urn": "urn:nir:stato:regio.decreto:1940-10-28;1443",
            "nome": "Codice di Procedura Civile",
            "anno": "1940"
        },
        "codice_consumo": {
            "urn": "urn:nir:stato:decreto.legislativo:2005-09-06;206",
            "nome": "Codice del Consumo",
            "anno": "2005"
        },
        "codice_privacy": {
            "urn": "urn:nir:stato:decreto.legislativo:2003-06-30;196",
            "nome": "Codice in materia di protezione dei dati personali",
            "anno": "2003"
        }
    }

    def __init__(self, config_path: str = "config/settings.yaml"):
        """
        Inizializza il fetcher delle normative.

        Args:
            config_path: Percorso al file di configurazione
        """
        self.config = self._load_config(config_path)
        self.base_url = self.config.get("normative", {}).get(
            "base_url",
            "https://www.normattiva.it"
        )
        self.data_dir = Path("data/normative_base")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Configurazione sessione HTTP
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Legal AI System)"
        })

        logger.info("NormativeFetcher inizializzato")

    def _load_config(self, config_path: str) -> Dict:
        """Carica la configurazione da file YAML."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"File di configurazione {config_path} non trovato, uso default")
            return {}

    def _compute_hash(self, text: str) -> str:
        """Calcola hash MD5 di un testo."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def _get_normativa_path(self, codice: str) -> Path:
        """Restituisce il percorso della directory di una normativa."""
        return self.data_dir / codice

    def _save_metadata(self, codice: str, metadata: Dict):
        """Salva i metadata di una normativa."""
        norm_path = self._get_normativa_path(codice)
        norm_path.mkdir(parents=True, exist_ok=True)

        metadata_file = norm_path / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        logger.debug(f"Metadata salvati per {codice}")

    def _load_metadata(self, codice: str) -> Optional[Dict]:
        """Carica i metadata di una normativa se esistono."""
        metadata_file = self._get_normativa_path(codice) / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def _save_articolo(self, codice: str, numero_articolo: str, articolo_data: Dict):
        """Salva un singolo articolo di una normativa."""
        articoli_dir = self._get_normativa_path(codice) / "articoli"
        articoli_dir.mkdir(parents=True, exist_ok=True)

        # Normalizza numero articolo per filename (es: "1" -> "art_001.json")
        filename = f"art_{numero_articolo.zfill(3)}.json"
        articolo_file = articoli_dir / filename

        with open(articolo_file, 'w', encoding='utf-8') as f:
            json.dump(articolo_data, f, ensure_ascii=False, indent=2)

    def is_normativa_cached(self, codice: str) -> bool:
        """
        Verifica se una normativa è già stata scaricata e salvata.

        Args:
            codice: Codice identificativo della normativa

        Returns:
            True se la normativa è in cache
        """
        metadata = self._load_metadata(codice)
        if metadata is None:
            return False

        # Verifica che esistano anche gli articoli
        articoli_dir = self._get_normativa_path(codice) / "articoli"
        return articoli_dir.exists() and len(list(articoli_dir.glob("*.json"))) > 0

    def _fetch_from_normattiva(self, urn: str, max_retries: int = 3) -> Optional[str]:
        """
        Scarica il contenuto di una normativa da Normattiva.it.

        Args:
            urn: URN della normativa
            max_retries: Numero massimo di tentativi

        Returns:
            Contenuto XML o None se fallisce
        """
        # Costruisce URL per Normattiva
        # Formato: /uri-res/N2Ls?urn:nir:...
        url = f"{self.base_url}/uri-res/N2Ls?{urn}"

        for attempt in range(max_retries):
            try:
                logger.info(f"Scarico normativa da: {url} (tentativo {attempt + 1}/{max_retries})")
                response = self.session.get(
                    url,
                    timeout=self.config.get("normative", {}).get("timeout", 30)
                )

                if response.status_code == 200:
                    logger.info("Normativa scaricata con successo")
                    return response.text
                elif response.status_code == 404:
                    logger.error(f"Normativa non trovata: {urn}")
                    return None
                else:
                    logger.warning(f"Status code {response.status_code}, riprovo...")

            except requests.RequestException as e:
                logger.error(f"Errore durante il download: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Backoff esponenziale

        return None

    def _parse_normativa_html(self, html_content: str) -> List[Dict]:
        """
        Parsing semplificato di normativa da HTML.

        Nota: Normattiva restituisce HTML, non XML puro.
        Questo parser estrae articoli dal contenuto HTML.

        Args:
            html_content: Contenuto HTML della normativa

        Returns:
            Lista di dizionari con dati degli articoli
        """
        articoli = []

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Cerca tutti gli elementi articolo (dipende dalla struttura HTML di Normattiva)
            # Questo è un parsing semplificato - la struttura reale potrebbe variare
            articoli_elements = soup.find_all(['div', 'article'], class_=lambda x: x and 'articolo' in x.lower())

            if not articoli_elements:
                # Fallback: cerca pattern comuni
                articoli_elements = soup.find_all(text=lambda t: t and 'Art.' in t)

            for idx, elem in enumerate(articoli_elements, 1):
                # Estrai testo dell'articolo
                if hasattr(elem, 'get_text'):
                    testo = elem.get_text(strip=True)
                else:
                    testo = str(elem)

                # Cerca numero articolo nel testo
                numero = str(idx)
                if 'Art.' in testo:
                    # Estrae numero dopo "Art."
                    try:
                        numero = testo.split('Art.')[1].split()[0].strip('.')
                    except:
                        pass

                articolo_data = {
                    "numero": numero,
                    "rubrica": "",  # Da estrarre se disponibile
                    "testo": testo,
                    "commi": [],  # Da parsare se necessario
                    "note": ""
                }

                articoli.append(articolo_data)

            logger.info(f"Estratti {len(articoli)} articoli dalla normativa")

        except Exception as e:
            logger.error(f"Errore nel parsing HTML: {e}")

        return articoli

    def _create_fallback_normativa(self, codice: str, info: Dict) -> List[Dict]:
        """
        Crea una versione fallback di una normativa con dati minimi.

        Questo viene usato quando Normattiva.it non è disponibile.
        Include solo informazioni base per permettere al sistema di funzionare.

        Args:
            codice: Codice della normativa
            info: Informazioni base della normativa

        Returns:
            Lista di articoli fallback
        """
        logger.warning(f"Creazione fallback per {codice}")

        # Dati minimi per funzionamento base
        articoli_fallback = [
            {
                "numero": "1",
                "rubrica": "Articolo di fallback",
                "testo": f"ATTENZIONE: Questa è una versione fallback di {info['nome']}. "
                         f"Il testo completo non è stato scaricato. "
                         f"Si consiglia di verificare la normativa originale.",
                "commi": [],
                "note": "Dati non disponibili da Normattiva.it"
            }
        ]

        return articoli_fallback

    def download_normativa(
        self,
        codice: str,
        force_refresh: bool = False,
        use_fallback: bool = True
    ) -> bool:
        """
        Scarica e salva una normativa specifica.

        Args:
            codice: Codice identificativo della normativa
            force_refresh: Se True, riscarica anche se in cache
            use_fallback: Se True, usa fallback se download fallisce

        Returns:
            True se il download ha successo
        """
        # Verifica se già in cache
        if not force_refresh and self.is_normativa_cached(codice):
            logger.info(f"Normativa {codice} già in cache")
            return True

        if codice not in self.NORMATIVE_PRIORITARIE:
            logger.error(f"Codice normativa {codice} non riconosciuto")
            return False

        info = self.NORMATIVE_PRIORITARIE[codice]
        logger.info(f"Download di: {info['nome']}")

        # Scarica da Normattiva
        html_content = self._fetch_from_normattiva(info['urn'])

        articoli = []
        if html_content:
            articoli = self._parse_normativa_html(html_content)

        # Se non ci sono articoli e fallback è abilitato
        if not articoli and use_fallback:
            articoli = self._create_fallback_normativa(codice, info)

        if not articoli:
            raise NormativeNotFoundError(f"Impossibile scaricare {codice}")

        # Salva metadata
        metadata = {
            "codice": codice,
            "nome": info['nome'],
            "anno": info['anno'],
            "urn": info['urn'],
            "data_download": datetime.now().isoformat(),
            "hash": self._compute_hash(str(articoli)),
            "numero_articoli": len(articoli),
            "fonte": "normattiva" if html_content else "fallback"
        }

        self._save_metadata(codice, metadata)

        # Salva articoli
        for articolo in articoli:
            self._save_articolo(codice, articolo['numero'], articolo)

        logger.info(f"Normativa {codice} salvata con successo ({len(articoli)} articoli)")
        return True

    def download_all_prioritarie(
        self,
        progress_callback=None,
        force_refresh: bool = False
    ) -> Dict[str, bool]:
        """
        Scarica tutte le normative prioritarie.

        Args:
            progress_callback: Funzione callback per aggiornare progress bar
            force_refresh: Se True, riscarica tutto

        Returns:
            Dizionario {codice: successo}
        """
        risultati = {}
        totale = len(self.NORMATIVE_PRIORITARIE)

        for idx, codice in enumerate(self.NORMATIVE_PRIORITARIE.keys(), 1):
            try:
                logger.info(f"Download {idx}/{totale}: {codice}")

                if progress_callback:
                    progress_callback(idx, totale, codice)

                successo = self.download_normativa(
                    codice,
                    force_refresh=force_refresh
                )
                risultati[codice] = successo

                # Piccola pausa tra download per non sovraccaricare il server
                if idx < totale:
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Errore download {codice}: {e}")
                risultati[codice] = False

        return risultati

    def get_normativa(self, codice: str) -> Optional[Dict]:
        """
        Recupera una normativa già scaricata.

        Args:
            codice: Codice della normativa

        Returns:
            Dizionario con metadata e articoli
        """
        if not self.is_normativa_cached(codice):
            logger.warning(f"Normativa {codice} non in cache")
            return None

        metadata = self._load_metadata(codice)

        # Carica tutti gli articoli
        articoli_dir = self._get_normativa_path(codice) / "articoli"
        articoli = []

        for art_file in sorted(articoli_dir.glob("art_*.json")):
            with open(art_file, 'r', encoding='utf-8') as f:
                articoli.append(json.load(f))

        return {
            "metadata": metadata,
            "articoli": articoli
        }

    def get_articolo(self, codice: str, numero: str) -> Optional[Dict]:
        """
        Recupera un articolo specifico di una normativa.

        Args:
            codice: Codice della normativa
            numero: Numero dell'articolo

        Returns:
            Dati dell'articolo o None
        """
        filename = f"art_{numero.zfill(3)}.json"
        art_path = self._get_normativa_path(codice) / "articoli" / filename

        if not art_path.exists():
            logger.warning(f"Articolo {numero} non trovato in {codice}")
            return None

        with open(art_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_normative_available(self) -> List[Dict]:
        """
        Lista tutte le normative disponibili (scaricate).

        Returns:
            Lista di metadata delle normative
        """
        normative = []

        for norm_dir in self.data_dir.iterdir():
            if norm_dir.is_dir():
                metadata = self._load_metadata(norm_dir.name)
                if metadata:
                    normative.append(metadata)

        return normative

    def clear_cache(self, codice: Optional[str] = None):
        """
        Cancella la cache delle normative.

        Args:
            codice: Se specificato, cancella solo quella normativa
        """
        if codice:
            norm_path = self._get_normativa_path(codice)
            if norm_path.exists():
                import shutil
                shutil.rmtree(norm_path)
                logger.info(f"Cache di {codice} cancellata")
        else:
            import shutil
            for norm_dir in self.data_dir.iterdir():
                if norm_dir.is_dir():
                    shutil.rmtree(norm_dir)
            logger.info("Tutta la cache cancellata")

    def get_statistics(self) -> Dict:
        """
        Restituisce statistiche sulle normative scaricate.

        Returns:
            Dizionario con statistiche
        """
        normative = self.list_normative_available()

        totale_articoli = sum(n.get('numero_articoli', 0) for n in normative)

        return {
            "numero_normative": len(normative),
            "totale_articoli": totale_articoli,
            "normative": [n['codice'] for n in normative],
            "spazio_disco_mb": self._get_directory_size(self.data_dir) / (1024 * 1024)
        }

    def _get_directory_size(self, path: Path) -> int:
        """Calcola dimensione totale di una directory in bytes."""
        total = 0
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
        return total


def main():
    """Funzione di test per il modulo."""
    logging.basicConfig(level=logging.INFO)

    fetcher = NormativeFetcher()

    print("=== Test NormativeFetcher ===\n")

    # Test download singola normativa
    print("Download Costituzione...")
    successo = fetcher.download_normativa("costituzione")
    print(f"Risultato: {'✅' if successo else '❌'}\n")

    # Test recupero normativa
    if successo:
        costituzione = fetcher.get_normativa("costituzione")
        if costituzione:
            print(f"Normativa: {costituzione['metadata']['nome']}")
            print(f"Articoli: {len(costituzione['articoli'])}\n")

    # Statistiche
    stats = fetcher.get_statistics()
    print("Statistiche:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
