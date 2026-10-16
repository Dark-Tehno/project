import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from account.models import (
    DarkAccount,
    Version,
)


def chat_web_versions(request):
    return render(request, "chat/versions.html")

def chat_web_release(request):
    return render(request, "chat/release.html")

def data_js(request):
    versions = Version.objects.all()
    platforms = {
        "windows": "Dark.Talk Windows",
        "linux": "Dark.Talk Linux",
        "macos": "Dark.Talk macOS",
        "android": "Dark.Talk Android",
        "ios": "Dark.Talk iOS",
        "web": "Dark.Talk Web",
    }
    version_data = [
        {
            "id": version.id,
            "application": version.application,
            "version": version.version,
            "image": version.image.url,
            "description": version.description,
            "file": version.file.url,
        }
        for version in versions
    ]
    data = (
        f"window.PLATFORMS = {json.dumps(platforms)};\n"
        f"window.VERSIONS = {json.dumps(version_data)};"
    )
    return HttpResponse(data, content_type="application/javascript")