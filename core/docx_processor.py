"""
Modulo per la gestione di template DOCX e generazione documenti finali.

Questo modulo si occupa di:
- Parsing di template DOCX con placeholders
- Generazione di documenti finali mantenendo formattazione
- Applicazione di highlighting basato su confidence
- Aggiunta di bibliografia e commenti marginali
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from docx.text.paragraph import Paragraph

from core.confidence_scorer import ConfidenceLevel, CitationScore

logger = logging.getLogger(__name__)


@dataclass
class TemplateVariable:
    """
    Rappresenta una variabile trovata nel template.

    Attributes:
        name: Nome della variabile (es: "CLIENTE")
        placeholder: Placeholder completo (es: "{{CLIENTE}}")
        default_value: Valore di default opzionale
    """
    name: str
    placeholder: str
    default_value: Optional[str] = None

    def __str__(self):
        return f"{self.name} ({self.placeholder})"


@dataclass
class TemplateSection:
    """
    Rappresenta una sezione del template.

    Attributes:
        name: Nome della sezione
        start_index: Indice paragrafo di inizio
        end_index: Indice paragrafo di fine
        is_repeatable: Se True, la sezione è ripetibile
        variables: Variabili contenute nella sezione
    """
    name: str
    start_index: int
    end_index: int
    is_repeatable: bool = False
    variables: List[TemplateVariable] = None

    def __post_init__(self):
        if self.variables is None:
            self.variables = []


class DocxProcessor:
    """
    Classe per processare template DOCX e generare documenti finali.

    Funzionalità:
    - Parsing template con identificazione placeholders
    - Sostituzione variabili mantenendo formattazione
    - Highlighting basato su confidence scores
    - Aggiunta bibliografia e note
    """

    # Pattern per identificare placeholders
    PLACEHOLDER_PATTERNS = [
        r'\{\{([A-Z_0-9]+)\}\}',  # {{VARIABILE}}
        r'<<<([A-Z_0-9]+)>>>',    # <<<VARIABILE>>>
    ]

    # Pattern per sezioni ripetibili
    LOOP_START_PATTERN = r'<<<LOOP_START:([A-Z_0-9]+)>>>'
    LOOP_END_PATTERN = r'<<<LOOP_END:([A-Z_0-9]+)>>>'

    def __init__(self):
        """Inizializza il processore DOCX."""
        logger.info("DocxProcessor inizializzato")

    def parse_template(self, template_path: str) -> Dict:
        """
        Analizza un template DOCX ed estrae struttura e variabili.

        Args:
            template_path: Percorso al file template

        Returns:
            Dizionario con informazioni sul template
        """
        logger.info(f"Parsing template: {template_path}")

        try:
            doc = Document(template_path)
        except Exception as e:
            logger.error(f"Errore apertura template: {e}")
            raise

        # Estrai informazioni
        variables = self._extract_variables(doc)
        sections = self._extract_sections(doc)
        styles = self._extract_styles(doc)

        template_info = {
            "path": template_path,
            "variables": variables,
            "sections": sections,
            "styles": styles,
            "paragraph_count": len(doc.paragraphs),
            "has_loops": any(s.is_repeatable for s in sections)
        }

        logger.info(f"Template analizzato: {len(variables)} variabili, {len(sections)} sezioni")

        return template_info

    def _extract_variables(self, doc: Document) -> List[TemplateVariable]:
        """
        Estrae tutte le variabili dal documento.

        Args:
            doc: Documento DOCX

        Returns:
            Lista di TemplateVariable
        """
        variables = {}  # Usa dict per evitare duplicati

        for paragraph in doc.paragraphs:
            text = paragraph.text

            for pattern in self.PLACEHOLDER_PATTERNS:
                matches = re.finditer(pattern, text)
                for match in matches:
                    var_name = match.group(1)
                    placeholder = match.group(0)

                    if var_name not in variables:
                        variables[var_name] = TemplateVariable(
                            name=var_name,
                            placeholder=placeholder
                        )

        # Cerca anche nelle tabelle
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        text = paragraph.text
                        for pattern in self.PLACEHOLDER_PATTERNS:
                            matches = re.finditer(pattern, text)
                            for match in matches:
                                var_name = match.group(1)
                                placeholder = match.group(0)

                                if var_name not in variables:
                                    variables[var_name] = TemplateVariable(
                                        name=var_name,
                                        placeholder=placeholder
                                    )

        return list(variables.values())

    def _extract_sections(self, doc: Document) -> List[TemplateSection]:
        """
        Estrae sezioni dal documento, incluse quelle ripetibili.

        Args:
            doc: Documento DOCX

        Returns:
            Lista di TemplateSection
        """
        sections = []
        current_section = None
        loop_stack = []

        for idx, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text

            # Cerca inizio loop
            loop_start_match = re.search(self.LOOP_START_PATTERN, text)
            if loop_start_match:
                section_name = loop_start_match.group(1)
                current_section = TemplateSection(
                    name=section_name,
                    start_index=idx,
                    end_index=-1,
                    is_repeatable=True
                )
                loop_stack.append(current_section)
                continue

            # Cerca fine loop
            loop_end_match = re.search(self.LOOP_END_PATTERN, text)
            if loop_end_match and loop_stack:
                section_name = loop_end_match.group(1)
                if loop_stack[-1].name == section_name:
                    section = loop_stack.pop()
                    section.end_index = idx
                    sections.append(section)
                continue

        # Se non ci sono loop espliciti, considera il documento come unica sezione
        if not sections:
            sections.append(TemplateSection(
                name="MAIN",
                start_index=0,
                end_index=len(doc.paragraphs) - 1,
                is_repeatable=False
            ))

        return sections

    def _extract_styles(self, doc: Document) -> Dict:
        """
        Estrae informazioni sugli stili usati nel template.

        Args:
            doc: Documento DOCX

        Returns:
            Dizionario con informazioni sugli stili
        """
        styles_info = {
            "paragraph_styles": set(),
            "character_styles": set(),
            "has_custom_styles": False
        }

        for paragraph in doc.paragraphs:
            if paragraph.style:
                styles_info["paragraph_styles"].add(paragraph.style.name)

        # Converti set in list per JSON serialization
        styles_info["paragraph_styles"] = list(styles_info["paragraph_styles"])
        styles_info["character_styles"] = list(styles_info["character_styles"])

        return styles_info

    def generate_document(
        self,
        template_path: str,
        output_path: str,
        variables: Dict[str, str],
        content: Optional[str] = None,
        citations: Optional[List[CitationScore]] = None,
        apply_highlighting: bool = True
    ) -> str:
        """
        Genera un documento finale dal template.

        Args:
            template_path: Percorso al template
            output_path: Percorso output del documento generato
            variables: Dizionario {NOME_VAR: valore}
            content: Contenuto generato dall'AI (opzionale)
            citations: Lista di citazioni con score (opzionale)
            apply_highlighting: Se True, applica highlighting basato su confidence

        Returns:
            Percorso al documento generato
        """
        logger.info(f"Generazione documento da template: {template_path}")

        # Carica template
        doc = Document(template_path)

        # Sostituisci variabili
        doc = self._replace_variables(doc, variables)

        # Se c'è contenuto generato, inseriscilo
        if content:
            doc = self._insert_generated_content(doc, content, citations, apply_highlighting)

        # Aggiungi bibliografia se ci sono citazioni
        if citations:
            self._add_bibliography(doc, citations)

        # Salva documento
        doc.save(output_path)
        logger.info(f"Documento generato: {output_path}")

        return output_path

    def _replace_variables(self, doc: Document, variables: Dict[str, str]) -> Document:
        """
        Sostituisce le variabili nel documento mantenendo la formattazione.

        Args:
            doc: Documento DOCX
            variables: Dizionario con valori delle variabili

        Returns:
            Documento modificato
        """
        # Sostituisci nei paragrafi
        for paragraph in doc.paragraphs:
            self._replace_in_paragraph(paragraph, variables)

        # Sostituisci nelle tabelle
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        self._replace_in_paragraph(paragraph, variables)

        return doc

    def _replace_in_paragraph(self, paragraph: Paragraph, variables: Dict[str, str]):
        """
        Sostituisce variabili in un paragrafo mantenendo la formattazione originale.

        Args:
            paragraph: Paragrafo da modificare
            variables: Dizionario variabili
        """
        # Ottieni testo completo
        full_text = paragraph.text

        # Cerca tutte le variabili
        for pattern in self.PLACEHOLDER_PATTERNS:
            matches = list(re.finditer(pattern, full_text))

            for match in matches:
                var_name = match.group(1)
                placeholder = match.group(0)

                if var_name in variables:
                    value = variables[var_name]

                    # Sostituisci mantenendo formattazione
                    # Questo è un approccio semplificato
                    # Per mantenere formattazione complessa serve logica più sofisticata
                    full_text = full_text.replace(placeholder, value)

        # Aggiorna testo del paragrafo
        # Nota: questo rimuove formattazione complessa
        # Per preservarla completamente serve un approccio run-by-run
        if full_text != paragraph.text:
            paragraph.text = full_text

    def _insert_generated_content(
        self,
        doc: Document,
        content: str,
        citations: Optional[List[CitationScore]],
        apply_highlighting: bool
    ) -> Document:
        """
        Inserisce contenuto generato dall'AI nel documento.

        Args:
            doc: Documento DOCX
            content: Contenuto da inserire
            citations: Citazioni con confidence scores
            apply_highlighting: Se applicare highlighting

        Returns:
            Documento modificato
        """
        # Cerca marker per inserimento (es: {{CONTENUTO_GENERATO}})
        content_inserted = False

        for paragraph in doc.paragraphs:
            if "{{CONTENUTO_GENERATO}}" in paragraph.text or "<<<CONTENT>>>" in paragraph.text:
                # Cancella il placeholder
                paragraph.clear()

                # Inserisci contenuto con highlighting
                self._add_highlighted_content(paragraph, content, citations, apply_highlighting)
                content_inserted = True
                break

        # Se non c'è marker, aggiungi alla fine
        if not content_inserted:
            new_paragraph = doc.add_paragraph()
            self._add_highlighted_content(new_paragraph, content, citations, apply_highlighting)

        return doc

    def _add_highlighted_content(
        self,
        paragraph: Paragraph,
        content: str,
        citations: Optional[List[CitationScore]],
        apply_highlighting: bool
    ):
        """
        Aggiunge contenuto con highlighting al paragrafo.

        Args:
            paragraph: Paragrafo target
            content: Contenuto da aggiungere
            citations: Citazioni
            apply_highlighting: Se applicare highlighting
        """
        # Se non ci sono citazioni o highlighting disabilitato, aggiungi solo testo
        if not citations or not apply_highlighting:
            paragraph.add_run(content)
            return

        # Altrimenti, processa il contenuto cercando markers di citazione
        # e applica highlighting appropriato

        # Pattern per citazioni nel testo: [N.1], [1], etc.
        citation_pattern = r'\[N\.(\d+)\]|\[(\d+)\]'

        # Split content per citazioni
        parts = re.split(f'({citation_pattern})', content)

        current_score = 0.5  # Default score

        for part in parts:
            if not part:
                continue

            # Se è un marker di citazione
            citation_match = re.match(citation_pattern, part)
            if citation_match:
                # Estrai numero citazione
                cit_num = citation_match.group(1) or citation_match.group(2)
                cit_idx = int(cit_num) - 1

                # Aggiorna score corrente
                if 0 <= cit_idx < len(citations):
                    current_score = citations[cit_idx].score

                # Aggiungi marker citazione
                run = paragraph.add_run(part)
                run.font.superscript = True
                run.font.size = Pt(8)
            else:
                # Testo normale - applica highlighting basato su score corrente
                run = paragraph.add_run(part)

                if current_score >= 0.8:
                    run.font.highlight_color = WD_COLOR_INDEX.BRIGHT_GREEN
                elif current_score >= 0.5:
                    run.font.highlight_color = WD_COLOR_INDEX.YELLOW
                else:
                    run.font.highlight_color = WD_COLOR_INDEX.PINK

    def _add_bibliography(self, doc: Document, citations: List[CitationScore]):
        """
        Aggiunge sezione bibliografia al documento.

        Args:
            doc: Documento DOCX
            citations: Lista di citazioni
        """
        # Aggiungi page break
        doc.add_page_break()

        # Aggiungi titolo
        title = doc.add_paragraph("RIFERIMENTI NORMATIVI")
        title.style = 'Heading 1'

        # Aggiungi citazioni numerate
        for idx, citation in enumerate(citations, 1):
            # Formato: [1] Art. X, Fonte
            bib_text = f"[{idx}] {citation.source}"

            # Aggiungi metadata se disponibili
            if citation.metadata:
                if "articolo" in citation.metadata:
                    bib_text += f" - Art. {citation.metadata['articolo']}"
                if "comma" in citation.metadata:
                    bib_text += f", Comma {citation.metadata['comma']}"

            para = doc.add_paragraph(bib_text, style='List Number')

            # Aggiungi indicator di confidence
            conf_run = para.add_run(f" (Confidence: {citation.score:.0%})")
            conf_run.font.italic = True
            conf_run.font.size = Pt(9)

            # Colora basandosi su livello
            if citation.level == ConfidenceLevel.HIGH:
                conf_run.font.color.rgb = RGBColor(0, 128, 0)  # Verde
            elif citation.level == ConfidenceLevel.MEDIUM:
                conf_run.font.color.rgb = RGBColor(255, 165, 0)  # Arancione
            else:
                conf_run.font.color.rgb = RGBColor(255, 0, 0)  # Rosso

    def export_bibliography_txt(
        self,
        citations: List[CitationScore],
        output_path: str
    ) -> str:
        """
        Esporta bibliografia in formato TXT.

        Args:
            citations: Lista di citazioni
            output_path: Percorso file output

        Returns:
            Percorso al file generato
        """
        logger.info(f"Esportazione bibliografia TXT: {output_path}")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("RIFERIMENTI NORMATIVI\n")
            f.write("=" * 50 + "\n\n")

            for idx, citation in enumerate(citations, 1):
                f.write(f"[{idx}] {citation.source}\n")

                if citation.metadata:
                    if "articolo" in citation.metadata:
                        f.write(f"    Art. {citation.metadata['articolo']}")
                    if "comma" in citation.metadata:
                        f.write(f", Comma {citation.metadata['comma']}")
                    f.write("\n")

                f.write(f"    Confidence: {citation.score:.0%} ({citation.level.value})\n")
                f.write("\n")

        logger.info("Bibliografia TXT esportata")
        return output_path

    def add_review_comments(
        self,
        doc: Document,
        review_points: List[Tuple[str, str]]
    ) -> Document:
        """
        Aggiunge commenti di revisione al documento.

        Args:
            doc: Documento DOCX
            review_points: Lista di tuple (sezione, commento)

        Returns:
            Documento modificato
        """
        # Aggiungi sezione "Note di Revisione"
        doc.add_page_break()

        title = doc.add_paragraph("NOTE DI REVISIONE")
        title.style = 'Heading 1'

        warning = doc.add_paragraph(
            "ATTENZIONE: Le seguenti sezioni necessitano di revisione e verifica "
            "da parte del professionista prima dell'utilizzo."
        )
        warning.runs[0].font.bold = True
        warning.runs[0].font.color.rgb = RGBColor(255, 0, 0)

        for section, comment in review_points:
            para = doc.add_paragraph()

            # Sezione
            section_run = para.add_run(f"• {section}: ")
            section_run.font.bold = True

            # Commento
            comment_run = para.add_run(comment)
            comment_run.font.italic = True

        return doc

    def create_sample_template(self, output_path: str) -> str:
        """
        Crea un template DOCX di esempio per test.

        Args:
            output_path: Percorso output

        Returns:
            Percorso al template creato
        """
        logger.info(f"Creazione template di esempio: {output_path}")

        doc = Document()

        # Titolo
        title = doc.add_paragraph("RELAZIONE LEGALE")
        title.style = 'Title'

        # Informazioni base
        doc.add_paragraph(f"Cliente: {{{{CLIENTE}}}}")
        doc.add_paragraph(f"Data: {{{{DATA}}}}")
        doc.add_paragraph(f"Oggetto: {{{{OGGETTO}}}}")

        # Separatore
        doc.add_paragraph("_" * 50)

        # Placeholder per contenuto generato
        doc.add_paragraph()
        content_marker = doc.add_paragraph("{{CONTENUTO_GENERATO}}")
        content_marker.runs[0].font.italic = True
        content_marker.runs[0].font.color.rgb = RGBColor(128, 128, 128)

        # Firma
        doc.add_paragraph()
        doc.add_paragraph("_" * 50)
        doc.add_paragraph(f"Avv. {{{{AVVOCATO}}}}")
        doc.add_paragraph(f"Firma: ________________")

        doc.save(output_path)
        logger.info("Template di esempio creato")

        return output_path


def main():
    """Funzione di test per il modulo."""
    logging.basicConfig(level=logging.INFO)

    processor = DocxProcessor()

    print("=== Test DocxProcessor ===\n")

    # Crea template di esempio
    template_path = "data/templates/template_esempio.docx"
    Path("data/templates").mkdir(parents=True, exist_ok=True)

    processor.create_sample_template(template_path)
    print(f"✅ Template creato: {template_path}\n")

    # Parse template
    template_info = processor.parse_template(template_path)
    print(f"Variabili trovate: {len(template_info['variables'])}")
    for var in template_info['variables']:
        print(f"  - {var.name}")
    print()

    # Test generazione documento
    variables = {
        "CLIENTE": "Rossi Mario",
        "DATA": "18/11/2025",
        "OGGETTO": "Responsabilità extracontrattuale",
        "AVVOCATO": "Bianchi Giovanni"
    }

    output_path = "data/templates/test_output.docx"
    processor.generate_document(
        template_path=template_path,
        output_path=output_path,
        variables=variables,
        content="Contenuto di test generato dall'AI. [N.1]",
        citations=[
            CitationScore(
                text="Art. 2043 c.c.",
                source="Codice Civile",
                score=0.9,
                level=ConfidenceLevel.HIGH,
                metadata={"articolo": "2043", "fonte": "c.c."}
            )
        ]
    )

    print(f"✅ Documento generato: {output_path}")


if __name__ == "__main__":
    main()
