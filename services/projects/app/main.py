import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import comentarios, financiero, logistica, notificaciones, projects, reportes

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Mactral Projects Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(financiero.router)
app.include_router(financiero.tablero_router)
app.include_router(financiero.cxp_router)
app.include_router(financiero.anticipo1_router)
app.include_router(logistica.router)
app.include_router(notificaciones.router)
app.include_router(comentarios.router)
app.include_router(reportes.router)


@app.get("/health")
def health():
    return {"status": "ok"}
