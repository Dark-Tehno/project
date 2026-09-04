import uuid
from datetime import timedelta
from django.shortcuts import render
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import TemporaryEmail, IncomingEmail

def get_or_create_temp_email(request):
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    temp_email = TemporaryEmail.objects.filter(session_key=session_key).first()

    if temp_email and temp_email.expires_at < timezone.now():
        temp_email.delete()
        temp_email = None

    if not temp_email:
        email_username = str(uuid.uuid4())[:8]
        email_domain = "vsp210.ru"
        
        temp_email = TemporaryEmail.objects.create(
            session_key=session_key,
            email_address=f"{email_username}@{email_domain}",
            expires_at=timezone.now() + timedelta(minutes=10)
        )
    
    return temp_email

def temp_mail_view(request):
    temp_email = get_or_create_temp_email(request)
    emails = temp_email.emails.order_by('-received_at')
    return render(request, 'mail/inbox.html', {'temp_email': temp_email, 'emails': emails})

@csrf_exempt
@require_POST
def mail_webhook(request):
    sender = request.POST.get('from')
    recipient = request.POST.get('recipient')
    subject = request.POST.get('subject')
    body_plain = request.POST.get('body-plain', '')

    try:
        temp_email = TemporaryEmail.objects.get(email_address=recipient)
        if temp_email.expires_at < timezone.now():
            return HttpResponse("Email expired", status=406)

        email = IncomingEmail.objects.create(
            temporary_email=temp_email,
            sender=sender,
            subject=subject,
            body=body_plain
        )

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"email_{temp_email.id}",
            {
                "type": "email.message",
                "message": {
                    'sender': email.sender,
                    'subject': email.subject,
                    'body': email.body,
                    'received_at': email.received_at.strftime('%Y-%m-%d %H:%M:%S')
                }
            }
        )
        return HttpResponse("OK", status=200)
    except TemporaryEmail.DoesNotExist:
        return HttpResponse("User not found", status=404)

def extend_email_session(request):
    temp_email = get_or_create_temp_email(request)
    temp_email.expires_at = timezone.now() + timedelta(minutes=10)
    temp_email.save()
    return JsonResponse({'status': 'ok', 'expires_at': temp_email.expires_at.isoformat()})
