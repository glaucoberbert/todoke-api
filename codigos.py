# codigos.py — gera e confere o código de 6 dígitos enviado por e-mail

import hashlib
import hmac
import secrets
from datetime import timedelta

from seguranca import SECRET_KEY

VALIDADE_CODIGO = timedelta(minutes=15)    # tempo que o código vale
MAX_TENTATIVAS_CODIGO = 5                  # erros permitidos por código
INTERVALO_REENVIO = timedelta(seconds=60)  # espera mínima entre dois envios


def gerar_codigo() -> str:
    # "secrets" gera números aleatórios seguros (o "random" comum é previsível).
    # :06d completa com zeros à esquerda, por exemplo 000042.
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_codigo(codigo: str) -> str:
    # Embaralha o código com a chave secreta (HMAC-SHA256).
    # No banco fica só o resultado, nunca o código de verdade.
    return hmac.new(SECRET_KEY.encode(), codigo.encode(), hashlib.sha256).hexdigest()


def codigo_confere(codigo_digitado: str, hash_guardado: str) -> bool:
    # compare_digest compara sem vazar informação pelo tempo que leva.
    return hmac.compare_digest(hash_codigo(codigo_digitado), hash_guardado)