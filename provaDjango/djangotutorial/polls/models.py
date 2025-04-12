from django.db import models

class Articolo(models.Model):
    titolo = models.CharField(max_length=200)
    contenuto = models.TextField()
    data_pubblicazione = models.DateTimeField(auto_now_add=True)

    def __str__(self): #metodo che rappresenta l'oggetto come stringa
        return self.titolod
