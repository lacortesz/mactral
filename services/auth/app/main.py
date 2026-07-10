import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, modules, users

# Sin esto, logger.info() en app/mailer.py no emite nada: el logger raíz no
# tiene handler configurado por defecto y los mensajes INFO se descartan
# silenciosamente (ver app/mailer.py).
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Mactral Auth Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(modules.router)


@app.get("/health")
def health():
    return {"status": "ok"}
