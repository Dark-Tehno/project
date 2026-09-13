from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, 'stlm/index.html')

def about(request):
    return render(request, 'stlm/about.html')

def albums(request):
    return render(request, 'stlm/albums.html')

def tour(request):
    return render(request, 'stlm/tour.html')

def merch(request):
    return render(request, 'stlm/merch.html')

def news(request):
    return render(request, 'stlm/news.html')