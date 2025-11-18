"""
Modulo per la valutazione dell'affidabilità delle risposte generate.

Questo modulo implementa:
- Calcolo del confidence score per ogni retrieval
- Sistema di highlighting basato su confidence
- Generazione di report di affidabilità
- Identificazione di parti che necessitano verifica
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
from docx.enum.text import WD_COLOR_INDEX

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Livelli di confidenza per le citazioni."""
    HIGH = "high"  # > 0.8 - Verde
    MEDIUM = "medium"  # 0.5-0.8 - Giallo
    LOW = "low"  # < 0.5 - Rosso
    UNVERIFIED = "unverified"  # Nessuna fonte


@dataclass
class CitationScore:
    """
    Rappresenta il punteggio di confidenza di una citazione.

    Attributes:
        text: Testo della citazione
        source: Fonte della citazione
        score: Punteggio di confidenza (0-1)
        level: Livello di confidenza
        metadata: Metadati aggiuntivi
    """
    text: str
    source: str
    score: float
    level: ConfidenceLevel
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Converte in dizionario."""
        return {
            "text": self.text,
            "source": self.source,
            "score": self.score,
            "level": self.level.value,
            "metadata": self.metadata
        }


@dataclass
class SectionScore:
    """
    Rappresenta il punteggio di una sezione del documento.

    Attributes:
        section_name: Nome della sezione
        overall_score: Punteggio complessivo
        citations: Lista di citazioni nella sezione
        needs_review: Se True, la sezione necessita revisione
        comments: Commenti sulla sezione
    """
    section_name: str
    overall_score: float
    citations: List[CitationScore] = field(default_factory=list)
    needs_review: bool = False
    comments: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Converte in dizionario."""
        return {
            "section_name": self.section_name,
            "overall_score": self.overall_score,
            "citations": [c.to_dict() for c in self.citations],
            "needs_review": self.needs_review,
            "comments": self.comments
        }


