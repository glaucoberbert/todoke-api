# database.py — configuração da conexão com o banco (Postgres no Neon)

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# A string de conexão vem da variável de ambiente DATABASE_URL (configurada no Render).
# Assim a senha do banco nunca fica escrita no código nem vai para o GitHub.
URL_DO_BANCO = os.environ.get("DATABASE_URL")
if not URL_DO_BANCO:
    raise RuntimeError("Falta a variável de ambiente DATABASE_URL (veja o Render > Environment).")

# O Neon entrega a URL começando com "postgresql://".
# O SQLAlchemy precisa saber qual driver usar, então trocamos para "postgresql+psycopg://".
if URL_DO_BANCO.startswith("postgresql://"):
    URL_DO_BANCO = URL_DO_BANCO.replace("postgresql://", "postgresql+psycopg://", 1)

# O "engine" é a ponte principal com o banco.
# pool_pre_ping=True: antes de usar uma conexão guardada, testa se ela ainda está viva.
# Isso evita erro quando o Neon "dorme" por falta de uso e derruba as conexões.
engine = create_engine(URL_DO_BANCO, pool_pre_ping=True)

# Fábrica de "sessões". Uma sessão é uma conversa curta com o banco (abre, usa, fecha).
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# Classe base: todas as tabelas (models) herdam dela, e assim o SQLAlchemy sabe quais existem.
class Base(DeclarativeBase):
    pass


# Função usada pelas rotas do FastAPI para ganhar uma sessão e fechá-la no final,
# aconteça o que acontecer (o "finally" garante o fechamento).
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()