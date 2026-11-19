# main.py — servidor do Todoke (Parte 1 do TCC)
# Etapa 2: conexão com o banco (Neon) + tabela de motoboys + rota /saude/banco.

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Motoboy  # importar aqui faz o SQLAlchemy "conhecer" a tabela

log = logging.getLogger(__name__)


# Código que roda uma vez quando o servidor liga (tudo antes do "yield").
@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    # Cria no banco as tabelas que ainda não existem (as que já existem são mantidas).
    Base.metadata.create_all(bind=engine)
    yield


# Cria o aplicativo e liga o código de inicialização acima.
app = FastAPI(title="Todoke API", version="0.2.0", lifespan=ciclo_de_vida)


@app.get("/")
def raiz():
    return {"mensagem": "Servidor do Todoke no ar"}


# Rota de "saúde" do servidor: só responde "estou vivo".
@app.get("/saude")
def saude():
    return {"status": "ok"}


# Rota de "saúde" do banco: testa se o servidor consegue falar com o Neon.
# "Depends(get_db)" entrega uma sessão do banco pronta para uso.
@app.get("/saude/banco")
def saude_banco(db: Session = Depends(get_db)):
    try:
        # Pergunta mais simples possível ao banco: "SELECT 1".
        db.execute(text("SELECT 1"))
        # Conta quantos motoboys existem (prova que a tabela foi criada).
        total = db.scalar(select(func.count()).select_from(Motoboy))
        return {"banco": "conectado", "motoboys_cadastrados": total}
    except Exception:
        # O detalhe do erro vai só para o log do Render, nunca para quem chamou
        # (por segurança, para não vazar informação do banco).
        log.exception("Falha ao testar o banco")
        raise HTTPException(status_code=503, detail="Banco indisponível")