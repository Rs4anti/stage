from django.http import HttpResponse, JsonResponse
from langchain_community.llms import Ollama

def index(request):
    return HttpResponse("Hello, world! Questa è la pagina per chattare con un LLM.")


# Inizializza Ollama con un modello locale
llm = Ollama(model="mistral")

def chat_response(request):
    #Risponde a una query usando Ollama in locale con LangChain

    #http://127.0.0.1:8000/chatLLM/query/?query=Chi%20ha%20scoperto%20l%27America%3F
    user_query = request.GET.get("query", "")

    if not user_query:
        return JsonResponse({"error": "Nessuna query fornita"}, status=400)

    # Risposta con LangChain
    response = llm.invoke(user_query)

    return JsonResponse({"response": response})
