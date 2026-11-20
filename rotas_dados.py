# rotas_dados.py — dados de cada motoboy: estado do app, turnos fechados e clientes salvos.
#
# REGRA DE OURO: toda consulta filtra por "motoboy.id", que vem do TOKEN (não do pedido).
# Assim cada motoboy só enxerga e altera o que é dele.

import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Motoboy
from models_dados import Cliente, EstadoApp, TurnoArquivado
from schemas_dados import (
    ClienteSaida,
    ClientesEntrada,
    ClientesSalvosSaida,
    EstadoEntrada,
    EstadoSaida,
    TurnoDetalhe,
    TurnoEntrada,
    TurnoResumo,
    VersaoSaida,
)
from seguranca import motoboy_atual
from textos import normalizar

router = APIRouter(tags=["Dados do motoboy"])

LIMITE_BYTES = 1_000_000  # tamanho máximo de um bloco de dados (protege o banco)


def _tamanho_ok(dados: dict) -> None:
    # Recusa blocos de JSON grandes demais (erro 413).
    if len(json.dumps(dados, separators=(",", ":"))) > LIMITE_BYTES:
        raise HTTPException(status_code=413, detail="Dados grandes demais")


# ======================= ESTADO DO APP =======================

@router.get("/estado", response_model=EstadoSaida)
def ler_estado(motoboy: Motoboy = Depends(motoboy_atual), db: Session = Depends(get_db)):
    # Devolve o estado salvo deste motoboy (ou versão 0 e dados vazios, se nunca salvou).
    estado = db.get(EstadoApp, motoboy.id)
    if estado is None:
        return EstadoSaida(versao=0, dados=None)
    return EstadoSaida(versao=estado.versao, dados=estado.dados)


def _conflito(db: Session, motoboy_id: int) -> HTTPException:
    # Monta o erro 409 contando qual é a versão que o servidor tem.
    estado = db.get(EstadoApp, motoboy_id)
    return HTTPException(
        status_code=409,
        detail={
            "mensagem": "O servidor tem dados mais novos que os deste aparelho.",
            "versao_servidor": estado.versao if estado else 0,
        },
    )


@router.put("/estado", response_model=VersaoSaida)
def salvar_estado(
    entrada: EstadoEntrada,
    motoboy: Motoboy = Depends(motoboy_atual),
    db: Session = Depends(get_db),
):
    _tamanho_ok(entrada.dados)

    # Primeira vez deste motoboy (o aparelho diz que a versão base é 0): cria a linha.
    if entrada.versao_base == 0:
        try:
            db.add(EstadoApp(motoboy_id=motoboy.id, versao=1, dados=entrada.dados))
            db.commit()
        except IntegrityError:
            # Já existia uma linha: outro aparelho salvou primeiro.
            db.rollback()
            raise _conflito(db, motoboy.id)
        return VersaoSaida(versao=1)

    # Já existe: só atualiza SE a versão do servidor ainda for a que o aparelho conhece.
    # Tudo numa única instrução (UPDATE ... WHERE versao = ...), então dois aparelhos
    # salvando ao mesmo tempo não se atropelam.
    resultado = db.execute(
        update(EstadoApp)
        .where(EstadoApp.motoboy_id == motoboy.id, EstadoApp.versao == entrada.versao_base)
        .values(dados=entrada.dados, versao=entrada.versao_base + 1)
        .execution_options(synchronize_session=False)
    )
    if resultado.rowcount == 0:
        # Ninguém foi atualizado: a versão do servidor é outra (mais nova).
        db.rollback()
        raise _conflito(db, motoboy.id)
    db.commit()
    return VersaoSaida(versao=entrada.versao_base + 1)


# ======================= TURNOS FECHADOS =======================

@router.put("/turnos/{turno_id}", response_model=TurnoResumo)
def arquivar_turno(
    turno_id: Annotated[str, Path(min_length=1, max_length=64)],
    entrada: TurnoEntrada,
    motoboy: Motoboy = Depends(motoboy_atual),
    db: Session = Depends(get_db),
):
    # Guarda um turno fechado. Se o mesmo turno for enviado de novo, SUBSTITUI (não duplica).
    _tamanho_ok(entrada.dados)
    turno = db.scalar(
        select(TurnoArquivado).where(
            TurnoArquivado.motoboy_id == motoboy.id, TurnoArquivado.turno_id == turno_id
        )
    )
    if turno is None:
        turno = TurnoArquivado(
            motoboy_id=motoboy.id, turno_id=turno_id, fechado_em=entrada.fechado_em, dados=entrada.dados
        )
        db.add(turno)
    else:
        turno.fechado_em = entrada.fechado_em
        turno.dados = entrada.dados
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflito ao salvar o turno. Tente de novo.")
    db.refresh(turno)
    return turno


