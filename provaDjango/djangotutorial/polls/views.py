from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from polls.models import Articolo, AtomicService, Owner
from .forms import ArticoloForm
from django.utils.timezone import now

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

def atomic_service(request):
    if request.method == "GET":
        if not AtomicService.objects.exists():
            owner, _ = Owner.objects.get_or_create(actor_id="actor_001", name="Production Leader")

            AtomicService.objects.create(
                id="001",
                name="ReceiveSalesOrderData",
                category="collect",
                owner=owner,
                http_method="POST",
                endpoint="/sales-orders",
                input_data={"customer_id": "integer", "product_id": "integer", "quantity": "integer"},
                output_data={"order_id": "integer", "status": "string"},
                security={"authentication": "OAuth2", "rbac_role": ["ProductionLeader"]},
                created_at=now(),
                updated_at=now()
            )

        services = AtomicService.objects.all()

        return render(request, 'polls/atomic_service_list.html', {'services': services})
