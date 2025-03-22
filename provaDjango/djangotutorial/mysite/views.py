from django.http import HttpResponse

def index(request):
    return HttpResponse("Hello, world! Questa è la homepage.")