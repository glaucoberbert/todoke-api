# email_envio.py — envia e-mails pelo Brevo, usando a API por HTTPS
# (o Render grátis bloqueia o envio por SMTP, por isso não usamos SMTP).

import html
import logging
import os

import httpx

from codigos import VALIDADE_CODIGO

log = logging.getLogger(__name__)

# Ficam no Render (Environment), nunca no código.
BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
EMAIL_REMETENTE = os.environ.get("EMAIL_REMETENTE")
if not BREVO_API_KEY or not EMAIL_REMETENTE:
    raise RuntimeError("Faltam BREVO_API_KEY e/ou EMAIL_REMETENTE (veja o Render > Environment).")

URL_BREVO = "https://api.brevo.com/v3/smtp/email"


def enviar_codigo(destino: str, nome: str, codigo: str) -> bool:
    # Envia o código de confirmação. Devolve True se o Brevo aceitou, False se deu erro.
    minutos = int(VALIDADE_CODIGO.total_seconds() // 60)
    # html.escape: o nome vem do usuário, então "desarmamos" qualquer HTML dentro dele.
    nome_html = html.escape(nome)

    corpo = {
        "sender": {"name": "Todoke", "email": EMAIL_REMETENTE},
        "to": [{"email": destino, "name": nome}],
        "subject": "Seu código de confirmação do Todoke",
        "htmlContent": (
            f"<p>Olá, {nome_html}!</p>"
            "<p>Seu código de confirmação é:</p>"
            f'<p style="font-size:32px;font-weight:bold;letter-spacing:6px">{codigo}</p>'
            f"<p>Ele vale por {minutos} minutos. "
            "Se você não criou uma conta no Todoke, ignore este e-mail.</p>"
        ),
        "textContent": (
            f"Olá, {nome}! Seu código de confirmação do Todoke é {codigo}. "
            f"Ele vale por {minutos} minutos. Se você não criou uma conta, ignore este e-mail."
        ),
    }
    try:
        resposta = httpx.post(
            URL_BREVO,
            json=corpo,
            headers={"api-key": BREVO_API_KEY, "accept": "application/json"},
            timeout=10,  # desiste depois de 10 segundos
        )
        if resposta.status_code in (200, 201):
            return True
        # O motivo da recusa vai só para o log do Render.
        log.error("Brevo recusou o envio: %s %s", resposta.status_code, resposta.text)
    except httpx.HTTPError:
        log.exception("Erro de rede ao falar com o Brevo")
    return False