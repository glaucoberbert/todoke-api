# schemas_dados.py — formato dos dados que entram e saem das rotas de dados

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------- estado do app ----------
class EstadoEntrada(BaseModel):
    dados: dict[str, Any]                 # o conteúdo do app (JSON)
    versao_base: int = Field(ge=0)        # a versão que o aparelho tinha ao carregar (0 = nunca salvou)


class EstadoSaida(BaseModel):
    versao: int                           # 0 = o servidor ainda não tem nada deste motoboy
    dados: dict[str, Any] | None


class VersaoSaida(BaseModel):
    versao: int


# ---------- turnos fechados ----------
class TurnoEntrada(BaseModel):
    fechado_em: datetime
    dados: dict[str, Any]


class TurnoResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # permite montar a partir do objeto do banco
    turno_id: str
    fechado_em: datetime


class TurnoDetalhe(TurnoResumo):
    dados: dict[str, Any]


# ---------- clientes ----------
class ClienteEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    bairro: str = Field(default="", max_length=100)
    endereco: str = Field(min_length=1, max_length=200)


class ClientesEntrada(BaseModel):
    # O app manda vários de uma vez (todos os de uma rota terminada). Máximo 100 por envio.
    clientes: list[ClienteEntrada] = Field(max_length=100)


class ClienteSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    bairro: str
    endereco: str
    usos: int


class ClientesSalvosSaida(BaseModel):
    salvos: int