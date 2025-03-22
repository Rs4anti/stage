from django.db import models

class Articolo(models.Model):
    titolo = models.CharField(max_length=200)
    contenuto = models.TextField()
    data_pubblicazione = models.DateTimeField(auto_now_add=True)

    def __str__(self): #metodo che rappresenta l'oggetto come stringa
        return self.titolo


class Articolo_esteso(models.Model):
    titolo = models.CharField(max_length=200)
    contenuto = models.TextField()
    data_pubblicazione = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titolo


class Owner(models.Model):
    actor_id = models.CharField(max_length=50)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class AtomicService(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, default="atomic")  # Valore fisso "atomic"
    category = models.CharField(max_length=50)  # collect, process, dispatch, display
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE)

    http_method = models.CharField(max_length=10)  # POST, GET, PUT, DELETE
    endpoint = models.CharField(max_length=255)

    input_data = models.JSONField()  # Salva il dizionario di input
    output_data = models.JSONField()  # Salva il dizionario di output

    properties = models.JSONField(blank=True, null=True)  # Proprietà personalizzate
    security = models.JSONField()  # Autenticazione e RBAC

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    def __str__(self):
        return self.name
