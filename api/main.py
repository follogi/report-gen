"""
FastAPI Backend per Legal RAG Engine.

Endpoints:
- POST /api/upload/esempio - Upload file esempio
- POST /api/upload/template - Upload template
- POST /api/generate - Genera relazione
- GET /api/normative - Lista normative disponibili
- GET /api/status - Status sistema
"""

import logging
import os
from pathlib import Path
from typing import List, Optional
import uuid

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.rag_engine import LegalRAGEngine, RAGEngineError

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inizializza FastAPI
app = FastAPI(
    title="Legal RAG API",
    description="API per generazione relazioni legali con RAG",
    version="1.0.0"
)

# CORS per sviluppo locale
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In produzione: specifica domini
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monta static files per frontend
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Inizializza RAG engine (lazy loading)
rag_engine: Optional[LegalRAGEngine] = None

# Directory temporanea per sessioni
SESSIONS_DIR = Path("data/sessions")
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


# ==================== MODELS ====================

class GenerateRequest(BaseModel):
    """Request per generazione relazione."""
    user_prompt: str
    session_id: str
    style: str = "formale"  # formale, semi_formale, sintetico


class GenerateResponse(BaseModel):
    """Response generazione relazione."""
    document: str
    confidence: float
    citations: List[dict]
    needs_review: bool
    session_id: str


# ==================== HELPER FUNCTIONS ====================

def get_rag_engine() -> LegalRAGEngine:
    """Lazy loading del RAG engine."""
    global rag_engine

    if rag_engine is None:
        logger.info("Inizializzazione RAG Engine...")
        try:
            rag_engine = LegalRAGEngine()

            # Build normative index se non esiste
            if rag_engine.normative_index is None:
                logger.info("Costruzione indice normative...")
                rag_engine.build_normative_index(force_rebuild=False)

            logger.info(" RAG Engine pronto")
        except Exception as e:
            logger.error(f"L Errore inizializzazione RAG: {e}")
            raise HTTPException(status_code=500, detail=f"Errore inizializzazione RAG: {str(e)}")

    return rag_engine


def get_session_dir(session_id: str) -> Path:
    """Ottieni directory sessione, crea se non esiste."""
    session_dir = SESSIONS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


# ==================== ENDPOINTS ====================

@app.get("/")
async def root():
    """Serve frontend HTML."""
    return FileResponse("frontend/index.html")


@app.get("/api/status")
async def get_status():
    """Status del sistema."""
    try:
        engine = get_rag_engine()
        stats = engine.get_statistics()

        return {
            "status": "ready",
            "statistics": stats,
            "message": "Sistema operativo"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.get("/api/normative")
async def list_normative():
    """Lista normative disponibili."""
    try:
        engine = get_rag_engine()
        normative = engine.normative_loader.list_available_normative()

        return {
            "normative": normative,
            "count": len(normative)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/session/create")
async def create_session():
    """Crea nuova sessione."""
    session_id = str(uuid.uuid4())
    session_dir = get_session_dir(session_id)

    # Crea sottodirectory
    (session_dir / "esempi").mkdir(exist_ok=True)
    (session_dir / "template").mkdir(exist_ok=True)

    return {
        "session_id": session_id,
        "message": "Sessione creata"
    }


@app.post("/api/upload/esempio")
async def upload_esempio(
    session_id: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    Upload file esempio per la sessione.

    Supporta: .txt, .docx, .pdf
    """
    session_dir = get_session_dir(session_id)
    esempi_dir = session_dir / "esempi"

    uploaded_files = []

    for file in files:
        # Valida estensione
        if not file.filename.endswith(('.txt', '.docx', '.pdf')):
            raise HTTPException(
                status_code=400,
                detail=f"Formato non supportato: {file.filename}"
            )

        # Salva file
        file_path = esempi_dir / file.filename
        with open(file_path, 'wb') as f:
            content = await file.read()
            f.write(content)

        uploaded_files.append({
            "filename": file.filename,
            "size": len(content),
            "path": str(file_path)
        })

        logger.info(f"Esempio caricato: {file.filename} ({len(content)} bytes)")

    return {
        "session_id": session_id,
        "uploaded_files": uploaded_files,
        "count": len(uploaded_files)
    }


@app.post("/api/upload/template")
async def upload_template(
    session_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload template per formattazione output.

    Supporta: .txt, .docx
    """
    session_dir = get_session_dir(session_id)
    template_dir = session_dir / "template"

    # Valida estensione
    if not file.filename.endswith(('.txt', '.docx')):
        raise HTTPException(
            status_code=400,
            detail=f"Formato template non supportato: {file.filename}"
        )

    # Salva file (sovrascrive eventuale precedente)
    ext = file.filename.split('.')[-1]
    file_path = template_dir / f"template.{ext}"
    with open(file_path, 'wb') as f:
        content = await file.read()
        f.write(content)

    logger.info(f"Template caricato: {file.filename}")

    return {
        "session_id": session_id,
        "template_file": file.filename,
        "size": len(content),
        "path": str(file_path)
    }


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_report(request: GenerateRequest):
    """
    Genera relazione legale.

    Usa:
    - Normative dall'indice globale
    - Esempi dalla sessione
    - Template dalla sessione
    - Prompt utente
    """
    try:
        engine = get_rag_engine()
        session_dir = get_session_dir(request.session_id)

        # Carica esempi se presenti
        esempi_dir = session_dir / "esempi"
        esempio_files = list(esempi_dir.glob("*"))

        if esempio_files:
            logger.info(f"Costruzione indice esempi: {len(esempio_files)} file")
            engine.build_esempi_index(
                esempio_files=[str(f) for f in esempio_files],
                session_id=request.session_id
            )

        # TODO: Carica template se presente
        template_content = None  # Per ora opzionale

        # Genera documento
        logger.info(f"Generazione relazione per sessione {request.session_id}")
        result = engine.generate_legal_document(
            user_request=request.user_prompt,
            template_structure=template_content,
            esempi_context=None if not esempio_files else "esempi_available",
            style=request.style
        )

        return GenerateResponse(
            document=result["document"],
            confidence=result["confidence"],
            citations=[c.to_dict() for c in result["citations"]],
            needs_review=result["needs_review"],
            session_id=request.session_id
        )

    except RAGEngineError as e:
        logger.error(f"Errore RAG: {e}")
        raise HTTPException(status_code=500, detail=f"Errore generazione: {str(e)}")
    except Exception as e:
        logger.error(f"Errore generico: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Elimina sessione e cleanup indici."""
    try:
        engine = get_rag_engine()
        engine.clear_session_index(session_id)

        # TODO: elimina file sessione se necessario

        return {"message": f"Sessione {session_id} eliminata"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== STARTUP/SHUTDOWN ====================

@app.on_event("startup")
async def startup_event():
    """Inizializzazione all'avvio."""
    logger.info("=€ Avvio Legal RAG API...")

    # Pre-carica RAG engine
    try:
        get_rag_engine()
    except Exception as e:
        logger.error(f"  RAG Engine non disponibile all'avvio: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup allo shutdown."""
    logger.info("=K Shutdown Legal RAG API")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Solo per sviluppo
    )
