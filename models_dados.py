# models_dados.py — tabelas dos dados de cada motoboy (estado, turnos fechados, clientes)

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB  # coluna que guarda JSON no Postgres
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class EstadoApp(Base):
    # O "estado atual" do app (serviços, rota em andamento, turno aberto): UMA linha por motoboy.
    __tablename__ = "estados"

    # A chave primária é o próprio id do motoboy, então não existem duas linhas do mesmo motoboy.
    # ondelete="CASCADE": se a conta for apagada, os dados dela somem junto.
    motoboy_id: Mapped[int] = mapped_column(ForeignKey("motoboys.id", ondelete="CASCADE"), primary_key=True)
    # Sobe 1 a cada salvamento. Serve para detectar aparelho com dados desatualizados.
    versao: Mapped[int] = mapped_column(Integer, default=1)
    # O conteúdo do app, guardado como JSON.
    dados: Mapped[dict[str, Any]] = mapped_column(JSONB)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TurnoArquivado(Base):
    # Turnos já FECHADOS (o relatório do dia). Uma linha por turno.
    __tablename__ = "turnos_arquivados"

    id: Mapped[int] = mapped_column(primary_key=True)
    motoboy_id: Mapped[int] = mapped_column(ForeignKey("motoboys.id", ondelete="CASCADE"), index=True)
    # O id que o próprio app gerou para o turno (o servidor guarda igual, sem trocar).
    turno_id: Mapped[str] = mapped_column(String(64))
    fechado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    dados: Mapped[dict[str, Any]] = mapped_column(JSONB)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Não pode existir o mesmo turno duas vezes para o mesmo motoboy.
    __table_args__ = (UniqueConstraint("motoboy_id", "turno_id", name="uq_turno_por_motoboy"),)


class Cliente(Base):
    # Clientes salvos de cada motoboy, para o autocompletar (nome <-> endereço).
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    motoboy_id: Mapped[int] = mapped_column(ForeignKey("motoboys.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(100))
    bairro: Mapped[str] = mapped_column(String(100), default="")
    endereco: Mapped[str] = mapped_column(String(200))
    # Versões "limpas" (sem acento, minúsculas) usadas só para buscar e para evitar duplicados.
    nome_busca: Mapped[str] = mapped_column(String(100))
    endereco_busca: Mapped[str] = mapped_column(String(200))
    # Quantas vezes já foi usado (os mais usados aparecem primeiro) e quando foi a última vez.
    usos: Mapped[int] = mapped_column(Integer, default=1)
    ultimo_uso: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Mesmo nome + mesmo endereço para o mesmo motoboy = mesmo cliente (não duplica).
    __table_args__ = (UniqueConstraint("motoboy_id", "nome_busca", "endereco_busca", name="uq_cliente_por_motoboy"),)