# main.py — servidor do Todoke (Parte 1 do TCC)
# Etapa 3: + cadastro, login e rota /eu (ficam no arquivo rotas_auth.py).

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Motoboy  # importar aqui faz o SQLAlchemy "conhecer" a tabela
from rotas_auth import router as router_auth  # NOVO: rotas de cadastro/login

log = logging.getLogger(__name__)


# Código que roda uma vez quando o servidor liga (tudo antes do "yield").
@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    # Cria no banco as tabelas que ainda não existem (as que já existem são mantidas).
    Base.metadata.create_all(bind=engine)
    yield


# Cria o aplicativo e liga o código de inicialização acima.
app = FastAPI(title="Todoke API", version="0.3.0", lifespan=ciclo_de_vida)

# NOVO: liga ao servidor as rotas definidas em rotas_auth.py
app.include_router(router_auth)


@app.get("/")
def raiz():
    return {"mensagem": "Servidor do Todoke no ar"}


# Rota de "saúde" do servidor: só responde "estou vivo".
@app.get("/saude")
def saude():
    return {"status": "ok"}


# Rota de "saúde" do banco: testa se o servidor consegue falar com o Neon.
@app.get("/saude/banco")
def saude_banco(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        total = db.scalar(select(func.count()).select_from(Motoboy))
        return {"banco": "conectado", "motoboys_cadastrados": total}
    except Exception:
        # O detalhe do erro vai só para o log do Render, nunca para quem chamou.
        log.exception("Falha ao testar o banco")
        raise HTTPException(status_code=503, detail="Banco indisponível")