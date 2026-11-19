# main.py — servidor do Todoke (Parte 1 do TCC)
# Etapa 1: servidor mínimo, só para provar que está no ar.

# FastAPI é o "framework": ele cuida de receber pedidos (requests)
# vindos do app e de devolver respostas.
from fastapi import FastAPI

# Cria o aplicativo. O título aparece na página automática /docs.
app = FastAPI(title="Todoke API", version="0.1.0")


# "@app.get('/')" quer dizer: quando alguém abrir o endereço raiz (/),
# rode a função logo abaixo.
@app.get("/")
def raiz():
    # O dicionário do Python vira JSON automaticamente.
    return {"mensagem": "Servidor do Todoke no ar"}


# Rota de "saúde" (health check): só responde "estou vivo".
# Serve para nós (e para o Render) saberem se o servidor subiu direito.
@app.get("/saude")
def saude():
    return {"status": "ok"}