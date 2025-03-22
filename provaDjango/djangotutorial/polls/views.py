from django.http import HttpResponse
from django.shortcuts import render, redirect
from polls.models import Articolo
from .forms import ArticoloForm

def lista_articoli(request):
    # Creare un nuovo articolo (solo una volta, altrimenti continua a crearne!)
    if not Articolo.objects.filter(titolo="Il mio primo post").exists():
        articolo = Articolo(titolo="Il mio primo post", contenuto="Ciao mondo!")
        articolo.save()

    # Recuperare tutti gli articoli
    articoli = Articolo.objects.all()
    
    return render(request, 'polls/lista_articoli.html', {'articoli': articoli})


def crea_articolo(request):
    if request.method == 'POST':
        form = ArticoloForm(request.POST)
        if form.is_valid():
            form.save()  # Salva l'articolo nel database MongoDB
            return redirect('lista_articoli')  # Sostituisci con l'URL a cui vuoi reindirizzare
    else:
        form = ArticoloForm()
    return render(request, 'polls/crea_articolo.html', {'form': form})


def index(request):
    return HttpResponse("Hello! Questa è la homepage dei polls.")