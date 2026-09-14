from django.shortcuts import render

from .models import Participant, Music, Album, Concert, Merch, News

# Create your views here.
def index(request):
    return render(request, 'stlm/index.html')

def about(request):
    participants = Participant.objects.all()
    return render(request, 'stlm/about.html', {"participants": participants})

def albums(request):
    return render(request, 'stlm/albums.html')

def tour(request):
    return render(request, 'stlm/tour.html')

def merch(request):
    return render(request, 'stlm/merch.html')

def news(request):
    return render(request, 'stlm/news.html')