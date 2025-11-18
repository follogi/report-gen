"""
Script per creare template DOCX di esempio.
"""

from pathlib import Path
from core.docx_processor import DocxProcessor


def main():
    """Crea template di esempio."""
    processor = DocxProcessor()

    # Crea directory se non esiste
    Path("data/templates").mkdir(parents=True, exist_ok=True)

    template_path = "data/templates/template_esempio.docx"

    print(f"Creazione template di esempio: {template_path}")

    processor.create_sample_template(template_path)

    print(f"✅ Template creato con successo: {template_path}")


if __name__ == "__main__":
    main()
