from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
)

async def send_user_email(email: str, password: str):
    message = MessageSchema(
        subject="Welcome to KnowledgeHub",
        recipients=[email],
        body=f"""
Hi,

Welcome to KnowledgeHub! Your account is ready.

Login Details:
URL: https://knowledgehub-reactjs.vercel.app/login
Email: {email}
Password: {password}

Please keep your credentials secure.

You can:
• Browse documents
• View clauses
• Search using tags

Note: Google Drive access is managed by Admin.

Regards,
Admin
""",
        subtype="plain"
    )

    fm = FastMail(conf)
    await fm.send_message(message)