
import smtplib
import ssl

from email.message import EmailMessage

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict
)
from datetime import datetime
from decimal import Decimal


class EmailSettings(BaseSettings):
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


email_settings = EmailSettings()


def send_verification_email(
    recipient: str,
    otp: str
) -> None:

    message = EmailMessage()

    message["Subject"] = (
        "Library Lending System - Email Verification"
    )

    message["From"] = email_settings.SMTP_USER
    message["To"] = recipient

    message.set_content(
        f"Hello,\n\n"
        f"Your verification OTP is: {otp}\n\n"
        f"This OTP is valid for 10 minutes.\n\n"
        f"Do not share this code with anyone.\n\n"
        f"Library Lending System"
    )

    try:
        context = ssl.create_default_context()

        with smtplib.SMTP(
            email_settings.SMTP_HOST,
            email_settings.SMTP_PORT,
            timeout=20
        ) as server:

            server.ehlo()
            server.starttls(context=context)
            server.ehlo()

            server.login(
                email_settings.SMTP_USER,
                email_settings.SMTP_PASSWORD
            )

            server.send_message(message)

        print(
            "Verification email sent successfully."
        )

    except smtplib.SMTPAuthenticationError:
        print(
            "SMTP authentication failed. "
            "Check Gmail address and App Password."
        )
        raise

    except smtplib.SMTPException as error:
        print(
            f"SMTP error: {type(error).__name__}"
        )
        raise

    except OSError as error:
        print(
            f"SMTP connection error: {type(error).__name__}"
        )
        raise


def send_payment_receipt_email(
    recipient: str,
    member_name: str,
    member_id: str,
    payment_id: str,
    payment_method: str,
    amount: Decimal,
    paid_at: datetime
) -> None:

    message = EmailMessage()

    message["Subject"] = (
        "Library Membership Activated - Payment Receipt"
    )

    message["From"] = email_settings.SMTP_USER
    message["To"] = recipient

    receipt_number = f"REC-{payment_id[:8].upper()}"

    message.set_content(
        f"Hello {member_name},\n\n"
        f"Congratulations! Your library membership "
        f"has been activated successfully.\n\n"
        f"MEMBERSHIP DETAILS\n"
        f"------------------------------\n"
        f"Member ID: {member_id}\n"
        f"Name: {member_name}\n"
        f"Email: {recipient}\n\n"
        f"PAYMENT RECEIPT\n"
        f"------------------------------\n"
        f"Receipt Number: {receipt_number}\n"
        f"Payment ID: {payment_id}\n"
        f"Payment Method: {payment_method} (Demo)\n"
        f"Amount: INR {amount:.2f}\n"
        f"Payment Status: PAID\n"
        f"Payment Date: {paid_at.strftime('%d-%m-%Y %H:%M UTC')}\n\n"
        f"Note: This is a simulated payment. "
        f"No real money was collected.\n\n"
        f"You can now log in to the Library Lending System.\n\n"
        f"Thank you,\n"
        f"Library Lending System"
    )

    context = ssl.create_default_context()

    with smtplib.SMTP(
        email_settings.SMTP_HOST,
        email_settings.SMTP_PORT,
        timeout=20
    ) as server:

        server.ehlo()
        server.starttls(context=context)
        server.ehlo()

        server.login(
            email_settings.SMTP_USER,
            email_settings.SMTP_PASSWORD
        )

        server.send_message(message)
