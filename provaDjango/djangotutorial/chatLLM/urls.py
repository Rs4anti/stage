from django.urls import path

from . import views
from .views import index, chat_response

urlpatterns = [
    path("", index, name="index"),
    path("query/", chat_response, name="chat_response"),
]