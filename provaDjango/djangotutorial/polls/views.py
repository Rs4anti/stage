from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.utils.timezone import now
from polls.forms import ArticoloForm
from django.conf import settings
from polls.mongodb import db

def lista_articoli(request):
    # Controlla se esiste già l'articolo
    if not db.articoli.find_one({"titolo": "Il mio primo post"}):
        articolo = {
            "titolo": "Il mio primo post",
            "contenuto": "Ciao mondo!",
            "created_at": now()
        }
        db.articoli.insert_one(articolo)

    # Recupera tutti gli articoli
    articoli = list(db.articoli.find())
    
    return render(request, 'polls/lista_articoli.html', {'articoli': articoli})

def crea_articolo(request):
    if request.method == 'POST':
        form = ArticoloForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            db.articoli.insert_one({
                "titolo": data["titolo"],
                "contenuto": data["contenuto"],
                "created_at": now()
            })
            return redirect('lista_articoli')
    else:
        form = ArticoloForm()
    return render(request, 'polls/crea_articolo.html', {'form': form})

def atomic_service(request):
    if request.method == "GET":
        if db.atomic_services.count_documents({}) == 0:
            owner = {
                "actor_id": "actor_001",
                "name": "Production Leader"
            }
            db.owners.insert_one(owner)

            service = {
                "id": "001",
                "name": "ReceiveSalesOrderData",
                "category": "collect",
                "owner": owner,
                "http_method": "POST",
                "endpoint": "/sales-orders",
                "input_data": {"customer_id": "integer", "product_id": "integer", "quantity": "integer"},
                "output_data": {"order_id": "integer", "status": "string"},
                "security": {"authentication": "OAuth2", "rbac_role": ["ProductionLeader"]},
                "created_at": now(),
                "updated_at": now()
            }
            db.atomic_services.insert_one(service)

        services = list(db.atomic_services.find())

        return render(request, 'polls/atomic_service_list.html', {'services': services})
