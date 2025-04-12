from django.shortcuts import render

def data_view_editor(request):
    return render(request, 'editor/view.html')