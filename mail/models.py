from django.db import models
from django.utils import timezone
from datetime import timedelta


def default_expires_at():
    return timezone.now() + timedelta(minutes=10)


class TemporaryEmail(models.Model):
    session_key = models.CharField(max_length=40, unique=True, db_index=True)
    email_address = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expires_at)

    def __str__(self):
        return self.email_address


class IncomingEmail(models.Model):
    temporary_email = models.ForeignKey(TemporaryEmail, on_delete=models.CASCADE, related_name='emails')
    sender = models.CharField(max_length=255)
    sender_name = models.CharField(max_length=255, blank=True, null=True)
    subject = models.CharField(max_length=255)
    body = models.TextField(blank=True, null=True) 
    html_body = models.TextField(blank=True, null=True) 
    received_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True) 

    def __str__(self):
        return f"From: {self.sender} | To: {self.temporary_email.email_address}"
