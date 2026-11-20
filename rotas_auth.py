# rotas_auth.py — rotas de cadastro, login e "quem sou eu"

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Motoboy
from schemas import CadastroEntrada, LoginEntrada, MotoboySaida, TokenSaida
from seguranca import HASH_FALSO, criar_token, gerar_hash, motoboy_atual, senha_confere

# Um "router" agrupa rotas; o main.py liga ele ao servidor.
router = APIRouter(tags=["Autenticação"])


@router.post("/auth/cadastro", response_model=MotoboySaida, status_code=201)
def cadastrar(dados: CadastroEntrada, db: Session = Depends(get_db)):
    # Padroniza o e-mail (minúsculas, sem espaços) para "Ana@x.com" e "ana@x.com" serem o mesmo.
    email = dados.email.lower().strip()

    # Já existe alguém com esse e-mail?
    if db.scalar(select(Motoboy).where(Motoboy.email == email)):
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
    db.refresh(motoboy)  # recarrega para pegar id e data gerados pelo banco
    return motoboy


@router.post("/auth/login", response_model=TokenSaida)
def entrar(dados: LoginEntrada, db: Session = Depends(get_db)):
    email = dados.email.lower().strip()
    motoboy = db.scalar(select(Motoboy).where(Motoboy.email == email))

    # Se o e-mail não existe, conferimos contra o hash falso (veja seguranca.py).
    hash_para_conferir = motoboy.senha_hash if motoboy else HASH_FALSO
    senha_ok = senha_confere(dados.senha, hash_para_conferir)

    # Mesma mensagem para "e-mail errado" e "senha errada": não revela qual dos dois falhou.
    if motoboy is None or not senha_ok:
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")

    token, expira = criar_token(motoboy.id, dados.lembrar)
    return TokenSaida(access_token=token, expira_em=expira)


@router.get("/eu", response_model=MotoboySaida)
def quem_sou_eu(motoboy: Motoboy = Depends(motoboy_atual)):
    # Rota protegida: só chega aqui quem mandou um token válido.
    return motoboy