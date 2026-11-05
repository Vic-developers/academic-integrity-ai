import secrets
import smtplib
from datetime import timedelta
from email.message import EmailMessage
from celery import Celery
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.config import settings
from app.db import engine
from app.models import EmailJob, ResetToken, User
from app.security import digest, now

celery = Celery("academic_integrity", broker=settings().redis_url)
celery.conf.update(
    worker_concurrency=1,
    task_ignore_result=True,
    task_serializer="json",
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "deliver-reset-email": {"task": "app.worker.deliver", "schedule": 5.0},
        "bibliography": {"task": "app.worker.bibliography", "schedule": 2.0, "options": {"expires": 5}},
        "literal-audits": {"task": "app.worker.literal_audits", "schedule": 2.0, "options": {"expires": 5}},
        "extract-documents": {"task": "app.worker.extract_documents", "schedule": 2.0, "options": {"expires": 5}},
    },
)


@celery.task(name="app.worker.deliver")
def deliver() -> int:
    count = 0
    # Database is the durable queue; SKIP LOCKED prevents duplicate concurrent deliveries.
    for _ in range(10):
        with Session(engine) as db, db.begin():
            candidate = db.execute(
                select(EmailJob.id, EmailJob.user_id)
                .where(EmailJob.state == "pending")
                .order_by(EmailJob.created_at)
                .limit(1)
            ).first()
            if candidate is None:
                break
            # Match the reset endpoint lock order: user first, then job.
            user = db.scalar(select(User).where(User.id == candidate.user_id).with_for_update())
            job = db.scalar(
                select(EmailJob)
                .where(EmailJob.id == candidate.id, EmailJob.state == "pending")
                .with_for_update(skip_locked=True)
                .execution_options(populate_existing=True)
            )
            if job is None:
                continue
            if user is None or not user.active:
                job.state = "cancelled"
                continue
            token = secrets.token_urlsafe(32)
            message = EmailMessage()
            message["Subject"] = "Recuperación de acceso — Academic Integrity AI"
            message["From"], message["To"] = settings().smtp_from, user.email
            message.set_content(
                "Solicitaste cambiar tu contraseña. Este enlace caduca en 30 minutos:\n"
                + settings().public_origin
                + "/restablecer#token="
                + token
                + "\nSi no lo solicitaste, ignora este mensaje."
            )
            job.attempts += 1
            try:
                with smtplib.SMTP(settings().smtp_host, settings().smtp_port, timeout=10) as smtp:
                    if settings().smtp_starttls:
                        import ssl

                        smtp.starttls(context=ssl.create_default_context())
                    if settings().smtp_username:
                        smtp.login(settings().smtp_username, settings().smtp_password)
                    smtp.send_message(message)
            except (OSError, smtplib.SMTPException):
                if job.attempts >= 3:
                    job.state = "failed"
                # Preserve bounded attempts; no provider error strings or addresses in logs.
                break
            db.execute(delete(ResetToken).where(ResetToken.user_id == user.id))
            db.add(ResetToken(id=digest(token), user_id=user.id, expires_at=now() + timedelta(minutes=30)))
            job.state = "sent"
            count += 1
    return count


@celery.task(name="app.worker.extract_documents")
def extract_documents() -> int:
    from app.documents.jobs import process_next

    return int(process_next())


@celery.task(name="app.worker.literal_audits")
def literal_audits() -> int:
    from app.audits.jobs import process_next

    return int(process_next())


@celery.task(name="app.worker.bibliography")
def bibliography() -> int:
    from app.bibliography.jobs import process_next

    return int(process_next())