class ConfidenceScorer:
    """
    Classe per valutare l'affidabilità delle risposte generate.

    Calcola confidence score basandosi su:
    - Similarity score dei chunks recuperati
    - Presenza di citazioni esatte
    - Keywords matching
    - Completezza delle fonti
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Inizializza lo scorer.

        Args:
            config: Configurazione con threshold e parametri
        """
        self.config = config or {}
        self.high_threshold = self.config.get("confidence", {}).get("high_threshold", 0.8)
        self.medium_threshold = self.config.get("confidence", {}).get("medium_threshold", 0.5)
        self.min_acceptable = self.config.get("confidence", {}).get("min_acceptable", 0.3)

        logger.info(f"ConfidenceScorer inizializzato (H:{self.high_threshold}, "
                   f"M:{self.medium_threshold}, Min:{self.min_acceptable})")

    def score_retrieval(
        self,
        query: str,
        retrieved_chunks: List[Dict],
        similarity_scores: Optional[List[float]] = None
    ) -> List[CitationScore]:
        """
        Calcola il confidence score per i chunks recuperati.

        Args:
            query: Query originale
            retrieved_chunks: Chunks recuperati dal RAG
            similarity_scores: Score di similarità (opzionale)

        Returns:
            Lista di CitationScore
        """
        citation_scores = []

        for idx, chunk in enumerate(retrieved_chunks):
            # Estrai informazioni dal chunk
            text = chunk.get("text", "")
            source = chunk.get("source", "Unknown")
            metadata = chunk.get("metadata", {})

            # Calcola score base dalla similarità
            base_score = similarity_scores[idx] if similarity_scores else 0.5

            # Ajust score basandosi su vari fattori
            adjusted_score = self._adjust_score(
                query=query,
                text=text,
                base_score=base_score,
                metadata=metadata
            )

            # Determina livello di confidenza
            level = self._get_confidence_level(adjusted_score)

            citation = CitationScore(
                text=text,
                source=source,
                score=adjusted_score,
                level=level,
                metadata=metadata
            )

            citation_scores.append(citation)

        return citation_scores

    def _adjust_score(
        self,
        query: str,
        text: str,
        base_score: float,
        metadata: Dict
    ) -> float:
        """
        Ajusta il punteggio base considerando vari fattori.

        Args:
            query: Query originale
            text: Testo del chunk
            base_score: Score base di similarità
            metadata: Metadati del chunk

        Returns:
            Score ajustato (0-1)
        """
        score = base_score

        # Boost per citazione esatta di articolo
        if self._has_exact_article_citation(text):
            score = min(score + 0.15, 1.0)
            logger.debug("Boost per citazione esatta articolo: +0.15")

        # Boost se il metadata include articolo e comma specifici
        if "articolo" in metadata and "comma" in metadata:
            score = min(score + 0.1, 1.0)
            logger.debug("Boost per metadata completi: +0.1")

        # Penalizza se keywords importanti della query mancano
        query_keywords = self._extract_keywords(query)
        text_keywords = self._extract_keywords(text)

        keyword_match_ratio = len(query_keywords & text_keywords) / max(len(query_keywords), 1)

        if keyword_match_ratio < 0.3:
            score = max(score - 0.2, 0.0)
            logger.debug(f"Penalità per keyword mancanti: -0.2 (match: {keyword_match_ratio:.2f})")

        # Penalizza testi molto corti (probabilmente incompleti)
        if len(text.split()) < 20:
            score = max(score - 0.1, 0.0)
            logger.debug("Penalità per testo breve: -0.1")

        return score

    def _has_exact_article_citation(self, text: str) -> bool:
        """
        Verifica se il testo contiene una citazione esatta di articolo.

        Pattern cercati:
        - Art. X
        - Articolo X
        - Art. X, Comma Y

        Args:
            text: Testo da verificare

        Returns:
            True se contiene citazione esatta
        """
        patterns = [
            r'\bArt\.\s*\d+',
            r'\bArticolo\s+\d+',
            r'\bart\.\s*\d+',
            r'\barticolo\s+\d+'
        ]

        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def _extract_keywords(self, text: str) -> set:
        """
        Estrae keywords significative da un testo.

        Args:
            text: Testo da analizzare

        Returns:
            Set di keywords
        """
        # Stopwords italiane comuni
        stopwords = {
            'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una',
            'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra',
            'e', 'o', 'ma', 'se', 'che', 'chi', 'cui', 'è', 'sono',
            'del', 'della', 'dei', 'delle', 'al', 'alla', 'ai', 'alle'
        }

        # Tokenizza e pulisci
        words = re.findall(r'\b\w+\b', text.lower())

        # Filtra stopwords e parole troppo corte
        keywords = {w for w in words if w not in stopwords and len(w) > 3}

        return keywords

    def _get_confidence_level(self, score: float) -> ConfidenceLevel:
        """
        Determina il livello di confidenza basandosi sullo score.

        Args:
            score: Score di confidenza (0-1)

        Returns:
            ConfidenceLevel appropriato
        """
        if score >= self.high_threshold:
            return ConfidenceLevel.HIGH
        elif score >= self.medium_threshold:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def get_highlight_color(self, score: float) -> WD_COLOR_INDEX:
        """
        Restituisce il colore di highlighting appropriato per un punteggio.

        Args:
            score: Score di confidenza (0-1)

        Returns:
            Colore WD_COLOR_INDEX per python-docx
        """
        level = self._get_confidence_level(score)

        color_map = {
            ConfidenceLevel.HIGH: WD_COLOR_INDEX.BRIGHT_GREEN,
            ConfidenceLevel.MEDIUM: WD_COLOR_INDEX.YELLOW,
            ConfidenceLevel.LOW: WD_COLOR_INDEX.PINK
        }

        return color_map.get(level, WD_COLOR_INDEX.AUTO)

    def score_generated_text(
        self,
        generated_text: str,
        citations: List[Dict]
    ) -> SectionScore:
        """
        Calcola lo score complessivo di un testo generato.

        Args:
            generated_text: Testo generato dall'AI
            citations: Lista di citazioni utilizzate

        Returns:
            SectionScore con valutazione completa
        """
        # Converti citazioni in CitationScore se non lo sono già
        citation_scores = []
        for cit in citations:
            if isinstance(cit, CitationScore):
                citation_scores.append(cit)
            else:
                # Crea CitationScore da dict
                citation_scores.append(
                    CitationScore(
                        text=cit.get("text", ""),
                        source=cit.get("source", "Unknown"),
                        score=cit.get("score", 0.5),
                        level=self._get_confidence_level(cit.get("score", 0.5)),
                        metadata=cit.get("metadata", {})
                    )
                )

        # Calcola score medio delle citazioni
        if citation_scores:
            overall_score = np.mean([c.score for c in citation_scores])
        else:
            overall_score = 0.0

        # Verifica se necessita revisione
        needs_review = overall_score < self.medium_threshold

        # Genera commenti
        comments = []

        if overall_score >= self.high_threshold:
            comments.append("✅ Alta affidabilità - citazioni dirette verificate")
        elif overall_score >= self.medium_threshold:
            comments.append("⚠️ Affidabilità media - interpretazione basata su fonti")
        else:
            comments.append("❌ Bassa affidabilità - necessita verifica manuale")

        # Controlla pattern problematici
        if "[NORMATIVA DA VERIFICARE]" in generated_text:
            needs_review = True
            comments.append("⚡ Contiene normative non verificate")

        # Controlla presenza di citazioni nel testo
        citation_markers = len(re.findall(r'\[N\.\d+\]|\[\d+\]', generated_text))
        if citation_markers == 0:
            needs_review = True
            comments.append("⚡ Nessuna citazione trovata nel testo")

        section_score = SectionScore(
            section_name="Generated",
            overall_score=overall_score,
            citations=citation_scores,
            needs_review=needs_review,
            comments=comments
        )

        return section_score

    def generate_report(
        self,
        sections: List[SectionScore]
    ) -> Dict:
        """
        Genera un report completo di affidabilità.

        Args:
            sections: Lista di sezioni valutate

        Returns:
            Dizionario con report completo
        """
        total_citations = sum(len(s.citations) for s in sections)
        high_confidence = sum(
            1 for s in sections for c in s.citations
            if c.level == ConfidenceLevel.HIGH
        )
        medium_confidence = sum(
            1 for s in sections for c in s.citations
            if c.level == ConfidenceLevel.MEDIUM
        )
        low_confidence = sum(
            1 for s in sections for c in s.citations
            if c.level == ConfidenceLevel.LOW
        )

        sections_to_review = [s for s in sections if s.needs_review]

        overall_score = np.mean([s.overall_score for s in sections]) if sections else 0.0

        report = {
            "overall_score": float(overall_score),
            "total_sections": len(sections),
            "sections_to_review": len(sections_to_review),
            "total_citations": total_citations,
            "citation_breakdown": {
                "high_confidence": high_confidence,
                "medium_confidence": medium_confidence,
                "low_confidence": low_confidence
            },
            "percentages": {
                "high": (high_confidence / max(total_citations, 1)) * 100,
                "medium": (medium_confidence / max(total_citations, 1)) * 100,
                "low": (low_confidence / max(total_citations, 1)) * 100
            },
            "sections": [s.to_dict() for s in sections],
            "sections_needing_review": [s.section_name for s in sections_to_review],
            "recommendation": self._generate_recommendation(overall_score)
        }

        return report

    def _generate_recommendation(self, overall_score: float) -> str:
        """
        Genera una raccomandazione basata sullo score complessivo.

        Args:
            overall_score: Score complessivo del documento

        Returns:
            Testo della raccomandazione
        """
        if overall_score >= self.high_threshold:
            return (
                "Il documento presenta un'alta affidabilità. "
                "Le citazioni sono precise e verificate. "
                "Si consiglia comunque una revisione finale da parte del professionista."
            )
        elif overall_score >= self.medium_threshold:
            return (
                "Il documento presenta affidabilità media. "
                "Molte affermazioni sono basate su interpretazione di fonti. "
                "È necessaria una revisione accurata delle sezioni evidenziate."
            )
        else:
            return (
                "Il documento presenta bassa affidabilità. "
                "Numerose affermazioni necessitano di verifica e integrazione. "
                "È INDISPENSABILE una revisione completa da parte del professionista "
                "prima dell'utilizzo."
            )

    def apply_highlighting_to_text(
        self,
        text: str,
        score: float
    ) -> Tuple[str, str]:
        """
        Genera indicazioni per l'highlighting del testo.

        Args:
            text: Testo da evidenziare
            score: Score di confidenza

        Returns:
            Tupla (testo, nome_colore)
        """
        level = self._get_confidence_level(score)

        color_names = {
            ConfidenceLevel.HIGH: "verde",
            ConfidenceLevel.MEDIUM: "giallo",
            ConfidenceLevel.LOW: "rosso"
        }

        return text, color_names.get(level, "auto")

    def get_review_suggestions(
        self,
        section_score: SectionScore
    ) -> List[str]:
        """
        Genera suggerimenti specifici per la revisione di una sezione.

        Args:
            section_score: Score della sezione

        Returns:
            Lista di suggerimenti
        """
        suggestions = []

        # Analizza le citazioni
        low_scores = [c for c in section_score.citations if c.level == ConfidenceLevel.LOW]

        if low_scores:
            suggestions.append(
                f"Verificare {len(low_scores)} citazioni a bassa confidenza"
            )

        # Controlla se ci sono citazioni
        if not section_score.citations:
            suggestions.append(
                "CRITICO: Nessuna citazione normativa trovata. "
                "Aggiungere riferimenti normativi appropriati."
            )

        # Controlla score complessivo
        if section_score.overall_score < self.min_acceptable:
            suggestions.append(
                "CRITICO: Affidabilità sotto la soglia minima. "
                "Riscrivere la sezione con fonti verificate."
            )

        # Analizza metadata delle citazioni
        missing_metadata = [
            c for c in section_score.citations
            if not c.metadata.get("articolo") or not c.metadata.get("fonte")
        ]

        if missing_metadata:
            suggestions.append(
                f"Completare metadata per {len(missing_metadata)} citazioni"
            )

        return suggestions


