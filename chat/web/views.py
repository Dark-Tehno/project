from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from account.models import (
    DarkAccount,
    Version,
)


# def chat_web_index(request):
