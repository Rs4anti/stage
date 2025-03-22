from django.contrib import admin
from .models import Articolo, AtomicService

@admin.register(Articolo)
class ArticoloAdmin(admin.ModelAdmin):
    list_display = ("titolo", "contenuto")
    search_fields = ("titolo", "contenuto")

@admin.register(AtomicService)
class AtomicAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category")
    search_fields = ("id", "name", "category", "http_method")
