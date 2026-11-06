from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_optional_user
from app.auth import router as auth_router
from app.db import Base, engine, get_db
from app.db_models import Prediction, User
from app.email_parser import parse_eml
from app.model import SpamClassifier
from app.schemas import (
    BatchEmailRequest,
    BatchPredictionResponse,
    EmailRequest,
    EmlPrediction,
    EmlPredictionResponse,
    HistoryItem,
    PredictionResponse,
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
MAX_EML_FILES = 20
MAX_EML_BYTES = 1_000_000

classifier = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the tables if they don't exist yet
    Base.metadata.create_all(engine)
    # Load the model once at startup instead of on every request
    global classifier
    classifier = SpamClassifier()
    yield


app = FastAPI(
    title="Email Spam Detection API",
    description="Classify emails as spam or ham using a Hugging Face model",
    version="1.1.0",
    lifespan=lifespan,
)
app.include_router(auth_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _validate(texts):
    if any(not t.strip() for t in texts):
        raise HTTPException(status_code=422, detail="Text must not be empty or whitespace")


def _record(db: Session, user: User, source: str, snippets: List[str], predictions: List[dict]):
    for snippet, pred in zip(snippets, predictions):
        db.add(
            Prediction(
                user_id=user.id,
                source=source,
                snippet=" ".join(snippet.split())[:200],
                label=pred["label"],
                confidence=pred["confidence"],
            )
        )
    db.commit()


@app.get("/", include_in_schema=False)
def index(user: Optional[User] = Depends(get_optional_user)):
    if user is None:
        return RedirectResponse("/login")
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/login", include_in_schema=False)
def login_page(user: Optional[User] = Depends(get_optional_user)):
    if user is not None:
        return RedirectResponse("/")
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": classifier is not None,
        "model_name": classifier.model_name if classifier else None,
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(
    request: EmailRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _validate([request.text])
    prediction = classifier.predict([request.text])[0]
    _record(db, user, "text", [request.text], [prediction])
    return prediction


@app.post("/predict/batch", response_model=BatchPredictionResponse)
def predict_batch(
    request: BatchEmailRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _validate(request.texts)
    predictions = classifier.predict(request.texts)
    _record(db, user, "text", request.texts, predictions)
    return {"predictions": predictions}


@app.post("/predict/eml", response_model=EmlPredictionResponse)
def predict_eml(
    files: List[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(files) > MAX_EML_FILES:
        raise HTTPException(status_code=422, detail=f"Upload at most {MAX_EML_FILES} files at once")

    results = []
    to_classify = []  # (index into results, text to classify)
    for f in files:
        name = f.filename or "email.eml"
        data = f.file.read(MAX_EML_BYTES + 1)
        if len(data) > MAX_EML_BYTES:
            results.append(EmlPrediction(filename=name, error="File is larger than 1 MB"))
            continue
        try:
            subject, body = parse_eml(data)
        except Exception:
            results.append(EmlPrediction(filename=name, error="Could not read this file as an email"))
            continue
        text = f"{subject}\n\n{body}".strip()
        if not text:
            results.append(EmlPrediction(filename=name, subject=subject, error="Email has no text"))
            continue
        results.append(EmlPrediction(filename=name, subject=subject))
        to_classify.append((len(results) - 1, text))

    if to_classify:
        texts = [text for _, text in to_classify]
        predictions = classifier.predict(texts)
        for (i, _), pred in zip(to_classify, predictions):
            results[i].prediction = PredictionResponse(**pred)
        snippets = [results[i].subject or text for i, text in to_classify]
        _record(db, user, "eml", snippets, predictions)

    return {"results": results}


@app.get("/history", response_model=List[HistoryItem])
def history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Prediction)
        .where(Prediction.user_id == user.id)
        .order_by(Prediction.created_at.desc(), Prediction.id.desc())
        .limit(50)
    )
    return list(rows)
