# rotas_auth.py — cadastro, confirmação de e-mail, login e "quem sou eu"

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from codigos import (
    INTERVALO_REENVIO,
    MAX_TENTATIVAS_CODIGO,
    VALIDADE_CODIGO,
    codigo_confere,
    gerar_codigo,
    hash_codigo,
)
from database import get_db
from email_envio import enviar_codigo
from models import Motoboy
from schemas import (
    CadastroEntrada,
    CadastroSaida,
    ConfirmarEmailEntrada,
    LoginEntrada,
    MensagemSaida,
    MotoboySaida,
    ReenviarCodigoEntrada,
    TokenSaida,
)
from seguranca import HASH_FALSO, criar_token, gerar_hash, motoboy_atual, senha_confere

router = APIRouter(tags=["Autenticação"])

MAX_FALHAS_LOGIN = 5                    # senhas erradas seguidas até bloquear
TEMPO_BLOQUEIO = timedelta(minutes=15)  # quanto tempo o login fica bloqueado


# ---------- funções auxiliares (o "_" no início indica uso interno deste arquivo) ----------

def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _buscar_por_email(db: Session, email: str) -> Motoboy | None:
    # Padroniza o e-mail (minúsculas, sem espaços) antes de procurar.
    return db.scalar(select(Motoboy).where(Motoboy.email == email.lower().strip()))


def _enviar_novo_codigo(db: Session, motoboy: Motoboy) -> bool:
    # Gera um código novo, guarda só o HASH dele no banco e manda o código por e-mail.
    codigo = gerar_codigo()
    agora = _agora()
    motoboy.codigo_hash = hash_codigo(codigo)
    motoboy.codigo_expira_em = agora + VALIDADE_CODIGO
    motoboy.codigo_enviado_em = agora
    motoboy.codigo_tentativas = 0  # código novo, contagem de erros zerada
    db.commit()
    return enviar_codigo(motoboy.email, motoboy.nome, codigo)


# ---------- rotas ----------

@router.post("/auth/cadastro", response_model=CadastroSaida, status_code=201)
def cadastrar(dados: CadastroEntrada, db: Session = Depends(get_db)):
    email = dados.email.lower().strip()

    if _buscar_por_email(db, email):
        raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado")

    # Cria o motoboy guardando só o HASH da senha, nunca a senha.
    motoboy = Motoboy(
        nome=dados.nome.strip(),
        email=email,
        senha_hash=gerar_hash(dados.senha),
    )
    db.add(motoboy)
    try:
        db.commit()
    except IntegrityError:
        # Caso raro: dois cadastros iguais ao mesmo tempo. O banco (unique) barra o segundo.
        db.rollback()
        raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado")
    db.refresh(motoboy)

    # NOVO: envia o código de 6 dígitos para o e-mail.
    enviado = _enviar_novo_codigo(db, motoboy)

    saida = CadastroSaida.model_validate(motoboy)
    saida.codigo_enviado = enviado  # o app usa isso para avisar "não deu para enviar, reenvie"
    return saida


@router.post("/auth/confirmar-email", response_model=MotoboySaida)
def confirmar_email(dados: ConfirmarEmailEntrada, db: Session = Depends(get_db)):
    # Uma mensagem só para todos os problemas: não revela se o e-mail existe.
    erro = HTTPException(
        status_code=400,
        detail="Código inválido, expirado ou com muitas tentativas. Peça um novo código.",
    )
    motoboy = _buscar_por_email(db, dados.email)

    if (
        motoboy is None
        or motoboy.email_confirmado
        or motoboy.codigo_hash is None
        or motoboy.codigo_expira_em is None
        or motoboy.codigo_expira_em < _agora()
        or motoboy.codigo_tentativas >= MAX_TENTATIVAS_CODIGO
    ):
        raise erro

    if not codigo_confere(dados.codigo, motoboy.codigo_hash):
        motoboy.codigo_tentativas += 1  # conta o erro; no limite, o código "queima"
        db.commit()
        raise erro

    # Acertou: confirma o e-mail e apaga o código usado.
    motoboy.email_confirmado = True
    motoboy.codigo_hash = None
    motoboy.codigo_expira_em = None
    motoboy.codigo_tentativas = 0
    db.commit()
    db.refresh(motoboy)
    return motoboy


@router.post("/auth/reenviar-codigo", response_model=MensagemSaida)
def reenviar_codigo(dados: ReenviarCodigoEntrada, db: Session = Depends(get_db)):
    motoboy = _buscar_por_email(db, dados.email)
    if motoboy and not motoboy.email_confirmado:
        agora = _agora()
        # Só reenvia se já passou o intervalo mínimo desde o último envio.
        recente = motoboy.codigo_enviado_em and (agora - motoboy.codigo_enviado_em) < INTERVALO_REENVIO
        if not recente:
            _enviar_novo_codigo(db, motoboy)
    # Resposta igual em qualquer caso, para não revelar quais e-mails existem.
    return MensagemSaida(
        mensagem="Se o e-mail estiver cadastrado e ainda não confirmado, enviamos um novo código."
    )


@router.post("/auth/login", response_model=TokenSaida)
def entrar(dados: LoginEntrada, db: Session = Depends(get_db)):
    motoboy = _buscar_por_email(db, dados.email)
    agora = _agora()

    # NOVO: conta bloqueada por muitas senhas erradas?
    if motoboy and motoboy.bloqueado_ate and motoboy.bloqueado_ate > agora:
        raise HTTPException(status_code=429, detail="Muitas tentativas. Tente de novo em alguns minutos.")

    # Se o e-mail não existe, conferimos contra o hash falso (veja seguranca.py).
    hash_para_conferir = motoboy.senha_hash if motoboy else HASH_FALSO
    senha_ok = senha_confere(dados.senha, hash_para_conferir)

    if motoboy is None or not senha_ok:
        if motoboy:
            # NOVO: conta a falha; ao chegar no limite, bloqueia o login por um tempo.
            motoboy.login_falhas += 1
            if motoboy.login_falhas >= MAX_FALHAS_LOGIN:
                motoboy.bloqueado_ate = agora + TEMPO_BLOQUEIO
                motoboy.login_falhas = 0
            db.commit()
        # Mesma mensagem para "e-mail errado" e "senha errada".
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")

    # Senha certa: zera o contador de falhas.
    if motoboy.login_falhas:
        motoboy.login_falhas = 0
        db.commit()

    # NOVO: só entra quem confirmou o e-mail. O app usa o 403 para abrir a tela do código.
    if not motoboy.email_confirmado:
        raise HTTPException(status_code=403, detail="E-mail não confirmado")

    token, expira = criar_token(motoboy.id, dados.lembrar)
    return TokenSaida(access_token=token, expira_em=expira)


@router.get("/eu", response_model=MotoboySaida)
def quem_sou_eu(motoboy: Motoboy = Depends(motoboy_atual)):
    # Rota protegida: só chega aqui quem mandou um token válido.
    return motoboy