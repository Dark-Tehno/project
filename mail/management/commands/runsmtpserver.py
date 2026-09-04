import asyncio
from email.parser import BytesParser
from email.policy import default as default_policy
from email.utils import parseaddr, parsedate_to_datetime

from django.core.management.base import BaseCommand
from django.utils import timezone
from asgiref.sync import sync_to_async, async_to_sync
from channels.layers import get_channel_layer
from aiosmtpd.controller import Controller

from mail.models import TemporaryEmail, IncomingEmail

class DjangoSmtpHandler:
    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        """
        Проверяем существование получателя до приема тела письма.
        Это правильная практика, которая экономит ресурсы.
        """
        if not await self.email_exists(address):
            return '550 5.1.1 Recipient address rejected: User unknown'
        
        envelope.rcpt_tos.append(address)
        return '250 OK'

    async def handle_DATA(self, server, session, envelope):
        print(f"Получено сообщение от: {envelope.mail_from}")
        print(f"Получатели: {envelope.rcpt_tos}")

        await self.save_email(envelope)

        return '250 Message accepted for delivery'

    @sync_to_async
    def email_exists(self, address):
        return TemporaryEmail.objects.filter(email_address=address, expires_at__gt=timezone.now()).exists()

    @sync_to_async
    def save_email(self, envelope):
        msg = BytesParser(policy=default_policy).parsebytes(envelope.content)

        recipient_email = envelope.rcpt_tos[0]
        
        sender_name, sender_email = parseaddr(msg.get('From', ''))
        if not sender_email:
            sender_email = envelope.mail_from 

        subject = msg.get('Subject', '(без темы)')

        sent_at_str = msg.get('Date')
        sent_at = None
        if sent_at_str:
            try:
                sent_at = parsedate_to_datetime(sent_at_str)
            except Exception:
                print(f"Не удалось распознать дату: {sent_at_str}")

        body_plain = ''
        body_html = ''
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get('Content-Disposition'))
                if 'attachment' in cdispo:
                    continue
                
                charset = part.get_content_charset() or 'utf-8'
                payload = part.get_payload(decode=True)
                
                if ctype == 'text/plain' and not body_plain:
                    body_plain = payload.decode(charset, errors='replace')
                elif ctype == 'text/html' and not body_html:
                    body_html = payload.decode(charset, errors='replace')
        else:
            charset = msg.get_content_charset() or 'utf-8'
            payload = msg.get_payload(decode=True)
            if msg.get_content_type() == 'text/html':
                body_html = payload.decode(charset, errors='replace')
            else:
                body_plain = payload.decode(charset, errors='replace')

        try:
            temp_email = TemporaryEmail.objects.get(email_address=recipient_email)

            if temp_email.expires_at < timezone.now():
                print(f"Срок действия email {recipient_email} истек. Письмо проигнорировано.")
                return

            email = IncomingEmail.objects.create(
                temporary_email=temp_email,
                sender=sender_email,
                sender_name=sender_name or None,
                subject=subject,
                body=body_plain,
                html_body=body_html,
                sent_at=sent_at
            )
            print(f"Сохранено письмо от {sender_email} для {recipient_email}")

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"email_{temp_email.id}",
                {
                    "type": "email.message",
                    "message": {
                        'sender': email.sender,
                        'sender_name': email.sender_name,
                        'subject': email.subject,
                        'body': email.body,
                        'html_body': email.html_body,
                        'sent_at': email.sent_at.strftime('%Y-%m-%d %H:%M:%S') if email.sent_at else None,
                        'received_at': email.received_at.strftime('%Y-%m-%d %H:%M:%S'),
                    }
                }
            )
            print(f"Отправлено уведомление в группу email_{temp_email.id}")

        except TemporaryEmail.DoesNotExist:
            print(f"Временный email не найден: {recipient_email}")
        except Exception as e:
            print(f"Произошла ошибка: {e}")


class Command(BaseCommand):
    help = 'Запускает SMTP-сервер для получения временных email.'

    def handle(self, *args, **options):
        hostname = '0.0.0.0'
        port = 25
        self.stdout.write(self.style.SUCCESS(f'Запуск SMTP-сервера на {hostname}:{port}...'))
        controller = Controller(DjangoSmtpHandler(), hostname=hostname, port=port)
        
        try:
            controller.start()
            self.stdout.write(self.style.SUCCESS('SMTP-сервер запущен. Нажмите Ctrl+C для остановки.'))
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Остановка SMTP-сервера...'))
        finally:
            controller.stop()
            self.stdout.write(self.style.SUCCESS('SMTP-сервер остановлен.'))
