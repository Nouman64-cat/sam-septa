"""Post-scrape notification: upload Excel to S3 and email recipients via AWS SES SMTP."""

import logging
import os
import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def _get_recipients() -> list[str]:
    raw = os.getenv("RECIPIENT_EMAILS", "")
    return [e.strip() for e in raw.split(",") if e.strip()]


def _upload_to_s3(data: bytes, filename: str) -> str | None:
    """Upload Excel bytes to S3 under exports/<filename>; return the object URL or None."""
    import boto3

    bucket = os.getenv("AWS_S3_BUCKET_NAME")
    if not bucket:
        logger.warning("AWS_S3_BUCKET_NAME not set — skipping S3 upload")
        return None
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name           = os.getenv("AWS_REGION", "us-east-1"),
        )
        key = f"exports/{filename}"
        s3.put_object(
            Bucket      = bucket,
            Key         = key,
            Body        = data,
            ContentType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        url = f"https://{bucket}.s3.amazonaws.com/{key}"
        logger.info("S3 upload OK: %s", url)
        return url
    except Exception as exc:
        logger.error("S3 upload failed: %s", exc)
        return None


def _send_email(
    recipients: list[str],
    subject: str,
    body_html: str,
    attachment_data: bytes,
    filename: str,
) -> bool:
    """Send email with Excel attachment via AWS SES SMTP interface."""
    sender   = os.getenv("AWS_SES_FROM_EMAIL", "")
    username = os.getenv("AWS_SES_USERNAME", "")
    password = os.getenv("AWS_SES_PASSWORD", "")
    region   = os.getenv("AWS_REGION", "us-east-1")
    host     = f"email-smtp.{region}.amazonaws.com"
    port     = 587

    if not all([sender, username, password]):
        logger.warning("AWS SES SMTP credentials incomplete — skipping email notification")
        return False

    try:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"]    = sender
        msg["To"]      = ", ".join(recipients)

        msg.attach(MIMEText(body_html, "html"))

        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment_data)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(part)

        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls()
            server.login(username, password)
            server.sendmail(sender, recipients, msg.as_bytes())

        logger.info("Email sent via SES SMTP to %s", recipients)
        return True
    except Exception as exc:
        logger.error("SES SMTP email failed: %s", exc)
        return False


def _generate_excel(job_id: str, scraper_type: str) -> bytes | None:
    """Query the DB for the job's data, build a styled Excel, return raw bytes."""
    from utils.excel import styled_workbook
    from sqlmodel import Session, select
    from db import engine

    try:
        if scraper_type == "sam":
            from models import SamBid
            with Session(engine) as s:
                bids = s.exec(
                    select(SamBid)
                    .where(SamBid.job_id == job_id)
                    .order_by(SamBid.scraped_at.desc())
                ).all()
            headers = [
                "Notice Title", "Notice ID", "Decision", "Reason",
                "Department/Ind. Agency", "Description", "Subtier", "Updated Date",
                "Bid Repeat Count", "NAICS Code", "NAICS Title",
                "Date Offers Due", "Published Date", "Office",
            ]
            rows = [
                [
                    b.title, b.notice_id, b.decision or "PENDING", b.reason or "",
                    b.department, b.description, b.subtier, b.updated_date,
                    b.bid_repeat_count, b.naics_code, b.naics_title,
                    b.date_offers_due, b.published_date, b.office,
                ]
                for b in bids
            ]
            sheet_name = "SAM Bids"

        elif scraper_type == "septa":
            from models import SeptaQuote
            with Session(engine) as s:
                quotes = s.exec(
                    select(SeptaQuote)
                    .where(SeptaQuote.job_id == job_id)
                    .order_by(SeptaQuote.scraped_at.desc())
                ).all()
            headers = ["Requisition Number", "Summary", "Open Date", "Close Date"]
            rows = [
                [q.requisition_number, q.summary, q.open_date, q.close_date]
                for q in quotes
            ]
            sheet_name = "SEPTA Quotes"

        else:
            logger.warning("Unsupported scraper type '%s' — skipping Excel", scraper_type)
            return None

        stream = styled_workbook(sheet_name, headers, rows)
        return stream.read()

    except Exception as exc:
        logger.error("Excel generation failed for job %s: %s", job_id, exc)
        return None


def notify_job_completion(job_id: str, scraper_type: str, record_count: int) -> None:
    """Upload Excel to S3 and email recipients when a scrape job finishes successfully."""
    recipients = _get_recipients()
    if not recipients:
        logger.warning("RECIPIENT_EMAILS not configured — skipping notification")
        return

    _now     = datetime.now()
    _hr      = _now.strftime("%I").lstrip("0") or "12"
    ts       = _now.strftime(f"%Y-%m-%d, {_hr}:%M %p")
    filename = f"{scraper_type}_{ts}.xlsx"

    excel_bytes = _generate_excel(job_id, scraper_type)
    if not excel_bytes:
        logger.error("Aborting notification for job %s — Excel generation failed", job_id)
        return

    s3_url  = _upload_to_s3(excel_bytes, filename)
    s3_link = f'<a href="{s3_url}">Download from S3</a>' if s3_url else "<em>S3 upload unavailable</em>"

    subject   = f"{scraper_type.upper()} Scrape Complete — {record_count} records ({ts})"
    body_html = f"""\
<html><body>
<p>The <strong>{scraper_type.upper()}</strong> scraper has finished.</p>
<ul>
  <li><strong>Job ID:</strong> {job_id}</li>
  <li><strong>Records scraped:</strong> {record_count}</li>
  <li><strong>Completed at:</strong> {ts}</li>
</ul>
<p>The Excel report is attached to this email. {s3_link}</p>
</body></html>"""

    _send_email(recipients, subject, body_html, excel_bytes, filename)
