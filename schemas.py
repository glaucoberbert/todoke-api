# schemas.py — o "formato" dos dados que entram e saem da API.
# O FastAPI usa estas classes para validar o que chega e filtrar o que sai.

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CadastroEntrada(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    email: EmailStr                                    # confere o formato do e-mail
    senha: str = Field(min_length=8, max_length=128)   # mínimo 8 caracteres


class LoginEntrada(BaseModel):
    email: EmailStr
    senha: str = Field(max_length=128)
    lembrar: bool = False  # "lembrar de mim": True = token de 30 dias


class TokenSaida(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expira_em: datetime


class MotoboySaida(BaseModel):
    # Dados que podem SAIR da API. Repare: NÃO tem senha_hash nem código,
    # então eles nunca vazam, mesmo que a gente devolva o motoboy inteiro.
    model_config = ConfigDict(from_attributes=True)  # permite montar a partir do objeto do banco

    id: int
    nome: str
    email: str
    email_confirmado: bool


# NOVO: resposta do cadastro = dados do motoboy + aviso se o e-mail com o código saiu.
class CadastroSaida(MotoboySaida):
    codigo_enviado: bool = True


# NOVO: entrada de "confirmar e-mail".
class ConfirmarEmailEntrada(BaseModel):
    email: EmailStr
    codigo: str = Field(pattern=r"^\d{6}$")  # exatamente 6 dígitos


# NOVO: entrada de "reenviar código".
class ReenviarCodigoEntrada(BaseModel):
    email: EmailStr


# NOVO: resposta simples com uma mensagem.
class MensagemSaida(BaseModel):
    mensagem: str