@router.get("/turnos", response_model=list[TurnoResumo])
def listar_turnos(
    limite: Annotated[int, Query(ge=1, le=200)] = 50,
    motoboy: Motoboy = Depends(motoboy_atual),
    db: Session = Depends(get_db),
):
    # Lista os turnos fechados (só data e id), do mais recente para o mais antigo.
    consulta = (
        select(TurnoArquivado)
        .where(TurnoArquivado.motoboy_id == motoboy.id)
        .order_by(TurnoArquivado.fechado_em.desc())
        .limit(limite)
    )
    return db.scalars(consulta).all()


@router.get("/turnos/{turno_id}", response_model=TurnoDetalhe)
def ver_turno(
    turno_id: Annotated[str, Path(min_length=1, max_length=64)],
    motoboy: Motoboy = Depends(motoboy_atual),
    db: Session = Depends(get_db),
):
    turno = db.scalar(
        select(TurnoArquivado).where(
            TurnoArquivado.motoboy_id == motoboy.id, TurnoArquivado.turno_id == turno_id
        )
    )
    # Turno de OUTRO motoboy também cai aqui (404): não revelamos que ele existe.
    if turno is None:
        raise HTTPException(status_code=404, detail="Turno não encontrado")
    return turno


# ======================= CLIENTES (AUTOCOMPLETAR) =======================

@router.put("/clientes", response_model=ClientesSalvosSaida)
def salvar_clientes(
    entrada: ClientesEntrada,
    motoboy: Motoboy = Depends(motoboy_atual),
    db: Session = Depends(get_db),
):
    # Guarda clientes (nome + endereço). Se já existe o mesmo cliente, só soma 1 no uso.
    agora = datetime.now(timezone.utc)
    salvos = 0
    for c in entrada.clientes:
        nome_busca = normalizar(c.nome)
        endereco_busca = normalizar(c.endereco)
        if not nome_busca or not endereco_busca:
            continue  # ignora itens vazios

        existente = db.scalar(
            select(Cliente).where(
                Cliente.motoboy_id == motoboy.id,
                Cliente.nome_busca == nome_busca,
                Cliente.endereco_busca == endereco_busca,
            )
        )
        if existente:
            existente.usos += 1
            existente.ultimo_uso = agora
            existente.nome = c.nome.strip()            # fica com a grafia mais recente
            existente.endereco = c.endereco.strip()
            if c.bairro.strip():
                existente.bairro = c.bairro.strip()
        else:
            db.add(
                Cliente(
                    motoboy_id=motoboy.id,
                    nome=c.nome.strip(),
                    bairro=c.bairro.strip(),
                    endereco=c.endereco.strip(),
                    nome_busca=nome_busca,
                    endereco_busca=endereco_busca,
                    ultimo_uso=agora,
                )
            )
            # flush: manda o cliente novo ao banco já, para que o mesmo cliente repetido
            # mais adiante neste envio seja encontrado (a sessão não faz isso sozinha).
            db.flush()
        salvos += 1

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflito ao salvar clientes. Tente de novo.")
    return ClientesSalvosSaida(salvos=salvos)


@router.get("/clientes", response_model=list[ClienteSaida])
def buscar_clientes(
    q: Annotated[str, Query(max_length=100)] = "",
    limite: Annotated[int, Query(ge=1, le=20)] = 8,
    motoboy: Motoboy = Depends(motoboy_atual),
    db: Session = Depends(get_db),
):
    # Sugestões para o autocompletar. "q" é o que a pessoa digitou (nome OU endereço).
    consulta = select(Cliente).where(Cliente.motoboy_id == motoboy.id)
    q_limpo = normalizar(q)  # só letras, números e espaços: seguro para usar no LIKE
    if q_limpo:
        consulta = consulta.where(
            or_(
                Cliente.nome_busca.like(f"{q_limpo}%"),       # nome começa com o digitado
                Cliente.nome_busca.like(f"% {q_limpo}%"),     # ou alguma palavra do nome começa
                Cliente.endereco_busca.like(f"%{q_limpo}%"),  # ou o endereço contém o digitado
            )
        )
    # Mais usados primeiro; empate: usado mais recentemente.
    consulta = consulta.order_by(Cliente.usos.desc(), Cliente.ultimo_uso.desc()).limit(limite)
    return db.scalars(consulta).all()


@router.delete("/clientes/{cliente_id}", status_code=204)
def apagar_cliente(
    cliente_id: int,
    motoboy: Motoboy = Depends(motoboy_atual),
    db: Session = Depends(get_db),
):
    # Apaga um cliente salvo (por exemplo, um endereço digitado errado).
    cliente = db.scalar(
        select(Cliente).where(Cliente.id == cliente_id, Cliente.motoboy_id == motoboy.id)
    )
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    db.delete(cliente)
    db.commit()
    return Response(status_code=204)