def main():
    """Funzione di test per il modulo."""
    logging.basicConfig(level=logging.INFO)

    scorer = ConfidenceScorer()

    print("=== Test ConfidenceScorer ===\n")

    # Test retrieval scoring
    query = "responsabilità extracontrattuale"
    chunks = [
        {
            "text": "Art. 2043 c.c. - Qualunque fatto doloso o colposo...",
            "source": "Codice Civile",
            "metadata": {"articolo": "2043", "fonte": "c.c."}
        },
        {
            "text": "La responsabilità può essere contrattuale o extracontrattuale",
            "source": "Manuale",
            "metadata": {}
        }
    ]

    scores = scorer.score_retrieval(query, chunks, [0.9, 0.6])

    for i, score in enumerate(scores):
        print(f"Chunk {i+1}:")
        print(f"  Score: {score.score:.2f}")
        print(f"  Level: {score.level.value}")
        print(f"  Color: {scorer.get_highlight_color(score.score)}")
        print()

    # Test section scoring
    generated = "La responsabilità extracontrattuale è disciplinata dall'Art. 2043 c.c. [N.1]"
    section = scorer.score_generated_text(generated, [scores[0].to_dict()])

    print(f"Section Score: {section.overall_score:.2f}")
    print(f"Needs Review: {section.needs_review}")
    print(f"Comments: {section.comments}")
    print()

    # Test report generation
    report = scorer.generate_report([section])
    print("Report:")
    print(f"  Overall: {report['overall_score']:.2f}")
    print(f"  Recommendation: {report['recommendation']}")


if __name__ == "__main__":
    main()
