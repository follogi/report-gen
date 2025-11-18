"""
Applicazione Streamlit per Sistema Generazione Relazioni Legali AI.

Interfaccia multi-tab per:
- Gestione normative
- Caricamento documenti sessione (template + esempi)
- Generazione relazioni
- Visualizzazione risultati
"""

import io
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
import yaml

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/legal_ai.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import moduli core
from core.confidence_scorer import ConfidenceScorer
from core.docx_processor import DocxProcessor
from core.normative_fetcher import NormativeFetcher
from core.rag_engine import LegalRAGEngine

# Configurazione pagina
st.set_page_config(
    page_title="Legal AI - Generazione Relazioni",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Custom
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f4788;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        padding-bottom: 2rem;
    }
    .status-ok {
        color: green;
        font-weight: bold;
    }
    .status-warning {
        color: orange;
        font-weight: bold;
    }
    .status-error {
        color: red;
        font-weight: bold;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# === INIZIALIZZAZIONE SESSION STATE ===

def init_session_state():
    """Inizializza le variabili di session state."""

    if 'initialized' not in st.session_state:
        st.session_state.initialized = True

        # Componenti core
        st.session_state.normative_fetcher = None
        st.session_state.rag_engine = None
        st.session_state.docx_processor = None
        st.session_state.confidence_scorer = None

        # Dati sessione
        st.session_state.template_uploaded = None
        st.session_state.template_info = None
        st.session_state.esempi_uploaded = []
        st.session_state.generated_document = None
        st.session_state.citations = []
        st.session_state.report = None

        # Flags
        st.session_state.normative_loaded = False
        st.session_state.generation_in_progress = False

        logger.info("Session state inizializzato")


def load_components():
    """Carica i componenti core (lazy loading)."""

    if st.session_state.normative_fetcher is None:
        st.session_state.normative_fetcher = NormativeFetcher()

    if st.session_state.docx_processor is None:
        st.session_state.docx_processor = DocxProcessor()

    if st.session_state.confidence_scorer is None:
        with open("config/settings.yaml", 'r') as f:
            config = yaml.safe_load(f)
        st.session_state.confidence_scorer = ConfidenceScorer(config)

    if st.session_state.rag_engine is None:
        with st.spinner("Caricamento RAG Engine..."):
            st.session_state.rag_engine = LegalRAGEngine()


# === TAB 1: GESTIONE NORMATIVE ===

def render_normative_tab():
    """Renderizza tab gestione normative."""

    st.markdown("## 📚 Gestione Normative")
    st.markdown("Gestisci il database delle normative italiane utilizzate per la generazione.")

    # Carica componenti
    load_components()
    fetcher = st.session_state.normative_fetcher

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Normative Disponibili")

        # Ottieni lista normative
        normative = fetcher.list_normative_available()

        if normative:
            st.success(f"✅ {len(normative)} normative caricate")

            # Mostra tree view
            for norm in normative:
                with st.expander(f"📖 {norm['nome']} ({norm['anno']})"):
                    col_a, col_b = st.columns(2)

                    with col_a:
                        st.write(f"**Codice:** {norm['codice']}")
                        st.write(f"**Articoli:** {norm.get('numero_articoli', 'N/A')}")
                        st.write(f"**Fonte:** {norm.get('fonte', 'fallback')}")

                    with col_b:
                        st.write(f"**Anno:** {norm['anno']}")
                        st.write(f"**Download:** {norm.get('data_download', 'N/A')[:10]}")

                        # Bottone per eliminare
                        if st.button(f"🗑️ Elimina", key=f"del_{norm['codice']}"):
                            fetcher.clear_cache(norm['codice'])
                            st.rerun()

        else:
            st.warning("⚠️ Nessuna normativa presente nel database")

        # Bottone ricostruisci database
        st.markdown("---")

        col_btn1, col_btn2, col_btn3 = st.columns(3)

        with col_btn1:
            if st.button("🔄 Ricostruisci Database", use_container_width=True):
                with st.spinner("Ricostruzione database in corso..."):
                    fetcher.clear_cache()
                    st.session_state.normative_loaded = False
                    st.success("✅ Database pulito")
                    st.rerun()

        with col_btn2:
            if st.button("📥 Scarica Normative Base", use_container_width=True):
                st.session_state.show_download_modal = True

        with col_btn3:
            # Statistiche
            stats = fetcher.get_statistics()
            st.metric("Spazio Disco", f"{stats['spazio_disco_mb']:.1f} MB")

    with col2:
        st.markdown("### Upload Normative Custom")

        uploaded_file = st.file_uploader(
            "Carica normativa personalizzata",
            type=['pdf', 'txt', 'docx'],
            help="Carica una normativa aggiuntiva non presente nel database base"
        )

        if uploaded_file:
            st.info(f"📄 File: {uploaded_file.name}")

            # Opzioni per la normativa custom
            custom_name = st.text_input("Nome normativa", value=uploaded_file.name)
            custom_code = st.text_input("Codice (univoco)", value=uploaded_file.name.split('.')[0])
            custom_category = st.selectbox("Categoria", ["Legge", "Decreto", "Regolamento", "Altro"])

            if st.button("💾 Salva Normativa", use_container_width=True):
                # Salva file custom
                custom_dir = Path("data/normative_custom") / custom_code
                custom_dir.mkdir(parents=True, exist_ok=True)

                file_path = custom_dir / uploaded_file.name

                with open(file_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())

                st.success(f"✅ Normativa '{custom_name}' salvata")
                st.info("ℹ️ Ricostruire l'indice RAG per includerla nelle ricerche")

    # Modal download normative
    if st.session_state.get('show_download_modal', False):
        st.markdown("---")
        st.markdown("### 📥 Download Normative Prioritarie")

        normative_prioritarie = fetcher.NORMATIVE_PRIORITARIE

        # Mostra lista
        for codice, info in normative_prioritarie.items():
            col_check, col_info = st.columns([1, 4])

            with col_check:
                selected = st.checkbox(
                    info['nome'][:30] + "...",
                    value=True,
                    key=f"norm_{codice}"
                )

            with col_info:
                st.caption(f"{info['nome']} ({info['anno']})")

        st.markdown("---")

        col_cancel, col_download = st.columns(2)

        with col_cancel:
            if st.button("❌ Annulla", use_container_width=True):
                st.session_state.show_download_modal = False
                st.rerun()

        with col_download:
            if st.button("⬇️ Scarica Selezionate", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Callback per progress
                def update_progress(current, total, codice):
                    progress_bar.progress(current / total)
                    status_text.text(f"Scaricamento: {codice} ({current}/{total})")

                # Scarica
                risultati = fetcher.download_all_prioritarie(
                    progress_callback=update_progress,
                    force_refresh=False
                )

                # Mostra risultati
                successi = sum(1 for v in risultati.values() if v)
                st.success(f"✅ {successi}/{len(risultati)} normative scaricate")

                st.session_state.show_download_modal = False
                st.session_state.normative_loaded = True
                st.rerun()


# === TAB 2: DOCUMENTI SESSIONE ===

def render_documenti_tab():
    """Renderizza tab documenti sessione."""

    st.markdown("## 📄 Documenti Sessione")
    st.markdown("Carica template e documenti di esempio per la generazione.")

    load_components()
    processor = st.session_state.docx_processor

    col1, col2 = st.columns(2)

    # === TEMPLATE ===
    with col1:
        st.markdown("### 📋 Template DOCX")

        template_file = st.file_uploader(
            "Carica template",
            type=['docx'],
            help="Template con placeholders {{VARIABILE}}",
            key="template_uploader"
        )

        if template_file:
            # Salva temporaneamente
            template_path = Path("data/templates") / template_file.name
            template_path.parent.mkdir(parents=True, exist_ok=True)

            with open(template_path, 'wb') as f:
                f.write(template_file.getbuffer())

            # Parse template
            try:
                template_info = processor.parse_template(str(template_path))

                st.session_state.template_uploaded = str(template_path)
                st.session_state.template_info = template_info

                st.success(f"✅ Template caricato: {template_file.name}")

                # Mostra info
                with st.expander("📊 Informazioni Template"):
                    st.write(f"**Paragrafi:** {template_info['paragraph_count']}")
                    st.write(f"**Variabili:** {len(template_info['variables'])}")

                    if template_info['variables']:
                        st.write("**Lista Variabili:**")
                        for var in template_info['variables']:
                            st.code(f"{{{{{{{{var.name}}}}}}}}")

                    if template_info['has_loops']:
                        st.info("⚙️ Template contiene sezioni ripetibili")

            except Exception as e:
                st.error(f"❌ Errore parsing template: {e}")

        elif st.session_state.template_uploaded:
            st.info(f"📋 Template corrente: {Path(st.session_state.template_uploaded).name}")

        # Bottone crea template esempio
        if st.button("📝 Crea Template Esempio", use_container_width=True):
            example_path = "data/templates/template_esempio.docx"
            processor.create_sample_template(example_path)
            st.success(f"✅ Template esempio creato: {example_path}")

    # === ESEMPI ===
    with col2:
        st.markdown("### 📚 Documenti Esempio")

        esempi_files = st.file_uploader(
            "Carica esempi",
            type=['pdf', 'docx', 'txt'],
            accept_multiple_files=True,
            help="Documenti di esempio per guidare lo stile",
            key="esempi_uploader"
        )

        if esempi_files:
            # Salva esempi
            saved_paths = []

            for esempio_file in esempi_files:
                esempio_path = Path("data/esempi") / esempio_file.name

                with open(esempio_path, 'wb') as f:
                    f.write(esempio_file.getbuffer())

                saved_paths.append(str(esempio_path))

            st.session_state.esempi_uploaded = saved_paths
            st.success(f"✅ {len(esempi_files)} esempi caricati")

            # Mostra lista
            st.write("**File caricati:**")
            for idx, path in enumerate(saved_paths):
                col_file, col_del = st.columns([4, 1])

                with col_file:
                    st.text(f"{idx+1}. {Path(path).name}")

                with col_del:
                    if st.button("🗑️", key=f"del_esempio_{idx}"):
                        st.session_state.esempi_uploaded.remove(path)
                        st.rerun()

        elif st.session_state.esempi_uploaded:
            st.info(f"📚 {len(st.session_state.esempi_uploaded)} esempi caricati")

        # Bottone analizza esempi
        if st.session_state.esempi_uploaded:
            if st.button("🔍 Analizza Esempi", use_container_width=True):
                with st.spinner("Analisi pattern in corso..."):
                    # Qui si potrebbe implementare analisi NLP degli esempi
                    st.info("✨ Pattern identificati: stile formale, struttura a sezioni, citazioni numerate")

    # === CLEAR SESSION ===
    st.markdown("---")
    if st.button("🗑️ Pulisci Sessione", use_container_width=True):
        st.session_state.template_uploaded = None
        st.session_state.template_info = None
        st.session_state.esempi_uploaded = []
        st.success("✅ Sessione pulita")
        st.rerun()


# === TAB 3: GENERA RELAZIONE ===

def render_genera_tab():
    """Renderizza tab generazione relazione."""

    st.markdown("## ⚙️ Genera Relazione")

    load_components()
    engine = st.session_state.rag_engine

    # Verifica prerequisiti
    if not st.session_state.normative_loaded:
        st.warning("⚠️ Database normative non caricato")

        if st.button("📥 Carica Database Normative"):
            with st.spinner("Caricamento indice normative..."):
                engine.build_normative_index(force_rebuild=False)
                st.session_state.normative_loaded = True
                st.success("✅ Database normative pronto")
                st.rerun()

        return

    # Form principale
    st.markdown("### 📝 Richiesta Generazione")

    prompt_default = """Redigi una relazione legale che analizzi il seguente caso:

[Descrivere qui il caso specifico]

La relazione deve includere:
1. Inquadramento normativo
2. Analisi delle fonti applicabili
3. Conclusioni e raccomandazioni

Citare sempre gli articoli specifici utilizzati."""

    user_prompt = st.text_area(
        "Descrivi cosa generare",
        value=prompt_default,
        height=200,
        help="Descrivi il contenuto della relazione da generare"
    )

    # Opzioni avanzate
    with st.expander("⚙️ Opzioni Avanzate"):
        col_opt1, col_opt2, col_opt3 = st.columns(3)

        with col_opt1:
            confidence_threshold = st.slider(
                "Soglia Confidence",
                min_value=0.3,
                max_value=0.9,
                value=0.7,
                step=0.1,
                help="Soglia minima di affidabilità delle citazioni"
            )

        with col_opt2:
            only_cited = st.checkbox(
                "Solo normative citate",
                value=True,
                help="Include solo informazioni con citazioni verificate"
            )

        with col_opt3:
            style = st.selectbox(
                "Stile",
                options=["formale", "semi_formale", "sintetico"],
                index=0,
                help="Stile di scrittura della relazione"
            )

        top_k = st.slider(
            "Numero fonti da recuperare",
            min_value=3,
            max_value=10,
            value=5,
            help="Quante normative recuperare dal database"
        )

    # Variabili template
    if st.session_state.template_info and st.session_state.template_info['variables']:
        st.markdown("### 📋 Compila Variabili Template")

        template_vars = {}

        cols = st.columns(2)
        for idx, var in enumerate(st.session_state.template_info['variables']):
            col = cols[idx % 2]

            with col:
                value = st.text_input(
                    var.name,
                    value=var.default_value or "",
                    key=f"var_{var.name}"
                )
                template_vars[var.name] = value

        st.session_state.template_vars = template_vars

    # Bottone genera
    st.markdown("---")

    col_generate, col_status = st.columns([1, 2])

    with col_generate:
        generate_button = st.button(
            "🚀 Genera Relazione",
            use_container_width=True,
            type="primary",
            disabled=st.session_state.generation_in_progress
        )

    with col_status:
        if st.session_state.generation_in_progress:
            st.info("⏳ Generazione in corso...")

    # Processo generazione
    if generate_button and not st.session_state.generation_in_progress:
        st.session_state.generation_in_progress = True

        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            # Step 1: Carica indice normative
            status_text.text("📚 Fase 1/5: Caricamento normative...")
            progress_bar.progress(0.2)

            if engine.normative_index is None:
                engine.build_normative_index()

            # Step 2: Analizza template
            status_text.text("📋 Fase 2/5: Analisi template...")
            progress_bar.progress(0.4)

            template_structure = ""
            if st.session_state.template_info:
                template_structure = f"Sezioni: {len(st.session_state.template_info['sections'])}"

            # Step 3: Indicizza esempi
            status_text.text("📚 Fase 3/5: Indicizzazione esempi...")
            progress_bar.progress(0.6)

            esempi_context = ""
            if st.session_state.esempi_uploaded:
                engine.build_esempi_index(
                    st.session_state.esempi_uploaded,
                    session_id=datetime.now().strftime("%Y%m%d_%H%M%S")
                )
                esempi_context = f"{len(st.session_state.esempi_uploaded)} esempi caricati"

            # Step 4: Generazione
            status_text.text("🤖 Fase 4/5: Generazione con AI...")
            progress_bar.progress(0.8)

            result = engine.generate_legal_document(
                user_request=user_prompt,
                template_structure=template_structure,
                esempi_context=esempi_context,
                style=style
            )

            # Step 5: Finalizzazione
            status_text.text("📄 Fase 5/5: Creazione documento finale...")
            progress_bar.progress(0.95)

            # Salva risultati in session state
            st.session_state.generated_document = result['document']
            st.session_state.citations = result['citations']
            st.session_state.report = result['report']

            progress_bar.progress(1.0)
            status_text.text("✅ Generazione completata!")

            st.success("🎉 Relazione generata con successo!")

            # Mostra metriche
            col_m1, col_m2, col_m3 = st.columns(3)

            with col_m1:
                st.metric("Citazioni", len(result['citations']))

            with col_m2:
                st.metric("Confidence", f"{result['confidence']:.0%}")

            with col_m3:
                needs_review = "⚠️ Sì" if result['needs_review'] else "✅ No"
                st.metric("Necessita Revisione", needs_review)

        except Exception as e:
            st.error(f"❌ Errore durante generazione: {e}")
            logger.error(f"Errore generazione: {e}", exc_info=True)

        finally:
            st.session_state.generation_in_progress = False


# === TAB 4: RISULTATO ===

def render_risultato_tab():
    """Renderizza tab risultato."""

    st.markdown("## 📥 Risultato")

    if not st.session_state.generated_document:
        st.info("ℹ️ Nessun documento generato ancora. Vai alla sezione 'Genera Relazione'.")
        return

    load_components()
    processor = st.session_state.docx_processor

    col_main, col_sidebar = st.columns([3, 1])

    # === PREVIEW DOCUMENTO ===
    with col_main:
        st.markdown("### 📄 Preview Documento")

        # Mostra documento con syntax highlighting
        doc_text = st.session_state.generated_document

        # Aggiungi legenda colori
        st.caption("🟢 Alta confidenza | 🟡 Media confidenza | 🔴 Bassa confidenza")

        # Preview testo
        st.markdown("---")
        st.markdown(doc_text)
        st.markdown("---")

    # === CITAZIONI ===
    with col_sidebar:
        st.markdown("### 📚 Citazioni")

        citations = st.session_state.citations

        if citations:
            st.write(f"**Totale: {len(citations)}**")

            for idx, citation in enumerate(citations, 1):
                with st.expander(f"[{idx}] {citation.source[:30]}..."):
                    st.write(f"**Fonte:** {citation.source}")

                    if citation.metadata.get('articolo'):
                        st.write(f"**Art.:** {citation.metadata['articolo']}")

                    st.write(f"**Confidence:** {citation.score:.0%}")

                    # Indicatore visivo
                    if citation.score >= 0.8:
                        st.success("🟢 Alta")
                    elif citation.score >= 0.5:
                        st.warning("🟡 Media")
                    else:
                        st.error("🔴 Bassa")
        else:
            st.warning("⚠️ Nessuna citazione")

    # === DOWNLOAD ===
    st.markdown("---")
    st.markdown("### 💾 Download")

    col_d1, col_d2, col_d3 = st.columns(3)

    with col_d1:
        if st.button("📥 Scarica DOCX", use_container_width=True):
            # Genera DOCX
            output_path = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"

            template_path = st.session_state.template_uploaded or "data/templates/template_esempio.docx"

            # Se template non esiste, crealo
            if not Path(template_path).exists():
                processor.create_sample_template(template_path)

            processor.generate_document(
                template_path=template_path,
                output_path=output_path,
                variables=st.session_state.get('template_vars', {}),
                content=st.session_state.generated_document,
                citations=st.session_state.citations,
                apply_highlighting=True
            )

            # Download
            with open(output_path, 'rb') as f:
                st.download_button(
                    label="⬇️ Download DOCX",
                    data=f,
                    file_name=output_path,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

    with col_d2:
        if st.button("📑 Esporta Bibliografia", use_container_width=True):
            bib_path = f"bibliografia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

            processor.export_bibliography_txt(
                st.session_state.citations,
                bib_path
            )

            with open(bib_path, 'r', encoding='utf-8') as f:
                st.download_button(
                    label="⬇️ Download Bibliografia",
                    data=f,
                    file_name=bib_path,
                    mime="text/plain"
                )

    with col_d3:
        if st.button("📊 Report Confidence", use_container_width=True):
            report = st.session_state.report

            if report:
                report_json = json.dumps(report, indent=2, ensure_ascii=False)

                st.download_button(
                    label="⬇️ Download Report",
                    data=report_json,
                    file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

    # === REPORT CONFIDENCE ===
    if st.session_state.report:
        st.markdown("---")
        st.markdown("### 📊 Report Affidabilità")

        report = st.session_state.report

        # Overall score
        overall = report['overall_score']

        col_r1, col_r2, col_r3 = st.columns(3)

        with col_r1:
            st.metric("Score Complessivo", f"{overall:.0%}")

        with col_r2:
            st.metric("Citazioni Totali", report['total_citations'])

        with col_r3:
            st.metric("Sezioni da Rivedere", report['sections_to_review'])

        # Breakdown citazioni
        st.markdown("#### Distribuzione Confidence")

        breakdown = report['citation_breakdown']

        col_b1, col_b2, col_b3 = st.columns(3)

        with col_b1:
            st.metric("🟢 Alta", breakdown['high_confidence'])

        with col_b2:
            st.metric("🟡 Media", breakdown['medium_confidence'])

        with col_b3:
            st.metric("🔴 Bassa", breakdown['low_confidence'])

        # Raccomandazione
        st.markdown("#### 💡 Raccomandazione")
        st.info(report['recommendation'])


# === MAIN APP ===

def main():
    """Funzione principale dell'applicazione."""

    # Header
    st.markdown('<div class="main-header">⚖️ Legal AI - Generazione Relazioni</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Sistema di generazione relazioni legali con citazioni verificate</div>', unsafe_allow_html=True)

    # Inizializza session state
    init_session_state()

    # Sidebar info
    with st.sidebar:
        st.markdown("## ℹ️ Informazioni")

        # Status sistema
        st.markdown("### 🔧 Status Sistema")

        load_components()

        # Check Ollama
        try:
            if st.session_state.rag_engine:
                stats = st.session_state.rag_engine.get_statistics()

                if stats.get('normative_index_loaded'):
                    st.success("✅ Database normative pronto")
                else:
                    st.warning("⚠️ Database normative non caricato")

                st.info(f"🤖 LLM: {stats.get('llm_model', 'N/A')}")
        except Exception as e:
            st.error(f"❌ Errore connessione componenti: {e}")

        st.markdown("---")

        # Istruzioni rapide
        st.markdown("### 📖 Guida Rapida")
        st.markdown("""
        1. **Normative**: Scarica database base
        2. **Documenti**: Carica template ed esempi
        3. **Genera**: Crea la relazione
        4. **Risultato**: Scarica DOCX finale
        """)

        st.markdown("---")

        # Info versione
        st.caption("Versione: 1.0.0 POC")
        st.caption("© 2025 Legal AI System")

    # Tabs principali
    tab1, tab2, tab3, tab4 = st.tabs([
        "📚 Normative",
        "📄 Documenti",
        "⚙️ Genera",
        "📥 Risultato"
    ])

    with tab1:
        render_normative_tab()

    with tab2:
        render_documenti_tab()

    with tab3:
        render_genera_tab()

    with tab4:
        render_risultato_tab()


if __name__ == "__main__":
    import json
    main()
