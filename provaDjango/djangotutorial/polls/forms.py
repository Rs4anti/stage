from django import forms
from .models import Articolo

class ArticoloForm(forms.ModelForm):
    class Meta:
        model = Articolo
        fields = ['titolo', 'contenuto']  #Campi che voglio includere nella form
