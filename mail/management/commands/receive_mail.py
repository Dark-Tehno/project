import sys

from email.parser import BytesParser
from email.policy import default as default_policy
from email.utils import parseaddr, parsedate_to_datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from mail.models import TemporaryEmail, IncomingEmail


class Command(BaseCommand):
    help = "Получение входящего письма от Postfix"

    def handle(self, *args, **options):

        if len(sys.argv) < 3:
            self.stderr.write("Recipient not specified")
            sys.exit(75)

        recipient_email = sys.argv[2].lower()

        try:
            temp_email = TemporaryEmail.objects.get(
                email_address=recipient_email
            )
        except TemporaryEmail.DoesNotExist:
            self.stderr.write(f"Unknown recipient: {recipient_email}")
            sys.exit(75)

        if (
            temp_email.expires_at
            and temp_email.expires_at < timezone.now()
        ):
            self.stderr.write(f"Expired mailbox: {recipient_email}")
            sys.exit(75)

        raw_email = sys.stdin.buffer.read()

        if not raw_email:
            self.stderr.write("Empty message")
            sys.exit(75)

        msg = BytesParser(policy=default_policy).parsebytes(raw_email)

        sender_name, sender_email = parseaddr(msg.get("From", ""))

        subject = msg.get("Subject", "(без темы)")

        sent_at = None
        date_header = msg.get("Date")

        if date_header:
            try:
                sent_at = parsedate_to_datetime(date_header)
            except Exception:
                pass

        body_plain = ""
        body_html = ""

        if msg.is_multipart():

            for part in msg.walk():

                disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in disposition:
                    continue

                content_type = part.get_content_type()

                payload = part.get_payload(decode=True)

                if payload is None:
                    continue

                charset = part.get_content_charset() or "utf-8"

                try:
                    text = payload.decode(charset, errors="replace")
                except Exception:
                    text = payload.decode("utf-8", errors="replace")

                if content_type == "text/plain" and not body_plain:
                    body_plain = text

                elif content_type == "text/html" and not body_html:
                    body_html = text

        else:

            payload = msg.get_payload(decode=True)

            if payload:

                charset = msg.get_content_charset() or "utf-8"

                try:
                    text = payload.decode(charset, errors="replace")
                except Exception:
                    text = payload.decode("utf-8", errors="replace")

                if msg.get_content_type() == "text/html":
                    body_html = text
                else:
                    body_plain = text

        email = IncomingEmail.objects.create(
            temporary_email=temp_email,
            sender=sender_email,
            sender_name=sender_name or None,
            subject=subject,
            body=body_plain,
            html_body=body_html,
            sent_at=sent_at,
        )

        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            f"email_{temp_email.id}",
            {
                "type": "email.message",
                "message": {
                    "sender": email.sender,
                    "sender_name": email.sender_name,
                    "subject": email.subject,
                    "body": email.body,
                    "html_body": email.html_body,
                    "sent_at": (
                        email.sent_at.strftime("%Y-%m-%d %H:%M:%S")
                        if email.sent_at
                        else None
                    ),
                    "received_at": email.received_at.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                },
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Email saved for {recipient_email}"
            )
        )

        sys.exit(0)