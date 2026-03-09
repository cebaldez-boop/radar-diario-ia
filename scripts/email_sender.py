"""
Radar Diário de IA - Módulo de Envio de E-mail
Envia o relatório diário por e-mail via SMTP.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


def send_report_email(
    html_content: str,
    markdown_content: str,
    target_date: Optional[str] = None,
) -> bool:
    """
    Envia o relatório diário por e-mail.

    Args:
        html_content: Relatório em HTML (corpo principal).
        markdown_content: Relatório em Markdown (versão texto).
        target_date: Data do relatório.

    Returns:
        True se enviado com sucesso, False caso contrário.
    """
    if target_date is None:
        target_date = date.today().isoformat()

    # Configurações de e-mail
    sender = os.environ.get("EMAIL_SENDER", "")
    password = os.environ.get("EMAIL_PASSWORD", "")
    recipient = os.environ.get("EMAIL_RECIPIENT", "cebaldez@gmail.com")
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    if not sender or not password:
        logger.error("Credenciais de e-mail não configuradas (EMAIL_SENDER, EMAIL_PASSWORD)")
        return False

    try:
        # Criar mensagem
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"📡 Radar Diário de IA — {target_date}"
        msg["From"] = sender
        msg["To"] = recipient

        # Versão texto (Markdown)
        text_part = MIMEText(markdown_content, "plain", "utf-8")
        msg.attach(text_part)

        # Versão HTML
        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)

        # Enviar
        logger.info(f"Enviando relatório por e-mail para {recipient}...")

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)

        logger.info(f"Relatório enviado com sucesso para {recipient}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "Falha na autenticação SMTP. Verifique EMAIL_SENDER e EMAIL_PASSWORD. "
            "Para Gmail, use uma 'Senha de App': https://myaccount.google.com/apppasswords"
        )
        return False
    except Exception as e:
        logger.error(f"Erro ao enviar e-mail: {e}")
        return False
