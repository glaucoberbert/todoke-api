# seguranca.py — tudo que protege senhas e identifica quem está logado

import os
from datetime import datetime, timedelta, timezone

import jwt  # biblioteca PyJWT: cria e confere tokens
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import get_db
from models import Motoboy

# Chave secreta que ASSINA os tokens. Vem do Render (variável SECRET_KEY),
# nunca fica escrita no código. Quem não tem a chave não consegue forjar um token.
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("Falta a variável de ambiente SECRET_KEY (veja o Render > Environment).")

ALGORITMO = "HS256"                  # método de assinatura do token
DURACAO_CURTA = timedelta(hours=12)  # login normal
DURACAO_LONGA = timedelta(days=30)   # login com "lembrar de mim"

# ---------- SENHAS ----------

# O PasswordHasher usa o argon2 com configurações seguras por padrão.
_hasher = PasswordHasher()


def gerar_hash(senha: str) -> str:
    # Transforma a senha em um hash que NÃO volta para a senha original.
    # O argon2 já coloca um "sal" aleatório dentro do hash: duas pessoas com a
    # mesma senha terminam com hashes diferentes.
    return _hasher.hash(senha)


def senha_confere(senha: str, hash_guardado: str) -> bool:
    # Confere se a senha digitada gera o hash guardado. Devolve True ou False.
    try:
        return _hasher.verify(hash_guardado, senha)
    except (VerificationError, InvalidHashError):
        return False


# Hash de mentira, usado no login quando o e-mail não existe.
# Assim o servidor gasta o mesmo tempo nos dois casos, e ninguém descobre
# quais e-mails estão cadastrados medindo o tempo da resposta.
HASH_FALSO = gerar_hash("senha-qualquer-so-para-gastar-tempo")

# ---------- TOKENS ----------


def criar_token(motoboy_id: int, lembrar: bool) -> tuple[str, datetime]:
    # Monta o token com: quem é (sub), quando foi criado (iat) e quando vence (exp).
    duracao = DURACAO_LONGA if lembrar else DURACAO_CURTA
    agora = datetime.now(timezone.utc)
    expira = agora + duracao
    dados = {"sub": str(motoboy_id), "iat": agora, "exp": expira}
    token = jwt.encode(dados, SECRET_KEY, algorithm=ALGORITMO)
    return token, expira


# Lê o cabeçalho "Authorization: Bearer <token>" que o app manda em cada pedido.
# auto_error=False: quem responde o erro somos nós, sempre com 401.
_esquema_bearer = HTTPBearer(auto_error=False)


def motoboy_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_esquema_bearer),
    db: Session = Depends(get_db),
) -> Motoboy:
    # Usada nas rotas protegidas: "Depends(motoboy_atual)" devolve o motoboy logado
    # ou responde 401 se o token estiver ausente, inválido ou vencido.
    erro = HTTPException(
        status_code=401,
        detail="Não autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credenciais is None:
        raise erro
    try:
        # decode confere a assinatura e a validade (exp) automaticamente.
        dados = jwt.decode(credenciais.credentials, SECRET_KEY, algorithms=[ALGORITMO])
        motoboy_id = int(dados["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise erro
    motoboy = db.get(Motoboy, motoboy_id)  # busca o motoboy pelo id
    if motoboy is None:  # token válido, mas a conta foi apagada
        raise erro
    return motoboy