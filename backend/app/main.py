from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.exceptions import ArchaeologistError
from app.routes import analyze, health, info, notes, query

app = FastAPI(
    title="Code Archaeologist",
    version=settings.app_version,
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router)
app.include_router(info.router)
app.include_router(analyze.router)
app.include_router(query.router)
app.include_router(notes.router)


@app.exception_handler(ArchaeologistError)
async def handle_archaeologist_error(_request: Request, exc: ArchaeologistError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
