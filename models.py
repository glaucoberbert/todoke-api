# models.py — as tabelas do banco, descritas como classes Python

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
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

    # Guarda o HASH da senha (nunca a senha).
    senha_hash: Mapped[str] = mapped_column(String(255))

    # Vira True quando o motoboy digita o código de 6 dígitos recebido por e-mail.
    email_confirmado: Mapped[bool] = mapped_column(Boolean, default=False)

    # Data e hora do cadastro, preenchida pelo próprio banco.
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # ---- NOVO: código de 6 dígitos enviado por e-mail ----
    # Guardamos só o HASH do código, nunca o código em si.
    # "| None" significa que a coluna pode ficar vazia (NULL).
    codigo_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    # Até quando o código vale.
    codigo_expira_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    # Quando o último código foi enviado (para não deixar reenviar toda hora).
    codigo_enviado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    # Quantas vezes errou o código atual.
    codigo_tentativas: Mapped[int] = mapped_column(Integer, default=0)

    # ---- NOVO: proteção contra quem tenta adivinhar a senha ----
    # Quantas senhas erradas seguidas.
    login_falhas: Mapped[int] = mapped_column(Integer, default=0)
    # Se preenchido, o login fica bloqueado até essa data e hora.
    bloqueado_ate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)