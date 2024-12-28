import os, json, fitz, logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import emails  # type: ignore
import jwt
from jinja2 import Template
from jwt.exceptions import InvalidTokenError

from app.core.config import settings


@dataclass
class EmailData:
    html_content: str
    subject: str


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (
        Path(__file__).parent / "email-templates" / "build" / template_name
    ).read_text()
    html_content = Template(template_str).render(context)
    return html_content


def send_email(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    assert settings.emails_enabled, "no provided configuration for email variables"
    message = emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
    )
    smtp_options = {"host": settings.SMTP_HOST, "port": settings.SMTP_PORT}
    print("SMTP Username is: ", settings.SMTP_USER, "SMTP Password is: ", settings.SMTP_PASSWORD)
    if settings.SMTP_TLS:
        print("SMTP TLS is enabled")
        smtp_options["tls"] = True
    elif settings.SMTP_SSL:
        print("SMTP SSL is enabled")
        smtp_options["ssl"] = True
    if settings.SMTP_USER:
        print("SMTP User is enabled")
        smtp_options["user"] = settings.SMTP_USER
    if settings.SMTP_PASSWORD:
        print("SMTP Password is enabled")
        smtp_options["password"] = settings.SMTP_PASSWORD
    print("Email to is: ", email_to, "with ", smtp_options)
    response = message.send(to=email_to, smtp=smtp_options)
    print("Email response is: ", response)
    logging.info(f"send email result: {response}")


def generate_test_email(email_to: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Test email"
    html_content = render_email_template(
        template_name="test_email.html",
        context={"project_name": settings.PROJECT_NAME, "email": email_to},
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_reset_password_email(email_to: str, email: str, token: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Password recovery for user {email}"
    link = f"{settings.server_host}/reset-password?token={token}"
    html_content = render_email_template(
        template_name="reset_password.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_new_account_email(
    email_to: str, username: str, password: str
) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - New account for user {username}"
    html_content = render_email_template(
        template_name="new_account.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": username,
            "password": password,
            "email": email_to,
            "link": settings.server_host,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_invite_friend_email(
    email_to: str, username: str, inviter_name: str, deeplink: str
) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Invitation from {inviter_name}"
    html_content = render_email_template(
        template_name="invite_friend.mjml",
        context={
            "project_name": project_name,
            "username": username,
            "inviter_name": inviter_name,
            "deeplink": deeplink,
            "email": email_to,
        },
    )
    return EmailData(html_content=html_content, subject=subject)

def generate_password_reset_token(email: str) -> str:
    delta = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.now(timezone.utc)
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email},
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> str | None:
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return str(decoded_token["sub"])
    except InvalidTokenError:
        return None

class JSONProcessor:
    def __init__(self, data):
        self.data = data

    def to_json(self, output_file):
        entry = self.data
        transformed_entry = {
            "id": entry["id"],
            "text": entry["text"],
            "source": entry["source"],
            "metadata": {
                "title": entry["metadata"]["title"],
                "author": entry["metadata"]["author"]
            }
        }

        output_data = [transformed_entry]
        
        # Write the transformed data to a JSON file
        with open(output_file, 'w') as file:
            json.dump(output_data, file, indent=2)

import os
import fitz  # PyMuPDF library

class Parser:
    def __init__(self, file_path, title, author, source):
        self.file_path = file_path
        self.title = title
        self.author = author
        self.source = source
        self.pdf_data = self.read_pdf()

    def read_pdf(self):
        pdf_content = ''
        with fitz.open(self.file_path) as file:
            for page in file:
                pdf_content += page.get_text().strip()

        metadata = {
            'title': self.title,
            'author': self.author
        }

        return {
            'id': os.path.basename(self.file_path).split('.')[0],
            'text': pdf_content,
            'source': self.source,
            'metadata': metadata
        }