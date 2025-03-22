from django import forms
from .models import Articolo

class ArticoloForm(forms.ModelForm):
    class Meta:
        model = Articolo
        fields = ['titolo', 'contenuto']  # I campi che vuoi includere nel form
