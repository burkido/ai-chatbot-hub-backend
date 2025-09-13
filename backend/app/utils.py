import os, json, fitz, logging, jwt
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypedDict, List, Dict
from jinja2 import Template
from jwt.exceptions import InvalidTokenError

from app.core.config import settings
from app.core.i18n import get_translation, DEFAULT_LANGUAGE

import mailtrap as mt

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
    project_name: str = settings.PROJECT_NAME,
) -> None:
    assert settings.emails_enabled, "no provided configuration for email variables"
    
    try:
        # Create mail object using Mailtrap SDK
        mail = mt.Mail(
            sender=mt.Address(
                email=settings.EMAILS_FROM_EMAIL,
                name=project_name
            ),
            to=[mt.Address(email=email_to)],
            subject=subject,
            category="Application Email"
        )
        
        # Set content (HTML or text)
        if html_content:
            mail.html = html_content
        else:
            mail.text = "Email content not provided"
        
        # Create client and send email
        client = mt.MailtrapClient(token=settings.MAILTRAP_API_TOKEN)
        response = client.send(mail)
        
        # Log the response
        logging.info(f"Email sent successfully: {response}")
        print(f"Email sent successfully to {email_to}: {response}")
        
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")
        print(f"Failed to send email: {str(e)}")
        raise

def generate_test_email(email_to: str, deeplink: str, project_name: str, language: str = DEFAULT_LANGUAGE) -> EmailData:
    subject = get_translation("test_email_subject", language, project_name=project_name)
    html_content = render_email_template(
        template_name="test_email.html",
        context={"project_name": project_name, "email": email_to, "deeplink": deeplink},
    )
    return EmailData(html_content=html_content, subject=subject)

def generate_reset_password_email(email_to: str, email: str, token: str, deeplink: str, project_name: str, language: str = DEFAULT_LANGUAGE) -> EmailData:
    subject = get_translation("password_recovery_subject", language, project_name=project_name, email=email)
    html_content = render_email_template(
        template_name="reset_password.html",
        context={
            "project_name": project_name,
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": deeplink,
        },
    )
    return EmailData(html_content=html_content, subject=subject)

def generate_new_account_email(
    email_to: str, username: str, password: str, deeplink: str, project_name: str, language: str = DEFAULT_LANGUAGE
) -> EmailData:
    subject = get_translation("new_account_subject", language, project_name=project_name, username=username)
    html_content = render_email_template(
        template_name="new_account.html",
        context={
            "project_name": project_name,
            "username": username,
            "password": password,
            "email": email_to,
            "link": deeplink,
        },
    )
    return EmailData(html_content=html_content, subject=subject)

def generate_invite_friend_email(
    email_to: str, username: str, inviter_name: str, deeplink: str, project_name: str, language: str = DEFAULT_LANGUAGE
) -> EmailData:
    subject = get_translation("invitation_subject", language, project_name=project_name, inviter_name=inviter_name)
    html_content = render_email_template(
        template_name="invite_friend.html",
        context={
            "project_name": project_name,
            "username": username,
            "inviter_name": inviter_name,
            "deeplink": deeplink,
            "email": email_to,
        },
    )
    return EmailData(html_content=html_content, subject=subject)

def generate_email_verification_otp(email_to: str, otp: str, deeplink: str, project_name: str, language: str = DEFAULT_LANGUAGE) -> EmailData:
    subject = get_translation("email_verification_subject", language, project_name=project_name)
    html_content = render_email_template(
        template_name="verify_user.html",
        context={
            "project_name": project_name,
            "email": email_to,
            "verification_code": otp,
            "valid_minutes": 10,
            "verification_url": deeplink,
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

class PDFMetadata(TypedDict):
    title: str
    author: str

class PDFData(TypedDict):
    id: str
    text: str
    source: str
    metadata: PDFMetadata

class TxtData(TypedDict):
    id: str
    text: str
    source: str
    metadata: PDFMetadata

class JsonlData(TypedDict):
    id: str
    items: List[Dict[str, Any]]
    source: str
    metadata: PDFMetadata

class Parser:
    def __init__(self, file_path: str, title: str, author: str, source: str) -> None:
        self.file_path = file_path
        self.title = title
        self.author = author
        self.source = source
        self.pdf_data = self.read_pdf()

    def read_pdf(self) -> PDFData:
        pdf_content = ''
        with fitz.open(self.file_path) as file:
            for page in file:
                pdf_content += page.get_text().strip()

        metadata: PDFMetadata = {
            'title': self.title,
            'author': self.author
        }

        return {
            'id': os.path.basename(self.file_path).split('.')[0],
            'text': pdf_content,
            'source': self.source,
            'metadata': metadata
        }

class TxtParser:
    def __init__(self, file_path: str, title: str, author: str, source: str) -> None:
        self.file_path = file_path
        self.title = title
        self.author = author
        self.source = source
        self.txt_data = self.read_txt()

    def read_txt(self) -> TxtData:
        """Read a text file and return structured data"""
        with open(self.file_path, 'r', encoding='utf-8') as file:
            txt_content = file.read().strip()

        metadata: PDFMetadata = {
            'title': self.title,
            'author': self.author
        }

        return {
            'id': os.path.basename(self.file_path).split('.')[0],
            'text': txt_content,
            'source': self.source,
            'metadata': metadata
        }

class JsonlParser:
    def __init__(self, file_path: str, title: str, author: str, source: str) -> None:
        self.file_path = file_path
        self.title = title
        self.author = author
        self.source = source
        self.jsonl_data = self.read_jsonl()

    def read_jsonl(self) -> JsonlData:
        """Read a JSONL file and return structured data"""
        items = []
        with open(self.file_path, 'r', encoding='utf-8') as file:
            for line in file:
                try:
                    item = json.loads(line.strip())
                    items.append(item)
                except json.JSONDecodeError:
                    # Skip invalid JSON lines
                    continue

        metadata: PDFMetadata = {
            'title': self.title,
            'author': self.author
        }

        return {
            'id': os.path.basename(self.file_path).split('.')[0],
            'items': items,
            'source': self.source,
            'metadata': metadata
        }

def prefix_email_with_package(email: str, package_name: str) -> str:
    """
    Prefixes an email with the application package name.
    Example: prefix_email_with_package("user@example.com", "com.app.test") -> "com.app.test+user@example.com"
    """
    username, domain = email.split("@")
    return f"{package_name}+{username}@{domain}"

def extract_real_email(prefixed_email: str) -> str:
    """
    Extracts the real email from a prefixed email.
    Example: extract_real_email("com.app.test+user@example.com") -> "user@example.com"
    """
    if "+" not in prefixed_email:
        return prefixed_email
        
    parts = prefixed_email.split("+", 1)
    if len(parts) != 2:
        return prefixed_email
        
    return parts[1]