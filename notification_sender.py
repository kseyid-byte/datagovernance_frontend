from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage

import server


DEFAULT_BATCH_SIZE = 25


def main() -> None:
    batch_size = int(os.getenv("GOVERNANCE_NOTIFICATION_BATCH_SIZE", str(DEFAULT_BATCH_SIZE)))
    dry_run = os.getenv("GOVERNANCE_EMAIL_DRY_RUN", "false").strip().lower() in {"1", "true", "yes"}
    with server.connect() as db:
        notifications = pending_notifications(db, batch_size)
        for notification in notifications:
            try:
                if dry_run:
                    print(f"[DRY RUN] Would send notification {notification['notification_id']} to {notification['recipient_email']}")
                else:
                    send_email(notification)
                mark_sent(db, notification["notification_id"])
                db.commit()
                print(f"Sent notification {notification['notification_id']} to {notification['recipient_email']}")
            except Exception as exc:  # noqa: BLE001 - sender must record provider failures without stopping the batch.
                db.rollback()
                with server.connect() as retry_db:
                    mark_failed(retry_db, notification["notification_id"], str(exc))
                    retry_db.commit()
                print(f"Failed notification {notification['notification_id']}: {exc}")


def pending_notifications(db: server.LakebaseConnection, batch_size: int) -> list[dict]:
    return list(
        db.execute(
            """
            SELECT notification_id, recipient_email, subject, body
            FROM notification_outbox
            WHERE status = 'pending'
            ORDER BY created_at
            LIMIT ?
            """,
            (batch_size,),
        ).fetchall()
    )


def send_email(notification: dict) -> None:
    smtp_host = os.getenv("GOVERNANCE_SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("GOVERNANCE_SMTP_PORT", "587"))
    smtp_user = os.getenv("GOVERNANCE_SMTP_USER", "").strip()
    smtp_password = os.getenv("GOVERNANCE_SMTP_PASSWORD", "").strip()
    sender = os.getenv("GOVERNANCE_EMAIL_FROM", smtp_user).strip()
    if not smtp_host or not sender:
        raise RuntimeError("GOVERNANCE_SMTP_HOST and GOVERNANCE_EMAIL_FROM or GOVERNANCE_SMTP_USER are required")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = notification["recipient_email"]
    message["Subject"] = notification["subject"]
    message.set_content(notification["body"])

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
        smtp.starttls(context=context)
        if smtp_user and smtp_password:
            smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)


def mark_sent(db: server.LakebaseConnection, notification_id: str) -> None:
    db.execute(
        """
        UPDATE notification_outbox
        SET status = 'sent',
            attempts = attempts + 1,
            sent_at = ?,
            last_error = NULL
        WHERE notification_id = ?
        """,
        (server.now(), notification_id),
    )


def mark_failed(db: server.LakebaseConnection, notification_id: str, error_message: str) -> None:
    db.execute(
        """
        UPDATE notification_outbox
        SET status = CASE WHEN attempts + 1 >= 5 THEN 'failed' ELSE 'pending' END,
            attempts = attempts + 1,
            last_error = ?
        WHERE notification_id = ?
        """,
        (error_message[:1000], notification_id),
    )


if __name__ == "__main__":
    main()
