# models.py — as tabelas do banco, descritas como classes Python

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


# Cada classe vira uma tabela. Cada atributo vira uma coluna.
class Motoboy(Base):
    __tablename__ = "motoboys"  # nome da tabela no Postgres

    # Número único de cada motoboy, gerado automaticamente (1, 2, 3...).
    id: Mapped[int] = mapped_column(primary_key=True)

    # Nome de exibição.
    nome: Mapped[str] = mapped_column(String(100))

    # E-mail usado no login. unique=True: não deixa cadastrar o mesmo e-mail duas vezes.
    # index=True: deixa a busca por e-mail rápida (vamos buscar nele a cada login).
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # Guarda o HASH da senha (nunca a senha). Será preenchido na Etapa 3.
    senha_hash: Mapped[str] = mapped_column(String(255))

    # Vira True quando o motoboy digitar o código de 6 dígitos do e-mail (Etapa 4).
    email_confirmado: Mapped[bool] = mapped_column(Boolean, default=False)

    # Data e hora do cadastro, preenchida pelo próprio banco.
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())