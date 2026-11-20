# textos.py — ajuda a comparar textos sem ligar para acento, maiúscula ou pontuação

import re
import unicodedata


def normalizar(texto: str) -> str:
    # Exemplos: "Letícia  Silva" -> "leticia silva"
    #           "Rua das Palmeiras, 45" -> "rua das palmeiras 45"
    # NFKD separa a letra do acento; depois jogamos fora só os acentos.
    sem_acento = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    # Tudo que não for letra ou número vira espaço; depois tiramos espaços das pontas.
    return re.sub(r"[^a-z0-9]+", " ", sem_acento.lower()).strip()