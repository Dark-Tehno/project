from django.shortcuts import get_object_or_404, render

from .models import Participant, Music, Album, Concert, Merch, News

# Create your views here.
def index(request):
    return render(request, 'stlm/index.html')

def about(request):
    participants = Participant.objects.all()
    return render(request, 'stlm/about.html', {"participants": participants})

def albums(request):
    albums = Album.objects.prefetch_related('music').all()
    tracks = Music.objects.all()
    return render(request, 'stlm/albums.html', {'albums': albums, 'tracks': tracks})

def album_detail(request, album_id):
    album = get_object_or_404(Album.objects.prefetch_related('music'), pk=album_id)
    return render(request, 'stlm/album_detail.html', {'album': album})

def track_detail(request, track_id):
    track = get_object_or_404(Music, pk=track_id)
    albums = Album.objects.filter(music=track)
    return render(request, 'stlm/track_detail.html', {'track': track, 'albums': albums})

def tour(request):
    concerts = Concert.objects.all()
    return render(request, 'stlm/tour.html', {"concerts": concerts})

def merch(request):
    merchs = Merch.objects.all()
    return render(request, 'stlm/merch.html', {"merchs": merchs})

# def news(request):
#     return render(request, 'stlm/news.html')